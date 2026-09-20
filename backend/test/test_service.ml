open! Core
open! Async
open Hardcaml_workbench_protocol
module Adapter = Hardcaml_workbench_adapters.Dune_adapter
module Service = Hardcaml_workbench_backend.Service

let instance_id = V1.Daemon_instance_id.of_string "service-test"
let short_timeout = Time_float.Span.of_sec 4.
let fail message = raise_s [%message message]
let require condition message = if not condition then fail message

let ok = function
  | Ok value -> value
  | Error error -> raise_s [%message "service error" (error : V1.Error.t)]
;;

let shell root script : Adapter.Invocation.t =
  { executable = "/bin/sh"
  ; argv = [ "/bin/sh"; "-c"; script ]
  ; cwd = root
  ; environment = Inherit_daemon
  }
;;

let missing root : Adapter.Invocation.t =
  { executable = Filename.concat root "does-not-exist"
  ; argv = [ "does-not-exist" ]
  ; cwd = root
  ; environment = Inherit_daemon
  }
;;

let rec remove_tree path =
  match Sys_unix.file_exists ~follow_symlinks:false path with
  | `No | `Unknown -> ()
  | `Yes ->
    if Sys_unix.is_directory_exn ~follow_symlinks:false path
    then (
      Sys_unix.ls_dir path
      |> List.iter ~f:(fun name -> remove_tree (Filename.concat path name));
      Core_unix.rmdir path)
    else Core_unix.unlink path
;;

let with_temp_tree f =
  let directory = Filename_unix.temp_dir "hardcaml-workbench-service-test-" "" in
  let root = Filename.concat directory "project" in
  let log_dir = Filename.concat directory "logs" in
  Core_unix.mkdir root;
  Core_unix.mkdir log_dir;
  Out_channel.write_all
    (Filename.concat root "dune-project")
    ~data:"(lang dune 3.22)\n(name supervisor_test)\n";
  Out_channel.write_all (Filename.concat root "dune") ~data:"";
  Monitor.protect
    ~finally:(fun () -> In_thread.run (fun () -> remove_tree directory))
    (fun () -> f ~root ~log_dir)
;;

let with_service ?(events = ref []) ~root ~log_dir action_invocation f =
  let%bind service =
    Service.create
      ~kill_after:(Time_float.Span.of_ms 100.)
      ~action_invocation
      ~instance_id
      ~log_dir
      ()
  in
  let service = Or_error.ok_exn service in
  Service.set_event_sink service (fun event -> events := event :: !events);
  Monitor.protect
    ~finally:(fun () -> Service.shutdown service)
    (fun () ->
      let%bind opened =
        Service.open_project
          service
          { instance_id; root; environment = V1.Environment_selection.Inherit_daemon }
      in
      let project = (ok opened).project in
      f service project)
;;

let submit service project action submission_key =
  Service.submit_job
    service
    { instance_id; project = project.Project.id; action; submission_key }
  >>| ok
;;

let snapshot service : V1.Snapshot.Payload.t =
  Service.snapshot service { instance_id } |> ok
;;

let job service id =
  snapshot service
  |> fun snapshot ->
  List.find_exn snapshot.V1.Snapshot.Payload.jobs ~f:(fun job ->
    Job_id.equal job.Job.id id)
;;

let with_deadline ?(timeout = short_timeout) message deferred =
  Clock.with_timeout timeout deferred
  >>| function
  | `Result result -> result
  | `Timeout -> fail message
;;

let rec wait_for_job service id predicate =
  let current = job service id in
  if predicate current
  then return current
  else (
    let%bind () = Clock.after (Time_float.Span.of_ms 10.) in
    wait_for_job service id predicate)
;;

let wait_for_job service id predicate =
  with_deadline "timed out waiting for job state" (wait_for_job service id predicate)
;;

let wait_terminal service id = wait_for_job service id Job.is_terminal

let read_log
  ?(offset = 0)
  ?(max_records = V1.max_log_records)
  ?(max_bytes = V1.max_log_bytes)
  service
  job
  =
  Service.read_log service { instance_id; job; offset; max_records; max_bytes }
;;

let log_text payload =
  payload.V1.Read_log.Payload.records
  |> List.map ~f:(fun record -> record.V1.Read_log.Record.data)
  |> String.concat
;;

let require_error_kind result kind message =
  require
    (match result with
     | Error (error : V1.Error.t) -> V1.Error.Kind.equal error.kind kind
     | Ok _ -> false)
    message
;;

let test_project_opening ~root ~log_dir =
  let%bind service = Service.create ~instance_id ~log_dir () in
  let service = Or_error.ok_exn service in
  Monitor.protect
    ~finally:(fun () -> Service.shutdown service)
    (fun () ->
      let open_root requested_root =
        Service.open_project
          service
          { instance_id
          ; root = requested_root
          ; environment = V1.Environment_selection.Inherit_daemon
          }
      in
      let%bind first = open_root root in
      let first = ok first in
      let%bind repeated = open_root (Filename.concat root ".") in
      let repeated = ok repeated in
      require
        (Project_id.equal first.project.id repeated.project.id)
        "repeat-open did not reuse the canonical project session";
      require
        (String.equal
           (Project_root.to_absolute_path repeated.project.root)
           (Filename_unix.realpath root))
        "project root was not canonicalized";
      let%bind missing = open_root (Filename.concat root "missing") in
      require_error_kind missing Invalid_request "missing project root was accepted";
      let no_project = Filename.concat root "no-dune-project" in
      Core_unix.mkdir no_project;
      let%map invalid = open_root no_project in
      require_error_kind
        invalid
        Invalid_request
        "directory without dune-project was accepted")
;;

let test_live_output_and_events ~root ~log_dir =
  let events = ref [] in
  let invocation ~root ~environment:_ _ =
    shell
      root
      "printf stdout-live; printf stderr-live >&2; sleep 0.25; printf stdout-done"
  in
  with_service ~events ~root ~log_dir invocation (fun service project ->
    let%bind submitted = submit service project Build "live" in
    let id = submitted.job.id in
    let%bind running =
      wait_for_job service id (fun job -> Job.State.equal job.state Running)
    in
    require (not (Job.is_terminal running)) "live-output job completed too early";
    let rec wait_for_live_log () =
      let%bind read = read_log service id in
      let payload = ok read in
      if List.length payload.records >= 2
      then return payload
      else (
        let%bind () = Clock.after (Time_float.Span.of_ms 10.) in
        wait_for_live_log ())
    in
    let%bind live =
      with_deadline "live output was not observable" (wait_for_live_log ())
    in
    require (not live.eof) "running log was reported at EOF";
    require
      (List.exists live.records ~f:(fun record ->
         V1.Read_log.Stream.equal record.stream Stdout
         && String.is_substring record.data ~substring:"stdout-live"))
      "stdout was not tagged";
    require
      (List.exists live.records ~f:(fun record ->
         V1.Read_log.Stream.equal record.stream Stderr
         && String.is_substring record.data ~substring:"stderr-live"))
      "stderr was not tagged";
    let%bind finished = wait_terminal service id in
    require (Job.State.equal finished.state Complete) "successful job did not complete";
    let final = snapshot service in
    let sequenced = List.rev !events in
    require
      (List.for_alli sequenced ~f:(fun index event -> event.V1.Event.sequence = index + 1))
      "event sequences were not contiguous";
    require
      (final.cursor.sequence = List.length sequenced)
      "snapshot cursor did not match emitted events";
    let last_project =
      List.filter_map sequenced ~f:(fun event ->
        match event.event with
        | Project_upsert project -> Some project
        | _ -> None)
      |> List.last_exn
    in
    let last_job =
      List.filter_map sequenced ~f:(fun event ->
        match event.event with
        | Job_upsert job when Job_id.equal job.id id -> Some job
        | _ -> None)
      |> List.last_exn
    in
    require
      (Project.equal last_project (List.hd_exn final.projects))
      "snapshot project disagreed with events";
    require
      (Job.equal last_job (List.hd_exn final.jobs))
      "snapshot job disagreed with events";
    return ())
;;

let test_failure_modes ~root ~log_dir =
  let invocation ~root ~environment:_ = function
    | V1.Dune_action.Build -> shell root "exit 7"
    | Test -> shell root "kill -TERM $$"
  in
  let%bind () =
    with_service ~root ~log_dir invocation (fun service project ->
      let%bind nonzero = submit service project Build "nonzero" in
      let%bind nonzero = wait_terminal service nonzero.job.id in
      require
        (Job.State.equal nonzero.state Failed
         && Option.value_map nonzero.exit_status ~default:false ~f:(function
           | Exited 7 -> true
           | _ -> false))
        "nonzero exit was not preserved";
      let%bind signaled = submit service project Test "signaled" in
      let%bind signaled = wait_terminal service signaled.job.id in
      require
        (Job.State.equal signaled.state Failed
         && Option.value_map signaled.exit_status ~default:false ~f:(function
           | Signaled _ -> true
           | _ -> false))
        "signal termination was not preserved";
      return ())
  in
  let launch_log_dir = log_dir ^ "-launch" in
  with_service
    ~root
    ~log_dir:launch_log_dir
    (fun ~root ~environment:_ _ -> missing root)
    (fun service project ->
      let%bind launched = submit service project Build "launch" in
      let%map launched = wait_terminal service launched.job.id in
      require
        (Job.State.equal launched.state Failed
         && Option.value_map launched.exit_status ~default:false ~f:(function
           | Launch_failed _ -> true
           | _ -> false)
         && Option.is_some launched.failure)
        "launch failure was not classified")
;;

let pid_is_alive pid =
  try
    let stat = In_channel.read_all (sprintf "/proc/%d/stat" pid) in
    match String.split stat ~on:' ' with
    | _pid :: _comm :: state :: _ -> not (String.equal state "Z")
    | _ -> fail "could not parse descendant process state"
  with
  | Sys_error _ ->
    (try
       match Signal_unix.send Signal.zero (`Pid (Pid.of_int pid)) with
       | `Ok -> true
       | `No_such_process -> false
     with
     | _ -> false)
