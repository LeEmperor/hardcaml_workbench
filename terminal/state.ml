open! Core
open Hardcaml_workbench_protocol

let replace projects ~equal ~value =
  value :: List.filter projects ~f:(fun existing -> not (equal existing value))
;;

let remove values ~matches = List.filter values ~f:(Fn.non matches)

let apply_event (snapshot : V1.Snapshot.Payload.t) = function
  | V1.Event.Project_upsert project ->
    { snapshot with
      projects =
        replace snapshot.projects ~value:project ~equal:(fun existing value ->
          Project_id.equal existing.Project.id value.Project.id)
    }
  | Project_removed id ->
    { snapshot with
      projects =
        remove snapshot.projects ~matches:(fun project -> Project_id.equal project.id id)
    }
  | Job_upsert job ->
    { snapshot with
      jobs =
        replace snapshot.jobs ~value:job ~equal:(fun existing value ->
          Job_id.equal existing.Job.id value.Job.id)
    }
  | Job_removed id ->
    { snapshot with
      jobs = remove snapshot.jobs ~matches:(fun job -> Job_id.equal job.id id)
    }
  | Artifact_upsert artifact ->
    { snapshot with
      artifacts =
        replace snapshot.artifacts ~value:artifact ~equal:(fun existing value ->
          Artifact_id.equal existing.Artifact.id value.Artifact.id)
    }
  | Artifact_removed id ->
    { snapshot with
      artifacts =
        remove snapshot.artifacts ~matches:(fun artifact ->
          Artifact_id.equal artifact.id id)
    }
  | Log_available _ -> snapshot
;;

let apply_updates (snapshot : V1.Snapshot.Payload.t) (updates : V1.Updates.Payload.t) =
  if not
       (V1.Daemon_instance_id.equal
          snapshot.cursor.instance_id
          updates.next_cursor.instance_id)
  then Or_error.error_string "update cursor belongs to another daemon instance"
  else (
    let result =
      List.fold_until
        updates.events
        ~init:(snapshot, snapshot.cursor.sequence)
        ~f:(fun (snapshot, sequence) event ->
          if event.V1.Event.sequence <= sequence
          then Continue (snapshot, sequence)
          else if event.sequence <> sequence + 1
          then Stop (Or_error.error_string "incremental update sequence has a gap")
          else Continue (apply_event snapshot event.event, event.sequence))
        ~finish:Result.return
    in
    match result with
    | Error _ as error -> error
    | Ok (snapshot, sequence) ->
      if sequence <> updates.next_cursor.sequence
      then
        Or_error.error_string "incremental update cursor disagrees with its event batch"
      else Ok { snapshot with cursor = updates.next_cursor })
;;

let current_project ~opened (snapshot : V1.Snapshot.Payload.t) =
  match opened with
  | None -> None
  | Some opened ->
    (match
       List.find snapshot.projects ~f:(fun project ->
         Project_id.equal project.Project.id opened.V1.Open_project.Payload.project.id)
     with
     | Some project -> Some project
     | None -> Some opened.project)
;;

let add_job_if_absent (snapshot : V1.Snapshot.Payload.t) (job : Job.t) =
  if List.exists snapshot.jobs ~f:(fun existing -> Job_id.equal existing.id job.id)
  then snapshot
  else { snapshot with jobs = job :: snapshot.jobs }
;;

let test_instance = V1.Daemon_instance_id.of_string "daemon"
let test_project_id name = Project_id.of_string ("daemon/project/" ^ name)

let test_project ?(targets = []) ?(configurations = []) ~id ~name ~driver () : Project.t =
  { id
  ; root = Project_root.of_absolute_path ("/tmp/" ^ name)
  ; name
  ; integration =
      { level =
          Project_integration.level_of_components
            ~manifest:(Available { version = Some 1 })
            ~driver
      ; manifest = Available { version = Some 1 }
      ; driver
      }
  ; targets
  ; configurations
  }
;;

let test_snapshot projects jobs sequence : V1.Snapshot.Payload.t =
  { projects; jobs; artifacts = []; cursor = { instance_id = test_instance; sequence } }
;;

let test_opened project : V1.Open_project.Payload.t =
  { project
  ; environment =
      { selection = Inherit_daemon
      ; provenance = "test"
      ; dune_version = "3.24.2"
      ; command_prefix = []
      }
  ; workspace = { contexts = []; items = [] }
  }
;;

let test_updates snapshot events =
  let sequence =
    List.last events
    |> Option.value_map
         ~default:snapshot.V1.Snapshot.Payload.cursor.sequence
         ~f:(fun event -> event.V1.Event.sequence)
  in
  apply_updates
    snapshot
    { events
    ; next_cursor = { instance_id = test_instance; sequence }
    ; heartbeat = List.is_empty events
    }
  |> Or_error.ok_exn
;;

let sequenced sequence event : V1.Event.sequenced = { sequence; event }

