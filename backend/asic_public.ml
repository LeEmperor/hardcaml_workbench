open! Core
open Hardcaml_workbench_protocol

let require ok message = if not ok then failwith message

let field name = function
  | `Assoc fields ->
    Option.value (List.Assoc.find fields name ~equal:String.equal) ~default:`Null
  | _ -> `Null
;;

let text = function
  | `String s -> s
  | _ -> failwith "Expected JSON string"
;;

let integer = function
  | `Int n -> n
  | _ -> failwith "Expected JSON integer"
;;

let list = function
  | `List xs -> xs
  | _ -> failwith "Expected JSON array"
;;

let optional_text = function
  | `Null -> None
  | j -> Some (text j)
;;

let absolute s =
  require (Filename.is_absolute s) "Expected absolute public reference";
  s
;;

let decode text =
  let j = Yojson.Safe.from_string text in
  let rec check = function
    | `Assoc xs ->
      require
        (List.length xs
         = List.length (List.dedup_and_sort (List.map xs ~f:fst) ~compare:String.compare)
        )
        "Duplicate JSON key";
      List.iter xs ~f:(fun (_, j) -> check j)
    | `List xs -> List.iter xs ~f:check
    | `Float f -> require (Float.is_finite f) "Nonfinite JSON"
    | `Tuple _ | `Variant _ -> failwith "Nonstandard JSON"
    | _ -> ()
  in
  check j;
  j
;;

let envelope j contract version =
  require
    (String.equal (text (field "contract" j)) contract
     && integer (field "schema_version" j) = version)
    ("Unsupported public envelope: " ^ contract);
  j
;;

let metadata j =
  let c = field "cli_contract" j in
  require
    (integer (field "version" c) = 4
     && Poly.equal (field "namedflow1" (field "capabilities" c)) (`Bool true))
    "Installed provider requires exact CLI4 + namedflow1=true"
;;

let flows j =
  let j = envelope j "hardcaml-asic.flow-list" 1 in
  let catalog = envelope (field "declaration" j) "hardcaml-asic.flow-catalog" 1 in
  list (field "entries" catalog)
  |> List.map ~f:(fun e ->
    { Asic.Flow.id = text (field "id" (field "methodology" e))
    ; profiles = List.map (list (field "profiles" e)) ~f:(fun p -> text (field "id" p))
    ; default_profile = text (field "default_profile" e)
    })
;;

let preview selection j : Asic.Preview.t =
  let j = envelope j "hardcaml-asic.methodology-plan" 1 in
  let plan_identity = text (field "plan_identity" j) in
  require
    (String.length plan_identity = 64
     && String.for_all plan_identity ~f:(function
       | '0' .. '9' | 'a' .. 'f' -> true
       | _ -> false))
    "Invalid plan identity";
  { selection; plan_identity; plan_json = Yojson.Safe.to_string j }
;;

let allocation j : Asic.Reference.t =
  let j = envelope j "hardcaml-asic.stage-observation" 1 in
  require
    (String.equal (text (field "event" j)) "observation_allocated")
    "Expected early allocation";
  let stream_id = text (field "stream_id" j) in
  require (not (String.is_empty stream_id)) "Empty stream identity";
  { attempt = absolute (text (field "attempt" j)); stream_id }
;;

let execution_summary (r : Asic.Run.t) (preview : Asic.Preview.t) j =
  require
    (Poly.equal (field "contract" j) `Null && Poly.equal (field "schema_version" j) `Null)
    "Unsupported launcher record";
  require
    (String.equal (text (field "attempt_id" j)) r.reference.stream_id)
    "Launcher execution identity mismatch";
  require
    (List.mem
       [ "completed"; "failed"; "interrupted" ]
       (text (field "status" j))
       ~equal:String.equal)
    "Invalid execution status";
  ignore (integer (field "exit_code" j) : int);
  ignore (list (field "occurrences" j) : Yojson.Safe.t list);
  let plan = field "plan" j in
  require (integer (field "schema_version" plan) = 3) "Unsupported execution stage plan";
  ignore (list (field "stages" plan) : Yojson.Safe.t list);
  let reference =
    envelope (field "methodology" j) "hardcaml-asic.methodology-execution-reference" 1
  in
  require
    (Poly.equal (field "attempt_id" reference) (`String r.reference.stream_id)
     && Poly.equal (field "plan_identity" reference) (`String preview.plan_identity)
     && Poly.equal
          (field "expected_plan_identity" reference)
          (`String preview.plan_identity))
    "Launcher methodology identity mismatch";
  ignore (absolute (text (field "snapshot_path" reference)) : string)
;;