;;

let rec wait_pid_dead pid =
  if not (pid_is_alive pid)
  then return ()
  else (
    let%bind () = Clock.after (Time_float.Span.of_ms 20.) in
    wait_pid_dead pid)
;;

let running_child_script =
  "/bin/sh -c 'trap \"\" TERM; while :; do sleep 1; done' & echo $!; wait"
;;

let wait_for_child_pid service id =
  let rec loop () =
    let%bind read = read_log service id in
    match Int.of_string_opt (String.strip (log_text (ok read))) with
    | Some pid -> return pid
    | None ->
      let%bind () = Clock.after (Time_float.Span.of_ms 10.) in
      loop ()
  in
  with_deadline "child pid was not logged" (loop ())
;;

let test_cancellation_and_descendants ~root ~log_dir =
  with_service
    ~root
    ~log_dir
    (fun ~root ~environment:_ _ -> shell root running_child_script)
    (fun service project ->
      let%bind submitted = submit service project Build "cancel" in
      let id = submitted.job.id in
      let%bind pid = wait_for_child_pid service id in
      require (pid_is_alive pid) "descendant was not running";
      let%bind cancelled = Service.cancel_job service { instance_id; job = id } in
      let cancelled = (ok cancelled).job in
      require (Job.State.equal cancelled.state Cancelled) "job was not cancelled";
      let%map () = with_deadline "descendant survived cancellation" (wait_pid_dead pid) in
      ())
