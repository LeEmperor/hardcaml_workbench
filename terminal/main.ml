open! Core
open! Async
open Hardcaml_workbench_protocol
module Http = Hardcaml_workbench_native_http

let console_limit = 500
let minimum_width = 68
let minimum_height = 20
let take_end values count = List.rev values |> Fn.flip List.take count |> List.rev

type log_state =
  { mutable next_offset : int
  ; mutable records : V1.Read_log.Record.t list
  }

type session =
  { requested_endpoint : string option
  ; project_root : string option
  ; environment_selection : V1.Environment_selection.t
  ; environment_label : string
  ; diagnostics_file : string option
  ; mutable client : Http.Client.t
  ; mutable hello : V1.Hello.Response.t
  ; mutable opened : V1.Open_project.Payload.t option
  ; mutable snapshot : V1.Snapshot.Payload.t
  ; mutable selected : int
  ; logs : log_state Job_id.Table.t
  ; mutable status : string
  ; mutable polling : bool
  ; mutable reconnect_delay_ms : int
  ; mutable last_dimensions : Bonsai_term.Dimensions.t option
  }

let append_diagnostic file message =
  Option.iter file ~f:(fun file ->
    try
      Out_channel.with_file file ~append:true ~f:(fun channel ->
        Out_channel.fprintf
          channel
          "%s %s\n"
          (Time_ns.to_string_utc (Time_ns.now ()))
          message)
    with
    | _ -> ())
;;

let error_message error = Error.to_string_hum error

let protocol_error (error : V1.Error.t) =
  sprintf "%s: %s" (Sexp.to_string_hum (V1.Error.Kind.sexp_of_t error.kind)) error.message
;;

let request diagnostics thunk =
  Monitor.try_with_or_error thunk
  >>| Or_error.join
  >>| function
  | Error error ->
    append_diagnostic diagnostics ("request error: " ^ error_message error);
    Error (error_message error)
  | Ok (Error error) ->
    let message = protocol_error error in
    append_diagnostic diagnostics ("protocol error: " ^ message);
    Error message
  | Ok (Ok value) -> Ok value
;;

let hello_request diagnostics thunk =
  Monitor.try_with_or_error thunk
  >>| Or_error.join
  >>| Result.map_error ~f:(fun error ->
    let message = error_message error in
    append_diagnostic diagnostics ("connection error: " ^ message);
    message)
;;

let explicit_client endpoint =
  let uri = Uri.of_string endpoint in
  match Uri.scheme uri, Uri.host uri with
  | Some scheme, Some host
    when String.Caseless.equal scheme "http"
         && (String.Caseless.equal host "localhost"
             || String.equal host "127.0.0.1"
             || String.equal host "::1") -> Ok (Http.Client.create endpoint)
  | _ ->
    Or_error.error_string
      "--connect must be an http://localhost, http://127.0.0.1, or http://[::1] endpoint"
;;

let connect_client ~endpoint ~diagnostics =
  match endpoint with
  | Some endpoint ->
    (match explicit_client endpoint with
     | Error error -> return (Error (error_message error))
     | Ok client ->
       let%map hello = hello_request diagnostics (fun () -> Http.Client.hello client) in
       Result.map hello ~f:(fun hello -> client, hello))
  | None ->
    Monitor.try_with_or_error Http.Runtime.connect_or_start
    >>| Or_error.join
    >>| Result.map_error ~f:(fun error ->
      let message = error_message error in
      append_diagnostic diagnostics ("startup error: " ^ message);
      message)
;;

let check_version hello =
  if List.mem hello.V1.Hello.Response.protocol_versions V1.version ~equal:Int.equal
  then Ok ()
  else
    Or_error.error_s
      [%message
        "daemon does not support this client's protocol version"
          (V1.version : int)
          (hello.protocol_versions : int list)]
;;

let load_state ~endpoint ~project_root ~environment_selection ~diagnostics =
  let%bind connected = connect_client ~endpoint ~diagnostics in
  match connected with
  | Error _ as error -> return error
  | Ok (client, hello) ->
    (match check_version hello with
     | Error error -> return (Error (error_message error))
     | Ok () ->
       let instance_id = hello.instance_id in
       let%bind opened =
         match project_root with
         | None -> return (Ok None)
         | Some root ->
           request diagnostics (fun () ->
             Http.Client.open_project
               client
               { instance_id; root; environment = environment_selection })
           >>| Result.map ~f:Option.some
       in
       (match opened with
        | Error _ as error -> return error
        | Ok opened ->
          let%map snapshot =
            request diagnostics (fun () -> Http.Client.snapshot client { instance_id })
          in
          Result.map snapshot ~f:(fun snapshot -> client, hello, opened, snapshot)))
