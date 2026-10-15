open! Core
open! Async
open Hardcaml_workbench_protocol
module Service = Hardcaml_workbench_backend.Asic_service
module Config = Hardcaml_workbench_project_integration.Asic_config
module Public = Hardcaml_workbench_backend.Asic_public
module Owned_process = Hardcaml_workbench_backend.Asic_process
module Adapter = Hardcaml_workbench_adapters.Asic_adapter

let require condition message = if not condition then failwith message
let environment = V1.Environment_selection.Inherit_daemon

let handle service root operation =
  Service.handle service ~root ~environment operation
  >>| function
  | Ok snapshot -> snapshot
  | Error error -> raise_s [%message "ASIC request failed" (error : V1.Error.t)]
;;

let settled service root operation =
  let%bind (_ : Asic.Snapshot.t) = handle service root operation in
  let%bind () = Service.completion service in
  handle service root Get
;;

let selection profile : Asic.Selection.t =
  { flow = "standard"; profile; endpoint = "synthesis"; assignments = [] }
;;

let summary (snapshot : Asic.Snapshot.t) id =
  List.find_exn snapshot.summaries ~f:(fun s -> String.equal s.Asic.Summary.run.id id)
;;

let reports root =
  In_thread.run (fun () ->
    In_channel.read_lines (Filename.concat root "calls")
    |> List.count ~f:(fun line -> String.is_prefix line ~prefix:"[\"report\""))
;;

let launches root profile =
  In_thread.run (fun () ->
    In_channel.read_lines (Filename.concat root "calls")
    |> List.count ~f:(fun line ->
      String.is_prefix line ~prefix:"[\"flow\", \"run\""
      && String.is_substring line ~substring:("\"--profile\", \"" ^ profile ^ "\"")))
;;