;;

let test_shutdown_cleanup ~root ~log_dir =
  let%bind service =
    Service.create
      ~kill_after:(Time_float.Span.of_ms 100.)
      ~action_invocation:(fun ~root ~environment:_ _ -> shell root running_child_script)
      ~instance_id
      ~log_dir
      ()
  in
  let service = Or_error.ok_exn service in
  Monitor.protect
    ~finally:(fun () -> Service.shutdown service)
    (fun () ->
      let%bind opened =
        Service.open_project
          service
          { instance_id; root; environment = V1.Environment_selection.Inherit_daemon }
      in
      let project = (ok opened).project in
      let%bind submitted = submit service project Build "shutdown" in
      let id = submitted.job.id in
      let%bind pid = wait_for_child_pid service id in
      let%bind () =
        with_deadline "service shutdown timed out" (Service.shutdown service)
      in
      let stopped = job service id in
      require (Job.State.equal stopped.state Cancelled) "shutdown did not cancel job";
      let%map () = with_deadline "descendant survived shutdown" (wait_pid_dead pid) in
      ())
;;

let test_fifo_and_submission_keys ~root ~log_dir =
  let release = Filename.concat root "release-first" in
  let invocation_count = ref 0 in
  let invocation ~root ~environment:_ action =
    Int.incr invocation_count;
    match !invocation_count, action with
    | 1, V1.Dune_action.Build ->
      shell root (sprintf "echo first; while [ ! -e %s ]; do sleep 0.02; done" release)
    | _, _ -> shell root "echo second"
  in
  with_service ~root ~log_dir invocation (fun service project ->
    let%bind first = submit service project Build "first" in
    let%bind (_ : Job.t) =
      wait_for_job service first.job.id (fun job -> Job.State.equal job.state Running)
    in
    let%bind second = submit service project Test "second" in
    require
      (Job.State.equal (job service second.job.id).state Queued)
      "same-project job did not remain queued";
    require (!invocation_count = 1) "queued action was invoked before its turn";
    let%bind duplicate = submit service project Build "first" in
    require
      (Job_id.equal duplicate.job.id first.job.id)
      "same submission key did not deduplicate";
    let%bind conflict =
      Service.submit_job
        service
        { instance_id
        ; project = project.id
        ; action = V1.Dune_action.Test
        ; submission_key = "first"
        }
    in
    require_error_kind conflict Conflict "conflicting submission key was accepted";
    Out_channel.write_all release ~data:"release\n";
    let%bind first_done = wait_terminal service first.job.id in
    let%bind second_done = wait_terminal service second.job.id in
    require (Job.State.equal first_done.state Complete) "first FIFO job failed";
    require (Job.State.equal second_done.state Complete) "second FIFO job failed";
    require
      (Timestamp.compare
         (Option.value_exn first_done.finished_at)
         (Option.value_exn second_done.started_at)
       <= 0)
      "second FIFO job started before first finished";
    return ())