;;

let create_session
  ~endpoint
  ~project_root
  ~environment_selection
  ~environment_label
  ~diagnostics_file
  =
  let%map loaded =
    load_state
      ~endpoint
      ~project_root
      ~environment_selection
      ~diagnostics:diagnostics_file
  in
  Result.map loaded ~f:(fun (client, hello, opened, snapshot) ->
    { requested_endpoint = endpoint
    ; project_root
    ; environment_selection
    ; environment_label
    ; diagnostics_file
    ; client
    ; hello
    ; opened
    ; snapshot
    ; selected = 0
    ; logs = Job_id.Table.create ()
    ; status = "connected"
    ; polling = false
    ; reconnect_delay_ms = 250
    ; last_dimensions = None
    })
;;

let project_jobs session =
  let jobs =
    match session.opened with
    | None -> session.snapshot.jobs
    | Some opened ->
      List.filter session.snapshot.jobs ~f:(fun job ->
        Project_id.equal job.project opened.project.id)
  in
  List.sort jobs ~compare:(fun a b -> Timestamp.compare b.created_at a.created_at)
;;

let selected_job session = List.nth (project_jobs session) session.selected

let log_state session job =
  Hashtbl.find_or_add session.logs job ~default:(fun () ->
    { next_offset = 0; records = [] })
;;

let read_selected_log session =
  match selected_job session with
  | None -> return ()
  | Some job ->
    let state = log_state session job.id in
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.read_log
          session.client
          { instance_id = session.hello.instance_id
          ; job = job.id
          ; offset = state.next_offset
          ; max_records = 128
          ; max_bytes = V1.max_log_bytes
          })
    in
    (match response with
     | Error message -> session.status <- "log: " ^ message
     | Ok payload ->
       let records =
         List.filter payload.records ~f:(fun record -> record.offset >= state.next_offset)
       in
       state.next_offset <- payload.next_offset;
       state.records <- take_end (state.records @ records) console_limit)
;;

let rec refresh session =
  if session.polling
  then return ()
  else (
    session.polling <- true;
    Monitor.protect
      ~finally:(fun () ->
        session.polling <- false;
        return ())
      (fun () ->
        let update_request : V1.Updates.Request.t =
          { instance_id = session.hello.instance_id
          ; cursor = session.snapshot.cursor
          ; max_events = V1.max_update_events
          ; timeout_ms = 200
          }
        in
        let%bind updates =
          request session.diagnostics_file (fun () ->
            Http.Client.updates session.client update_request)
        in
        let%bind snapshot =
          request session.diagnostics_file (fun () ->
            Http.Client.snapshot
              session.client
              { instance_id = session.hello.instance_id })
        in
        match snapshot with
        | Error message ->
          session.status <- "disconnected: " ^ message ^ "; reconnecting...";
          let%bind () =
            Clock.after (Time_float.Span.of_ms (Float.of_int session.reconnect_delay_ms))
          in
          reconnect session
        | Ok snapshot ->
          session.snapshot <- snapshot;
          let count = List.length (project_jobs session) in
          session.selected <- Int.min session.selected (Int.max 0 (count - 1));
          session.status
          <- (match updates with
              | Ok _ -> "connected"
              | Error _ -> "connected; update cursor recovered from snapshot");
          read_selected_log session))

and reconnect session =
  session.status <- "reconnecting...";
  let%map loaded =
    load_state
      ~endpoint:session.requested_endpoint
      ~project_root:session.project_root
      ~environment_selection:session.environment_selection
      ~diagnostics:session.diagnostics_file
  in
  match loaded with
  | Error message ->
    session.status <- "reconnect failed: " ^ message;
    session.reconnect_delay_ms <- Int.min 5_000 (session.reconnect_delay_ms * 2)
  | Ok (client, hello, opened, snapshot) ->
    let instance_changed =
      not
        (String.equal
           (V1.Daemon_instance_id.to_string session.hello.instance_id)
           (V1.Daemon_instance_id.to_string hello.instance_id))
    in
    session.client <- client;
    session.hello <- hello;
    session.opened <- opened;
    session.snapshot <- snapshot;
    session.selected <- 0;
    Hashtbl.clear session.logs;
    session.reconnect_delay_ms <- 250;
    session.status
    <- (if instance_changed
        then "reconnected to new daemon instance; no jobs were resubmitted"
        else "reconnected; no jobs were resubmitted")
