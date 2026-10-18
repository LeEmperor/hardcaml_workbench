open! Core
open Hardcaml_workbench_protocol
module S = Simulation

type pane =
  | Catalog
  | Attempts
  | Cases
  | Detail
  | Artifacts
  | Logs

let pane = function
  | "simulation-catalog" -> Some Catalog
  | "simulation-attempts" -> Some Attempts
  | "simulation-cases" -> Some Cases
  | "simulation-detail" -> Some Detail
  | "simulation-artifacts" -> Some Artifacts
  | "simulation-logs" -> Some Logs
  | _ -> None
;;

let is_pane kind = Option.is_some (pane kind)

let pane_kind = function
  | Catalog -> "simulation-catalog"
  | Attempts -> "simulation-attempts"
  | Cases -> "simulation-cases"
  | Detail -> "simulation-detail"
  | Artifacts -> "simulation-artifacts"
  | Logs -> "simulation-logs"
;;

type t =
  { view : Simulation_view.t
  ; catalog : Simulation_catalog.t
  ; selected_artifact : string option
  }

let empty =
  { view = Simulation_view.empty
  ; catalog = Simulation_catalog.empty
  ; selected_artifact = None
  }
;;

let view t = t.view
let catalog t = t.catalog
let set_catalog t catalog = { t with catalog }
let update_catalog t f = set_catalog t (f t.catalog)
let selected_artifact t = t.selected_artifact

let artifact t =
  Option.bind (Simulation_view.detail t.view) ~f:(fun d ->
    List.find d.artifacts ~f:(fun a ->
      String.equal a.attempt_id d.id
      && Option.equal String.equal t.selected_artifact (Some a.id)))
;;

let set_view t view =
  let same_attempt =
    Option.equal String.equal t.view.attempt view.Simulation_view.attempt
  in
  let same_case = Option.equal String.equal t.view.case_id view.case_id in
  let catalog =
    if Option.equal S.Snapshot.equal t.view.snapshot view.snapshot
    then t.catalog
    else
      Option.value_map
        view.snapshot
        ~default:t.catalog
        ~f:(Simulation_catalog.update t.catalog)
  in
  let t =
    { view
    ; catalog
    ; selected_artifact =
        (if same_attempt && same_case then t.selected_artifact else None)
    }
  in
  if Option.is_some (Simulation_view.detail view) && Option.is_none (artifact t)
  then { t with selected_artifact = None }
  else t
;;

let select_attempt t id = set_view t (Simulation_view.select t.view id)

let select_case t id =
  match Simulation_view.detail t.view with
  | Some d when List.exists d.cases ~f:(fun c -> String.equal c.case_id id) ->
    if Option.equal String.equal t.view.case_id (Some id)
    then t
    else { t with view = { t.view with case_id = Some id }; selected_artifact = None }
  | _ -> t
;;

let select_artifact t id =
  match Simulation_view.detail t.view with
  | None -> t
  | Some d ->
    (match
       List.find d.artifacts ~f:(fun a ->
         String.equal a.id id && String.equal a.attempt_id d.id)
     with
     | None -> t
     | Some a ->
       { t with
         selected_artifact = Some id
       ; view = { t.view with case_id = Option.first_some a.case_id t.view.case_id }
       })
;;

let move_case t delta =
  match Simulation_view.detail t.view with
  | None -> t
  | Some d ->
    let ids = List.map d.cases ~f:(fun c -> c.case_id) in
    let index =
      Option.bind t.view.case_id ~f:(fun id ->
        List.findi ids ~f:(fun _ x -> String.equal id x))
      |> Option.value_map ~default:(if delta < 0 then List.length ids else -1) ~f:fst
    in
    Option.value_map
      (List.nth ids (Int.max 0 (Int.min (List.length ids - 1) (index + delta))))
      ~default:t
      ~f:(select_case t)
;;

let move_artifact t delta =
  match Simulation_view.detail t.view with
  | None -> t
  | Some d ->
    let ids =
      List.filter_map d.artifacts ~f:(fun a ->
        if String.equal a.attempt_id d.id then Some a.id else None)
    in
    let index =
      Option.bind t.selected_artifact ~f:(fun id ->
        List.findi ids ~f:(fun _ x -> String.equal id x))
      |> Option.value_map ~default:(if delta < 0 then List.length ids else -1) ~f:fst
    in
    Option.value_map
      (List.nth ids (Int.max 0 (Int.min (List.length ids - 1) (index + delta))))
      ~default:t
      ~f:(select_artifact t)
