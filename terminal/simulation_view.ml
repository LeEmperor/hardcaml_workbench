open! Core
open Hardcaml_workbench_protocol
module S = Simulation

type t =
  { snapshot : S.Snapshot.t option
  ; attempt : string option
  ; case_id : string option
  ; request : int
  ; error : string option
  ; older : bool
  ; logs : bool
  ; busy : bool
  ; notice : string option
  }

let empty =
  { snapshot = None
  ; attempt = None
  ; case_id = None
  ; request = 0
  ; error = None
  ; older = false
  ; logs = false
  ; busy = false
  ; notice = None
  }
;;

let begin_request t = { t with request = t.request + 1; busy = true }
let detail t = Option.bind t.snapshot ~f:(fun s -> s.detail)

let select t attempt =
  { t with
    attempt = Some attempt
  ; case_id = None
  ; snapshot = Option.map t.snapshot ~f:(fun s -> { s with detail = None })
  ; request = t.request + 1
  }
;;

let receive t ~ticket ~selected operation response =
  if ticket <> t.request || not (Option.equal String.equal selected t.attempt)
  then t
  else (
    match response with
    | Error error -> { t with error = Some error; busy = false }
    | Ok (s : S.Snapshot.t) ->
      let allocation =
        match operation with
        | S.Operation.Launch _ | Rerun _ -> true
        | _ -> false
      in
      let attempt =
        if allocation then Option.map s.detail ~f:(fun d -> d.id) else t.attempt
      in
      let detail =
        let supplied =
          Option.filter s.detail ~f:(fun d ->
            Option.equal String.equal (Some d.id) attempt)
        in
        Option.first_some
          supplied
          (if allocation
           then None
           else
             Option.filter (detail t) ~f:(fun d ->
               Option.equal String.equal (Some d.id) attempt))
      in
      let s =
        match operation, t.snapshot with
        | (S.Operation.Observe _ | Cancel _), Some old ->
          let attempts =
            List.map old.attempts ~f:(fun summary ->
              let summary =
                Option.value
                  (List.find s.attempts ~f:(fun current ->
                     String.equal current.id summary.id))
                  ~default:summary
              in
              match detail with
              | Some d when String.equal d.id summary.id ->
                { summary with lifecycle = d.lifecycle; outcome = d.outcome }
              | _ -> summary)
          in
          { s with attempts; next_before = old.next_before; detail }
        | _ -> { s with detail }
      in
      { t with
        snapshot = Some s
      ; attempt
      ; case_id =
          (match detail with
           | None -> t.case_id
           | Some d ->
             Option.filter t.case_id ~f:(fun id ->
               List.exists d.cases ~f:(fun c -> String.equal c.case_id id)))
      ; error = None
      ; busy = false
      ; older =
          (match operation with
           | History { before = Some _; _ } -> true
           | Get | History _ | Discover | Launch _ | Rerun _ -> false
           | _ -> t.older)
      })
;;

let selection (suite : S.Suite.t) : S.Selection.t =
  { suite = suite.id
  ; cases = List.map suite.cases ~f:(fun c -> c.id)
  ; seed = suite.default_seed
  ; parameters = List.map suite.parameters ~f:(fun p -> p.key, p.default)
  ; asic_inputs = []
  }
;;