;;

let submission_key action =
  sprintf
    "terminal-%s-%s-%06x"
    action
    (Time_ns.now () |> Time_ns.to_int63_ns_since_epoch |> Int63.to_string)
    (Random.bits ())
;;

let upsert_job (snapshot : V1.Snapshot.Payload.t) (job : Job.t) =
  let jobs =
    job
    :: List.filter snapshot.V1.Snapshot.Payload.jobs ~f:(fun (existing : Job.t) ->
      not (Job_id.equal existing.id job.id))
  in
  { snapshot with jobs }
;;

let submit session action =
  match session.opened with
  | None ->
    session.status <- "build/test requires --project-root";
    return ()
  | Some opened ->
    let action_name, protocol_action =
      match action with
      | `Build -> "build", V1.Dune_action.Build
      | `Test -> "test", V1.Dune_action.Test
    in
    let key = submission_key action_name in
    session.status <- sprintf "submitting %s..." action_name;
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.submit_job
          session.client
          { instance_id = session.hello.instance_id
          ; project = opened.project.id
          ; action = protocol_action
          ; submission_key = key
          })
    in
    (match response with
     | Error message ->
       session.status <- sprintf "%s submission failed: %s" action_name message
     | Ok payload ->
       session.snapshot <- upsert_job session.snapshot payload.job;
       session.selected <- 0;
       session.status
       <- sprintf "submitted %s as %s" action_name (Job_id.to_string payload.job.id))
;;

let cancel_selected session =
  match selected_job session with
  | None ->
    session.status <- "no selected job to cancel";
    return ()
  | Some job when Job.is_terminal job ->
    session.status <- "selected job is already terminal";
    return ()
  | Some job ->
    session.status <- "cancelling " ^ Job_id.to_string job.id ^ "...";
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.cancel_job
          session.client
          { instance_id = session.hello.instance_id; job = job.id })
    in
    (match response with
     | Error message -> session.status <- "cancel failed: " ^ message
     | Ok payload ->
       session.snapshot <- upsert_job session.snapshot payload.job;
       session.status <- "cancellation requested")
;;

let fit width text =
  if width <= 0
  then ""
  else if String.length text <= width
  then text
  else if width <= 3
  then String.prefix text width
  else String.prefix text (width - 3) ^ "..."
;;

let environment_lines session =
  match session.opened with
  | None ->
    [ "Project: none (use --project-root ROOT)"
    ; "Environment request: " ^ session.environment_label
    ; "Generic Dune workspace: no project opened"
    ]
  | Some opened ->
    let environment = opened.environment in
    let contexts =
      match opened.workspace.contexts with
      | [] -> "none reported"
      | contexts -> String.concat contexts ~sep:", "
    in
    let item_summary =
      if List.is_empty opened.workspace.items
      then "no workspace items reported"
      else
        sprintf
          "%d inspected item%s"
          (List.length opened.workspace.items)
          (if List.length opened.workspace.items = 1 then "" else "s")
    in
    [ sprintf
        "Project: %s  root=%s"
        opened.project.name
        (Project_root.to_absolute_path opened.project.root)
    ; sprintf
        "Environment request: %s  resolved=%s  dune=%s"
        session.environment_label
        environment.provenance
        environment.dune_version
    ; sprintf "Generic Dune workspace: contexts=%s; %s" contexts item_summary
    ]
;;