;;

let reconnect t =
  { t with
    view = { t.view with request = t.view.request + 1; busy = false }
  ; catalog = Simulation_catalog.invalidate t.catalog
  }
;;

let begin_request t = set_view t (Simulation_view.begin_request t.view)

let receive t ~ticket ~selected operation response =
  if ticket <> t.view.request || not (Option.equal String.equal selected t.view.attempt)
  then t
  else (
    let t =
      set_view t (Simulation_view.receive t.view ~ticket ~selected operation response)
    in
    match response with
    | Ok snapshot -> update_catalog t (fun c -> Simulation_catalog.update c snapshot)
    | Error error ->
      (match operation with
       | S.Operation.Discover ->
         update_catalog t (fun c -> Simulation_catalog.discovery_failed c error)
       | _ -> t))
;;

let atom = Simulation_view.atom
let row = Simulation_view.row

let attempt_label id =
  if String.equal (Overview_tiles.short_id id) id
  then id
  else
    Overview_tiles.short_id
      (Option.value (String.chop_prefix id ~prefix:"sim-") ~default:id)
;;

let artifact_details (a : S.Artifact.t) =
  [ row ("Selected artifact: " ^ a.id)
  ; row ("Artifact label: " ^ a.label)
  ; row ("Artifact attempt: " ^ a.attempt_id)
  ; row ("Artifact case: " ^ Option.value a.case_id ~default:"suite")
  ; row
      ~spans:
        [ Simulation_view.span
            ~start:(Simulation_view.text_width "Availability: ")
            (Simulation_view.availability_tone a.availability)
            (atom S.Artifact.Availability.sexp_of_t a.availability)
        ]
      ("Availability: " ^ atom S.Artifact.Availability.sexp_of_t a.availability)
  ; row ("Kind: " ^ a.kind ^ "; media type: " ^ a.media_type)
  ; row ("SHA256: " ^ Option.value a.sha256 ~default:"unavailable")
  ; row ("Artifact bytes: " ^ Option.value_map a.size ~default:"unknown" ~f:Int.to_string)
  ]
;;

let detail_rows t (d : S.Attempt.t) =
  [ row
      ~indicator:(Simulation_view.attempt_indicator d.lifecycle d.outcome)
      ~spans:
        [ Simulation_view.span
            ~start:0
            (Simulation_view.outcome_tone d.outcome)
            (atom S.Outcome.sexp_of_t d.outcome)
        ; Simulation_view.span
            ~start:
              (Simulation_view.text_width (atom S.Outcome.sexp_of_t d.outcome ^ " / "))
            (Simulation_view.lifecycle_tone d.lifecycle)
            (atom S.Lifecycle.sexp_of_t d.lifecycle)
        ]
      (atom S.Outcome.sexp_of_t d.outcome ^ " / " ^ atom S.Lifecycle.sexp_of_t d.lifecycle)
  ]
  @ List.concat_map d.cases ~f:(fun c ->
    if Option.equal String.equal t.view.case_id (Some c.case_id)
       || S.Case_status.equal c.status Failed
    then
      [ row
          ~indicator:(Simulation_view.case_indicator ~lifecycle:d.lifecycle c.status)
          ~value_start:(Simulation_view.text_width (c.case_id ^ ": "))
          (c.case_id ^ ": " ^ atom S.Case_status.sexp_of_t c.status)
      ]
      @ List.map (Option.to_list c.message) ~f:row
    else [])
  @ List.map (Option.to_list d.diagnostic) ~f:row
  @ Option.value_map (artifact t) ~default:[] ~f:artifact_details
  @ [ row ("Attempt: " ^ d.id)
    ; row ("Project: " ^ d.project_root)
    ; row ("Job: " ^ Job_id.to_string d.job)
    ; row ("Created: " ^ d.created_at)
    ; row ("Suite: " ^ d.captured.selection.suite)
    ; row ~indicator:Seed ("Seed: " ^ d.captured.selection.seed)
    ; row ("Captured cases: " ^ String.concat ~sep:", " d.captured.selection.cases)
    ; row
        ("Parameters: "
         ^ Sexp.to_string_mach
             ([%sexp_of: (string * string) list] d.captured.selection.parameters))
    ; row ("Discovery: " ^ d.captured.discovery_digest)
    ; row ("Provider: " ^ d.captured.provider_executable)
    ; row
        ("Provider arguments: "
         ^ Sexp.to_string_mach ([%sexp_of: string list] d.captured.provider_args))
    ; row
        ("Environment: " ^ atom V1.Environment_selection.sexp_of_t d.captured.environment)
    ; row
        ("Process exit: "
         ^ Option.value_map d.exit_code ~default:"unreported" ~f:Int.to_string)
    ]
  @ Option.value_map d.parent ~default:[] ~f:(fun p ->
    [ row ("Rerun parent attempt: " ^ p.attempt_id)
    ; row ("Rerun parent job: " ^ Job_id.to_string p.job)
    ])
  @ List.map d.captured.selection.asic_inputs ~f:(fun input ->
    row ("Explicit ASIC reference: " ^ atom S.Asic_input.sexp_of_t input))