let updates (r : Asic.Run.t) j =
  let j = envelope j "hardcaml-asic.stage-observation" 2 in
  require
    (String.equal (text (field "stream_id" j)) r.reference.stream_id
     && integer (field "after" j) = r.cursor)
    "Update identity mismatch";
  let cursor = integer (field "cursor" j) in
  require (cursor >= r.cursor) "Regressed update cursor";
  ignore
    (List.fold
       (list (field "events" j))
       ~init:r.cursor
       ~f:(fun previous e ->
         let e = envelope e "hardcaml-asic.stage-observation" 2 in
         let sequence = integer (field "sequence" e) in
         require
           (String.equal (text (field "stream_id" e)) r.reference.stream_id
            && sequence > previous
            && sequence <= cursor)
           "Invalid observation sequence";
         sequence)
     : int);
  cursor
;;

let inspection (r : Asic.Run.t) ~cursor j =
  let j = envelope j "hardcaml-asic.stage-observation" 2 in
  require
    (String.equal (text (field "stream_id" j)) r.reference.stream_id
     && integer (field "cursor" j) >= cursor)
    "Inspection identity/cursor mismatch";
  let writer_active =
    match field "writer_active" j with
    | `Bool b -> b
    | _ -> failwith "Missing writer status"
  in
  let outcome = field "outcome" (field "state" j) in
  let final =
    Poly.equal (field "observation_status" j) (`String "final")
    && (not writer_active)
    && (not (Poly.equal outcome `Null))
    && integer (field "cursor" j) = cursor
  in
  let status = if final then text (field "status" outcome) else "observing" in
  let execution_file =
    Option.map (optional_text (field "execution_file" j)) ~f:absolute
  in
  { r with cursor; status; execution_file; error = None }, final
;;

let digest text =
  Cryptokit.hash_string (Cryptokit.Hash.sha256 ()) text
  |> Cryptokit.transform_string (Cryptokit.Hexa.encode ())
;;

let count = function
  | `Int n when n >= 0 -> Some n
  | `Float f
    when Float.is_finite f
         && Float.(f >= 0. && f < of_int Int.max_value)
         && Float.equal (Float.round_down f) f -> Some (Float.to_int f)
  | _ -> None
;;

let summary (r : Asic.Run.t) ~expected_plan ~execution_file j : Asic.Summary.t =
  let j = envelope j "hardcaml-asic.report" 1 in
  require
    (String.equal (text (field "attempt_id" (field "execution" j))) r.reference.stream_id)
    "Report execution identity mismatch";
  let methodology =
    envelope (field "methodology" j) "hardcaml-asic.historical-methodology" 1
  in
  require
    (Poly.equal (field "state" methodology) (`String "recorded")
     && String.equal
          (text (field "attempt_id" (field "reference" methodology)))
          r.reference.stream_id)
    "Report methodology identity mismatch";
  let plan_identity = optional_text (field "plan_identity" methodology) in
  Option.iter expected_plan ~f:(fun p ->
    require (Option.equal String.equal plan_identity (Some p)) "Report plan mismatch");
  let checkpoints = list (field "checkpoints" j) in
  let checkpoint = List.last checkpoints in
  let metrics =
    Option.value_map checkpoint ~default:[] ~f:(fun c -> list (field "metrics" c))
  in
  let cell_count =
    List.find_map metrics ~f:(fun m ->
      if Poly.equal (field "raw_key" m) (`String "design__instance__count")
         && Poly.equal (field "availability" m) (`String "available")
      then count (field "value" m)
      else None)
  in
  let cells =
    Option.value_map checkpoint ~default:[] ~f:(fun c ->
      (match field "supplementary" c with
       | `Null -> []
       | j -> list j)
      |> List.concat_map ~f:(fun s ->
        match field "mapped_cell_types" s with
        | `Assoc xs ->
          List.filter_map xs ~f:(fun (name, n) ->
            Option.map (count n) ~f:(fun n -> name, n))
        | _ -> []))
  in
  require (List.length cells <= 4096) "Cell summary exceeds normalized budget";
  { run = r.run
  ; source_digest = digest (Yojson.Safe.to_string j)
  ; execution_file
  ; plan_identity
  ; cell_count
  ; cells
  ; timing = [] (* CLI4 has no normalized timing attribution/units contract. *)
  ; completion = text (field "status" (field "execution" j))
  ; acceptance = text (field "acceptance" j)
  ; producer =
      Option.value_map checkpoint ~default:"no checkpoint" ~f:(fun c ->
        Yojson.Safe.to_string
          (`Assoc
            [ "reference", field "reference" c; "metric_origin", field "metric_origin" c ]))
  ; observed_at = Time_float.to_string (Time_float.now ())
  ; freshness = Validated
  }
;;
