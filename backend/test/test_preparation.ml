open! Core
open! Async
open Hardcaml_workbench_protocol
module Service = Hardcaml_workbench_backend.Service
module Receipt = Hardcaml_workbench_backend.Preparation_receipt
module Config = Hardcaml_workbench_project_integration.Preparation_config
module Adapter = Hardcaml_workbench_adapters.Preparation_adapter
module Dune = Hardcaml_workbench_adapters.Dune_adapter

let require condition message = if not condition then failwith message

let ok = function
  | Ok x -> x
  | Error e -> failwith (Sexp.to_string_hum (V1.Error.sexp_of_t e))
;;

let instance_id = V1.Daemon_instance_id.of_string "preparation-test"

let selection : Preparation.Selection.t =
  { flow = "tiny-flow"
  ; profile = "fast"
  ; endpoint = "synthesis"
  ; assignments = [ "SYNTH_STRATEGY=AREA 0"; "SYNTH_HIERARCHICAL=true" ]
  }
;;

let shell ~root script : Dune.Invocation.t =
  { executable = "/bin/sh"
  ; argv = [ "/bin/sh"; "-c"; script ]
  ; cwd = root
  ; environment = Inherit_daemon
  }
;;

let fixture config ~root =
  let configuration =
    `Assoc
      [ "CLOCK_PERIOD", `Float 20.
      ; "DESIGN_NAME", `String "tiny"
      ; "VERILOG_FILES", `List [ `String "dir::tiny.v" ]
      ]
  in
  let config_bytes = Yojson.Safe.pretty_to_string configuration ^ "\n" in
  let rtl = "module tiny(input clk); endmodule\n" in
  let input = "let design = tiny\n" in
  let files =
    [ "constraints/top.sdc", "create_clock -name clk -period 20 [get_ports {clk}]\n"
    ; "info.yaml", "project:\n  top_module: tiny\n"
    ; "inputs/design.ml", input
    ; "simulation/tiny.v", rtl
    ; "src/config.json", config_bytes
    ; "src/tiny.v", rtl
    ]
  in
  let manifest_payload =
    `Assoc
      [ "schema_version", `Int 1
      ; "project", `String "tiny"
      ; "top_module", `String "tiny"
      ; "source_revision", `String (String.make 40 'a')
      ; ( "source_inputs"
        , `List
            [ `Assoc
                [ "path", `String "design.ml"
                ; "copy", `String "inputs/design.ml"
                ; "sha256", `String (Receipt.sha256 input)
                ; "git_status", `String " M design.ml"
                ]
            ] )
      ; ( "files"
        , `List
            (List.map files ~f:(fun (path, bytes) ->
               `Assoc [ "path", `String path; "sha256", `String (Receipt.sha256 bytes) ]))
        )
      ; "synthesis_sources", `List [ `String "src/tiny.v" ]
      ; "simulation_sources", `List [ `String "simulation/tiny.v" ]
      ; "resources", `List []
      ; "simulation_resources", `List []
      ; ( "target"
        , `Assoc
            [ "harness", `String "Tiny_tapeout"
            ; "technology", `String "cmos5l"
            ; "tiles", `String "1x1"
            ; "corner", `String "nom"
            ; "external_references", `List []
            ] )
      ; "adapter", `String "LibreLane"
      ; "operation", `String "Synthesis"
      ; "resolved_settings", `List []
      ; "flow_configuration", configuration
      ; "generated_settings", `Assoc [ "VERILOG_FILES", `List [ `String "dir::tiny.v" ] ]
      ; ( "requested_tools"
        , `Assoc [ "librelane", `String "3.1.0.dev3"; "python", `String "3.11" ] )
      ]
  in
  let bundle_identity = Receipt.sha256 (Yojson.Safe.to_string manifest_payload) in
  let manifest =
    match manifest_payload with
    | `Assoc fields -> `Assoc (("identity", `String bundle_identity) :: fields)
    | _ -> assert false
  in
  let manifest_bytes = Yojson.Safe.pretty_to_string manifest ^ "\n" in
  let snapshot =
    `Assoc
      [ "contract", `String "hardcaml-asic.flow-snapshot"
      ; "schema_version", `Int 1
      ; "declaration", `Assoc []
      ; "definition", `Assoc []
      ; "profile", `Assoc []
      ; ( "selected"
        , `Assoc [ "flow", `String selection.flow; "profile", `String selection.profile ]
        )
      ; "endpoint", `String selection.endpoint
      ; "stages", `List [ `String selection.endpoint ]
      ; "request", Receipt.assignments selection
      ; "parameters", `List []
      ]
  in
  let methodology =
    `Assoc
      [ "snapshot", snapshot
      ; "project_assignments", `List []
      ; "effective_parameters", `List []
      ; "translation", `Assoc []
      ; ( "recipe"
        , `Assoc
            [ "schema_version", `Int 4
            ; "stages", `List [ `String selection.endpoint ]
            ; "initial_boundary", `Null
            ] )
      ]
  in
  let plan_payload =
    `Assoc
      [ "contract", `String "hardcaml-asic.methodology-plan"
      ; "schema_version", `Int 1
      ; "methodology", methodology
      ; ( "methodology_hash"
        , `String (Receipt.identity "hardcaml-asic.methodology-hash" methodology) )
      ; "project_name", `String "tiny"
      ; "bundle_identity", `String bundle_identity
      ; "bundle_manifest", `String (Yojson.Safe.to_string manifest)
      ; "configuration_bytes", `String config_bytes
      ]
  in
  let plan_identity = Receipt.identity "hardcaml-asic.plan-identity" plan_payload in
  let plan =
    match plan_payload with
    | `Assoc fields -> `Assoc (fields @ [ "plan_identity", `String plan_identity ])
    | _ -> assert false
  in
  let bundles = Filename.concat config.Config.results_root "bundles" in
  Core_unix.mkdir config.results_root;
  Core_unix.mkdir bundles;
  let output_dir = Filename.concat bundles bundle_identity in
  let objects = Filename.concat bundles ".objects" in
  Core_unix.mkdir objects;
  let object_name = bundle_identity ^ ".123.00000001" in
  let object_dir = Filename.concat objects object_name in
  Core_unix.mkdir object_dir;
  let rec mkdir path =
    if Poly.equal (Sys_unix.file_exists path) `No
    then (
      mkdir (Filename.dirname path);
      Core_unix.mkdir path)
  in
  List.iter (("manifest.json", manifest_bytes) :: files) ~f:(fun (path, data) ->
    let path = Filename.concat object_dir path in
    mkdir (Filename.dirname path);
    Out_channel.write_all path ~data);
  Core_unix.symlink ~target:(Filename.concat ".objects" object_name) ~link_name:output_dir;
  let receipt =
    `Assoc
      [ "schema_version", `Int 1
      ; "kind", `String "bundle_emission"
      ; "bundle_identity", `String bundle_identity
      ; "plan_identity", `String plan_identity
      ; "output_dir", `String output_dir
      ; "reused", `Bool false
      ; "plan", plan
      ]
  in
  Out_channel.write_all
    (Filename.concat root "receipt.json")
    ~data:(Yojson.Safe.to_string receipt);
  plan_identity, receipt, output_dir
;;

let terminal (a : Preparation.Attempt.t) =
  match a.outcome with
  | Building | Emitting -> false
  | _ -> true
;;

let call service project operation =
  Service.preparation service { instance_id; project; operation }
;;

let get service project = call service project Get >>| ok
let latest snapshot = Option.value_exn snapshot.Preparation.Snapshot.latest

let wait_for service project predicate =
  let rec loop () =
    let%bind snapshot = get service project in
    if predicate snapshot
    then return snapshot
    else (
      let%bind () = Clock.after (Time_float.Span.of_ms 10.) in
      loop ())
  in
  let%map result = Clock.with_timeout (Time_float.Span.of_sec 5.) (loop ()) in
  match result with
  | `Result result -> result
  | `Timeout -> failwith "Preparation timed out"
;;

let with_service f =
  let directory = Filename_unix.temp_dir "wb004-test-" "" in
  let root = Filename.concat directory "project" in
  Core_unix.mkdir root;
  Out_channel.write_all
    (Filename.concat root "dune-project")
    ~data:"(lang dune 3.22)\n(name preparation_test)\n";
  Out_channel.write_all (Filename.concat root "dune") ~data:"";
  let config : Config.t =
    { schema_version = 1
    ; build_target = "bin/project.exe"
    ; results_root = Filename.concat directory "results"
    ; timeout_seconds = 10
    }
  in
  let write_config () =
    Out_channel.write_all
      (Filename.concat root Config.filename)
      ~data:(Sexp.to_string_hum (Config.sexp_of_t config))
  in
  let plan_identity, receipt, output_dir = fixture config ~root in
  let build_script = ref "printf build-log; sleep 0.1" in
  let emit_script = ref "printf emission-log >&2; cat receipt.json" in
  let builds = ref 0
  and emissions = ref 0 in
  let build c ~root ~environment =
    incr builds;
    if String.equal !build_script "raise-invocation"
    then failwith "Build invocation failed";
    let invocation = Adapter.build c ~root ~environment in
    require
      (List.equal
         String.equal
         invocation.argv
         [ "dune"
         ; "build"
         ; "-j6"
         ; "--root"
         ; root
         ; "--build-dir"
         ; Filename.concat root "_build"
         ; "--"
         ; c.build_target
         ])
      "Source target/build directory/concurrency changed";
    shell ~root !build_script
  in
  let emit c ~root ~environment ~selection:actual ~expected_plan_identity =
    incr emissions;
    require (Preparation.Selection.equal selection actual) "Selected parameters changed";
    require
      (Option.equal String.equal expected_plan_identity (Some plan_identity))
      "Expected plan identity dropped";
    let invocation =
      Adapter.emit c ~root ~environment ~selection:actual ~expected_plan_identity
    in
    require
      (String.equal invocation.executable (Config.source_executable c ~root))
      "Pinned executable used";
    require
      (List.equal
         String.equal
         invocation.argv
         [ Config.source_executable c ~root
         ; "flow"
         ; "emit"
         ; "--flow"
         ; "tiny-flow"
         ; "--profile"
         ; "fast"
         ; "--endpoint"
         ; "synthesis"
         ; "--source-root"
         ; root
         ; "--json"
         ; "--set"
         ; "SYNTH_STRATEGY=AREA 0"
         ; "--set"
         ; "SYNTH_HIERARCHICAL=true"
         ; "--results-root"
         ; c.results_root
         ; "--expected-plan-identity"
         ; plan_identity
         ])
      "Emission argv changed";
    shell ~root !emit_script
  in
  let%bind created =
    Service.create
      ~instance_id
      ~log_dir:(Filename.concat directory "logs")
      ~kill_after:(Time_float.Span.of_ms 20.)
      ~preparation_build_invocation:build
      ~preparation_emit_invocation:emit
      ()
  in
  let service = Or_error.ok_exn created in
  Monitor.protect
    ~finally:(fun () ->
      let%bind () = Service.shutdown service in
      In_thread.run (fun () -> Service.remove_tree_sync directory))
    (fun () ->
      let%bind opened =
        Service.open_project service { instance_id; root; environment = Inherit_daemon }
      in
      let project = (ok opened).project.id in
      let poison = Filename.concat root "provider" in
      Out_channel.write_all
        poison
        ~data:"#!/bin/sh\ntouch provider-was-invoked\nexit 99\n";
      Core_unix.chmod poison ~perm:0o700;
      Out_channel.write_all
        (Filename.concat root "hardcaml-workbench-asic.sexp")
        ~data:
          (sprintf
             "((schema_version 1)(project_executable %s)(provider_executable \
              %s)(results_root %s)(toolchain %s)(python ())(support_tools ())(pdk_root \
              ())(stage_timeout_seconds ()))"
             poison
             poison
             config.results_root
             root);
      let%bind () =
        f
          ~service
          ~project
          ~root
          ~config
          ~write_config
          ~plan_identity
          ~receipt
          ~output_dir
          ~build_script
          ~emit_script
          ~builds
          ~emissions
      in
      require
        (Poly.equal
           (Sys_unix.file_exists (Filename.concat root "provider-was-invoked"))
           `No)
        "Provider was invoked";
      return ())
