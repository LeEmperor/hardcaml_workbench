open! Core
open Hardcaml_workbench_protocol
open Bonsai_term

(** Pure utility tiles. The host owns frames, focus, input and fetching. In particular,
    [Asic.Snapshot] does not contain per-stage observations: neither its run status,
    requested endpoint, metrics nor terminal completion can fill in a checklist. *)
module Status = struct
  type t =
    | Unknown
    | Not_requested
    | Pending
    | Running
    | Completed
    | Failed
    | Skipped
  [@@deriving compare, equal, sexp]

  let label = function
    | Unknown -> "not reported"
    | Not_requested -> "not requested"
    | Pending -> "not run"
    | Running -> "running"
    | Completed -> "completed"
    | Failed -> "failed"
    | Skipped -> "skipped"
  ;;
end

module Role = struct
  type t =
    | Heading
    | Foreground
    | Muted
    | Active
    | Running
    | Success
    | Warning
    | Failure
  [@@deriving compare, equal, sexp]
end

type row =
  { label : string
  ; value : string
  ; role : Role.t
  ; status : Status.t option
  ; active : bool
  ; workspace : Workspace.Workspace_id.t option
  ; details : string list
  }

let row
  ?(role = Role.Foreground)
  ?status
  ?(active = false)
  ?workspace
  ?(details = [])
  label
  value
  =
  { label; value; role; status; active; workspace; details }
;;

let status_role : Status.t -> Role.t = function
  | Unknown | Not_requested -> Muted
  | Pending | Skipped -> Warning
  | Running -> Running
  | Completed -> Success
  | Failed -> Failure
;;

(** [requested=false] is not allowed to erase an observed outcome. A completed stage from
    an earlier invocation can legitimately be outside the current request. *)
let stage_status (stage : Stage.t) : Status.t =
  match stage.status with
  | Not_run -> if stage.requested then Pending else Not_requested
  | Running -> Running
  | Completed -> Completed
  | Failed _ -> Failed
  | Skipped _ -> Skipped
;;

let stage_row (stage : Stage.t) =
  let status = stage_status stage in
  let reason =
    match stage.status with
    | Failed { reason } | Skipped { reason } -> [ "Reason: " ^ reason ]
    | Not_run | Running | Completed -> []
  in
  row
    ~role:(status_role status)
    ~status
    ~details:([ sprintf "Requested: %b" stage.requested ] @ reason)
    stage.name
    (Status.label status)
;;

let default_stages = [ "Synthesis"; "Placement"; "CTS"; "Routing"; "Checks" ]
let run_identity (run : Run_ref.t) = Backend_id.to_string run.backend ^ "/" ^ run.id

(** Only shorten ASCII opaque identifiers. Human/provider labels remain intact and are
    clipped by display cells during rendering, never by UTF-8 byte offsets. *)
let short_id text =
  if String.for_all text ~f:(fun char -> Char.to_int char < 128)
     && String.length text > 15
  then String.prefix text 6 ^ "..." ^ String.suffix text 6
  else text
;;

let run_label (run : Run_ref.t) = Option.value run.label ~default:(short_id run.id)

(** Status vocabularies are field-specific. An unfamiliar value remains visible but
    neutral: e.g. operation completion cannot turn acceptance into a pass. These aggregate
    facts deliberately have no [Status.t] stage/checklist marker. *)
module Fact = struct
  type t =
    | Operation
    | Physical_completion
    | Verdict
    | Summary_completion

  let role field value : Role.t =
    match field, value with
    | Operation, "completed"
    | Physical_completion, "full"
    | Verdict, "pass"
    | Summary_completion, "completed" -> Success
    | Operation, "failed" | Physical_completion, "failed" | Verdict, "fail" -> Failure
    | Operation, ("running" | "starting") -> Running
    | Operation, ("interrupted" | "cancelled" | "queued")
    | Physical_completion, ("partial" | "incomplete")
    | Verdict, ("not_evaluated" | "not_requested" | "skipped") -> Warning
    | _ -> Muted
  ;;
end