;;

let rows t pane ~log_lines =
  let detail = Simulation_view.detail t.view in
  let rows =
    match pane with
    | Catalog -> Simulation_catalog.rows t.catalog
    | Attempts ->
      (if t.view.busy then [ row ~indicator:Running "Loading simulation history" ] else [])
      @ List.map (Option.to_list t.view.error @ Option.to_list t.view.notice) ~f:row
      @ Option.value_map
          t.view.snapshot
          ~default:[ row "No simulation history loaded" ]
          ~f:(fun s ->
            List.map (Option.to_list s.history_error) ~f:row
            @ List.concat_map s.attempts ~f:(fun a ->
              let prefix =
                (if Option.equal String.equal t.view.attempt (Some a.id)
                 then "> "
                 else "  ")
                ^ attempt_label a.id
                ^ " "
              in
              [ row
                  ~selected:(Option.equal String.equal t.view.attempt (Some a.id))
                  ~indicator:(Simulation_view.attempt_indicator a.lifecycle a.outcome)
                  ~spans:(Simulation_view.attempt_spans ~prefix a.lifecycle a.outcome)
                  (prefix
                   ^ atom S.Lifecycle.sexp_of_t a.lifecycle
                   ^ "/"
                   ^ atom S.Outcome.sexp_of_t a.outcome)
              ; row ("    " ^ a.suite ^ " · seed=" ^ a.seed)
              ]))
    | Cases ->
      Option.value_map
        detail
        ~default:[ row "Select an attempt" ]
        ~f:(fun d ->
          List.map d.cases ~f:(fun c ->
            let prefix =
              (if Option.equal String.equal t.view.case_id (Some c.case_id)
               then "> "
               else "  ")
              ^ c.case_id
              ^ ": "
            in
            row
              ~selected:(Option.equal String.equal t.view.case_id (Some c.case_id))
              ~indicator:(Simulation_view.case_indicator ~lifecycle:d.lifecycle c.status)
              ~value_start:
                (Bonsai_term.View.width
                   (Bonsai_term.View.text (Artifact_view.safe prefix)))
              (prefix ^ atom S.Case_status.sexp_of_t c.status)))
    | Detail ->
      Option.value_map
        detail
        ~default:[ row "Select an attempt for outcome and captured inputs" ]
        ~f:(detail_rows t)
    | Artifacts ->
      Option.value_map
        detail
        ~default:[ row "Select an attempt" ]
        ~f:(fun d ->
          List.map d.artifacts ~f:(fun a ->
            let prefix =
              (if Option.equal String.equal t.selected_artifact (Some a.id)
               then "> "
               else "  ")
              ^ a.label
              ^ " — "
              ^ Option.value a.case_id ~default:"suite"
              ^ " ["
            in
            let availability = atom S.Artifact.Availability.sexp_of_t a.availability in
            row
              ~selected:(Option.equal String.equal t.selected_artifact (Some a.id))
              ~indicator:Artifact
              ~spans:
                [ Simulation_view.span
                    ~start:(Simulation_view.text_width prefix)
                    (Simulation_view.availability_tone a.availability)
                    availability
                ]
              (prefix ^ availability ^ "]")))
    | Logs ->
      Option.value_map
        detail
        ~default:[ row "Select an attempt" ]
        ~f:(fun d ->
          row
            ~spans:(Simulation_view.attempt_spans ~prefix:"" d.lifecycle d.outcome)
            (atom S.Lifecycle.sexp_of_t d.lifecycle
             ^ "/"
             ^ atom S.Outcome.sexp_of_t d.outcome)
          :: row ("Attempt: " ^ d.id ^ "; job: " ^ Job_id.to_string d.job)
          :: List.map (log_lines d.job) ~f:row)
  in
  List.concat_map rows ~f:(fun r ->
    String.split_lines r.Simulation_view.text
    |> List.mapi ~f:(fun i text ->
      { r with
        text = Artifact_view.safe text
      ; indicator = (if i = 0 then r.indicator else None)
      ; value_start = (if i = 0 then r.value_start else None)
      ; selected = i = 0 && r.selected
      ; spans = (if i = 0 then r.spans else [])
      }))