;;

let run_fixture () =
  with_service
    (fun
        ~service
        ~project
        ~root
        ~config
        ~write_config
        ~plan_identity
        ~receipt
        ~output_dir
        ~build_script
        ~emit_script
        ~builds
        ~emissions
      ->
       let prepare key =
         call
           service
           project
           (Prepare
              { submission_key = key
              ; selection
              ; expected_plan_identity = Some plan_identity
              })
         >>| ok
       in
       let%bind initial = get service project in
       require
         (Preparation.Availability.equal
            initial.availability
            (Unavailable Not_configured))
         "ASIC presence inferred preparation capability";
       Out_channel.write_all (Filename.concat root Config.filename) ~data:"broken";
       let%bind invalid = get service project in
       require
         (match invalid.availability with
          | Unavailable (Invalid_configuration _) -> true
          | _ -> false)
         "Invalid config not typed";
       write_config ();
       let%bind first, duplicate = Deferred.both (prepare "one") (prepare "one") in
       require
         (String.equal (latest first).id (latest duplicate).id)
         "Duplicate submissions allocated twice";
       let%bind coalesced = prepare "also-one" in
       require
         (String.equal (latest first).id (latest coalesced).id)
         "Active identical selection not coalesced";
       let%bind conflict =
         call
           service
           project
           (Prepare
              { submission_key = "one"
              ; selection = { selection with profile = "other" }
              ; expected_plan_identity = Some plan_identity
              })
       in
       require
         (match conflict with
          | Error e -> V1.Error.Kind.equal e.kind Conflict
          | _ -> false)
         "Conflicting duplicate accepted";
       let%bind completed = wait_for service project (fun s -> terminal (latest s)) in
       let a = latest completed in
       require
         (Preparation.Outcome.equal a.outcome Completed)
         (Option.value a.diagnostic ~default:"No completed preparation");
       require (!builds = 1 && !emissions = 1) "Duplicate work executed";
       let build = Option.value_exn a.build_job
       and emission = Option.value_exn a.emission_job in
       require
         ((not (Job_id.equal build.id emission.id))
          && Job.State.equal build.state Complete
          && Job.State.equal emission.state Complete)
         "Stage statuses conflated";
       let%bind build_log =
         Service.read_log
           service
           { instance_id
           ; job = build.id
           ; offset = 0
           ; max_records = 100
           ; max_bytes = 65536
           }
       in
       require
         (String.is_substring
            (String.concat
               (List.map (ok build_log).records ~f:(fun r -> r.V1.Read_log.Record.data)))
            ~substring:"build-log")
         "Build log not retained";
       let bundle = Option.value_exn a.bundle in
       require
         (List.length bundle.artifacts = 7
          && String.equal bundle.plan_identity plan_identity)
         "Bundle handles missing";
       let%bind artifact =
         Service.read_artifact
           service
           { instance_id
           ; artifact = List.hd_exn bundle.artifacts
           ; offset = 0
           ; max_bytes = 65536
           }
       in
       require
         (String.is_substring (ok artifact).data ~substring:"identity")
         "Imported manifest inaccessible";
       let%bind _ = prepare "one" in
       require (!builds = 1) "Terminal submission replay executed again";
       build_script := "printf failed-build >&2; exit 7";
       let%bind _ = prepare "build-failure" in
       let%bind failed = wait_for service project (fun s -> terminal (latest s)) in
       require
         (Preparation.Outcome.equal (latest failed).outcome Build_failed
          && Option.is_none (latest failed).emission_job
          && !emissions = 1)
         "Failed build emitted bundle";
       let%bind replay = prepare "one" in
       require
         (Option.equal String.equal replay.requested_attempt (Some a.id)
          && Preparation.Outcome.equal (latest replay).outcome Build_failed)
         "Replayed submission lost its exact attempt or reordered history";
       build_script := "exit 0";
       emit_script := "printf failed-emission >&2; exit 8";
       let%bind _ = prepare "emit-failure" in
       let%bind failed = wait_for service project (fun s -> terminal (latest s)) in
       require
         (Preparation.Outcome.equal (latest failed).outcome Emission_failed
          && Option.is_none (latest failed).bundle)
         "Emission failure accepted";
       emit_script := "printf '{bad-json'";
       let%bind _ = prepare "malformed" in
       let%bind malformed = wait_for service project (fun s -> terminal (latest s)) in
       require
         (Preparation.Outcome.equal (latest malformed).outcome Emission_failed
          && Job.State.equal
               (Option.value_exn (latest malformed).emission_job).state
               Failed)
         "Malformed receipt completed";
       (* A valid receipt on a nonzero exit is still an emission failure. *)
       emit_script := "cat receipt.json; exit 9";
       let%bind _ = prepare "receipt-nonzero" in
       let%bind failed = wait_for service project (fun s -> terminal (latest s)) in
       require
         (Option.is_none (latest failed).bundle
          && List.is_empty (Option.value_exn (latest failed).emission_job).artifacts)
         "Failed emission imported evidence";
       build_script := "sleep 10";
       let%bind started = prepare "cancel-build" in
       let count = !emissions in
       let%bind cancelled = call service project (Cancel (latest started).id) >>| ok in
       require
         (Preparation.Outcome.equal (latest cancelled).outcome Cancelled
          && !emissions = count)
         "Cancelled build emitted";
       build_script := "exit 0";
       emit_script := "sleep 10";
       let%bind _ = prepare "cancel-emit" in
       let%bind started =
         wait_for service project (fun s -> Option.is_some (latest s).emission_job)
       in
       let%bind cancelled = call service project (Cancel (latest started).id) >>| ok in
       require
         (Preparation.Outcome.equal (latest cancelled).outcome Cancelled
          && Option.is_none (latest cancelled).bundle)
         "Cancelled emission completed";
       require
         (List.length cancelled.history = 7
          && Preparation.Outcome.equal (latest cancelled).outcome Cancelled)
         "History did not retain newest failures/cancellation";
       require cancelled.session_only "Session evidence advertised as durable";
       (* Keep one root job running while configuration changes. New requests must not
          coalesce into the old configuration, and queued stale work must not launch. *)
       build_script := "touch blocker-started; sleep 10";
       let%bind blocker = prepare "config-blocker" in
       let blocker_id = (latest blocker).id in
       let%bind _ =
         wait_for service project (fun _ ->
           Poly.equal (Sys_unix.file_exists (Filename.concat root "blocker-started")) `Yes)
       in
       let changed = { config with timeout_seconds = 11 } in
       Out_channel.write_all
         (Filename.concat root Config.filename)
         ~data:(Sexp.to_string_hum (Config.sexp_of_t changed));
       build_script := "touch stale-build-launched";
       let%bind queued = prepare "config-queued" in
       let queued_id = (latest queued).id in
       require
         (not (String.equal blocker_id queued_id))
         "Changed configuration coalesced into old work";
       require
         (Job.State.equal (Option.value_exn (latest queued).build_job).state Queued)
         "Configuration drift test did not queue its build";
       Out_channel.write_all
         (Filename.concat root Config.filename)
         ~data:
           (Sexp.to_string_hum (Config.sexp_of_t { config with timeout_seconds = 12 }));
       build_script := "touch cancelled-build-launched";
       let%bind queued_cancel = prepare "queued-cancel" in
       let%bind cancelled =
         call service project (Cancel (latest queued_cancel).id) >>| ok
       in
       require
         (Preparation.Outcome.equal (latest cancelled).outcome Cancelled)
         "Queued cancellation did not settle";
       write_config ();
       let%bind _ = call service project (Cancel blocker_id) >>| ok in
       let find_queued s =
         List.find_exn s.Preparation.Snapshot.history ~f:(fun a ->
           String.equal a.Preparation.Attempt.id queued_id)
       in
       let%bind failed = wait_for service project (fun s -> terminal (find_queued s)) in
       require
         (Preparation.Outcome.equal (find_queued failed).outcome Build_failed
          && Option.is_none (find_queued failed).emission_job
          && Poly.equal
               (Sys_unix.file_exists (Filename.concat root "stale-build-launched"))
               `No
          && Poly.equal
               (Sys_unix.file_exists (Filename.concat root "cancelled-build-launched"))
               `No)
         "Stale queued build launched after configuration drift";
       (* Drift during the build must also be checked before starting emission. *)
       build_script
       := "touch drift-build-started; while test ! -e release-drift-build; do sleep \
           0.01; done";
       emit_script := "touch stale-emission-launched; cat receipt.json";
       let%bind _ = prepare "config-emission" in
       let%bind _ =
         wait_for service project (fun _ ->
           Poly.equal
             (Sys_unix.file_exists (Filename.concat root "drift-build-started"))
             `Yes)
       in
       Out_channel.write_all
         (Filename.concat root Config.filename)
         ~data:(Sexp.to_string_hum (Config.sexp_of_t changed));
       Out_channel.write_all (Filename.concat root "release-drift-build") ~data:"";
       let%bind failed = wait_for service project (fun s -> terminal (latest s)) in
       require
         (Preparation.Outcome.equal (latest failed).outcome Emission_failed
          && Option.is_none (latest failed).bundle
          && Poly.equal
               (Sys_unix.file_exists (Filename.concat root "stale-emission-launched"))
               `No)
         "Stale emission launched after configuration drift during build";
       write_config ();
       build_script := "raise-invocation";
       let%bind failed, replay =
         Deferred.both (prepare "invocation-error") (prepare "invocation-error")
       in
       require
         (Preparation.Outcome.equal (latest failed).outcome Build_failed
          && Option.equal String.equal failed.requested_attempt replay.requested_attempt)
         "Invocation failure left an active attempt or blocked duplicate replay";
       Out_channel.write_all
         (Filename.concat root Config.filename)
         ~data:(Sexp.to_string_hum (Config.sexp_of_t { config with timeout_seconds = 1 }));
       build_script := "exit 0";
       emit_script
       := "receipt=$(cat receipt.json); trap 'printf \"%s\" \"$receipt\"; exit 0' TERM; \
           while :; do sleep 0.01; done";
       let%bind _ = prepare "timeout-zero-exit" in
       let%bind failed = wait_for service project (fun s -> terminal (latest s)) in
       let emission = Option.value_exn (latest failed).emission_job in
       require
         (Preparation.Outcome.equal (latest failed).outcome Emission_failed
          && Option.is_none (latest failed).bundle
          && List.is_empty emission.artifacts)
         "Timed out emitter published artifacts after handling TERM";
       require
         (Option.equal Job.Exit_status.equal emission.exit_status (Some (Exited 0)))
         "Timeout fixture did not exercise zero-exit receipt handling";
       write_config ();
       let validate ?(selected = selection) value =
         Receipt.validate
           config
           ~selection:selected
           ~expected_plan_identity:(Some plan_identity)
           (Yojson.Safe.to_string value)
       in
       require
         (Result.is_ok (validate receipt))
         "Provider-shaped private-object publication rejected";
       let set value key data =
         match value with
         | `Assoc fields ->
           `Assoc
             (List.map fields ~f:(fun (k, v) -> k, if String.equal k key then data else v))
         | _ -> assert false
       in
       require
         (Result.is_ok (validate (set receipt "reused" (`Bool true))))
         "Reused publication rejected";
       require
         (Result.is_error
            (validate ~selected:{ selection with profile = "other" } receipt))
         "Wrong selected profile accepted";
       require
         (Result.is_error
            (validate ~selected:{ selection with assignments = [] } receipt))
         "Wrong assignments accepted";
       require
         (Result.is_error
            (Receipt.validate
               config
               ~selection
               ~expected_plan_identity:(Some (String.make 64 '0'))
               (Yojson.Safe.to_string receipt)))
         "Wrong expected plan identity accepted";
       let duplicate_fields =
         match receipt with
         | `Assoc fields -> `Assoc (("kind", `String "bundle_emission") :: fields)
         | _ -> assert false
       in
       require
         (Result.is_error (validate duplicate_fields))
         "Duplicate JSON result fields accepted";
       require
         (Result.is_error
            (Config.parse_string
               "((schema_version 1)(build_target ../pinned.exe)(results_root \
                /tmp/results)(timeout_seconds 10))"))
         "Escaping build target accepted";
       require
         (Result.is_error
            (Config.parse_string
               "((schema_version 1)(build_target bin/project.exe)(project_executable \
                /stale/pinned)(results_root /tmp/results)(timeout_seconds 10))"))
         "Pinned executable override accepted";
       let target = Core_unix.readlink output_dir in
       let object_dir = Filename_unix.realpath output_dir in
       (* Exact existing plain directories are also a supported Bundle.publish layout. *)
       Core_unix.unlink output_dir;
       Core_unix.rename ~src:object_dir ~dst:output_dir;
       require
         (Result.is_ok (validate receipt))
         "Plain identity-directory publication rejected";
       Core_unix.rename ~src:output_dir ~dst:object_dir;
       Core_unix.symlink ~target ~link_name:output_dir;
       let replace_link target =
         Core_unix.unlink output_dir;
         Core_unix.symlink ~target ~link_name:output_dir
       in
       let escaped = Filename.concat root "escaped-bundle" in
       Core_unix.rename ~src:object_dir ~dst:escaped;
       replace_link escaped;
       require (Result.is_error (validate receipt)) "External publication link accepted";
       replace_link target;
       Core_unix.symlink ~target:escaped ~link_name:object_dir;
       require
         (Result.is_error (validate receipt))
         "Private object symlink escape accepted";
       Core_unix.unlink object_dir;
       Core_unix.rename ~src:escaped ~dst:object_dir;
       replace_link object_dir;
       require
         (Result.is_error (validate receipt))
         "Absolute link outside supported publication layout accepted";
       replace_link ".objects/wrong-identity.123.00000001";
       require
         (Result.is_error (validate receipt))
         "Wrong identity private object accepted";
       replace_link target;
       let objects = Filename.dirname object_dir in
       let escaped_objects = Filename.concat root "escaped-objects" in
       Core_unix.rename ~src:objects ~dst:escaped_objects;
       Core_unix.symlink ~target:escaped_objects ~link_name:objects;
       require
         (Result.is_error (validate receipt))
         "Symlinked .objects parent escape accepted";
       Core_unix.unlink objects;
       Core_unix.rename ~src:escaped_objects ~dst:objects;
       let src = Filename.concat object_dir "src" in
       let escaped_src = Filename.concat root "escaped-src" in
       Core_unix.rename ~src ~dst:escaped_src;
       Core_unix.symlink ~target:escaped_src ~link_name:src;
       require (Result.is_error (validate receipt)) "Symlinked member directory accepted";
       Core_unix.unlink src;
       Core_unix.rename ~src:escaped_src ~dst:src;
       let changed_plan =
         set (Receipt.field receipt "plan") "configuration_bytes" (`String "wrong bytes")
       in
       let changed_identity =
         Receipt.identity
           "hardcaml-asic.plan-identity"
           (Receipt.without changed_plan "plan_identity")
       in
       let changed_plan = set changed_plan "plan_identity" (`String changed_identity) in
       let changed_receipt =
         set (set receipt "plan" changed_plan) "plan_identity" (`String changed_identity)
       in
       let mismatch =
         Receipt.validate
           config
           ~selection
           ~expected_plan_identity:(Some changed_identity)
           (Yojson.Safe.to_string changed_receipt)
       in
       require
         (match mismatch with
          | Error error ->
            String.is_substring
              (Error.to_string_hum error)
              ~substring:"Configuration bytes mismatch"
          | Ok _ -> false)
         "Plan/configuration mismatch accepted or masked";
       Out_channel.write_all
         (Filename.concat output_dir "src/config.json")
         ~data:"tampered";
       require (Result.is_error (validate receipt)) "Tampered manifest file accepted";
       let wrapped =
         Adapter.emit
           config
           ~root
           ~environment:(Opam_switch "test-switch")
           ~selection
           ~expected_plan_identity:None
       in
       require
         (String.equal wrapped.executable "opam"
          && List.mem wrapped.argv "--switch=test-switch" ~equal:String.equal)
         "Selected environment lost";
       return ())
