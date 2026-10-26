open! Core
open Hardcaml_workbench_protocol
module H = Workspace_host
module O = Overview_tiles

let%test_unit "emission and checklist distinguish unavailable from supported not \
               requested, including no selected ASIC run"
  =
  let host, data, find =
    Host_view.refinement_fixture Hardcaml_workbench_workspaces.Overview.definition
  in
  let empty =
    { (Preparation_view.fixture_snapshot ()) with latest = None; history = [] }
  in
  let cases =
    [ None, O.Status.Unsupported
    ; Some { empty with availability = Unavailable Not_configured }, Unsupported
    ; ( Some
          { empty with
            availability = Unavailable (Invalid_configuration "invalid fixture")
          }
      , Unsupported )
    ; Some empty, Not_requested
    ]
  in
  List.iter cases ~f:(fun (snapshot, expected) ->
    let host = { host with preparation = snapshot } in
    let check rows label =
      let row = List.find_exn rows ~f:(fun r -> String.equal r.O.label label) in
      assert (Option.equal O.Status.equal row.status (Some expected));
      assert (String.equal row.value (Preparation_view.status_label expected))
    in
    check
      (Host_view.utility_rows host data (find "preparation") |> Option.value_exn)
      "Elaboration-bundle emission";
    check
      (Host_view.utility_rows host data (find "stage-checklist") |> Option.value_exn)
      "Elaboration";
    let registry = Option.value_exn host.registry in
    let registry =
      { registry with
        contexts = List.map registry.contexts ~f:(fun c -> { c with selected_run = None })
      }
    in
    check
      (Host_view.utility_rows
         { host with registry = Some registry }
         data
         (find "stage-checklist")
       |> Option.value_exn)
      "Elaboration")
;;

let%test_unit "generic RTL fallback is bounded to latest exact selected project target \
               configuration and never publishes an ASIC bundle"
  =
  let target : Target.t =
    { id = Target_id.of_string "target"
    ; name = "target"
    ; top = "top"
    ; backend = Backend_id.of_string "generic"
    ; clocks = []
    ; facts = []
    }
  in
  let configuration : Configuration.t =
    { id = Configuration_id.of_string "configuration"
    ; target = target.id
    ; name = "configuration"
    ; description = None
    }
  in
  let project =
    State.test_project
      ~id:(Project_id.of_string "project")
      ~name:"generic"
      ~driver:(Available { version = Some 1 })
      ~targets:[ target ]
      ~configurations:[ configuration ]
      ()
  in
  let scope =
    Preparation_view.Rtl_scope.create
      ~project:(Some project)
      ~target:(Some target.id)
      ~configuration:(Some configuration.id)
  in
  assert (Option.is_some scope);
  assert (
    Option.is_none
      (Preparation_view.Rtl_scope.create
         ~project:(Some project)
         ~target:(Some (Target_id.of_string "other"))
         ~configuration:(Some configuration.id)));
  let job id time state =
    { (Job.create
         ~id:(Job_id.of_string id)
         ~kind:{ namespace = "project-driver"; name = "generate-rtl" }
         ~project:project.id
         ~created_at:(Timestamp.of_time_ns (Time_ns.of_int_ns_since_epoch time)))
      with
      target = Some target.id
    ; configuration = Some configuration.id
    ; state
    ; artifacts = [ Artifact_id.of_string (id ^ "/rtl") ]
    }
  in
  let old = job "old-success" 1 Complete
  and failed = job "latest-failure" 2 Failed in
  let foreign =
    { (job "other-project" 3 Complete) with project = Project_id.of_string "elsewhere" }
  in
  let other_config =
    { (job "other-config" 4 Complete) with
      configuration = Some (Configuration_id.of_string "elsewhere")
    }
  in
  let generic_build =
    { (job "generic-build" 5 Complete) with
      kind = { namespace = "dune"; name = "build" }
    }
  in
  let jobs = [ old; foreign; failed; other_config; generic_build ] in
  let rows scope jobs =
    Preparation_view.rows
      ~snapshot:None
      ~jobs
      ~project:(Some project.id)
      ~rtl_scope:scope
      ~cursor:None
      ~detail:false
      ~log_lines:(fun id -> [ "RTL LOG " ^ Job_id.to_string id ])
  in
  let projected = rows scope jobs in
  let rtl = List.last_exn projected in
  assert (String.equal rtl.label "Generic RTL (not ASIC bundle)");
  assert (Option.equal O.Status.equal rtl.status (Some Failed));
  assert (List.mem rtl.details "RTL LOG latest-failure" ~equal:String.equal);
  assert (
    List.exists rtl.details ~f:(fun s ->
      String.is_substring s ~substring:"latest-failure/rtl"));
  let emission =
    List.find_exn projected ~f:(fun r ->
      String.equal r.O.label "Elaboration-bundle emission")
  in
  assert (Option.equal O.Status.equal emission.status (Some Unsupported));
  assert (List.length (rows None jobs) = 4);
  (* Available driver component/declared target alone is not a generate-rtl capability
     advertisement. *)
  assert (List.length (rows scope []) = 4);
  List.iter
    [ Job.State.Queued; Starting; Running; Complete; Failed; Cancelled ]
    ~f:(fun state ->
      let r = List.last_exn (rows scope [ job "observed" 1 state ]) in
      assert (
        Option.equal
          O.Status.equal
          r.status
          (Some (Preparation_view.job_status (job "observed" 1 state)))))
