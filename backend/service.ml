open! Core
open! Async
open Hardcaml_workbench_protocol
module Adapter = Hardcaml_workbench_adapters.Dune_adapter

type event_sink = V1.Event.sequenced -> unit

type log_record =
  { stream : V1.Read_log.Stream.t
  ; position : int
  ; length : int
  }

type project_session =
  { key : string
  ; root : string
  ; environment : V1.Environment_selection.t
  ; mutable project : Project.t
  ; mutable summary : V1.Environment_summary.t
  ; mutable workspace : V1.Dune_workspace.Inspection.t
  ; queue : job_entry Queue.t
  ; mutable worker_running : bool
  }

and job_entry =
  { action : V1.Dune_action.t
  ; session : project_session
  ; mutable job : Job.t
  ; log_path : string
  ; log_writer : Writer.t
  ; log_records : (int, log_record) Hashtbl.t
  ; mutable log_position : int
  ; mutable next_log_offset : int
  ; mutable log_tail : unit Deferred.t
  ; mutable process : Process.t option
  ; mutable cancel_requested : bool
  ; mutable escalation_started : bool
  ; escalation_finished : unit Ivar.t
  ; finished : unit Ivar.t
  }

type submission =
  { project : Project_id.t
  ; action : V1.Dune_action.t
  ; ready : (job_entry, V1.Error.t) Result.t Ivar.t
  }

type t =
  { instance_id : V1.Daemon_instance_id.t
  ; log_dir : string
  ; projects_by_key : (string, project_session) Hashtbl.t
  ; projects : (Project_id.t, project_session) Hashtbl.t
  ; jobs : (Job_id.t, job_entry) Hashtbl.t
  ; submissions : (string, submission) Hashtbl.t
  ; mutable event_sink : event_sink
  ; mutable sequence : int
  ; mutable next_project_id : int
  ; mutable next_job_id : int
  ; mutable shutting_down : bool
  ; kill_after : Time_float.Span.t
  ; action_invocation :
      root:string
      -> environment:V1.Environment_selection.t
      -> V1.Dune_action.t
      -> Adapter.Invocation.t
  }

let error kind message = Error (V1.Error.create kind message)

let check_instance t instance_id =
  if V1.Daemon_instance_id.equal instance_id t.instance_id
  then Ok ()
  else error V1.Error.Kind.Instance_changed "daemon instance has changed"
;;

let create
  ?(kill_after = Time_float.Span.of_sec 2.)
  ?(action_invocation = Adapter.action_invocation)
  ~instance_id
  ~log_dir
  ()
  =
  let%map result =
    Monitor.try_with_or_error (fun () ->
      In_thread.run (fun () ->
        match Sys_unix.file_exists log_dir with
        | `Yes ->
          if not (Sys_unix.is_directory_exn log_dir)
          then failwithf "log path is not a directory: %s" log_dir ()
        | `No | `Unknown -> Core_unix.mkdir log_dir ~perm:0o700))
  in
  Result.map result ~f:(fun () ->
    { instance_id
    ; log_dir
    ; projects_by_key = Hashtbl.create (module String)
    ; projects = Project_id.Table.create ()
    ; jobs = Job_id.Table.create ()
    ; submissions = Hashtbl.create (module String)
    ; event_sink = ignore
    ; sequence = 0
    ; next_project_id = 0
    ; next_job_id = 0
    ; shutting_down = false
    ; kill_after
    ; action_invocation
    })
;;

let set_event_sink t sink = t.event_sink <- sink

let emit t event =
  t.sequence <- t.sequence + 1;
  try t.event_sink { V1.Event.sequence = t.sequence; event } with
  | _ -> ()
;;

let snapshot t ({ instance_id } : V1.Snapshot.Request.t) =
  match check_instance t instance_id with
  | Error _ as error -> error
  | Ok () ->
    let projects =
      Hashtbl.data t.projects
      |> List.map ~f:(fun session -> session.project)
      |> List.sort ~compare:(fun (a : Project.t) b -> Project_id.compare a.id b.id)
    in
    let jobs =
      Hashtbl.data t.jobs
      |> List.map ~f:(fun entry -> entry.job)
      |> List.sort ~compare:(fun (a : Job.t) b -> Job_id.compare a.id b.id)
    in
    Ok
      { V1.Snapshot.Payload.projects
      ; jobs
      ; artifacts = []
      ; cursor = { instance_id = t.instance_id; sequence = t.sequence }
      }
;;

let command_output invocation =
  let args = List.tl invocation.Adapter.Invocation.argv |> Option.value ~default:[] in
  let argv0 = List.hd invocation.argv in
  let%bind process =
    Process.create ?argv0 ~working_dir:invocation.cwd ~prog:invocation.executable ~args ()
  in
  match process with
  | Error error -> return (Error (Error.to_string_hum error))
  | Ok process ->
    let%map output = Process.collect_output_and_wait process in
    (match output.exit_status with
     | Ok () -> Ok output.stdout
     | Error _ ->
       Error
         (sprintf
            "%s\n%s"
            (Unix.Exit_or_signal.to_string_hum output.exit_status)
            (String.prefix output.stderr 4096)))
;;

let canonical_project_root root =
  Monitor.try_with (fun () ->
    In_thread.run (fun () ->
      let root = Filename_unix.realpath root in
      if not (Sys_unix.is_directory_exn root)
      then failwith "project root is not a directory";
      let dune_project = Filename.concat root "dune-project" in
      (match Sys_unix.file_exists dune_project with
       | `Yes -> ()
       | `No | `Unknown -> failwith "project root must directly contain dune-project");
      (match (Core_unix.stat dune_project).st_kind with
       | S_REG -> ()
       | _ -> failwith "dune-project is not a regular file");
      root))
  >>| Result.map_error ~f:(fun exn -> Exn.to_string exn)