let freshness_label : Asic.Summary.Freshness.t -> string * Role.t = function
  | Validated -> "validated", Success
  | Cached_unverified -> "cached/unverified", Warning
  | Missing_source -> "source unavailable", Warning
  | Refresh_failed _ -> "refresh failed", Warning
;;

(** Compose only with a summary whose [run] matches the selected run; the caller already
    has that identity when loading host data. Cached facts retain their reported verdict,
    with freshness visible on every row and in inspection. No metrics, check counts, or
    summary completion are used to populate stages. *)
let summary_rows (summary : Asic.Summary.t) =
  let freshness, freshness_role = freshness_label summary.freshness in
  let details =
    [ "Run: " ^ run_identity summary.run
    ; "Freshness: " ^ freshness
    ; "Observed at: " ^ summary.observed_at
    ; "Source digest: " ^ summary.source_digest
    ; "Execution file: " ^ summary.execution_file
    ; "Producer: " ^ summary.producer
    ]
    @
    match summary.freshness with
    | Refresh_failed reason -> [ "Refresh error: " ^ reason ]
    | Validated | Cached_unverified | Missing_source -> []
  in
  let fact ?(extra = []) field label value =
    let visible = if String.is_empty value then "not reported" else value in
    let visible =
      match summary.freshness with
      | Validated -> visible
      | Cached_unverified | Missing_source | Refresh_failed _ ->
        visible ^ " (" ^ freshness ^ ")"
    in
    row ~role:(Fact.role field value) ~details:(details @ extra) label visible
  in
  row ~role:freshness_role ~details "Freshness" freshness
  ::
  (match summary.terminal with
   | None ->
     [ fact Summary_completion "Outcome (agg.)" summary.completion
     ; fact Verdict "Accept (agg.)" summary.acceptance
     ; row ~role:Muted ~details "Terminal result" "not imported"
     ]
   | Some terminal ->
     let extra =
       [ "Finalization attempt: " ^ terminal.attempt
       ; "Results file: " ^ terminal.results_file
       ; "Results digest: " ^ terminal.results_digest
       ]
     in
     [ fact ~extra Operation "Operation (agg.)" terminal.operation_status
     ; fact ~extra Physical_completion "Physical (agg.)" terminal.physical_completion
     ; fact ~extra Verdict "Accept (agg.)" terminal.acceptance
     ; fact ~extra Verdict "Timing (agg.)" terminal.timing_goal
     ]
     @
     if List.is_empty terminal.checks
     then
       [ row ~role:Muted ~details:(details @ extra) "Checks (aggregate)" "not reported" ]
     else
       List.map terminal.checks ~f:(fun (check : Asic.Check.t) ->
         fact
           ~extra:
             (extra
              @ Option.to_list
                  (Option.map check.reason ~f:(fun reason -> "Reason: " ^ reason))
              @ Option.to_list
                  (Option.map check.source ~f:(fun source -> "Source: " ^ source)))
           Verdict
           ("Check " ^ check.name ^ " (aggregate)")
           check.status))
;;

(** [observation] must identify its run explicitly. [expected_stages] supplies labels
    only, not a claim that work was requested. Matching is exact; extra observed stages
    are preserved. Duplicate observations are ambiguous and never produce a pass. *)