let main () =
  let rejected f message = require (Result.is_error (Or_error.try_with f)) message in
  rejected
    (fun () -> ignore (Public.decode "{\"cursor\":0,\"cursor\":1}" : Yojson.Safe.t))
    "Duplicate public JSON keys accepted";
  rejected
    (fun () ->
      Public.metadata
        (Public.decode
           "{\"cli_contract\":{\"version\":3,\"capabilities\":{\"namedflow1\":true}}}"))
    "Incompatible provider accepted";
  let%bind root, state_dir =
    In_thread.run (fun () ->
      let root = Filename_unix.temp_dir "workbench-asic-" "" in
      let state_dir = Filename.concat root "cache" in
      let fixture = Filename.concat root "fixture.py" in
      Out_channel.write_all fixture ~data:(In_channel.read_all "fake_provider.py");
      Core_unix.chmod fixture ~perm:0o700;
      let config : Config.t =
        { schema_version = 1
        ; project_executable = fixture
        ; provider_executable = fixture
        ; results_root = Filename.concat root "results"
        ; toolchain = root
        ; python = None
        ; support_tools = None
        ; pdk_root = None
        ; stage_timeout_seconds = Some 2
        }
      in
      Out_channel.write_all
        (Filename.concat root Config.filename)
        ~data:(Sexp.to_string (Config.sexp_of_t config));
      root, state_dir)
  in
  (* Reaping and repeated cleanup use the same Async Process ownership record. No raw PID
     signalling or independent waitpid is involved. *)
  let%bind exited =
    Process.create_exn
      ~working_dir:root
      ~prog:(Filename.concat root "fixture.py")
      ~args:[ "lifecycle-exit" ]
      ()
  in
  let%bind () =
    Monitor.protect
      ~finally:(fun () ->
        let%bind () = Owned_process.stop exited in
        let%bind () = Writer.close (Process.stdin exited) in
        let%bind () = Reader.close (Process.stdout exited) in
        Reader.close (Process.stderr exited))
      (fun () ->
        let%bind status = Process.wait exited in
        require (Result.is_ok status) "Natural-exit fixture failed";
        let%bind () = Owned_process.stop exited in
        Owned_process.stop exited)
  in
  let%bind () =
    Deferred.List.iter
      [ "lifecycle-wait", "timeout"
      ; "lifecycle-output", "record too large"
      ; "lifecycle-malformed", "Yojson"
      ; "lifecycle-cancel", "cancelled"
      ]
      ~how:`Sequential
      ~f:(fun (mode, expected_error) ->
        let cancel = Ivar.create () in
        let on_line line =
          if String.equal mode "lifecycle-malformed"
          then ignore (Public.decode line : Yojson.Safe.t);
          if String.equal mode "lifecycle-cancel" then Ivar.fill_if_empty cancel ();
          Deferred.unit
        in
        let invocation =
          Adapter.invocation
            ~root
            ~environment
            (Filename.concat root "fixture.py")
            [ mode ]
        in
        let%bind result =
          Monitor.try_with (fun () ->
            Owned_process.run
              ~seconds:(if String.equal mode "lifecycle-wait" then 3. else 10.)
              ~cancel:(Ivar.read cancel)
              ~on_process:ignore
              ~on_line
              invocation)
        in
        (match result with
         | Ok _ -> failwith ("Process failure fixture unexpectedly succeeded: " ^ mode)
         | Error exn ->
           require
             (String.is_substring (Exn.to_string exn) ~substring:expected_error)
             ("Wrong process failure: " ^ Exn.to_string exn));
        In_thread.run (fun () ->
          require
            (Poly.equal
               (Sys_unix.file_exists (Filename.concat root (mode ^ "-terminated")))
               `Yes)
            ("Process failure did not terminate/reap owned fixture: " ^ mode)))
  in
  let services = ref [] in
  let create ?(directory = state_dir) () =
    let service = Service.create ~state_dir:directory in
    services := service :: !services;
    service
  in
  Monitor.protect
    ~finally:(fun () -> Deferred.List.iter !services ~how:`Sequential ~f:Service.shutdown)
    (fun () ->
      let service = create () in
      let%bind discovered = settled service root Discover in
      require (List.length discovered.flows = 1) "Public discovery failed";
      let launch profile key =
        let%bind planned = settled service root (Plan (selection profile)) in
        let preview = Option.value_exn planned.preview in
        let%bind (_ : Asic.Snapshot.t) = handle service root (Run { key; preview }) in
        let%bind (_ : Asic.Snapshot.t) = handle service root (Run { key; preview }) in
        let rec allocation tries =
          require (tries > 0) "Early allocation not delivered";
          let%bind snapshot = handle service root Get in
          if List.exists snapshot.runs ~f:(fun r ->
               String.equal r.Asic.Run.run.id ("stream-" ^ profile))
          then return snapshot
          else (
            let%bind () = Clock.after (Time_float.Span.of_sec 0.01) in
            allocation (tries - 1))
        in
        let%bind early = allocation 40 in
        let r : Asic.Run.t =
          List.find_exn early.runs ~f:(fun r ->
            String.equal r.Asic.Run.run.id ("stream-" ^ profile))
        in
        require (Option.is_none r.execution_file) "Allocation was not early";
        let%bind () = Service.completion service in
        handle service root Get
      in
      let%bind first = launch "balanced" "one" in
      require
        (Option.equal Int.equal (summary first "stream-balanced").cell_count (Some 50))
        "R1 count";
      let%bind second = launch "synth_delay" "two" in
      require
        (Option.equal
           Int.equal
           (summary second "stream-synth_delay").cell_count
           (Some 73))
        "R2 count";
      let%bind initial_reports = reports root in
      require (initial_reports = 2) "Duplicate launch/materialization";
      let run id : Run_ref.t =
        let r : Asic.Run.t =
          List.find_exn second.runs ~f:(fun r -> String.equal r.Asic.Run.run.id id)
        in
        r.run
      in
      let r1 = run "stream-balanced"
      and r2 = run "stream-synth_delay" in
      let%bind (_ : Asic.Snapshot.t) = settled service root (Load_summary r1) in
      let%bind (_ : Asic.Snapshot.t) = settled service root (Load_summary r2) in
      let%bind (_ : Asic.Snapshot.t) = handle service root (Load_summary r1) in
      let%bind (_ : Asic.Snapshot.t) = handle service root (Load_summary r1) in
      let%bind () = Service.completion service in
      let%bind warm_reports = reports root in
      require (warm_reports = initial_reports) "Warm switch queried provider report";
      let%bind () = Service.shutdown service in
      let restarted = create () in
      let%bind restored = settled restarted root (Load_summary r1) in
      require
        (Asic.Summary.Freshness.equal
           (summary restored r1.id).freshness
           Cached_unverified)
        "L2 incorrectly claims source validation";
      let%bind restart_reports = reports root in
      require (restart_reports = initial_reports) "L2 rematerialized report";
      let%bind () =
        In_thread.run (fun () ->
          Out_channel.write_all (Filename.concat root "revision") ~data:"")
      in
      let%bind revised = settled restarted root (Refresh r1) in
      require
        (Option.equal Int.equal (summary revised r1.id).cell_count (Some 51))
        "Revision did not refresh";
      let%bind (_ : Asic.Snapshot.t) = settled restarted root (Load_summary r2) in
      let%bind () =
        In_thread.run (fun () ->
          Out_channel.write_all (Filename.concat root "missing") ~data:"")
      in
      let%bind missing = settled restarted root (Refresh r1) in
      require
        (Asic.Summary.Freshness.equal (summary missing r1.id).freshness Missing_source)
        "Missing source not explicit";
      require
        (Option.equal Int.equal (summary missing r2.id).cell_count (Some 73))
        "Refresh affected another run";
      let%bind () = Service.shutdown restarted in
      (* Corrupt derived entries rebuild only through the explicit public references. *)
      let%bind () =
        In_thread.run (fun () ->
          Core_unix.unlink (Filename.concat root "missing");
          List.iter (Sys_unix.ls_dir state_dir) ~f:(fun name ->
            if String.is_suffix name ~suffix:".summary.sexp"
            then Out_channel.write_all (Filename.concat state_dir name) ~data:"partial("))
      in
      let recovered = create () in
      let%bind before_cold = reports root in
      let%bind (_ : Asic.Snapshot.t) = handle recovered root (Load_summary r1) in
      let%bind (_ : Asic.Snapshot.t) = handle recovered root (Load_summary r1) in
      let%bind () = Service.completion recovered in
      let%bind rebuilt = handle recovered root Get in
      require
        (Option.equal Int.equal (summary rebuilt r1.id).cell_count (Some 51))
        "Corrupt L2 did not rebuild";
      let%bind after_cold = reports root in
      require (after_cold = before_cold + 1) "Concurrent cold reads were not coalesced";
      (* Drive the actual public registration/read path past the L1 working-set budget. *)
      let%bind () =
        Deferred.List.iter (List.init 34 ~f:Fn.id) ~how:`Sequential ~f:(fun index ->
          let profile = "extra-" ^ Int.to_string index in
          let attempt = Filename.concat root ("attempt-" ^ profile) in
          let%bind () =
            In_thread.run (fun () ->
              Core_unix.mkdir_p attempt ~perm:0o700;
              Out_channel.write_all (Filename.concat attempt "done") ~data:"")
          in
          let%bind registered =
            handle recovered root (Register { attempt; stream_id = "stream-" ^ profile })
          in
          let registered_run : Asic.Run.t =
            List.find_exn registered.runs ~f:(fun r ->
              String.equal r.Asic.Run.run.id ("stream-" ^ profile))
          in
          let run : Run_ref.t = registered_run.run in
          let%map loaded = settled recovered root (Load_summary run) in
          require (List.length loaded.summaries <= 32) "L1 exceeded entry budget")
      in
      let%bind before_evicted = reports root in
      let%bind reloaded = settled recovered root (Load_summary r1) in
      require
        (Option.equal Int.equal (summary reloaded r1.id).cell_count (Some 51))
        "Evicted run loaded wrong summary";
      let%bind after_evicted = reports root in
      require (before_evicted = after_evicted) "L1 eviction failed to reuse L2";
      (* Both overlapping requests must see a failed reservation, not one error and one
         apparent success. A normal file obstructing mkdir makes the write fail without
         modifying provider evidence or adding a persistence injection API. *)
      let reservation_dir = Filename.concat root "reservation-cache" in
      let reserving = create ~directory:reservation_dir () in
      let%bind planned = settled reserving root (Plan (selection "reservation")) in
      let preview = Option.value_exn planned.preview in
      let request = Asic.Operation.Run { key = "retry"; preview } in
      let%bind () =
        In_thread.run (fun () -> Out_channel.write_all reservation_dir ~data:"blocked")
      in
      let first = Service.handle reserving ~root ~environment request in
      let second = Service.handle reserving ~root ~environment request in
      let%bind first, second = Deferred.both first second in
      (match first, second with
       | Error a, Error b ->
         (* Async may add a different caller backtrace to each shared exception. *)
         require
           (V1.Error.Kind.equal a.kind b.kind
            && (not (String.is_empty a.message))
            && not (String.is_empty b.message))
           "Duplicate reservations did not both receive the write failure"
       | _ -> failwith "Failed reservation was acknowledged as successful");
      let%bind failed = handle reserving root Get in
      require
        (not
           (List.exists failed.operations ~f:(fun op ->
              String.equal op.Asic.Pending.key "run:retry")))
        "Failed reservation poisoned submission key";
      let%bind before_retry = launches root "reservation" in
      require (before_retry = 0) "Failed reservation launched provider";
      let%bind () = In_thread.run (fun () -> Core_unix.unlink reservation_dir) in
      let first = handle reserving root request in
      let second = handle reserving root request in
      let%bind (_ : Asic.Snapshot.t * Asic.Snapshot.t) = Deferred.both first second in
      let%bind () = Service.completion reserving in
      let%bind after_retry = launches root "reservation" in
      require (after_retry = 1) "Transient reservation retry did not launch exactly once";
      let%bind () = Service.shutdown reserving in
      let reopened = create ~directory:reservation_dir () in
      let%bind (_ : Asic.Snapshot.t) = settled reopened root request in
      let%bind after_reopen = launches root "reservation" in
      require (after_reopen = 1) "Committed reservation lost deduplication on restart";
      let%bind () = Service.shutdown reopened in
      (* Cancel only a daemon-owned launcher, including its automatic reader. *)
      let%bind () =
        In_thread.run (fun () ->
          Out_channel.write_all (Filename.concat root "hold") ~data:"")
      in
      let%bind planned = settled recovered root (Plan (selection "cancel")) in
      let%bind (_ : Asic.Snapshot.t) =
        handle
          recovered
          root
          (Run { key = "cancel"; preview = Option.value_exn planned.preview })
      in
      let rec wait_allocation attempts =
        require (attempts > 0) "Cancellation fixture allocation missing";
        let%bind snapshot = handle recovered root Get in
        if List.exists snapshot.runs ~f:(fun r ->
             String.equal r.Asic.Run.run.id "stream-cancel")
        then Deferred.unit
        else (
          let%bind () = Clock.after (Time_float.Span.of_sec 0.01) in
          wait_allocation (attempts - 1))
      in
      let%bind () = wait_allocation 100 in
      let%bind (_ : Asic.Snapshot.t) = handle recovered root (Cancel "run:cancel") in
      let%bind () = Service.completion recovered in
      let%bind cancelled = handle recovered root Get in
      require
        (List.exists cancelled.operations ~f:(fun op ->
           String.equal op.Asic.Pending.key "run:cancel" && String.equal op.state "failed"))
        "Owned launcher cancellation was not recorded";
      let%bind () =
        In_thread.run (fun () ->
          require
            (Poly.equal
               (Sys_unix.file_exists (Filename.concat root "attempt-cancel/terminated"))
               `Yes)
            "Cancellation did not await owned launcher SIGTERM/reaping";
          require
            (Poly.equal
               (Sys_unix.file_exists (Filename.concat root "attempt-cancel/done"))
               `No)
            "Cancelled launcher completed unexpectedly";
          List.iter [ "balanced"; "synth_delay" ] ~f:(fun profile ->
            require
              (Poly.equal
                 (Sys_unix.file_exists
                    (Filename.concat root ("attempt-" ^ profile ^ "/terminated")))
                 `No)
              "Natural completion was signalled"))
      in
      let%bind () = Service.shutdown recovered in
      Deferred.unit)
;;

let () =
  Command.async
    ~summary:"FS0 public ASIC adapter and summary cache fixtures"
    (Command.Param.return main)
  |> Command_unix.run
;;