module Form = struct
  type t =
    { suite : S.Suite.t
    ; selection : S.Selection.t
    ; field : int
    }

  let create suite = { suite; selection = selection suite; field = 0 }
  let parameter t = List.nth t.suite.parameters (t.field - 2)
  let confirming t = t.field >= 2 + List.length t.suite.parameters

  let query t =
    if t.field = 0
    then String.concat ~sep:" " t.selection.cases
    else if t.field = 1
    then t.selection.seed
    else if confirming t
    then "launch"
    else (
      let p = Option.value_exn (parameter t) in
      List.Assoc.find_exn t.selection.parameters p.key ~equal:String.equal)
  ;;

  let label t =
    if t.field = 0
    then "CASES — explicit space-separated case IDs"
    else if t.field = 1
    then "SEED — canonical unsigned 64-bit decimal"
    else if confirming t
    then "CONFIRM — type launch and Enter to submit captured inputs on current project"
    else (
      let p = Option.value_exn (parameter t) in
      "PARAMETER "
      ^ p.key
      ^ " — "
      ^ p.label
      ^
      if List.is_empty p.choices
      then " (free string)"
      else " choices: " ^ String.concat ~sep:", " p.choices)
  ;;

  let help t =
    [ "Suite: " ^ t.suite.id ^ " — " ^ t.suite.label
    ; label t
    ; "Ctrl-U clears; Backspace edits; Enter accepts field; Esc abandons form"
    ]
    @
    if t.field = 0
    then
      [ "Available cases: "
        ^ String.concat ~sep:" " (List.map t.suite.cases ~f:(fun c -> c.id))
      ]
    else if confirming t
    then [ Sexp.to_string_mach (S.Selection.sexp_of_t t.selection) ]
    else []
  ;;

  let accept t query =
    let open Or_error.Let_syntax in
    let%bind selection =
      if t.field = 0
      then (
        let cases =
          String.split (String.strip query) ~on:' '
          |> List.filter ~f:(Fn.non String.is_empty)
        in
        if List.is_empty cases
           || List.contains_dup cases ~compare:String.compare
           || List.exists cases ~f:(fun id ->
             not (List.exists t.suite.cases ~f:(fun c -> String.equal c.id id)))
        then Or_error.error_string "Choose nonempty, unique case IDs from this suite"
        else Ok { t.selection with cases })
      else if t.field = 1
      then (
        let max_seed = "18446744073709551615" in
        if String.is_empty query
           || (not (String.for_all query ~f:Char.is_digit))
           || (String.length query > 1 && Char.equal query.[0] '0')
           || String.length query > String.length max_seed
           || (String.length query = String.length max_seed
               && String.compare query max_seed > 0)
        then
          Or_error.error_string "Seed must be canonical decimal 0..18446744073709551615"
        else Ok { t.selection with seed = query })
      else if confirming t
      then
        if String.equal query "launch"
        then Ok t.selection
        else Or_error.error_string "Type launch to confirm"
      else (
        let p = Option.value_exn (parameter t) in
        if String.length query > S.Limits.string_bytes
           || ((not (List.is_empty p.choices))
               && not (List.mem p.choices query ~equal:String.equal))
        then Or_error.error_string ("Invalid parameter " ^ p.key)
        else
          Ok
            { t.selection with
              parameters =
                List.Assoc.add t.selection.parameters p.key query ~equal:String.equal
            })
    in
    if confirming t
    then Ok (`Launch selection)
    else Ok (`Next { t with selection; field = t.field + 1 })
  ;;
end

let progress (p : S.Progress.t) =
  sprintf
    "%d%s %s%s"
    p.completed
    (Option.value_map p.total ~default:" / ?" ~f:(sprintf " / %d"))
    p.unit_
    (if Option.is_none p.total then " (indeterminate)" else "")
;;

let atom f x = Sexp.to_string_mach (f x)

let rows t ~log_lines =
  let rows =
    [ "Structured simulation — project scoped"
    ; "j/k attempts; n/p cases; [/] scroll; l logs; palette: launch/rerun/cancel/export"
    ]
  in
  let rows = rows @ Option.to_list t.notice @ Option.to_list t.error in
  let rows =
    rows
    @
    match t.snapshot with
    | None -> [ "Loading simulation catalog/history" ]
    | Some s ->
      [ (if s.configured
         then "Provider configured"
         else "No simulation provider configured")
      ]
      @ Option.to_list s.discovery_error
      @ Option.to_list s.history_error
      @ Option.value_map s.discovery_job ~default:[] ~f:(fun j ->
        [ "Discovery job: " ^ Job_id.to_string j ])
      @ (match detail t with
         | None -> [ "Select an attempt from the palette (no job is launched)" ]
         | Some d ->
           [ "Attempt: " ^ d.id
           ; sprintf
               "%s / %s; process exit: %s"
               (atom S.Lifecycle.sexp_of_t d.lifecycle)
               (atom S.Outcome.sexp_of_t d.outcome)
               (Option.value_map d.exit_code ~default:"unreported" ~f:Int.to_string)
           ; sprintf
               "Suite: %s; seed: %s"
               d.captured.selection.suite
               d.captured.selection.seed
           ; "Parameters: "
             ^ Sexp.to_string_mach
                 ([%sexp_of: (string * string) list] d.captured.selection.parameters)
           ; sprintf
               "Explicit ASIC input references: %d"
               (List.length d.captured.selection.asic_inputs)
           ]
           @ Option.value_map d.parent ~default:[] ~f:(fun p ->
             [ "Rerun of " ^ p.attempt_id ^ " on current project" ])
           @ Option.to_list d.diagnostic
           @ Option.value_map d.progress ~default:[] ~f:(fun p ->
             [ "Progress: " ^ progress p ])
           @ List.concat_map
               (List.stable_sort d.cases ~compare:(fun a b ->
                  Bool.compare
                    (not (Option.equal String.equal t.case_id (Some a.case_id)))
                    (not (Option.equal String.equal t.case_id (Some b.case_id)))))
               ~f:(fun c ->
                 [ (if Option.equal String.equal t.case_id (Some c.case_id)
                    then "> "
                    else "  ")
                   ^ c.case_id
                   ^ ": "
                   ^ atom S.Case_status.sexp_of_t c.status
                 ]
                 @ Option.value_map c.progress ~default:[] ~f:(fun p ->
                   [ "  " ^ progress p ])
                 @ Option.value_map c.message ~default:[] ~f:(fun m ->
                   String.split_lines m |> List.map ~f:(fun l -> "  " ^ l)))
           @ List.map d.artifacts ~f:(fun a ->
             sprintf
               "Artifact %s: %s [%s]"
               a.id
               a.label
               (atom S.Artifact.Availability.sexp_of_t a.availability))
           @
           if t.logs
           then "JOB LOG (historical logs may be unavailable)" :: log_lines d.job
           else [])
      @ [ (if t.older then "HISTORY (older page)" else "HISTORY (newest page)") ]
      @ List.map s.attempts ~f:(fun a ->
        sprintf
          "%s %s seed=%s %s/%s"
          a.id
          a.suite
          a.seed
          (atom S.Lifecycle.sexp_of_t a.lifecycle)
          (atom S.Outcome.sexp_of_t a.outcome))
  in
  List.concat_map rows ~f:String.split_lines |> List.map ~f:Artifact_view.safe