let stage_rows ?(expected_stages = default_stages) ~selected_run ~asic ~observation () =
  let observed =
    match selected_run, observation with
    | Some selected, Some (run, stages) when Run_ref.equal selected run -> stages
    | _ -> []
  in
  (* Preserve the requested checklist order, followed by any provider-specific names. *)
  let names =
    List.stable_dedup
      (expected_stages @ List.map observed ~f:(fun (s : Stage.t) -> s.name))
      ~compare:String.compare
  in
  let missing_reason =
    match selected_run, observation with
    | None, _ -> "No run selected"
    | Some selected, Some (run, _) when not (Run_ref.equal selected run) ->
      "Stage observation belongs to another run"
    | Some _, _ -> "No explicit stage status reported"
  in
  let checklist =
    List.map names ~f:(fun name ->
      match List.filter observed ~f:(fun s -> String.equal s.name name) with
      | [ stage ] -> stage_row stage
      | stages ->
        row
          ~role:Muted
          ~status:Unknown
          ~details:
            [ (if List.is_empty stages
               then missing_reason
               else "Conflicting/duplicate stage observations; inspect source")
            ]
          name
          (Status.label Unknown))
  in
  let process =
    match selected_run, asic with
    | Some run, Some (snapshot : Asic.Snapshot.t) ->
      (match List.find snapshot.runs ~f:(fun r -> Run_ref.equal r.run run) with
       | None -> [ row ~role:Muted "Observation" "selected run unavailable" ]
       | Some execution ->
         [ row
             ~role:Muted
             ~details:
               ([ "Run: " ^ run_identity run; "Process observation, not stage evidence" ]
                @ Option.to_list execution.error)
             "Process"
             (if String.is_empty execution.status
              then "not reported"
              else execution.status)
         ])
    | Some _, None -> [ row ~role:Muted "Observation" "ASIC not loaded" ]
    | None, _ -> [ row ~role:Muted "Run" "none selected" ]
  in
  checklist @ process
;;

(** Registry names are authoritative. Missing standard destinations are visible but have
    no [workspace] target; the parent can disable input or offer creation. *)
let navigation_rows ~(snapshot : Workspace.Snapshot.t) ~active_workspace =
  let existing =
    List.map snapshot.workspaces ~f:(fun w ->
      let active =
        Option.value_map
          active_workspace
          ~default:false
          ~f:(Workspace.Workspace_id.equal w.id)
      in
      row
        ~role:(if active then Active else Foreground)
        ~active
        ~workspace:w.id
        ~details:
          [ "Workspace: " ^ Workspace.Workspace_id.to_string w.id
          ; "Window: " ^ Workspace.Window_id.to_string w.window
          ; "Context: " ^ Workspace.Context_id.to_string w.context
          ]
        w.name
        (if active then "active" else ""))
  in
  existing
  @ List.filter_map [ "Overview"; "Timing"; "Testing" ] ~f:(fun name ->
    if List.exists snapshot.workspaces ~f:(fun w -> String.equal w.name name)
    then None
    else Some (row ~role:Muted name "not created"))
;;

(** Connection is verbatim: no green/connected inference from an arbitrary transport
    string. Project and run are explicit host inputs, never guessed from other runs. *)
let status_rows
  ~(snapshot : Workspace.Snapshot.t)
  ~active_workspace
  ~(project : Project.t option)
  ~(selected_run : Run_ref.t option)
  ~connection
  =
  let arrangement =
    Option.bind active_workspace ~f:(fun id ->
      List.find snapshot.workspaces ~f:(fun w -> Workspace.Workspace_id.equal w.id id))
  in
  let linkage =
    match arrangement with
    | None -> row ~role:Muted "Context" "workspace unavailable"
    | Some w ->
      (match
         List.find snapshot.contexts ~f:(fun c ->
           Workspace.Context_id.equal c.id w.context)
       with
       | None -> row ~role:Warning "Context" "unavailable"
       | Some context ->
         let shared =
           Workspace.Context_id.equal context.id snapshot.main_context
           || List.count snapshot.workspaces ~f:(fun other ->
                Workspace.Context_id.equal other.context context.id)
              > 1
         in
         row
           ~details:
             [ "Context: " ^ Workspace.Context_id.to_string context.id
             ; "Workspace: " ^ Workspace.Workspace_id.to_string w.id
             ; sprintf "Selection revision: %d" context.selection_revision
             ]
           "Context"
           ((if shared then "Linked: " else "Independent: ") ^ context.name))
  in
  [ row "Connection" (if String.is_empty connection then "not reported" else connection)
  ; row
      ~details:
        (Option.to_list
           (Option.map project ~f:(fun p -> "Project: " ^ Project_id.to_string p.id)))
      "Project"
      (Option.value_map project ~default:"none open" ~f:(fun p -> p.name))
  ; linkage
  ; row
      ~details:
        (Option.to_list
           (Option.map selected_run ~f:(fun run -> "Run: " ^ run_identity run)))
      "Run"
      (Option.value_map selected_run ~default:"none selected" ~f:run_label)
  ]
;;