let render session ({ Bonsai_term.Dimensions.width; height } as dimensions) =
  let open Bonsai_term in
  if not (Option.equal Dimensions.equal session.last_dimensions (Some dimensions))
  then (
    session.last_dimensions <- Some dimensions;
    append_diagnostic
      session.diagnostics_file
      (sprintf "dimensions width=%d height=%d" width height));
  let background = View.rectangle ~width ~height () in
  let content =
    if width < minimum_width || height < minimum_height
    then
      View.center
        (View.vcat
           [ View.text ~attrs:[ Attr.bold ] "Hardcaml Workbench"
           ; View.text
               (sprintf
                  "Terminal too small (%dx%d); need at least %dx%d"
                  width
                  height
                  minimum_width
                  minimum_height)
           ; View.text "Resize to continue. q exits."
           ])
        ~within:dimensions
    else (
      let jobs = project_jobs session in
      let header =
        [ "Hardcaml Workbench | terminal workflow | " ^ session.status
        ; sprintf
            "Daemon: %s | instance=%s | protocol=v%d"
            (Http.Client.endpoint session.client)
            (V1.Daemon_instance_id.to_string session.hello.instance_id)
            V1.version
        ]
      in
      let workspace_rows =
        match session.opened with
        | None -> [ "  (no project opened)" ]
        | Some opened ->
          if List.is_empty opened.workspace.items
          then [ "  (no local items reported)" ]
          else
            List.map opened.workspace.items ~f:(fun item ->
              sprintf
                "  %-12s %s%s"
                item.kind
                (if List.is_empty item.names
                 then "(unnamed)"
                 else String.concat item.names ~sep:",")
                (Option.value_map item.source_path ~default:"" ~f:(fun path ->
                   "  " ^ path)))
      in
      let job_rows =
        if List.is_empty jobs
        then [ "  (no jobs)" ]
        else
          List.mapi jobs ~f:(fun index job ->
            sprintf
              "%s %-24s %-12s %-16s %s"
              (if index = session.selected then ">" else " ")
              (Job_id.to_string job.id)
              (Job.State.to_string job.state)
              (Job.Kind.to_string job.kind)
              (Option.value job.phase ~default:""))
      in
      let detail =
        match selected_job session with
        | None -> [ ""; "SELECTED JOB"; "  none" ]
        | Some job ->
          [ ""
          ; "SELECTED JOB"
          ; sprintf
              "  %s | state=%s | exit=%s | failure=%s"
              (Job_id.to_string job.id)
              (Job.State.to_string job.state)
              (Option.value_map job.exit_status ~default:"-" ~f:(fun value ->
                 Sexp.to_string_hum (Job.Exit_status.sexp_of_t value)))
              (Option.value job.failure ~default:"-")
          ]
      in
      let controls =
        "b build | t test | c cancel | j/k select | r reconnect/refresh | q exit"
      in
      let top_height = Int.max 8 ((height - List.length header - 3) / 2) in
      let console_height = Int.max 1 (height - List.length header - top_height - 3) in
      let left_width = width / 3 in
      let right_width = width - left_width - 1 in
      let pane ~width ~height lines =
        let lines = List.take lines height in
        let lines = lines @ List.init (height - List.length lines) ~f:(fun _ -> "") in
        lines
        |> List.map ~f:(fun line ->
          let line = fit width line in
          View.text (line ^ String.make (width - String.length line) ' '))
        |> View.vcat
      in
      let project_pane =
        pane
          ~width:left_width
          ~height:top_height
          ([ "PROJECT / GENERIC DUNE WORKSPACE" ]
           @ environment_lines session
           @ [ ""; "DUNE ITEMS" ]
           @ workspace_rows
           @ [ ""; "Hardcaml hierarchy: unavailable until project driver integration" ])
      in
      let jobs_pane =
        pane ~width:right_width ~height:top_height ([ "JOBS" ] @ job_rows @ detail)
      in
      let upper =
        View.hcat
          [ project_pane
          ; View.rectangle ~fill:'|' ~width:1 ~height:top_height ()
          ; jobs_pane
          ]
      in
      let console =
        match selected_job session with
        | None -> [ "  (select a job to read logs)" ]
        | Some job ->
          let state = log_state session job.id in
          if List.is_empty state.records
          then [ "  (no log records yet)" ]
          else
            List.concat_map state.records ~f:(fun record ->
              let tag =
                match record.stream with
                | V1.Read_log.Stream.Stdout -> "[stdout] "
                | Stderr -> "[stderr] "
              in
              String.split_lines record.data |> List.map ~f:(fun line -> tag ^ line))
            |> Fn.flip take_end console_height
      in
      View.vcat
        [ View.vcat (List.map header ~f:(fun line -> View.text (fit width line)))
        ; upper
        ; View.text (String.make width '-')
        ; View.text "LIVE STDOUT / STDERR"
        ; pane ~width ~height:console_height console
        ; View.text (fit width controls)
        ])
  in
  View.zcat [ content; background ]
;;

let key_is char = function
  | Bonsai_term.Event.Key.ASCII value -> Char.equal char value
  | Uchar value -> Uchar.equal value (Uchar.of_char char)
  | _ -> false
;;