;;

let project_name root =
  Monitor.try_with (fun () ->
    In_thread.run (fun () ->
      let sexps = Sexp.load_sexps (Filename.concat root "dune-project") in
      List.find_map sexps ~f:(function
        | Sexp.List [ Atom "name"; Atom name ] -> Some name
        | Atom _ | List _ -> None)))
  >>| function
  | Ok (Some name) -> name
  | Ok None | Error _ -> Filename.basename root
;;

let environment_key environment =
  Sexp.to_string_mach (V1.Environment_selection.sexp_of_t environment)
;;

let mint_project_id t =
  t.next_project_id <- t.next_project_id + 1;
  Project_id.of_string
    (sprintf
       "%s-project-%d"
       (V1.Daemon_instance_id.to_string t.instance_id)
       t.next_project_id)
;;

let open_project t ({ instance_id; root; environment } : V1.Open_project.Request.t) =
  match check_instance t instance_id with
  | Error _ as error -> return error
  | Ok () when t.shutting_down -> return (error Conflict "daemon is shutting down")
  | Ok () ->
    let%bind canonical = canonical_project_root root in
    (match canonical with
     | Error message -> return (error Invalid_request message)
     | Ok root ->
       let key = root ^ "\000" ^ environment_key environment in
       (match Hashtbl.find t.projects_by_key key with
        | Some session ->
          return
            (Ok
               { V1.Open_project.Payload.project = session.project
               ; environment = session.summary
               ; workspace = session.workspace
               })
        | None ->
          let%bind probe = command_output (Adapter.probe_invocation ~root environment) in
          (match probe |> Result.bind ~f:Adapter.parse_probe_output with
           | Error message -> return (error Unsupported_operation message)
           | Ok dune_version ->
             let%bind inspection =
               command_output (Adapter.inspect_invocation ~root environment)
             in
             (match inspection |> Result.bind ~f:Adapter.parse_workspace with
              | Error message -> return (error Internal_failure message)
              | Ok workspace ->
                let%map name = project_name root in
                let summary = Adapter.environment_summary environment ~dune_version in
                let project : Project.t =
                  { id = mint_project_id t
                  ; root = Project_root.of_absolute_path root
                  ; name
                  ; integration = Project_integration.generic_dune
                  ; targets = []
                  ; configurations = []
                  }
                in
                let session =
                  { key
                  ; root
                  ; environment
                  ; project
                  ; summary
                  ; workspace
                  ; queue = Queue.create ()
                  ; worker_running = false
                  }
                in
                Hashtbl.set t.projects_by_key ~key ~data:session;
                Hashtbl.set t.projects ~key:project.id ~data:session;
                emit t (Project_upsert session.project);
                Ok
                  { V1.Open_project.Payload.project = session.project
                  ; environment = session.summary
                  ; workspace = session.workspace
                  }))))
