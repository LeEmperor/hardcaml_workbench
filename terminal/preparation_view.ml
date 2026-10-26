open! Core
open Hardcaml_workbench_protocol
module O = Overview_tiles

module Rtl_scope = struct
  type t =
    { project : Project_id.t
    ; target : Target_id.t
    ; configuration : Configuration_id.t
    }

  let create ~(project : Project.t option) ~target ~configuration =
    Option.bind project ~f:(fun p ->
      Option.bind target ~f:(fun target ->
        Option.bind configuration ~f:(fun configuration ->
          if Option.is_some (Project.target p target)
             && List.exists p.configurations ~f:(fun c ->
               Configuration_id.equal c.id configuration
               && Target_id.equal c.target target)
          then Some { project = p.id; target; configuration }
          else None)))
  ;;
end

let latest_rtl ~scope ~jobs =
  Option.bind scope ~f:(fun (s : Rtl_scope.t) ->
    State.latest_generation
      jobs
      ~project:s.project
      ~target:s.target
      ~configuration:s.configuration)
;;

let active (a : Preparation.Attempt.t) =
  match a.outcome with
  | Building | Emitting -> true
  | _ -> false
;;

let outcome = function
  | Preparation.Outcome.Building -> O.Status.Running
  | Emitting -> Running
  | Completed -> Completed
  | Build_failed | Emission_failed -> Failed
  | Cancelled -> Cancelled
;;

let outcome_label : Preparation.Outcome.t -> string = function
  | Building -> "building"
  | Emitting -> "emitting elaboration bundle"
  | Completed -> "completed"
  | Build_failed -> "build failed"
  | Emission_failed -> "emission failed"
  | Cancelled -> "cancelled"
;;

let unrequested_status = function
  | Some { Preparation.Snapshot.availability = Available; _ } -> O.Status.Not_requested
  | None | Some { availability = Unavailable _; _ } -> O.Status.Unsupported
;;

let checklist_status snapshot =
  Option.bind snapshot ~f:(fun (s : Preparation.Snapshot.t) -> s.latest)
  |> Option.value_map ~default:(unrequested_status snapshot) ~f:(fun a ->
    outcome a.outcome)
;;

let status_label = function
  | O.Status.Unsupported -> "unavailable"
  | status -> O.Status.label status
;;

let job_status (j : Job.t) : O.Status.t =
  match j.state with
  | Queued -> Pending
  | Starting | Running -> Running
  | Complete -> Completed
  | Failed -> Failed
  | Cancelled -> Cancelled
;;

let attempts snapshot =
  Option.value_map snapshot ~default:[] ~f:(fun (s : Preparation.Snapshot.t) ->
    Option.to_list s.latest @ s.history
    |> List.stable_dedup ~compare:(fun a b ->
      String.compare a.Preparation.Attempt.id b.id))
;;

let selected snapshot cursor =
  let all = attempts snapshot in
  Option.first_some
    (Option.bind cursor ~f:(fun id -> List.find all ~f:(fun a -> String.equal a.id id)))
    (List.hd all)
;;

let selection ~remembered ~(asic : Asic.Snapshot.t option) =
  let chosen =
    match remembered with
    | Some s -> Ok s
    | None ->
      (match Option.bind asic ~f:(fun s -> s.catalog_default) with
       | None -> Error "Choose current flow/profile/overrides in Plan first"
       | Some p ->
         let endpoint =
           Option.bind asic ~f:(fun a ->
             List.find a.flows ~f:(fun f -> String.equal f.id p.flow))
           |> Option.bind ~f:(fun f ->
             if List.mem f.fresh_stage_endpoints "synthesis" ~equal:String.equal
             then Some "synthesis"
             else List.hd f.fresh_stage_endpoints)
         in
         (match endpoint with
          | None -> Error "Choose an explicit selected-flow endpoint in Plan first"
          | Some endpoint ->
            Ok
              { Asic.Selection.flow = p.flow
              ; profile = p.profile
              ; endpoint
              ; assignments = []
              }))
  in
  (* Explicit current-project inputs can be built before an ASIC catalog exists. The
     freshly built selected-flow publisher validates them authoritatively. *)
  chosen