;;

module Test_data = struct
  let suite : S.Suite.t =
    { id = "suite"
    ; label = "Suite"
    ; default_seed = "7"
    ; cases = [ { id = "a"; label = "A" }; { id = "b"; label = "B" } ]
    ; parameters = []
    }
  ;;

  let artifact : S.Artifact.t =
    { id = "artifact-full-id"
    ; attempt_id = "attempt-full-id"
    ; case_id = Some "a"
    ; label = "not a report keyword"
    ; kind = "custom"
    ; media_type = "text/plain"
    ; size = Some 7
    ; sha256 = Some "full-sha256"
    ; availability = Available
    }
  ;;

  let attempt : S.Attempt.t =
    { id = "attempt-full-id"
    ; job = Job_id.of_string "exact-job"
    ; project_root = "/project"
    ; created_at = "now"
    ; parent = None
    ; captured =
        { selection = Simulation_view.selection suite
        ; discovery_digest = "digest"
        ; provider_executable = "/provider"
        ; provider_args = [ "arg" ]
        ; environment = V1.Environment_selection.Inherit_daemon
        }
    ; lifecycle = Finished
    ; outcome = Failed
    ; exit_code = Some 0
    ; diagnostic = Some "checker diagnostic"
    ; progress = None
    ; cases =
        [ { case_id = "a"
          ; status = Failed
          ; message = Some "expected 0 got 1"
          ; progress = None
          }
        ; { case_id = "b"; status = Passed; message = None; progress = None }
        ]
    ; artifacts = [ artifact ]
    ; next_sequence = 5
    ; recent_events = []
    }
  ;;

  let snapshot : S.Snapshot.t =
    { configured = true
    ; discovery = Some { protocol_version = 1; suites = [ suite ] }
    ; discovery_digest = Some "digest"
    ; discovery_job = None
    ; discovery_error = None
    ; attempts = []
    ; next_before = None
    ; detail = Some attempt
    ; byte_page = None
    ; history_error = None
    }
  ;;

  let loaded () =
    let t = select_attempt empty attempt.id |> begin_request in
    receive
      t
      ~ticket:t.view.request
      ~selected:t.view.attempt
      (Observe attempt.id)
      (Ok snapshot)
  ;;
end

let%test_unit "workspace browsing independent of attempt and other workspaces" =
  let t = Test_data.loaded () in
  let other = Test_data.loaded () in
  let t = update_catalog t (fun c -> Simulation_catalog.toggle_case c "a") in
  assert (
    S.Attempt.equal (Option.value_exn (Simulation_view.detail t.view)) Test_data.attempt);
  assert (
    List.equal String.equal (Simulation_catalog.selected_cases other.catalog) [ "a"; "b" ]);
  let t = select_case t "b" |> fun t -> select_artifact t "artifact-full-id" in
  assert (Option.equal String.equal t.view.case_id (Some "a"));
  assert (Option.equal String.equal (selected_artifact t) (Some "artifact-full-id"));
  assert (Option.is_none (selected_artifact other));
  let t = select_case t "b" in
  assert (Option.is_none (artifact t));
  let t = select_artifact t "artifact-full-id" |> fun t -> select_attempt t "new" in
  assert (Option.is_none (artifact t));
  assert (Option.is_none (Simulation_view.detail t.view));
  assert (Option.is_none t.view.case_id)
;;