let marker (appearance : Appearance.t) (row : row) =
  match appearance.icons with
  | None_ -> ""
  | Ascii ->
    (match row.status with
     | Some Completed -> "[+] "
     | Some Failed -> "[x] "
     | Some Running -> "[>] "
     | Some Pending -> "[ ] "
     | Some Skipped -> "[-] "
     | Some Not_requested -> "[.] "
     | Some Unknown -> "[?] "
     | None -> if row.active then "> " else "")
  | Unicode ->
    (match row.status with
     | Some Completed -> "✓ "
     | Some Failed -> "✗ "
     | Some Running -> "▶ "
     | Some Pending -> "○ "
     | Some Skipped -> "− "
     | Some Not_requested -> "· "
     | Some Unknown -> "? "
     | None -> if row.active then "◆ " else "")
;;

(** Map roles to the host's theme, e.g. [Active -> Host_view.Role.Selection]. Full values
    and identity are available through [inspection_lines] before clipping. [title=None]
    makes a headerless tile. No nested frame or background is imposed. *)
let render ?title ~(appearance : Appearance.t) ~attrs ~width ~height rows =
  let width = Int.max 0 width
  and height = Int.max 0 height in
  let heading =
    Option.to_list
      (Option.map title ~f:(fun title ->
         let title =
           match appearance.preset with
           | Instrument -> String.uppercase title
           | Structured | Minimal | Studio | Structured_studio -> title
         in
         View.text ~attrs:(attrs Role.Heading) title))
  in
  let indent =
    match appearance.density with
    | Comfortable when width >= 30 -> " "
    | Compact | Comfortable -> ""
  in
  let content =
    List.map rows ~f:(fun row ->
      let value = if String.is_empty row.value then "" else ": " ^ row.value in
      View.text
        ~attrs:(attrs row.role)
        (indent ^ marker appearance row ^ row.label ^ value))
  in
  let view = View.vcat (List.take (heading @ content) height) in
  let view =
    View.crop
      ~r:(Int.max 0 (View.width view - width))
      ~b:(Int.max 0 (View.height view - height))
      view
  in
  View.zcat [ view; View.rectangle ~width ~height () ]
;;

let inspection_lines rows =
  List.concat_map rows ~f:(fun row ->
    (row.label ^ if String.is_empty row.value then "" else ": " ^ row.value)
    :: row.details)
;;

let%test_unit "stage outcomes preserve request and observation distinctions" =
  let check requested status expect =
    [%test_result: Status.t] (stage_status { name = "stage"; requested; status }) ~expect
  in
  check false Not_run Not_requested;
  check true Not_run Pending;
  check false Completed Completed;
  check true Running Running;
  check true (Failed { reason = "tool error" }) Failed;
  check false (Skipped { reason = "unsupported" }) Skipped
;;

let%test_unit "aggregate colors require field-specific explicit facts" =
  let check field value expect = [%test_result: Role.t] (Fact.role field value) ~expect in
  check Operation "completed" Success;
  check Verdict "completed" Muted;
  check Physical_completion "completed" Muted;
  check Physical_completion "full" Success;
  check Physical_completion "incomplete" Warning;
  check Verdict "pass" Success;
  check Verdict "fail" Failure;
  check Verdict "not_evaluated" Warning;
  check Verdict "unknown" Muted;
  check Verdict "future-provider-verdict" Muted;
  check Verdict "" Muted;
  [%test_result: string] (short_id "0123456789abcdefghijkl") ~expect:"012345...ghijkl"
;;