let tui session ~exit ~dimensions graph =
  let open Bonsai_term in
  let poll = Effect.of_deferred_thunk (fun () -> refresh session) in
  Bonsai.Clock.every
    ~when_to_start_next_effect:`Wait_period_after_previous_effect_finishes_blocking
    ~trigger_on_activate:true
    (Bonsai.return (Time_ns.Span.of_ms 500.))
    (Bonsai.return poll)
    graph;
  let view =
    Bonsai.map2
      dimensions
      (Bonsai.Clock.approx_now ~tick_every:(Time_ns.Span.of_ms 100.) graph)
      ~f:(fun dimensions _now -> render session dimensions)
  in
  let handler =
    Bonsai.return (fun (event : Event.t) ->
      match event with
      | Key_press { key; mods = [] } when key_is 'q' key -> exit ()
      | Key_press { key; mods = [ Ctrl ] } when key_is 'c' key || key_is 'C' key ->
        exit ()
      | Key_press { key; mods = [] } when key_is 'b' key ->
        Effect.of_deferred_thunk (fun () -> submit session `Build)
      | Key_press { key; mods = [] } when key_is 't' key ->
        Effect.of_deferred_thunk (fun () -> submit session `Test)
      | Key_press { key; mods = [] } when key_is 'c' key ->
        Effect.of_deferred_thunk (fun () -> cancel_selected session)
      | Key_press { key; mods = [] } when key_is 'j' key ->
        let count = List.length (project_jobs session) in
        session.selected <- Int.min (Int.max 0 (count - 1)) (session.selected + 1);
        Effect.Ignore
      | Key_press { key; mods = [] } when key_is 'k' key ->
        session.selected <- Int.max 0 (session.selected - 1);
        Effect.Ignore
      | Key_press { key; mods = [] } when key_is 'r' key ->
        Effect.of_deferred_thunk (fun () -> reconnect session)
      | _ -> Effect.Ignore)
  in
  ~view, ~handler
;;

let print_opened session =
  printf "Hardcaml Workbench\n";
  printf "Daemon: %s\n" (Http.Client.endpoint session.client);
  printf "Instance: %s\n" (V1.Daemon_instance_id.to_string session.hello.instance_id);
  List.iter (environment_lines session) ~f:print_endline;
  let jobs = project_jobs session in
  printf "Jobs: %d\n" (List.length jobs);
  List.iter jobs ~f:(fun job ->
    printf
      "Job %s: %s (%s)\n"
      (Job_id.to_string job.id)
      (Job.State.to_string job.state)
      (Job.Kind.to_string job.kind));
  printf "Hardcaml operations: unavailable (project driver integration is not active)\n"
;;

let print_log_record (record : V1.Read_log.Record.t) =
  let tag =
    match record.stream with
    | V1.Read_log.Stream.Stdout -> "stdout"
    | Stderr -> "stderr"
  in
  let lines = String.split_lines record.data in
  if List.is_empty lines
  then printf "[%s]\n%!" tag
  else List.iter lines ~f:(fun line -> printf "[%s] %s\n%!" tag line)
;;

let wait_for_job session initial_job =
  let rec loop job offset =
    let%bind logs =
      request session.diagnostics_file (fun () ->
        Http.Client.read_log
          session.client
          { instance_id = session.hello.instance_id
          ; job = job.Job.id
          ; offset
          ; max_records = V1.max_log_records
          ; max_bytes = V1.max_log_bytes
          })
    in
    match logs with
    | Error message -> return (Error message)
    | Ok logs ->
      List.iter logs.records ~f:print_log_record;
      let%bind snapshot =
        request session.diagnostics_file (fun () ->
          Http.Client.snapshot session.client { instance_id = session.hello.instance_id })
      in
      (match snapshot with
       | Error message -> return (Error message)
       | Ok snapshot ->
         let current =
           List.find snapshot.jobs ~f:(fun candidate -> Job_id.equal candidate.id job.id)
         in
         (match current with
          | None -> return (Error "submitted job disappeared from daemon snapshot")
          | Some current when Job.is_terminal current && logs.eof -> return (Ok current)
          | Some current ->
            let%bind () = Clock_ns.after (Time_ns.Span.of_ms 200.) in
            loop current logs.next_offset))
  in
  loop initial_job 0
;;

let run_plain_action session action ~wait =
  match session.opened with
  | None -> return (Or_error.error_string "--action requires --project-root")
  | Some opened ->
    let name, protocol_action =
      match action with
      | `Build -> "build", V1.Dune_action.Build
      | `Test -> "test", V1.Dune_action.Test
    in
    let key = submission_key name in
    let%bind submitted =
      request session.diagnostics_file (fun () ->
        Http.Client.submit_job
          session.client
          { instance_id = session.hello.instance_id
          ; project = opened.project.id
          ; action = protocol_action
          ; submission_key = key
          })
    in
    (match submitted with
     | Error message -> return (Or_error.error_string message)
     | Ok payload ->
       printf
         "Submitted %s job %s (submission-key=%s)\n%!"
         name
         (Job_id.to_string payload.job.id)
         key;
       if not wait
       then return (Ok ())
       else (
         let%map finished = wait_for_job session payload.job in
         match finished with
         | Error message -> Or_error.error_string message
         | Ok job ->
           printf
             "Job %s: %s\n%!"
             (Job_id.to_string job.id)
             (Job.State.to_string job.state);
           if Job.State.equal job.state Complete
           then Ok ()
           else
             Or_error.error_string
               (sprintf "job ended in state %s" (Job.State.to_string job.state))))
;;

let parse_environment value =
  match value with
  | "inherited" ->
    Ok (V1.Environment_selection.Inherit_daemon, "inherited (daemon environment)")
  | value ->
    (match String.chop_prefix value ~prefix:"opam:" with
     | Some switch when not (String.is_empty switch) ->
       Ok (V1.Environment_selection.Opam_switch switch, "opam switch " ^ switch)
     | _ -> Or_error.error_string "--environment must be inherited or opam:SWITCH")
;;

let parse_action = function
  | None -> Ok None
  | Some "build" -> Ok (Some `Build)
  | Some "test" -> Ok (Some `Test)
  | Some _ -> Or_error.error_string "--action must be build or test"
;;

let run ~endpoint ~project_root ~environment ~plain ~action ~wait ~diagnostics_file () =
  let diagnostics_file =
    Option.first_some diagnostics_file (Sys.getenv "HARDCAML_WORKBENCH_DIAGNOSTICS")
  in
  match parse_environment environment, parse_action action with
  | Error error, _ | _, Error error -> return (Error error)
  | Ok (environment_selection, environment_label), Ok action ->
    if Option.is_some action && not plain
    then return (Or_error.error_string "--action is available only with --plain")
    else if wait && Option.is_none action
    then return (Or_error.error_string "--wait requires --action")
    else if Option.is_some action && Option.is_none project_root
    then return (Or_error.error_string "--action requires --project-root")
    else (
      let%bind created =
        create_session
          ~endpoint
          ~project_root
          ~environment_selection
          ~environment_label
          ~diagnostics_file
      in
      match created with
      | Error message -> return (Or_error.error_string message)
      | Ok session ->
        if plain || not (Core_unix.isatty Core_unix.stdout)
        then (
          print_opened session;
          match action with
          | None -> return (Ok ())
          | Some action -> run_plain_action session action ~wait)
        else
          Monitor.try_with_or_error (fun () ->
            Bonsai_term.start_with_exit ~dispose:true ~mouse:No_mouse_events (tui session))
          >>| Or_error.join
          >>| Result.map_error ~f:(fun error ->
            append_diagnostic diagnostics_file ("terminal error: " ^ error_message error);
            error))
;;

let command =
  Command.async_or_error
    ~summary:"Connect to Hardcaml Workbench"
    (let%map_open.Command endpoint =
       flag "--connect" (optional string) ~doc:"URL attach without automatic startup"
     and project_root =
       flag "--project-root" (optional string) ~doc:"ROOT open a Dune project"
     and environment =
       flag
         "--environment"
         (optional_with_default "inherited" string)
         ~doc:"inherited|opam:SWITCH project command environment (default: inherited)"
     and plain = flag "--plain" no_arg ~doc:" print status without terminal control"
     and action =
       flag "--action" (optional string) ~doc:"build|test submit one action in plain mode"
     and wait = flag "--wait" no_arg ~doc:" wait for a plain-mode action and stream logs"
     and diagnostics_file =
       flag
         "--diagnostics-file"
         (optional string)
         ~doc:"FILE append dimensions and caught errors outside the active terminal"
     in
     run ~endpoint ~project_root ~environment ~plain ~action ~wait ~diagnostics_file)
;;

let () = Command_unix.run command