;;

let update_job t entry job =
  entry.job <- job;
  emit t (Job_upsert job)
;;

let append_log t entry stream data =
  let pieces = String.to_list data |> List.chunks_of ~length:(16 * 1024) in
  List.iter pieces ~f:(fun chars ->
    let data = String.of_char_list chars in
    let offset = entry.next_log_offset in
    let record = { stream; position = entry.log_position; length = String.length data } in
    entry.next_log_offset <- offset + 1;
    entry.log_position <- entry.log_position + record.length;
    Hashtbl.set entry.log_records ~key:offset ~data:record;
    let previous = entry.log_tail in
    entry.log_tail
    <- (let%bind () = previous in
        Writer.write entry.log_writer data;
        let%map () = Writer.flushed entry.log_writer in
        emit t (Log_available { job = entry.job.id; next_offset = offset + 1 })));
  entry.log_tail
;;

let drain t entry stream reader =
  let%map (_ : unit Reader.read_one_chunk_at_a_time_result) =
    Reader.read_one_chunk_at_a_time reader ~handle_chunk:(fun buffer ~pos ~len ->
      let data = Bigstring.To_string.sub buffer ~pos ~len in
      let%map () = append_log t entry stream data in
      `Continue)
  in
  ()
;;

let exit_status = function
  | Ok () -> Job.Exit_status.Exited 0
  | Error (`Exit_non_zero code) -> Exited code
  | Error (`Signal signal) -> Signaled { signal = Signal.to_string signal }
;;

let signal_group process signal = Signal_unix.send_i signal (`Group (Process.pid process))

let begin_escalation t entry process =
  if not entry.escalation_started
  then (
    entry.escalation_started <- true;
    signal_group process Signal.term;
    don't_wait_for
      (let%bind () = Clock.after t.kill_after in
       signal_group process Signal.kill;
       Ivar.fill_if_empty entry.escalation_finished ();
       return ()))
;;

let finish_entry t entry state status failure =
  let now = Timestamp.of_time_ns (Time_ns.now ()) in
  update_job
    t
    entry
    { entry.job with
      state
    ; phase = None
    ; exit_status = status
    ; failure
    ; finished_at = Some now
    };
  Ivar.fill_if_empty entry.finished ()
;;

let rec run_next t session =
  match Queue.dequeue session.queue with
  | None -> session.worker_running <- false
  | Some entry when Job.is_terminal entry.job -> run_next t session
  | Some entry ->
    don't_wait_for
      (let started_at = Timestamp.of_time_ns (Time_ns.now ()) in
       update_job
         t
         entry
         { entry.job with
           state = Starting
         ; phase = Some "starting"
         ; started_at = Some started_at
         };
       let invocation =
         t.action_invocation
           ~root:session.root
           ~environment:session.environment
           entry.action
       in
       let args = List.tl invocation.argv |> Option.value ~default:[] in
       let argv0 = List.hd invocation.argv in
       let%bind created =
         Process.create
           ?argv0
           ~working_dir:invocation.cwd
           ~setpgid:Core_unix.Pgid.new_process_group
           ~prog:invocation.executable
           ~args
           ()
       in
       match created with
       | Error launch_error ->
         let reason = Error.to_string_hum launch_error in
         if entry.cancel_requested || t.shutting_down
         then finish_entry t entry Cancelled (Some (Launch_failed { reason })) None
         else finish_entry t entry Failed (Some (Launch_failed { reason })) (Some reason);
         let%bind () = Writer.close entry.log_writer in
         run_next t session;
         return ()
       | Ok process ->
         entry.process <- Some process;
         don't_wait_for (Writer.close (Process.stdin process));
         update_job t entry { entry.job with state = Running; phase = Some "running" };
         if entry.cancel_requested || t.shutting_down
         then begin_escalation t entry process;
         let stdout = drain t entry Stdout (Process.stdout process) in
         let stderr = drain t entry Stderr (Process.stderr process) in
         let%bind status = Process.wait process in
         let%bind () = Deferred.all_unit [ stdout; stderr; entry.log_tail ] in
         let%bind () = Writer.close entry.log_writer in
         let status = exit_status status in
         if entry.cancel_requested || t.shutting_down
         then finish_entry t entry Cancelled (Some status) None
         else (
           match status with
           | Exited 0 -> finish_entry t entry Complete (Some status) None
           | Exited _ | Signaled _ -> finish_entry t entry Failed (Some status) None
           | Launch_failed _ -> assert false);
         run_next t session;
         return ())