let%test_unit "cached summary facts retain freshness and do not acquire stage statuses" =
  let summary : Asic.Summary.t =
    { run =
        { backend = Backend_id.of_string "asic"
        ; id = "saved-run"
        ; build = None
        ; label = None
        }
    ; source_digest = "digest"
    ; execution_file = "/saved/execution.json"
    ; plan_identity = None
    ; cell_count = Some 100
    ; cells = []
    ; metrics = []
    ; terminal = None
    ; timing = []
    ; completion = "completed"
    ; acceptance = "unknown"
    ; producer = "saved producer"
    ; observed_at = "saved observation"
    ; freshness = Cached_unverified
    }
  in
  let rows = summary_rows summary in
  let completion = List.nth_exn rows 1 in
  [%test_result: Role.t] completion.role ~expect:Success;
  [%test_result: string] completion.value ~expect:"completed (cached/unverified)";
  assert (List.for_all rows ~f:(fun row -> Option.is_none row.status));
  assert (List.mem completion.details "Run: asic/saved-run" ~equal:String.equal);
  let failed = summary_rows { summary with freshness = Refresh_failed "offline" } in
  assert (
    List.mem (List.hd_exn failed).details "Refresh error: offline" ~equal:String.equal);
  let terminal : Asic.Terminal_result.t =
    { attempt = "attempt"
    ; results_file = "/saved/results.json"
    ; results_digest = "results-digest"
    ; operation_status = "completed"
    ; physical_completion = "incomplete"
    ; acceptance = "not_evaluated"
    ; timing_goal = "unknown"
    ; metrics = []
    ; checks =
        [ { name = "drc"
          ; status = "fail"
          ; reason = Some "violations"
          ; source = Some "report"
          }
        ]
    ; evidence = "{}"
    }
  in
  let terminal_rows = summary_rows { summary with terminal = Some terminal } in
  let find label =
    List.find_exn terminal_rows ~f:(fun row -> String.equal row.label label)
  in
  [%test_result: Role.t] (find "Operation (agg.)").role ~expect:Success;
  [%test_result: Role.t] (find "Physical (agg.)").role ~expect:Warning;
  [%test_result: Role.t] (find "Accept (agg.)").role ~expect:Warning;
  [%test_result: Role.t] (find "Timing (agg.)").role ~expect:Muted;
  let drc = find "Check drc (aggregate)" in
  [%test_result: Role.t] drc.role ~expect:Failure;
  assert (List.mem drc.details "Reason: violations" ~equal:String.equal);
  assert (List.mem drc.details "Source: report" ~equal:String.equal);
  assert (List.for_all terminal_rows ~f:(fun row -> Option.is_none row.status))
;;

let%test_unit "process completion is not stage evidence; mismatched and duplicate \
               observations are unknown"
  =
  let run id : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id; build = None; label = None }
  in
  let selected = run "selected" in
  let stage : Stage.t = { name = "Synthesis"; requested = true; status = Completed } in
  let asic : Asic.Snapshot.t =
    { configured = true
    ; flows = []
    ; description_json = None
    ; preview = None
    ; runs =
        [ { run = selected
          ; reference = { attempt = "attempt"; stream_id = "stream" }
          ; selection = None
          ; cursor = 0
          ; status = "completed"
          ; execution_file = None
          ; error = None
          }
        ]
    ; operations = []
    ; summaries = []
    ; finalizations = []
    ; artifacts = []
    ; artifact_pages = []
    ; cache_error = None
    }
  in
  let check observation expect =
    let rows =
      stage_rows
        ~expected_stages:[ "Synthesis" ]
        ~selected_run:(Some selected)
        ~asic:(Some asic)
        ~observation
        ()
    in
    [%test_result: Status.t option] (List.hd_exn rows).status ~expect:(Some expect)
  in
  check None Unknown;
  check (Some (run "other", [ stage ])) Unknown;
  check (Some (selected, [ stage; stage ])) Unknown;
  check (Some (selected, [ stage ])) Completed
;;

let%test_unit "navigation retains registry identities and missing destinations are not \
               actionable"
  =
  let snapshot =
    Workspace.initial ~session_id:(Workspace.Session_id.of_string "session")
  in
  let active = (List.hd_exn snapshot.workspaces).id in
  let rows = navigation_rows ~snapshot ~active_workspace:(Some active) in
  let overview = List.find_exn rows ~f:(fun row -> String.equal row.label "Overview") in
  assert overview.active;
  assert (Option.equal Workspace.Workspace_id.equal overview.workspace (Some active));
  let testing = List.find_exn rows ~f:(fun row -> String.equal row.label "Testing") in
  assert (Option.is_none testing.workspace);
  assert (not testing.active);
  [%test_result: string] testing.value ~expect:"not created"
;;