;;

let%test_unit "request and attempt fences reject stale receipts" =
  let t = select empty "new" |> begin_request in
  let stale =
    receive t ~ticket:(t.request - 1) ~selected:t.attempt S.Operation.Get (Error "stale")
  in
  assert (Option.is_none stale.error);
  let stale =
    receive t ~ticket:t.request ~selected:(Some "old") S.Operation.Get (Error "stale")
  in
  assert (Option.is_none stale.error);
  assert (
    String.is_substring
      (progress { case_id = None; completed = 4; total = None; unit_ = "cycles" })
      ~substring:"indeterminate");
  assert (
    not
      (String.is_substring
         (String.concat (rows empty ~log_lines:(fun _ -> [])))
         ~substring:"ASIC-run"))
;;

let%test_unit "launch wizard captures explicit cases uint64 seed and declared parameters \
               before submission"
  =
  let suite : S.Suite.t =
    { id = "suite"
    ; label = "Suite"
    ; default_seed = "1"
    ; cases = [ { id = "a"; label = "A" }; { id = "b"; label = "B" } ]
    ; parameters =
        [ { key = "mode"; label = "Mode"; default = "fast"; choices = [ "fast"; "slow" ] }
        ; { key = "text"; label = "Text"; default = ""; choices = [] }
        ]
    }
  in
  let f = Form.create suite in
  List.iter [ ""; "unknown"; "a a" ] ~f:(fun q ->
    assert (Or_error.is_error (Form.accept f q)));
  let next f q =
    match Form.accept f q |> Or_error.ok_exn with
    | `Next f -> f
    | `Launch _ -> assert false
  in
  let f = next f "b" in
  List.iter [ "-1"; "01"; "18446744073709551616"; "1.0" ] ~f:(fun q ->
    assert (Or_error.is_error (Form.accept f q)));
  let f = next f "18446744073709551615" in
  assert (Or_error.is_error (Form.accept f "invalid"));
  let f = next f "slow" |> fun f -> next f "" in
  assert (Form.confirming f);
  match Form.accept f "launch" |> Or_error.ok_exn with
  | `Next _ -> assert false
  | `Launch s ->
    assert (List.equal String.equal s.cases [ "b" ]);
    assert (String.equal s.seed "18446744073709551615");
    assert (
      String.equal (List.Assoc.find_exn s.parameters "mode" ~equal:String.equal) "slow");
    assert (List.is_empty s.asic_inputs)
;;