let%test_unit "live discovery events replace the pending project in the attached session" =
  let project_id = test_project_id "selected" in
  let pending =
    test_project
      ~id:project_id
      ~name:"fixture"
      ~driver:(Unusable { reason = "driver discovery pending" })
      ()
  in
  let opened = test_opened pending in
  let target : Target.t =
    { id = Target_id.of_string "daemon/project/selected/target/counter"
    ; name = "Four-bit counter"
    ; top = "counter"
    ; backend = Backend_id.of_string "simulation"
    ; clocks = []
    ; facts = []
    }
  in
  let configuration : Configuration.t =
    { id = Configuration_id.of_string "daemon/project/selected/configuration/default"
    ; target = target.id
    ; name = "Default four-bit counter"
    ; description = None
    }
  in
  let available =
    test_project
      ~id:project_id
      ~name:"fixture"
      ~driver:(Available { version = Some 1 })
      ~targets:[ target ]
      ~configurations:[ configuration ]
      ()
  in
  let job =
    { (Job.create
         ~id:(Job_id.of_string "discovery-job")
         ~kind:{ namespace = "project-driver"; name = "describe" }
         ~project:project_id
         ~created_at:(Timestamp.of_time_ns Time_ns.epoch))
      with
      state = Complete
    ; exit_status = Some (Exited 0)
    }
  in
  let snapshot = test_snapshot [ pending ] [] 10 in
  let snapshot =
    test_updates
      snapshot
      [ sequenced 11 (Project_upsert available); sequenced 12 (Job_upsert job) ]
  in
  let selected = current_project ~opened:(Some opened) snapshot |> Option.value_exn in
  assert (Project.equal selected available);
  assert (List.length selected.targets = 1);
  assert (List.length selected.configurations = 1)
;;

let%test_unit "project and job event ordering cannot restore stale discovery" =
  let project_id = test_project_id "ordering" in
  let pending =
    test_project
      ~id:project_id
      ~name:"ordering"
      ~driver:(Unusable { reason = "pending" })
      ()
  in
  let available =
    test_project
      ~id:project_id
      ~name:"changed target"
      ~driver:(Available { version = Some 1 })
      ()
  in
  let complete =
    { (Job.create
         ~id:(Job_id.of_string "ordering-job")
         ~kind:{ namespace = "project-driver"; name = "describe" }
         ~project:project_id
         ~created_at:(Timestamp.of_time_ns Time_ns.epoch))
      with
      state = Complete
    }
  in
  let snapshot = test_snapshot [ pending ] [] 0 in
  let job_first = test_updates snapshot [ sequenced 1 (Job_upsert complete) ] in
  assert (Project.equal (List.hd_exn job_first.projects) pending);
  let finished = test_updates job_first [ sequenced 2 (Project_upsert available) ] in
  assert (Project.equal (List.hd_exn finished.projects) available)
;;

let%test_unit "changed and failed refresh events replace only their project" =
  let selected_id = test_project_id "selected" in
  let other_id = test_project_id "other" in
  let target name : Target.t =
    { id = Target_id.of_string ("daemon/project/selected/target/" ^ name)
    ; name
    ; top = "counter"
    ; backend = Backend_id.of_string "simulation"
    ; clocks = []
    ; facts = []
    }
  in
  let old_target = target "old-target" in
  let changed_target = target "changed-target" in
  let configuration target name : Configuration.t =
    { id = Configuration_id.of_string ("daemon/project/selected/configuration/" ^ name)
    ; target = target.Target.id
    ; name
    ; description = None
    }
  in
  let old =
    test_project
      ~id:selected_id
      ~name:"old discovery"
      ~driver:(Available { version = Some 1 })
      ~targets:[ old_target ]
      ~configurations:[ configuration old_target "old-configuration" ]
      ()
  in
  let other =
    test_project
      ~id:other_id
      ~name:"other project"
      ~driver:(Available { version = Some 1 })
      ()
  in
  let changed =
    { old with
      name = "changed discovery"
    ; targets = [ changed_target ]
    ; configurations = [ configuration changed_target "changed-configuration" ]
    }
  in
  let failed =
    { changed with
      integration =
        { changed.integration with
          level = Manifest
        ; driver = Unusable { reason = "malformed driver output" }
        }
    ; targets = []
    ; configurations = []
    }
  in
  let snapshot = test_snapshot [ old; other ] [] 20 in
  let opened = test_opened old in
  let other_changed = { other with name = "updated other project" } in
  let snapshot = test_updates snapshot [ sequenced 21 (Project_upsert other_changed) ] in
  assert (
    Project.equal (current_project ~opened:(Some opened) snapshot |> Option.value_exn) old);
  let snapshot = test_updates snapshot [ sequenced 22 (Project_upsert changed) ] in
  assert (
    Project.equal
      (List.find_exn snapshot.projects ~f:(fun p -> Project_id.equal p.id selected_id))
      changed);
  assert (
    Project.equal
      (List.find_exn snapshot.projects ~f:(fun p -> Project_id.equal p.id other_id))
      other_changed);
  let snapshot = test_updates snapshot [ sequenced 23 (Project_upsert failed) ] in
  let selected =
    List.find_exn snapshot.projects ~f:(fun p -> Project_id.equal p.id selected_id)
  in
  assert (List.is_empty selected.targets && List.is_empty selected.configurations);
  assert (
    match selected.integration.driver with
    | Unusable { reason } -> String.equal reason "malformed driver output"
    | Absent | Available _ -> false);
  let duplicate = test_updates snapshot [ sequenced 23 (Project_upsert changed) ] in
  assert (V1.Snapshot.Payload.equal duplicate snapshot);
  assert (
    Result.is_error
      (apply_updates
         snapshot
         { events = [ sequenced 25 (Project_upsert changed) ]
         ; next_cursor = { instance_id = test_instance; sequence = 25 }
         ; heartbeat = false
         }))
;;
