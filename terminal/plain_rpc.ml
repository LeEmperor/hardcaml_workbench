open! Core
open Hardcaml_workbench_protocol

(** These are the daemon's machine operation identifiers/states, not log messages or
    provider execution-status prose. Query completion is not run completion. *)
let active (operation : Asic.Pending.t) =
  String.equal operation.state "pending" || String.equal operation.state "executing"
;;

let digest text =
  Cryptokit.hash_string (Cryptokit.Hash.sha256 ()) text
  |> Cryptokit.transform_string (Cryptokit.Hexa.encode ())
;;

let keys (operation : Asic.Operation.t) (snapshot : Asic.Snapshot.t) =
  match operation with
  | Get -> List.filter snapshot.operations ~f:active |> List.map ~f:(fun op -> op.key)
  | Discover -> [ "discover" ]
  | Describe flow -> [ "describe:" ^ flow ]
  | Plan selection ->
    [ "plan:" ^ digest (Sexp.to_string_mach (Asic.Selection.sexp_of_t selection)) ]
  | Run { key; _ } -> [ "run:" ^ key ]
  | Register _ -> []
  | Observe run ->
    let key = "observe:" ^ run.id in
    (* The service coalesces Observe with an already running automatic observer. Automatic
       observers carry [run]; their lifetime is the physical execution, not a one-shot
       query. Return their current snapshot instead of waiting for that entire execution.
       One-shot reads have no Pending.run and are awaited. *)
    if List.exists snapshot.operations ~f:(fun op ->
         String.equal op.key key && active op && Option.is_some op.run)
    then []
    else [ key ]
  | Load_summary run -> [ "summary:" ^ run.id ]
  | Refresh run -> [ "refresh:" ^ run.id ]
  | Cancel key ->
    [ (if List.exists snapshot.operations ~f:(fun op -> String.equal op.key key)
       then key
       else "run:" ^ key)
    ]
;;

let watched_keys operation keys (snapshot : Asic.Snapshot.t) =
  match (operation : Asic.Operation.t) with
  | Run _ ->
    keys
    @ List.concat_map snapshot.operations ~f:(fun op ->
      if List.mem keys op.key ~equal:String.equal
      then
        Option.value_map op.run ~default:[] ~f:(fun run ->
          let observer = "observe:" ^ run.id in
          if List.exists snapshot.operations ~f:(fun op -> String.equal op.key observer)
          then [ observer ]
          else [])
      else [])
    |> List.dedup_and_sort ~compare:String.compare
  | _ -> keys
;;

type progress =
  | Pending
  | Complete
  | Failed of string

let progress ~wait keys (snapshot : Asic.Snapshot.t) =
  List.fold keys ~init:Complete ~f:(fun progress key ->
    match progress with
    | Failed _ -> progress
    | Pending | Complete ->
      (match List.find snapshot.operations ~f:(fun op -> String.equal op.key key) with
       | None -> Failed ("Requested ASIC operation is absent or evicted: " ^ key)
       | Some { error = Some error; _ } -> Failed (key ^ ": " ^ error)
       | Some op ->
         (match op.state with
          | "completed" -> progress
          | "pending" | "executing" -> if wait then Pending else progress
          | "failed" | "detached" -> Failed (key ^ ": " ^ op.state)
          | state -> Failed ("Unknown ASIC operation state for " ^ key ^ ": " ^ state))))
;;

let%test_unit "documented typed operation sexps decode without a shell or human-output \
               parser"
  =
  let plan =
    Asic.Operation.t_of_sexp
      (Sexp.of_string
         "(Plan ((flow synth) (profile default) (endpoint synthesis) (assignments \
          (WIDTH=4))))")
  in
  assert (
    match plan with
    | Plan selection ->
      String.equal selection.flow "synth"
      && List.equal String.equal selection.assignments [ "WIDTH=4" ]
    | _ -> false);
  let mutation =
    Workspace.Operation.t_of_sexp
      (Sexp.of_string
         "(Mutate (expected_revision 0) (mutation (Make_independent workspace-4)))")
  in
  assert (
    match mutation with
    | Mutate { expected_revision = 0; mutation = Make_independent _ } -> true
    | _ -> false)
;;

let%test_unit "Observe waits for its read, independently of a long execution" =
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id = "fixture"; build = None; label = None }
  in
  let operation key kind state : Asic.Pending.t =
    { key; kind; state; run = None; error = None }
  in
  let snapshot : Asic.Snapshot.t =
    { configured = true
    ; flows = []
    ; description_json = None
    ; preview = None
    ; runs = []
    ; operations =
        [ operation "run:long" "run" "executing"
        ; operation "observe:fixture" "observe" "completed"
        ]
    ; summaries = []
    ; cache_error = None
    }
  in
  let watched = keys (Observe run) snapshot in
  assert (
    match progress ~wait:true watched snapshot with
    | Complete -> true
    | _ -> false);
  assert (
    match progress ~wait:true (keys Get snapshot) snapshot with
    | Pending -> true
    | _ -> false);
  assert (
    match progress ~wait:false (keys Get snapshot) snapshot with
    | Complete -> true
    | _ -> false)
;;

let%test_unit "Observe does not await the lifetime of a coalesced automatic observer" =
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id = "fixture"; build = None; label = None }
  in
  let observer : Asic.Pending.t =
    { key = "observe:fixture"
    ; kind = "observe"
    ; state = "executing"
    ; run = Some run
    ; error = None
    }
  in
  let snapshot : Asic.Snapshot.t =
    { configured = true
    ; flows = []
    ; description_json = None
    ; preview = None
    ; runs = []
    ; operations = [ observer ]
    ; summaries = []
    ; cache_error = None
    }
  in
  assert (List.is_empty (keys (Observe run) snapshot));
  assert (
    match progress ~wait:true (keys Get snapshot) snapshot with
    | Pending -> true
    | _ -> false)
;;

let%test_unit "a targeted operation failure fails without treating historical failures \
               as Get failures"
  =
  let failed : Asic.Pending.t =
    { key = "discover"
    ; kind = "discover"
    ; state = "failed"
    ; run = None
    ; error = Some "fixture failure"
    }
  in
  let snapshot : Asic.Snapshot.t =
    { configured = true
    ; flows = []
    ; description_json = None
    ; preview = None
    ; runs = []
    ; operations = [ failed ]
    ; summaries = []
    ; cache_error = None
    }
  in
  assert (
    match progress ~wait:true (keys Discover snapshot) snapshot with
    | Failed _ -> true
    | _ -> false);
  assert (
    match progress ~wait:true (keys Get snapshot) snapshot with
    | Complete -> true
    | _ -> false)
;;