let%test_unit "late responses reconnect and artifact removal cannot retarget \
               investigation"
  =
  let old = Test_data.loaded () |> begin_request in
  let t = select_attempt old "new" in
  let stale =
    receive
      t
      ~ticket:old.view.request
      ~selected:old.view.attempt
      (Observe "attempt-full-id")
      (Ok Test_data.snapshot)
  in
  assert (Option.equal String.equal stale.view.attempt (Some "new"));
  assert (Option.is_none (Simulation_view.detail stale.view));
  let t = reconnect old in
  let stale =
    receive
      t
      ~ticket:old.view.request
      ~selected:old.view.attempt
      Discover
      (Ok Test_data.snapshot)
  in
  assert (not stale.view.busy);
  assert (Or_error.is_error (Simulation_catalog.launch stale.catalog));
  let t =
    Test_data.loaded () |> fun t -> select_artifact t "artifact-full-id" |> begin_request
  in
  let snapshot =
    { Test_data.snapshot with detail = Some { Test_data.attempt with artifacts = [] } }
  in
  let t =
    receive
      t
      ~ticket:t.view.request
      ~selected:t.view.attempt
      (Observe "attempt-full-id")
      (Ok snapshot)
  in
  assert (Option.is_none (selected_artifact t));
  let t = begin_request t in
  let t =
    receive
      t
      ~ticket:t.view.request
      ~selected:t.view.attempt
      Discover
      (Error "discovery rejected")
  in
  assert (Or_error.is_error (Simulation_catalog.launch t.catalog));
  assert (List.length (Simulation_catalog.visible_cases t.catalog) = 2)
;;

let%test_unit "cooperative rows keep facts typed full provenance and logs separate" =
  let t = Test_data.loaded () |> fun t -> select_case t "a" in
  List.iter [ Catalog; Attempts; Cases; Detail; Artifacts; Logs ] ~f:(fun p ->
    assert (Option.equal Poly.equal (pane (pane_kind p)) (Some p)));
  assert (not (is_pane "simulation"));
  let no_logs _ = assert false in
  let detail = rows t Detail ~log_lines:no_logs in
  let text =
    String.concat ~sep:"\n" (List.map detail ~f:(fun r -> r.Simulation_view.text))
  in
  List.iter
    [ "Failed / Finished"
    ; "expected 0 got 1"
    ; "attempt-full-id"
    ; "exact-job"
    ; "/project"
    ; "/provider"
    ; "digest"
    ; "Process exit: 0"
    ]
    ~f:(fun substring -> assert (String.is_substring text ~substring));
  assert (not (String.is_substring text ~substring:"artifact-full-id"));
  let cases = rows t Cases ~log_lines:no_logs in
  assert (Option.equal Poly.equal (List.nth_exn cases 0).indicator (Some Indicator.Failed));
  assert (Option.is_some (List.nth_exn cases 0).value_start);
  let artifacts = rows t Artifacts ~log_lines:no_logs in
  assert (
    Option.equal Poly.equal (List.nth_exn artifacts 0).indicator (Some Indicator.Artifact));
  let logs =
    rows t Logs ~log_lines:(fun job ->
      assert (String.equal (Job_id.to_string job) "exact-job");
      [ "Passed Failed report artifact"; "\027[31muntrusted\027[0m" ])
  in
  assert (String.equal (List.nth_exn logs 0).text "Finished/Failed");
  assert (String.equal (List.nth_exn logs 2).text "Passed Failed report artifact");
  assert (Option.is_none (List.nth_exn logs 2).indicator);
  assert (List.is_empty (List.nth_exn logs 2).spans);
  assert (not (String.contains (List.nth_exn logs 3).text '\027'))
;;