;;

let%test_unit "preparation input form captures exact selected inputs and rejects stale \
               captured workspace"
  =
  let host, _, _ =
    Host_view.refinement_fixture Hardcaml_workbench_workspaces.Overview.definition
  in
  let capture = H.capture host |> Option.value_exn in
  let form capture =
    { host with
      H.palette =
        Some
          { capture
          ; commands = []
          ; query = "routing X=1 Y=exact"
          ; index = 0
          ; argument = Some (H.Preparation_inputs ("chosen-flow", "chosen-profile"))
          }
    }
  in
  (match snd (H.input (form capture) Enter ~commands:[]) with
   | Execute (_, Select_preparation selection) ->
     assert (
       Asic.Selection.equal
         selection
         { flow = "chosen-flow"
         ; profile = "chosen-profile"
         ; endpoint = "routing"
         ; assignments = [ "X=1"; "Y=exact" ]
         })
   | _ -> assert false);
  match
    snd
      (H.input (form { capture with revision = capture.revision - 1 }) Enter ~commands:[])
  with
  | No_effect -> ()
  | _ -> assert false
;;

let%test_unit "preparation tile keyboard inspection and history preserve stage logs and \
               physical run isolation"
  =
  let host, data, find =
    Host_view.refinement_fixture Hardcaml_workbench_workspaces.Overview.definition
  in
  let tile = find "preparation" in
  let snapshot = Preparation_view.fixture_snapshot () in
  let host = { host with preparation = Some snapshot; focus = Some tile.id } in
  let data = { data with log_lines = (fun id -> [ "LOG " ^ Job_id.to_string id ]) } in
  let press host key = H.input host key ~commands:[] in
  let before = host.registry in
  let inspected, effect = press host Enter in
  (match effect with
   | No_effect -> ()
   | _ -> assert false);
  assert (H.local inspected tile.id).utility_detail;
  let rows = Host_view.utility_rows inspected data tile |> Option.value_exn in
  let text = O.inspection_lines rows |> String.concat ~sep:"\n" in
  List.iter
    [ "LOG new-failure/build"
    ; "LOG new-failure/emit"
    ; "old-success"
    ; "bundle-old-success"
    ; "independent of selected historical ASIC run"
    ]
    ~f:(fun substring -> assert (String.is_substring text ~substring));
  let older, effect = press inspected (Character 'j') in
  (match effect with
   | No_effect -> ()
   | _ -> assert false);
  assert (Option.equal String.equal (H.local older tile.id).cursor (Some "old-success"));
  let old_text =
    Host_view.utility_rows older data tile
    |> Option.value_exn
    |> O.inspection_lines
    |> String.concat ~sep:"\n"
  in
  assert (String.is_substring old_text ~substring:"LOG old-success/emit");
  assert (phys_equal before older.registry);
  List.iter
    [ 'r', `Prepare; 'x', `Cancel; 'a', `Artifact ]
    ~f:(fun (key, expected) ->
      match snd (press older (Character key)), expected with
      | Execute (_, Prepare_project), `Prepare
      | Execute (_, Cancel_preparation), `Cancel
      | Execute (_, Preparation_artifact), `Artifact -> ()
      | _ -> assert false);
  let checklist = find "stage-checklist" in
  let items = O.checklist_items ~asic:data.asic ~run:Fs0_fixture.run_a in
  assert (String.equal (O.checklist_id (List.hd_exn items)) "preparation:elaboration");
  assert (Option.is_none (Host_view.checklist_preview host data checklist));
  let rows = Host_view.utility_rows host data checklist |> Option.value_exn in
  assert (String.equal (List.hd_exn rows).label "Elaboration");
  assert (Option.equal O.Status.equal (List.hd_exn rows).status (Some Failed));
  let matching_summary =
    { (Option.value_exn (data.summary Fs0_fixture.run_a)) with
      Asic.Summary.plan_identity = Some "plan"
    }
  in
  let matching_data = { data with summary = (fun _ -> Some matching_summary) } in
  let relation host =
    Host_view.utility_rows host matching_data checklist
    |> Option.value_exn
    |> List.hd_exn
    |> fun row -> String.concat ~sep:"\n" row.O.details
  in
  assert (String.is_substring (relation host) ~substring:"No exact match");
  let completed = Preparation_view.fixture_attempt "matched-current" Completed in
  let matched_host =
    { host with preparation = Some { snapshot with latest = Some completed } }
  in
  assert (
    String.is_substring (relation matched_host) ~substring:"Exact plan identity match");
  List.iter [ false; true ] ~f:(fun horizontal ->
    let rendered =
      Host_view.tile_view
        ~horizontal_stages:horizontal
        host
        data
        checklist
        ~width:120
        ~height:12
      |> Host_view.plain_text
    in
    assert (String.is_substring rendered ~substring:"Elaboration"));
  let catalog = H.catalog host ~project:data.project ~jobs:[] in
  List.iter
    [ "preparation.prepare"; "preparation.cancel"; "tile.add.preparation" ]
    ~f:(fun id ->
      assert (List.exists catalog ~f:(fun command -> String.equal command.H.id id)))