;;

let prepare ~snapshot ~selection ~submission_key ~expected_plan_identity =
  match snapshot, selection with
  | Some { Preparation.Snapshot.availability = Available; latest; _ }, Ok selection
    when not (Option.exists latest ~f:active) ->
    Ok
      (Preparation.Operation.Prepare { submission_key; selection; expected_plan_identity })
  | Some { availability = Unavailable _; _ }, _ ->
    Error "Preparation unavailable (configuration)"
  | None, _ -> Error "Preparation capability unavailable or not loaded"
  | _, Error reason -> Error reason
  | _ -> Error "Preparation already active"
;;

let attempt_details (a : Preparation.Attempt.t) =
  [ "Selection: "
    ^ a.selection.flow
    ^ " / "
    ^ a.selection.profile
    ^ " / endpoint "
    ^ a.selection.endpoint
  ; "Overrides: " ^ String.concat ~sep:"; " a.selection.assignments
  ; "Selection identity: " ^ a.selection_identity
  ; "Expected plan: " ^ Option.value a.expected_plan_identity ~default:"none"
  ; "Source root: " ^ a.source_root
  ; "Build target: " ^ a.build_target
  ; "Source executable: " ^ a.source_executable
  ; "Results root: " ^ a.results_root
  ; "Timeout: " ^ Int.to_string a.timeout_seconds ^ " seconds"
  ; "Environment: " ^ Sexp.to_string (V1.Environment_selection.sexp_of_t a.environment)
  ; "Created: " ^ Sexp.to_string (Timestamp.sexp_of_t a.created_at)
  ; "Outcome: " ^ outcome_label a.outcome
  ]
  @ Option.to_list (Option.map a.diagnostic ~f:(fun d -> "Diagnostic: " ^ d))
  @ Option.value_map a.bundle ~default:[] ~f:(fun b ->
    [ "Bundle: " ^ b.bundle_identity
    ; "Plan: " ^ b.plan_identity
    ; "Output directory: " ^ b.output_dir
    ; "Reused: " ^ Bool.to_string b.reused
    ]
    @ List.map b.artifacts ~f:(fun id ->
      "Artifact (palette opens exact handle): " ^ Artifact_id.to_string id))
;;