;;

let test_log_paging ~root ~log_dir =
  let line = String.make 120 'x' in
  let script =
    sprintf "i=0; while [ $i -lt 3000 ]; do printf '%%s\\n' %s; i=$((i+1)); done" line
  in
  with_service
    ~root
    ~log_dir
    (fun ~root ~environment:_ _ -> shell root script)
    (fun service project ->
      let%bind submitted = submit service project Build "large-log" in
      let id = submitted.job.id in
      let%bind finished = wait_terminal service id in
      require (Job.State.equal finished.state Complete) "large-output job failed";
      let rec pages offset total records =
        let%bind page = read_log ~offset ~max_records:2 service id in
        let page = ok page in
        List.iteri page.records ~f:(fun index record ->
          require
            (record.offset = offset + index)
            "log record offsets were not contiguous");
        let total = total + String.length (log_text page) in
        let records = records + List.length page.records in
        if page.eof
        then return (page.next_offset, total, records)
        else (
          require (page.next_offset > offset) "log paging made no progress";
          pages page.next_offset total records)
      in
      let%bind final_offset, total_bytes, total_records = pages 0 0 0 in
      require (total_bytes > V1.max_log_bytes) "log did not exceed one in-memory page";
      require (total_records > 2) "large log was not split into records";
      let%bind eof = read_log ~offset:final_offset service id in
      let eof = ok eof in
      require (eof.eof && List.is_empty eof.records) "EOF read was inconsistent";
      let%bind negative = read_log ~offset:(-1) service id in
      require_error_kind negative Invalid_request "negative log offset was accepted";
      let%bind future = read_log ~offset:(final_offset + 1) service id in
      require_error_kind future Invalid_request "future log offset was accepted";
      let%bind zero_records = read_log ~max_records:0 service id in
      require_error_kind zero_records Invalid_request "zero max_records was accepted";
      let%bind too_many_records =
        read_log ~max_records:(V1.max_log_records + 1) service id
      in
      require_error_kind
        too_many_records
        Invalid_request
        "oversized max_records was accepted";
      let%bind zero_bytes = read_log ~max_bytes:0 service id in
      require_error_kind zero_bytes Invalid_request "zero max_bytes was accepted";
      let%bind too_many_bytes = read_log ~max_bytes:(V1.max_log_bytes + 1) service id in
      require_error_kind too_many_bytes Invalid_request "oversized max_bytes was accepted";
      let files = Sys_unix.ls_dir log_dir in
      require (List.length files = 1) "expected one file-backed job log";
      let size = (Core_unix.stat (Filename.concat log_dir (List.hd_exn files))).st_size in
      require (Int64.to_int_exn size = total_bytes) "log file size disagreed with paging";
      return ())
;;

let run () =
  with_temp_tree (fun ~root ~log_dir ->
    let tests =
      [ "project opening and repeat identity", test_project_opening
      ; "live output and event consistency", test_live_output_and_events
      ; "failure modes", test_failure_modes
      ; "cancellation and descendant cleanup", test_cancellation_and_descendants
      ; "shutdown cleanup", test_shutdown_cleanup
      ; "FIFO and submission keys", test_fifo_and_submission_keys
      ; "file-backed log paging", test_log_paging
      ]
    in
    Deferred.List.iter tests ~how:`Sequential ~f:(fun (name, test) ->
      let test_log_dir =
        Filename.concat log_dir (String.tr name ~target:' ' ~replacement:'-')
      in
      printf "test: %s\n%!" name;
      test ~root ~log_dir:test_log_dir))
;;

let command =
  Command.async ~summary:"Test backend process supervision" (Command.Param.return run)
;;

let () = Command_unix.run command