;;

(* Optional read-only acceptance check against a provider's real receipt and publication.
   Selection and store location are taken from that supplied receipt. *)
let validate_receipt_file path =
  let output = In_channel.read_all path in
  let receipt = Yojson.Safe.from_string output in
  let plan = Receipt.field receipt "plan" in
  let snapshot = Receipt.field (Receipt.field plan "methodology") "snapshot" in
  let selected = Receipt.field snapshot "selected" in
  let selection : Preparation.Selection.t =
    { flow = Receipt.text (Receipt.field selected "flow")
    ; profile = Receipt.text (Receipt.field selected "profile")
    ; endpoint = Receipt.text (Receipt.field snapshot "endpoint")
    ; assignments =
        Receipt.array (Receipt.field snapshot "request")
        |> List.map ~f:(fun a ->
          let value =
            match Receipt.field a "value" with
            | `String s -> s
            | `Bool true -> "true"
            | `Bool false -> "false"
            | _ -> failwith "Unsupported provider assignment"
          in
          Receipt.text (Receipt.field a "key") ^ "=" ^ value)
    }
  in
  let config : Config.t =
    { schema_version = 1
    ; build_target = "unused.exe"
    ; timeout_seconds = 10
    ; results_root =
        Filename.dirname
          (Filename.dirname (Receipt.text (Receipt.field receipt "output_dir")))
    }
  in
  let validated =
    Receipt.validate
      config
      ~selection
      ~expected_plan_identity:
        (Some (Receipt.text (Receipt.field receipt "plan_identity")))
      output
    |> Or_error.ok_exn
  in
  printf
    "Validated real receipt: %s (%d files)\n"
    validated.bundle.bundle_identity
    (List.length validated.files)
;;

let () =
  Command_unix.run
    (Command.async
       ~summary:"WB004 supervised preparation tests"
       (let%map_open.Command receipt =
          flag
            "-receipt"
            (optional string)
            ~doc:"PATH also validate an existing real provider receipt read-only"
        in
        fun () ->
          let%map () = run_fixture () in
          Option.iter receipt ~f:validate_receipt_file))
;;