let rows ~snapshot ~jobs ~project ~rtl_scope ~cursor ~detail ~log_lines =
  let row status label value details =
    O.row ~status ~role:(O.status_role status) ~details label value
  in
  let scope =
    "Current project; independent of selected historical ASIC run; session-only history"
  in
  let stage label job =
    match job with
    | None -> row O.Status.Not_requested label "not requested" [ scope ]
    | Some (j : Job.t) ->
      let status = job_status j in
      row
        status
        label
        (O.Status.label status)
        ([ "Job: " ^ Job_id.to_string j.id
         ; "Process exit: "
           ^ Option.value_map j.exit_status ~default:"not reported" ~f:(fun s ->
             Sexp.to_string (Job.Exit_status.sexp_of_t s))
         ]
         @ Option.to_list
             (Option.map j.failure ~f:(fun reason -> "Job failure: " ^ reason))
         @ log_lines j.id)
  in
  let verification =
    List.filter jobs ~f:(fun (j : Job.t) ->
      Option.exists project ~f:(Project_id.equal j.project)
      && String.equal j.kind.namespace "dune"
      && String.equal j.kind.name "test")
    |> List.max_elt ~compare:(fun a b -> Timestamp.compare a.created_at b.created_at)
  in
  let all = attempts snapshot in
  let generic_build =
    List.filter jobs ~f:(fun (j : Job.t) ->
      Option.exists project ~f:(Project_id.equal j.project)
      && String.equal j.kind.namespace "dune"
      && String.equal j.kind.name "build")
    |> List.max_elt ~compare:(fun a b -> Timestamp.compare a.created_at b.created_at)
  in
  let current = if detail then selected snapshot cursor else List.hd all in
  let availability =
    match snapshot with
    | None -> "capability unavailable / not loaded"
    | Some { availability = Unavailable Not_configured; _ } ->
      "unavailable: not configured"
    | Some { availability = Unavailable (Invalid_configuration reason); _ } ->
      "unavailable: " ^ reason
    | Some _ -> "not requested / no session history"
  in
  let result =
    match current with
    | None ->
      [ O.row ~role:Muted "Preparation" availability
      ; stage "Build (generic dune.build)" generic_build
      ; row
          (unrequested_status snapshot)
          "Elaboration-bundle emission"
          (status_label (unrequested_status snapshot))
          [ scope; availability ]
      ]
    | Some a ->
      let details =
        [ scope
        ; "Session-only: "
          ^ Bool.to_string
              (Option.value_map snapshot ~default:true ~f:(fun s -> s.session_only))
        ; "Requested attempt: "
          ^ Option.value
              (Option.bind snapshot ~f:(fun s -> s.requested_attempt))
              ~default:"none"
        ]
      in
      [ row
          (outcome a.outcome)
          "Project attempt"
          (a.id ^ " — " ^ outcome_label a.outcome)
          details
      ; stage "Build" a.build_job
      ; (let r = stage "Elaboration-bundle emission" a.emission_job in
         { r with
           details = r.details @ attempt_details a
         ; value =
             r.value
             ^ Option.value_map a.bundle ~default:"" ~f:(fun b ->
               " / bundle " ^ b.bundle_identity)
         })
      ]
  in
  let result =
    result
    @ [ (let r = stage "Verification (project test command)" verification in
         { r with
           value =
             (if Option.equal O.Status.equal r.status (Some Completed)
              then "process succeeded"
              else r.value)
         ; details = "Process success is not semantic test pass" :: r.details
         })
      ]
  in
  let result =
    match current, latest_rtl ~scope:rtl_scope ~jobs, rtl_scope with
    | None, Some job, Some selected ->
      let generic = stage "Generic RTL (not ASIC bundle)" (Some job) in
      result
      @ [ { generic with
            details =
              [ "Observed generate-rtl process for the exact current selected \
                 target/configuration"
              ; "Target: " ^ Target_id.to_string selected.target
              ; "Configuration: " ^ Configuration_id.to_string selected.configuration
              ; "Generic RTL generation is not selected-flow ASIC bundle publication"
              ; "This job is evidence of an invocation, not an advertisement of future \
                 driver capabilities"
              ]
              @ generic.details
              @ List.map job.artifacts ~f:(fun id ->
                "RTL artifact (palette opens exact handle): " ^ Artifact_id.to_string id)
          }
        ]
    | _ -> result
  in
  let result =
    match detail, Option.bind snapshot ~f:(fun s -> s.latest), current with
    | true, Some latest, Some inspected when not (String.equal latest.id inspected.id) ->
      row
        (outcome latest.outcome)
        "Latest project attempt"
        (latest.id ^ " — " ^ outcome_label latest.outcome)
        [ "Inspecting historical attempt "
          ^ inspected.id
          ^ "; latest outcome remains authoritative"
        ]
      :: result
    | _ -> result
  in
  if not detail
  then result
  else
    result
    @ [ O.row
          ~role:Muted
          "Controls"
          "j/k attempts; Enter inspect; r prepare; x cancel; a artifact"
      ]
    @ List.map all ~f:(fun a ->
      row (outcome a.outcome) "History" a.id (attempt_details a))
    @ (List.filter jobs ~f:(fun (j : Job.t) ->
         Option.exists project ~f:(Project_id.equal j.project)
         && String.equal j.kind.namespace "dune"
         && String.equal j.kind.name "test")
       |> List.map ~f:(fun j -> stage "Verification process history" (Some j)))
;;