;;

let action_kind = function
  | V1.Dune_action.Build -> { Job.Kind.namespace = "dune"; name = "build" }
  | Test -> { namespace = "dune"; name = "test" }
;;

let mint_job_id t =
  t.next_job_id <- t.next_job_id + 1;
  Job_id.of_string
    (sprintf "%s-job-%d" (V1.Daemon_instance_id.to_string t.instance_id) t.next_job_id)
;;

let submit_job
  t
  ({ instance_id; project; action; submission_key } : V1.Submit_job.Request.t)
  =
  match check_instance t instance_id with
  | Error _ as error -> return error
  | Ok () when t.shutting_down -> return (error Conflict "daemon is shutting down")
  | Ok () when String.is_empty submission_key ->
    return (error Invalid_request "submission_key must not be empty")
  | Ok () ->
    (match Hashtbl.find t.submissions submission_key with
     | Some submission ->
       if Project_id.equal project submission.project
          && V1.Dune_action.equal action submission.action
       then (
         let%map ready = Ivar.read submission.ready in
         Result.map ready ~f:(fun entry -> { V1.Submit_job.Payload.job = entry.job }))
       else return (error Conflict "submission_key was already used for another request")
     | None ->
       (match Hashtbl.find t.projects project with
        | None -> return (error Not_found "project is not open")
        | Some session ->
          let id = mint_job_id t in
          let submission = { project; action; ready = Ivar.create () } in
          Hashtbl.set t.submissions ~key:submission_key ~data:submission;
          let job =
            Job.create
              ~id
              ~kind:(action_kind action)
              ~project
              ~created_at:(Timestamp.of_time_ns (Time_ns.now ()))
          in
          let log_path =
            Filename.concat
              t.log_dir
              (sprintf "job-%d-%d.log" (Pid.to_int (Core_unix.getpid ())) t.next_job_id)
          in
          let%map opened =
            Monitor.try_with_or_error (fun () ->
              Writer.open_file ~append:true ~perm:0o600 log_path)
          in
          (match opened with
           | Error open_error ->
             let failure =
               V1.Error.create
                 Internal_failure
                 ("could not open job log: " ^ Error.to_string_hum open_error)
             in
             Ivar.fill_exn submission.ready (Error failure);
             Error failure
           | Ok log_writer ->
             let entry =
               { action
               ; session
               ; job
               ; log_path
               ; log_writer
               ; log_records = Hashtbl.create (module Int)
               ; log_position = 0
               ; next_log_offset = 0
               ; log_tail = return ()
               ; process = None
               ; cancel_requested = false
               ; escalation_started = false
               ; escalation_finished = Ivar.create ()
               ; finished = Ivar.create ()
               }
             in
             Hashtbl.set t.jobs ~key:id ~data:entry;
             Ivar.fill_exn submission.ready (Ok entry);
             Queue.enqueue session.queue entry;
             emit t (Job_upsert job);
             if not session.worker_running
             then (
               session.worker_running <- true;
               run_next t session);
             Ok { V1.Submit_job.Payload.job })))
;;

let cancel_entry t entry =
  if Job.is_terminal entry.job
  then return ()
  else (
    entry.cancel_requested <- true;
    match entry.process with
    | Some process ->
      begin_escalation t entry process;
      Deferred.all_unit [ Ivar.read entry.finished; Ivar.read entry.escalation_finished ]
    | None when Job.State.equal entry.job.state Queued ->
      finish_entry t entry Cancelled None None;
      let%bind () = Writer.close entry.log_writer in
      return ()
    | None -> Ivar.read entry.finished)