let%test_unit "large navigators expose a unique typed cursor; artifact identity stays \
               exact"
  =
  let attempts : S.Summary.t list =
    List.init 25 ~f:(fun i ->
      { S.Summary.id = sprintf "attempt-%02d-full-identity" i
      ; job = Test_data.attempt.job
      ; suite = "suite"
      ; seed = "7"
      ; created_at = "now"
      ; parent = None
      ; lifecycle = Finished
      ; outcome = Failed
      })
  in
  let cases : S.Case_result.t list =
    List.init 1024 ~f:(fun i ->
      { S.Case_result.case_id = sprintf "case-%04d" i
      ; status = Passed
      ; message = None
      ; progress = None
      })
  in
  let artifacts =
    List.init 32 ~f:(fun i ->
      { Test_data.artifact with
        id = sprintf "artifact-%02d-exact-id" i
      ; label = "Evidence label\ncontinuation"
      ; case_id = Some "case-1023"
      })
  in
  let attempt =
    { Test_data.attempt with
      id = (List.last_exn attempts).id
    ; cases
    ; artifacts =
        List.map artifacts ~f:(fun a ->
          { a with S.Artifact.attempt_id = (List.last_exn attempts).id })
    }
  in
  let snapshot = { Test_data.snapshot with attempts; detail = Some attempt } in
  let t =
    set_view
      empty
      { Simulation_view.empty with attempt = Some attempt.id; snapshot = Some snapshot }
  in
  let t = select_case t "case-1023" in
  let selected pane t =
    rows t pane ~log_lines:(fun _ -> assert false)
    |> List.filter ~f:(fun r -> r.Simulation_view.selected)
  in
  let only pane t =
    let rows = selected pane t in
    assert (List.length rows = 1);
    (List.hd_exn rows).text
  in
  assert (String.equal (only Attempts t) "> attemp...entity Finished/Failed");
  let navigator = rows t Attempts ~log_lines:(fun _ -> assert false) in
  assert (List.length navigator = 2 * List.length attempts);
  List.iteri navigator ~f:(fun i r ->
    if i mod 2 = 0
    then assert (Option.is_some r.indicator)
    else (
      assert (String.equal r.text "    suite · seed=7");
      assert (not r.selected);
      assert (Option.is_none r.indicator);
      assert (List.is_empty r.spans)));
  assert (Option.equal String.equal t.view.attempt (Some attempt.id));
  assert (String.equal (only Cases t) "> case-1023: Passed");
  assert (List.is_empty (selected Artifacts t));
  let t = select_artifact t "artifact-31-exact-id" in
  assert (String.equal (only Artifacts t) "> Evidence label");
  let navigator = rows t Artifacts ~log_lines:(fun _ -> assert false) in
  assert (List.length navigator = 64);
  assert (
    List.for_all navigator ~f:(fun r ->
      not (String.is_substring r.text ~substring:"SHA256:")));
  let detail =
    rows t Detail ~log_lines:(fun _ -> assert false)
    |> List.map ~f:(fun r -> r.Simulation_view.text)
    |> String.concat ~sep:"\n"
  in
  List.iter
    [ "artifact-31-exact-id"
    ; "attempt-24-full-identity"
    ; "full-sha256"
    ; "text/plain"
    ; "Artifact case: case-1023"
    ]
    ~f:(fun substring -> assert (String.is_substring detail ~substring));
  assert (String.equal (Option.value_exn (artifact t)).id "artifact-31-exact-id");
  assert (Option.is_some (artifact (select_case t "case-1023")));
  assert (Option.is_none (artifact (select_case t "case-0000")));
  assert (
    Option.is_none (artifact (set_view t { t.view with case_id = Some "case-0000" })))
;;

let%test_unit "compact attempt labels preserve short and non-ASCII identities" =
  List.iter [ "sim-42"; "Passed-ID"; "simulation-試験-long-identity" ] ~f:(fun id ->
    assert (String.equal (attempt_label id) id));
  let id = "sim-3a91c2abcdef0123456789e84b" in
  assert (String.equal (attempt_label id) "3a91c2...89e84b");
  let attempt = { Test_data.attempt with id } in
  let summary : S.Summary.t =
    { id
    ; job = attempt.job
    ; suite = "controlled-fifo"
    ; seed = "18446744073709551615"
    ; created_at = attempt.created_at
    ; parent = None
    ; lifecycle = attempt.lifecycle
    ; outcome = attempt.outcome
    }
  in
  let snapshot =
    { Test_data.snapshot with attempts = [ summary ]; detail = Some attempt }
  in
  let t =
    set_view empty { Simulation_view.empty with snapshot = Some snapshot }
    |> fun t -> select_attempt t id
  in
  let t = begin_request t in
  let t =
    receive t ~ticket:t.view.request ~selected:(Some id) (Observe id) (Ok snapshot)
  in
  let navigator = rows t Attempts ~log_lines:(fun _ -> assert false) in
  assert (
    List.equal
      String.equal
      (List.map navigator ~f:(fun r -> r.Simulation_view.text))
      [ "> 3a91c2...89e84b Finished/Failed"
      ; "    controlled-fifo · seed=18446744073709551615"
      ]);
  assert (List.hd_exn navigator).selected;
  assert (not (List.last_exn navigator).selected);
  assert (Option.equal String.equal t.view.attempt (Some id));
  assert (String.equal (Option.value_exn (Simulation_view.detail t.view)).id id);
  assert (
    List.exists
      (rows t Detail ~log_lines:(fun _ -> assert false))
      ~f:(fun r -> String.equal r.text ("Attempt: " ^ id)))
;;