let fixture_attempt id outcome : Preparation.Attempt.t =
  let job name state =
    { (Job.create
         ~id:(Job_id.of_string (id ^ "/" ^ name))
         ~kind:{ namespace = "preparation"; name }
         ~project:(Project_id.of_string "project")
         ~created_at:(Timestamp.of_time_ns Time_ns.epoch))
      with
      state
    }
  in
  { id
  ; selection =
      { flow = "flow"
      ; profile = "profile"
      ; endpoint = "routing"
      ; assignments = [ "X=a b" ]
      }
  ; selection_identity = "selection"
  ; expected_plan_identity = Some "plan"
  ; source_root = "/source"
  ; build_target = "source.exe"
  ; source_executable = "_build/default/source.exe"
  ; results_root = "/results"
  ; timeout_seconds = 10
  ; environment = Inherit_daemon
  ; created_at = Timestamp.of_time_ns Time_ns.epoch
  ; outcome
  ; build_job = Some (job "build" Complete)
  ; emission_job =
      Some
        (job
           "emit"
           (match outcome with
            | Completed -> Complete
            | Cancelled -> Cancelled
            | Emitting -> Running
            | _ -> Failed))
  ; bundle =
      (match outcome with
       | Completed ->
         Some
           { bundle_identity = "bundle-" ^ id
           ; plan_identity = "plan"
           ; output_dir = "/bundle"
           ; reused = false
           ; plan_json = "{}"
           ; artifacts = [ Artifact_id.of_string (id ^ "/artifact") ]
           }
       | _ -> None)
  ; diagnostic = None
  }
;;

let fixture_snapshot () : Preparation.Snapshot.t =
  { availability = Available
  ; session_only = true
  ; requested_attempt = None
  ; latest = Some (fixture_attempt "new-failure" Emission_failed)
  ; history =
      [ fixture_attempt "new-failure" Emission_failed
      ; fixture_attempt "old-success" Completed
      ]
  }
;;

let%test_unit "preparation preserves failed headline, completed build, exact logs and \
               prior publication"
  =
  let snapshot = Some (fixture_snapshot ()) in
  let rows =
    rows
      ~snapshot
      ~jobs:[]
      ~project:None
      ~rtl_scope:None
      ~cursor:None
      ~detail:false
      ~log_lines:(fun id -> [ "exact log " ^ Job_id.to_string id ])
  in
  assert (Option.equal O.Status.equal (List.hd_exn rows).status (Some Failed));
  assert (Option.equal O.Status.equal (List.nth_exn rows 1).status (Some Completed));
  assert (Option.equal O.Status.equal (List.nth_exn rows 2).status (Some Failed));
  assert (
    List.mem
      (List.nth_exn rows 1).details
      "exact log new-failure/build"
      ~equal:String.equal);
  assert (
    List.mem
      (List.nth_exn rows 2).details
      "exact log new-failure/emit"
      ~equal:String.equal);
  let old = selected snapshot (Some "old-success") |> Option.value_exn in
  assert (Option.is_some old.bundle);
  assert (List.length (attempts snapshot) = 2);
  assert (O.Status.equal (outcome Cancelled) Cancelled)
;;

let%test_unit "preparation guards capability, availability, activity and captures exact \
               inputs without physical Run"
  =
  let s = fixture_snapshot () in
  let captured = (fixture_attempt "captured" Completed).selection in
  let prepare snapshot selection =
    prepare
      ~snapshot
      ~selection
      ~submission_key:"key"
      ~expected_plan_identity:(Some "exact-plan")
  in
  (match prepare (Some s) (Ok captured) with
   | Ok (Prepare p) ->
     assert (Asic.Selection.equal p.selection captured);
     assert (Option.equal String.equal p.expected_plan_identity (Some "exact-plan"))
   | _ -> assert false);
  assert (Result.is_error (prepare None (Ok captured)));
  assert (
    Result.is_error
      (prepare (Some { s with availability = Unavailable Not_configured }) (Ok captured)));
  assert (
    Result.is_error
      (prepare
         (Some { s with latest = Some (fixture_attempt "active" Emitting) })
         (Ok captured)));
  assert (Result.is_error (prepare (Some s) (Error "no selection")));
  assert (
    Asic.Selection.equal
      (Result.ok_or_failwith (selection ~remembered:(Some captured) ~asic:None))
      captured);
  assert (Result.is_error (selection ~remembered:None ~asic:None));
  let rows =
    rows
      ~snapshot:(Some { s with latest = None; history = [] })
      ~jobs:[]
      ~project:None
      ~rtl_scope:None
      ~cursor:None
      ~detail:false
      ~log_lines:(fun _ -> [])
  in
  assert (String.is_substring (List.hd_exn rows).value ~substring:"no session history")
;;