;;

let cancel_job t ({ instance_id; job } : V1.Cancel_job.Request.t) =
  match check_instance t instance_id with
  | Error _ as error -> return error
  | Ok () ->
    (match Hashtbl.find t.jobs job with
     | None -> return (error Not_found "job was not found")
     | Some entry ->
       let%map () = cancel_entry t entry in
       Ok { V1.Cancel_job.Payload.job = entry.job })
;;

let read_exact reader ~position ~length =
  let buffer = Bytes.create length in
  let%bind (_ : int64) = Reader.lseek reader (Int64.of_int position) ~mode:`Set in
  let rec loop offset =
    if offset = length
    then return (Ok (Bytes.to_string buffer))
    else (
      let%bind read = Reader.read reader ~pos:offset ~len:(length - offset) buffer in
      match read with
      | `Eof -> return (Error "unexpected end of log file")
      | `Ok count -> loop (offset + count))
  in
  loop 0
;;

let rec flush_current_log_tail entry =
  let tail = entry.log_tail in
  let%bind () = tail in
  if phys_equal tail entry.log_tail then return () else flush_current_log_tail entry
;;

let read_log
  t
  ({ instance_id; job; offset; max_records; max_bytes } : V1.Read_log.Request.t)
  =
  match check_instance t instance_id with
  | Error _ as error -> return error
  | Ok ()
    when max_records <= 0
         || max_records > V1.max_log_records
         || max_bytes <= 0
         || max_bytes > V1.max_log_bytes ->
    return (error Invalid_request "invalid log read bounds")
  | Ok () ->
    (match Hashtbl.find t.jobs job with
     | None -> return (error Not_found "job was not found")
     | Some entry when offset < 0 || offset > entry.next_log_offset ->
       return (error Invalid_request "log offset is outside the available range")
     | Some entry ->
       let%bind () = flush_current_log_tail entry in
       let rec select index count bytes records =
         if count = max_records || index = entry.next_log_offset
         then List.rev records, index
         else (
           let record = Hashtbl.find_exn entry.log_records index in
           if bytes + record.length > max_bytes
           then List.rev records, index
           else select (index + 1) (count + 1) (bytes + record.length) (record :: records))
       in
       let metadata, next_offset = select offset 0 0 [] in
       let%bind records =
         match metadata with
         | [] -> return (Ok [])
         | _ ->
           Monitor.try_with (fun () ->
             let%bind reader = Reader.open_file entry.log_path in
             Monitor.protect
               ~finally:(fun () -> Reader.close reader)
               (fun () ->
                 Deferred.List.mapi metadata ~how:`Sequential ~f:(fun index record ->
                   let%map data =
                     read_exact reader ~position:record.position ~length:record.length
                     >>| Result.ok_or_failwith
                   in
                   { V1.Read_log.Record.offset = offset + index
                   ; stream = record.stream
                   ; data
                   })))
           >>| Result.map_error ~f:Exn.to_string
       in
       (match records with
        | Error message -> return (error Internal_failure message)
        | Ok records ->
          return
            (Ok
               { V1.Read_log.Payload.records
               ; next_offset
               ; eof = Job.is_terminal entry.job && next_offset = entry.next_log_offset
               })))
;;

let shutdown t =
  t.shutting_down <- true;
  let%bind () =
    Hashtbl.data t.submissions
    |> Deferred.List.iter ~how:`Parallel ~f:(fun submission ->
      let%bind ready = Ivar.read submission.ready in
      match ready with
      | Error _ -> return ()
      | Ok entry -> cancel_entry t entry)
  in
  Monitor.try_with (fun () ->
    In_thread.run (fun () ->
      Sys_unix.readdir t.log_dir
      |> Array.iter ~f:(fun name -> Core_unix.unlink (Filename.concat t.log_dir name));
      Core_unix.rmdir t.log_dir))
  >>| ignore
;;