;;

let%test_unit "generic verification process completion and generic RTL cannot publish \
               bundle evidence"
  =
  let job =
    { (Option.value_exn (Preparation_view.fixture_attempt "test" Completed).build_job) with
      kind = { namespace = "dune"; name = "test" }
    }
  in
  let rows =
    Preparation_view.rows
      ~snapshot:None
      ~jobs:[ job ]
      ~project:(Some job.project)
      ~rtl_scope:None
      ~cursor:None
      ~detail:false
      ~log_lines:(fun _ -> [])
  in
  let emission = List.nth_exn rows 2
  and verification = List.nth_exn rows 3 in
  assert (Option.equal O.Status.equal emission.status (Some Unsupported));
  assert (String.equal emission.value "unavailable");
  assert (String.equal verification.value "process succeeded");
  assert (
    List.exists verification.details ~f:(fun s ->
      String.is_substring s ~substring:"not semantic test pass"));
  let unsupported =
    Preparation_view.rows
      ~snapshot:
        (Some
           { (Preparation_view.fixture_snapshot ()) with
             latest = None
           ; history = []
           ; availability = Unavailable Not_configured
           })
      ~jobs:[]
      ~project:None
      ~rtl_scope:None
      ~cursor:None
      ~detail:false
      ~log_lines:(fun _ -> [])
  in
  assert (
    String.is_substring
      (List.hd_exn unsupported).value
      ~substring:"unavailable: not configured")
;;