let%test_unit "history, selection, normalized failure and captured rerun inputs stay \
               independent"
  =
  let suite : S.Suite.t =
    { id = "counter"
    ; label = "Counter"
    ; cases = [ { id = "wraps"; label = "Wraps" } ]
    ; default_seed = "18446744073709551615"
    ; parameters = [ { key = "cycles"; label = "Cycles"; default = "17"; choices = [] } ]
    }
  in
  let selection = selection suite in
  let attempt : S.Attempt.t =
    { id = "old"
    ; job = Job_id.of_string "old-job"
    ; project_root = "/project"
    ; created_at = "now"
    ; parent = None
    ; captured =
        { selection
        ; discovery_digest = "digest"
        ; provider_executable = "/provider"
        ; provider_args = []
        ; environment = V1.Environment_selection.Inherit_daemon
        }
    ; lifecycle = Finished
    ; outcome = Incomplete
    ; exit_code = Some 1
    ; diagnostic = Some "Truncated event stream"
    ; progress = None
    ; cases =
        [ { case_id = "wraps"
          ; status = Failed
          ; message = Some "expected 0, got 1"
          ; progress =
              Some
                { case_id = Some "wraps"; completed = 5; total = None; unit_ = "cycles" }
          }
        ]
    ; artifacts = []
    ; next_sequence = 4
    ; recent_events = []
    }
  in
  let snapshot : S.Snapshot.t =
    { configured = true
    ; discovery = Some { protocol_version = 1; suites = [ suite ] }
    ; discovery_digest = Some "digest"
    ; discovery_job = None
    ; discovery_error = None
    ; attempts = []
    ; next_before = Some "older"
    ; detail = Some attempt
    ; byte_page = None
    ; history_error = None
    }
  in
  let a = select empty "old" |> begin_request in
  let a = receive a ~ticket:a.request ~selected:a.attempt (Observe "old") (Ok snapshot) in
  let b = select empty "another" in
  assert (Option.equal String.equal b.attempt (Some "another"));
  assert (Option.is_none (detail b));
  let text = String.concat ~sep:"\n" (rows a ~log_lines:(fun _ -> [])) in
  List.iter
    [ "Incomplete"
    ; "Failed"
    ; "expected 0, got 1"
    ; "indeterminate"
    ; selection.seed
    ; "Truncated event stream"
    ]
    ~f:(fun substring -> assert (String.is_substring text ~substring));
  assert (S.Selection.equal (Option.value_exn (detail a)).captured.selection selection);
  let semantic_failure =
    { a with
      snapshot =
        Some
          { snapshot with
            detail = Some { attempt with outcome = Failed; exit_code = Some 0 }
          }
    }
  in
  assert (
    String.is_substring
      (String.concat ~sep:"\n" (rows semantic_failure ~log_lines:(fun _ -> [])))
      ~substring:"Finished / Failed; process exit: 0");
  let a = begin_request a in
  let a =
    receive
      a
      ~ticket:a.request
      ~selected:a.attempt
      (History { before = Some "older"; limit = 25 })
      (Ok { snapshot with detail = None; next_before = None })
  in
  assert a.older;
  assert (S.Attempt.equal (Option.value_exn (detail a)) attempt);
  let a = begin_request a in
  let a = receive a ~ticket:a.request ~selected:a.attempt (Observe "old") (Ok snapshot) in
  assert (Option.is_none (Option.value_exn a.snapshot).next_before);
  let summary : S.Summary.t =
    { id = attempt.id
    ; job = attempt.job
    ; suite = selection.suite
    ; seed = selection.seed
    ; created_at = attempt.created_at
    ; parent = None
    ; lifecycle = Queued
    ; outcome = Unknown
    }
  in
  let a =
    { a with
      snapshot = Some { (Option.value_exn a.snapshot) with attempts = [ summary ] }
    }
    |> begin_request
  in
  let a = receive a ~ticket:a.request ~selected:a.attempt (Observe "old") (Ok snapshot) in
  let summary = List.hd_exn (Option.value_exn a.snapshot).attempts in
  assert (
    S.Lifecycle.equal summary.lifecycle Finished
    && S.Outcome.equal summary.outcome Incomplete);
  let changed = select a "different" |> begin_request in
  let stale =
    receive changed ~ticket:a.request ~selected:a.attempt (Observe "old") (Ok snapshot)
  in
  assert (
    Option.equal String.equal stale.attempt (Some "different")
    && Option.is_none (detail stale));
  let stale =
    receive
      changed
      ~ticket:a.request
      ~selected:a.attempt
      (Launch { submission_key = "old-key"; discovery_digest = "digest"; selection })
      (Ok snapshot)
  in
  assert (
    Option.equal String.equal stale.attempt (Some "different")
    && Option.is_none (detail stale))
;;
