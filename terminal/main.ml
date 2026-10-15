open! Core
open! Async
open Hardcaml_workbench_protocol
module Http = Hardcaml_workbench_native_http
module Baseline_fixture = Terminal_presentation.Baseline_fixture
module Presentation = Terminal_presentation.Presentation
module State = Terminal_presentation.State
module Host = Terminal_presentation.Workspace_host
module Host_view = Terminal_presentation.Host_view
module Appearance = Terminal_presentation.Appearance
module Plain_rpc = Terminal_presentation.Plain_rpc
module Launch_preferences = Terminal_presentation.Launch_preferences
module Asic_intents = Terminal_presentation.Asic_intents
module Fs0_fixture = Terminal_presentation.Fs0_fixture

let console_limit = 500
let minimum_width = 68
let minimum_height = 20
let take_end values count = List.rev values |> Fn.flip List.take count |> List.rev

type log_state =
  { mutable next_offset : int
  ; mutable records : V1.Read_log.Record.t list
  ; mutable fetch : Presentation.Log_fetch.t
  }

type artifact_view =
  { artifact : Artifact_id.t
  ; content : string
  ; truncated : bool
  }

type hierarchy_view =
  { hierarchy : Hierarchy.t
  ; nodes : Hierarchy.Node.t String.Table.t
  ; children : Hierarchy.Node.t list String.Table.t
  ; mutable selected_key : string
  ; mutable expanded : String.Set.t
  ; mutable scroll : int
  ; mutable pane_scroll : int
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
  ; mutable selected_target : Target_id.t option
  ; mutable selected_configuration : Configuration_id.t option
  ; mutable selected_artifact : Artifact_id.t option
  ; mutable artifact_view : artifact_view option
  ; mutable hierarchy_view : hierarchy_view option
  ; hierarchy_errors : string Artifact_id.Table.t
  ; logs : log_state Job_id.Table.t
  ; mutable status : string
  ; mutable polling : bool
  ; mutable reconnect_delay_ms : int
  ; mutable last_dimensions : Bonsai_term.Dimensions.t option
  ; mutable show_connection_details : bool
  ; mutable connection_details_scroll : int
  ; mutable host : Host.t
  ; mutable registry_busy : bool
  ; mutable asic : Asic.Snapshot.t option
  ; mutable asic_request_id : int
  ; mutable asic_applied_id : int
  ; mutable view_on_allocation : (string * Host.launch_target) option
  ; mutable remembered_selection : Asic.Selection.t option
  ; mutable preferences_loaded : bool
  ; mutable preference_saves : unit Deferred.t
  ; mutable asic_reads : Asic_intents.t
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
    let session =
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
      ; selected_target = None
      ; selected_configuration = None
      ; selected_artifact = None
      ; artifact_view = None
      ; hierarchy_view = None
      ; hierarchy_errors = Artifact_id.Table.create ()
      ; logs = Job_id.Table.create ()
      ; status = "connected"
      ; polling = false
      ; reconnect_delay_ms = 250
      ; last_dimensions = None
      ; show_connection_details = false
      ; connection_details_scroll = 0
      ; host = Host.empty
      ; registry_busy = false
      ; asic = None
      ; asic_request_id = 0
      ; asic_applied_id = 0
      ; view_on_allocation = None
      ; remembered_selection = None
      ; preferences_loaded = false
      ; preference_saves = Deferred.unit
      ; asic_reads = Asic_intents.empty
      }
    in
    session)
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

let current_project session =
  State.current_project ~opened:session.opened session.snapshot
;;

let project_artifacts session =
  match current_project session with
  | None -> []
  | Some project ->
    List.filter session.snapshot.artifacts ~f:(fun artifact ->
      Project_id.equal artifact.project project.id)
    |> List.sort ~compare:(fun a b ->
      Timestamp.compare b.metadata.provenance.created_at a.metadata.provenance.created_at)
;;

let reconcile_selection session =
  match current_project session with
  | None ->
    session.selected_target <- None;
    session.selected_configuration <- None;
    session.selected_artifact <- None;
    session.artifact_view <- None;
    session.hierarchy_view <- None
  | Some project ->
    let target, configuration =
      State.reconcile_selection
        project
        ~target:session.selected_target
        ~configuration:session.selected_configuration
    in
    session.selected_target <- target;
    session.selected_configuration <- configuration;
    let artifacts = project_artifacts session in
    let selected_artifact =
      Option.first_some
        (Option.bind session.selected_artifact ~f:(fun id ->
           List.find artifacts ~f:(fun artifact -> Artifact_id.equal artifact.id id)))
        (List.hd artifacts)
    in
    session.selected_artifact
    <- Option.map selected_artifact ~f:(fun artifact -> artifact.id);
    Option.iter session.artifact_view ~f:(fun view ->
      if not
           (Option.value_map session.selected_artifact ~default:false ~f:(fun id ->
              Artifact_id.equal id view.artifact))
      then session.artifact_view <- None);
    Option.iter session.hierarchy_view ~f:(fun view ->
      if not
           (List.exists artifacts ~f:(fun artifact ->
              Artifact_id.equal artifact.id view.hierarchy.artifact))
      then session.hierarchy_view <- None)
;;

let selected_target session =
  match current_project session, session.selected_target with
  | Some project, Some id ->
    List.find project.targets ~f:(fun target -> Target_id.equal target.id id)
  | _ -> None
;;

let selected_configuration session =
  match current_project session, session.selected_configuration with
  | Some project, Some id ->
    List.find project.configurations ~f:(fun configuration ->
      Configuration_id.equal configuration.id id)
  | _ -> None
;;

let selected_artifact session =
  Option.bind session.selected_artifact ~f:(fun id ->
    List.find (project_artifacts session) ~f:(fun artifact ->
      Artifact_id.equal artifact.id id))
;;

let selected_job session = List.nth (project_jobs session) session.selected

let preserve_selected_job session selected_job_id =
  let jobs = project_jobs session in
  session.selected
  <- State.preserve_job_selection
       jobs
       ~selected_job:selected_job_id
       ~fallback_index:session.selected
;;

let is_hierarchy_artifact (artifact : Artifact.t) =
  String.equal artifact.kind.namespace "hardcaml"
  && String.equal artifact.kind.name "elaboration-hierarchy"
  && Artifact.Role.equal artifact.kind.role Report
  && Option.equal
       String.equal
       artifact.kind.media
       (Some "application/x-hardcaml-workbench-hierarchy-sexp")
;;

let hierarchy_artifact_for_job session job =
  List.find_map job.Job.artifacts ~f:(fun id ->
    List.find session.snapshot.artifacts ~f:(fun artifact ->
      Artifact_id.equal artifact.id id && is_hierarchy_artifact artifact))
;;

let current_generation session =
  match
    current_project session, session.selected_target, session.selected_configuration
  with
  | Some project, Some target, Some configuration ->
    State.latest_generation
      session.snapshot.jobs
      ~project:project.id
      ~target
      ~configuration
  | _ -> None
;;

let log_state session job =
  Hashtbl.find_or_add session.logs job ~default:(fun () ->
    { next_offset = 0; records = []; fetch = Presentation.Log_fetch.Not_requested })
;;

let read_job_log session (job : Job.t option) =
  match job with
  | None -> return ()
  | Some job ->
    let state = log_state session job.id in
    (match state.fetch with
     | Presentation.Log_fetch.Received { eof = true } -> return ()
     | _ ->
       let requested_instance = session.hello.instance_id in
       state.fetch <- Presentation.Log_fetch.Fetching;
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
        | _
          when not
                 (V1.Daemon_instance_id.equal
                    requested_instance
                    session.hello.instance_id) -> ()
        | Error message -> state.fetch <- Presentation.Log_fetch.Error message
        | Ok payload ->
          let records =
            List.filter payload.records ~f:(fun record ->
              record.offset >= state.next_offset)
          in
          state.next_offset <- payload.next_offset;
          state.records <- take_end (state.records @ records) console_limit;
          state.fetch <- Presentation.Log_fetch.Received { eof = payload.eof }))
;;

let read_selected_log session = read_job_log session (selected_job session)

let updates_request diagnostics thunk =
  Monitor.try_with_or_error thunk
  >>| Or_error.join
  >>| function
  | Error error -> Error (`Transport (error_message error))
  | Ok (Error error) -> Error (`Protocol error)
  | Ok (Ok payload) -> Ok payload
;;

let snapshot_request session ~instance_id =
  request session.diagnostics_file (fun () ->
    Http.Client.snapshot session.client { instance_id })
;;

let preference_location session =
  let opened = Option.value_exn session.opened in
  let project_key =
    Sexp.to_string_mach
      (Sexp.List
         [ Atom (Project_root.to_absolute_path opened.project.root)
         ; V1.Environment_selection.sexp_of_t opened.environment.selection
         ])
  in
  let state_directory =
    match Sys.getenv "XDG_STATE_HOME", Sys.getenv "HOME" with
    | Some directory, _ when not (String.is_empty directory) -> directory
    | _, Some home -> Filename.concat home ".local/state"
    | _ -> failwith "No XDG_STATE_HOME or HOME for terminal preferences"
  in
  let state_directory = Filename.concat state_directory "hardcaml-workbench/terminal" in
  project_key, Launch_preferences.path ~state_directory ~project_key
;;

let load_preferences session =
  if session.preferences_loaded || Option.is_none session.opened
  then return ()
  else (
    session.preferences_loaded <- true;
    let%map result =
      In_thread.run (fun () ->
        Or_error.try_with (fun () ->
          let project_key, path = preference_location session in
          match Sys_unix.file_exists path with
          | `No -> None
          | `Unknown -> failwith ("Cannot inspect terminal preferences: " ^ path)
          | `Yes ->
            let content = In_channel.read_all path in
            if String.length content > 64 * 1024
            then failwith "Terminal preference size limit exceeded";
            Some (Launch_preferences.decode ~project_key (Sexp.of_string content))))
    in
    match result with
    | Ok selection -> session.remembered_selection <- selection
    | Error error ->
      append_diagnostic
        session.diagnostics_file
        ("preference load: " ^ Error.to_string_hum error))
;;

let save_preferences session selection =
  session.remembered_selection <- Some selection;
  let previous = session.preference_saves in
  let finished = Ivar.create () in
  session.preference_saves <- Ivar.read finished;
  Monitor.protect
    ~finally:(fun () ->
      Ivar.fill_exn finished ();
      Deferred.unit)
    (fun () ->
      let%bind () = previous in
      let%map result =
        In_thread.run (fun () ->
          Or_error.try_with (fun () ->
            let project_key, path = preference_location session in
            let directory = Filename.dirname path in
            Core_unix.mkdir_p directory ~perm:0o700;
            let temp = Filename_unix.temp_file ~in_dir:directory ".launch-" ".tmp" in
            Exn.protect
              ~finally:(fun () ->
                if Poly.equal (Sys_unix.file_exists temp) `Yes then Core_unix.unlink temp)
              ~f:(fun () ->
                Out_channel.write_all
                  temp
                  ~data:
                    (Sexp.to_string_hum
                       (Launch_preferences.sexp_of_t
                          (Launch_preferences.create ~project_key selection))
                     ^ "\n");
                Core_unix.rename ~src:temp ~dst:path)))
      in
      match result with
      | Ok () -> ()
      | Error error ->
        session.host
        <- { session.host with
             notice = "Could not save launch preferences: " ^ Error.to_string_hum error
           })
;;

let workspace_request session operation =
  match current_project session with
  | None -> return ()
  | Some project ->
    let instance_id = session.hello.instance_id in
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.workspace
          session.client
          { instance_id; project = project.id; operation })
    in
    if V1.Daemon_instance_id.equal instance_id session.hello.instance_id
       && Option.value_map (current_project session) ~default:false ~f:(fun p ->
         Project_id.equal p.id project.id)
    then (
      match response with
      | Error message ->
        session.host <- { session.host with notice = "Workspace: " ^ message }
      | Ok snapshot -> session.host <- Host.receive session.host snapshot)
;;

let mutate_workspace session mutation =
  match session.host.registry with
  | None -> return ()
  | Some snapshot ->
    if session.registry_busy
    then (
      session.host
      <- { session.host with notice = "Workspace update pending; retry deliberately" };
      return ())
    else (
      session.registry_busy <- true;
      Monitor.protect
        ~finally:(fun () ->
          session.registry_busy <- false;
          return ())
        (fun () ->
          let%bind () =
            workspace_request
              session
              (Mutate { expected_revision = snapshot.revision; mutation })
          in
          (* Refresh after a conflict, but never silently retry the captured mutation. *)
          let notice = session.host.notice in
          let%map () = workspace_request session Get in
          if not (String.is_empty notice)
          then session.host <- { session.host with notice }))
;;

let asic_request session operation =
  match current_project session with
  | None -> return ()
  | Some project ->
    let instance_id = session.hello.instance_id in
    session.asic_request_id <- session.asic_request_id + 1;
    let request_id = session.asic_request_id in
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.asic session.client { instance_id; project = project.id; operation })
    in
    let current =
      V1.Daemon_instance_id.equal instance_id session.hello.instance_id
      && Option.value_map (current_project session) ~default:false ~f:(fun p ->
        Project_id.equal p.id project.id)
    in
    (* A rejected/timed-out launch must release its pending view even when a newer Get
       snapshot has already arrived. Never retry a potentially accepted launch. *)
    if current
    then (
      match operation, response, session.view_on_allocation with
      | Asic.Operation.Run { key; _ }, Error message, Some (pending, _)
        when String.equal key pending ->
        session.view_on_allocation <- None;
        session.host
        <- { session.host with notice = "ASIC launch not confirmed: " ^ message }
      | _ -> ());
    if request_id >= session.asic_applied_id && current
    then (
      match response with
      | Error message -> session.host <- { session.host with notice = "ASIC: " ^ message }
      | Ok snapshot ->
        session.asic_applied_id <- request_id;
        session.asic <- Some snapshot)
;;

let add_default_tiles session (registry : Workspace.Snapshot.t) workspace =
  Deferred.List.iter
    (Host.missing_default_tiles registry workspace)
    ~how:`Sequential
    ~f:(fun mutation ->
      match mutation, session.host.registry with
      | Workspace.Mutation.Create_tile { workspace; kind; _ }, Some current ->
        if List.exists current.tiles ~f:(fun tile ->
             Workspace.Workspace_id.equal tile.workspace workspace
             && String.equal tile.kind kind)
        then return ()
        else mutate_workspace session mutation
      | _ -> return ())
;;

let initialize_host_layout session =
  match session.host.registry with
  | Some registry when registry.revision = 0 ->
    Deferred.List.iter registry.workspaces ~how:`Sequential ~f:(fun workspace ->
      let%bind () =
        match
          List.find registry.tiles ~f:(fun tile ->
            Workspace.Workspace_id.equal tile.workspace workspace.id
            && String.equal tile.kind "run-selector")
        with
        | None -> return ()
        | Some tile ->
          let width, height =
            if String.equal workspace.name "Timing" then 28, 6 else 32, 12
          in
          mutate_workspace
            session
            (Resize_tile { tile = tile.id; geometry = { x = 0; y = 0; width; height } })
      in
      add_default_tiles session registry workspace)
  | _ -> return ()
;;

let refresh_host session =
  let%bind () = load_preferences session in
  let%bind () = workspace_request session Get in
  let%bind () = initialize_host_layout session in
  let%bind () = asic_request session Get in
  let%bind () =
    match session.view_on_allocation, session.host.registry, session.asic with
    | Some (key, target), Some registry, Some asic ->
      (match Asic_intents.allocation ~key asic with
       | Allocated run ->
         session.view_on_allocation <- None;
         (match Host.selection_after_allocation registry target run with
          | Some mutation -> mutate_workspace session mutation
          | _ ->
            session.host
            <- { session.host with
                 notice = "Run allocated; launch-and-view skipped because context changed"
               };
            return ())
       | Allocation_failed error ->
         session.view_on_allocation <- None;
         session.host <- { session.host with notice = error };
         return ()
       | Awaiting -> return ())
    | _ -> return ()
  in
  (* One bounded read intent per distinct visible run, shared by all its tiles. *)
  let runs = Host.evidence_runs session.host in
  match session.asic with
  | None -> return ()
  | Some snapshot ->
    let state, intents =
      Asic_intents.plan session.asic_reads ~now:(Time_ns.now ()) snapshot ~visible:runs
    in
    session.asic_reads <- state;
    Deferred.List.iter intents ~how:`Sequential ~f:(asic_request session)
;;

let apply_updates session ~instance_id updates =
  if not (V1.Daemon_instance_id.equal instance_id session.hello.instance_id)
  then Ok `Stale
  else (
    let selected_job_id = Option.map (selected_job session) ~f:(fun job -> job.id) in
    State.apply_updates session.snapshot updates
    |> Result.map ~f:(fun snapshot ->
      session.snapshot <- snapshot;
      reconcile_selection session;
      preserve_selected_job session selected_job_id;
      `Applied))
;;

let resync session ~instance_id =
  let selected_job_id = Option.map (selected_job session) ~f:(fun job -> job.id) in
  let%map snapshot = snapshot_request session ~instance_id in
  match snapshot with
  | _ when not (V1.Daemon_instance_id.equal instance_id session.hello.instance_id) ->
    Ok ()
  | Error _ as error -> error
  | Ok snapshot ->
    session.snapshot <- snapshot;
    reconcile_selection session;
    preserve_selected_job session selected_job_id;
    Ok ()
;;

let poll_updates session ~timeout_ms =
  let instance_id = session.hello.instance_id in
  let request : V1.Updates.Request.t =
    { instance_id
    ; cursor = session.snapshot.cursor
    ; max_events = V1.max_update_events
    ; timeout_ms
    }
  in
  let%bind response =
    updates_request session.diagnostics_file (fun () ->
      Http.Client.updates session.client request)
  in
  match response with
  | Ok updates ->
    (match apply_updates session ~instance_id updates with
     | Ok result -> return (Ok result)
     | Error error ->
       let%map resynced = resync session ~instance_id in
       Result.map resynced ~f:(fun () -> `Resynced)
       |> Result.map_error ~f:(fun message ->
         sprintf "%s; snapshot resync failed: %s" (Error.to_string_hum error) message))
  | Error (`Protocol error) when V1.Error.Kind.equal error.kind Resync_required ->
    let%map resynced = resync session ~instance_id in
    Result.map resynced ~f:(fun () -> `Resynced)
  | Error (`Protocol error) when V1.Error.Kind.equal error.kind Instance_changed ->
    return (Error (protocol_error error))
  | Error (`Protocol error) -> return (Error (protocol_error error))
  | Error (`Transport message) -> return (Error message)
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
        let%bind updates = poll_updates session ~timeout_ms:200 in
        match updates with
        | Error message ->
          session.status <- "disconnected: " ^ message ^ "; reconnecting...";
          let%bind () =
            Clock.after (Time_float.Span.of_ms (Float.of_int session.reconnect_delay_ms))
          in
          reconnect session
        | Ok update ->
          session.status
          <- (match update with
              | `Resynced -> "connected; update cursor recovered from snapshot"
              | `Applied | `Stale -> "connected");
          let%bind () = refresh_host session in
          let%bind () = read_selected_log session in
          Host.tiles session.host
          |> List.filter ~f:(fun tile ->
            String.equal tile.kind "logs" || String.equal tile.kind "project-tests")
          |> List.filter_map ~f:(fun tile -> (Host.local session.host tile.id).cursor)
          |> List.dedup_and_sort ~compare:String.compare
          |> Deferred.List.iter ~how:`Sequential ~f:(fun id ->
            read_job_log
              session
              (List.find (project_jobs session) ~f:(fun job ->
                 String.equal (Job_id.to_string job.id) id)))))

and reconnect session =
  let selected_job_id = Option.map (selected_job session) ~f:(fun job -> job.id) in
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
    session.host
    <- { session.host with
         registry = None
       ; palette = None
       ; prefix = 0
       ; editing_filter = false
       };
    session.asic <- None;
    if instance_changed
    then (
      session.view_on_allocation <- None;
      session.asic_reads <- Asic_intents.empty);
    if instance_changed
    then (
      session.hierarchy_view <- None;
      Hashtbl.clear session.hierarchy_errors);
    reconcile_selection session;
    if instance_changed
    then session.selected <- 0
    else preserve_selected_job session selected_job_id;
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
       session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
       session.selected <- 0;
       session.status
       <- sprintf "submitted %s as %s" action_name (Job_id.to_string payload.job.id))
;;

let refresh_integration session =
  match current_project session with
  | None ->
    session.status <- "integration refresh requires --project-root";
    return ()
  | Some project ->
    session.status <- "requesting integration refresh...";
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.refresh_integration
          session.client
          { instance_id = session.hello.instance_id; project = project.id })
    in
    (match response with
     | Error message -> session.status <- "integration refresh failed: " ^ message
     | Ok payload ->
       session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
       session.selected <- 0;
       session.status
       <- "integration refresh queued as " ^ Job_id.to_string payload.job.id)
;;

let next_after values current ~equal =
  match values with
  | [] -> None
  | first :: _ ->
    (match current with
     | None -> Some first
     | Some current ->
       (match List.findi values ~f:(fun _ value -> equal current value) with
        | None -> Some first
        | Some (index, _) ->
          Some (List.nth_exn values ((index + 1) mod List.length values))))
;;

let cycle_target session =
  match current_project session with
  | None -> session.status <- "no project target is available"
  | Some project ->
    let current = selected_target session in
    let next = next_after project.targets current ~equal:Target.equal in
    session.selected_target <- Option.map next ~f:(fun target -> target.id);
    session.selected_configuration <- None;
    reconcile_selection session;
    session.status
    <- Option.value_map next ~default:"no project target is available" ~f:(fun target ->
         "selected target " ^ target.name)
;;

let cycle_configuration session =
  match current_project session, selected_target session with
  | Some project, Some target ->
    let configurations =
      List.filter project.configurations ~f:(fun configuration ->
        Target_id.equal configuration.target target.id)
    in
    let current = selected_configuration session in
    let next = next_after configurations current ~equal:Configuration.equal in
    session.selected_configuration
    <- Option.map next ~f:(fun configuration -> configuration.id);
    session.status
    <- Option.value_map
         next
         ~default:"selected target has no configuration"
         ~f:(fun config -> "selected configuration " ^ config.name)
  | None, _ | _, None -> session.status <- "no target is selected"
;;

let cycle_artifact session =
  let artifacts = project_artifacts session in
  let current = selected_artifact session in
  let next = next_after artifacts current ~equal:Artifact.equal in
  session.selected_artifact <- Option.map next ~f:(fun artifact -> artifact.id);
  session.artifact_view <- None;
  session.status
  <- Option.value_map
       next
       ~default:"no generated artifact is available"
       ~f:(fun artifact -> "selected artifact " ^ artifact.metadata.display_name)
;;

let generate_rtl session =
  match
    current_project session, selected_target session, selected_configuration session
  with
  | Some project, Some target, Some configuration ->
    let key = submission_key "generate-rtl" in
    session.status
    <- sprintf "generating RTL for %s / %s..." target.name configuration.name;
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.generate_rtl
          session.client
          { instance_id = session.hello.instance_id
          ; project = project.id
          ; target = target.id
          ; configuration = configuration.id
          ; submission_key = key
          })
    in
    (match response with
     | Error message -> session.status <- "RTL generation failed: " ^ message
     | Ok payload ->
       session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
       session.selected <- 0;
       session.status
       <- sprintf
            "submitted RTL for %s / %s as %s"
            target.name
            configuration.name
            (Job_id.to_string payload.job.id))
  | None, _, _ ->
    session.status <- "RTL generation requires an open project";
    return ()
  | _, None, _ ->
    session.status <- "RTL generation requires a discovered target";
    return ()
  | _, _, None ->
    session.status <- "RTL generation requires a configuration for the selected target";
    return ()
;;

let inspect_artifact session =
  match selected_artifact session with
  | None ->
    session.status <- "no artifact is selected";
    return ()
  | Some artifact ->
    (match session.artifact_view with
     | Some view when Artifact_id.equal view.artifact artifact.id ->
       session.artifact_view <- None;
       session.status <- "closed artifact view";
       return ()
     | _ ->
       let limit = 1024 * 1024 in
       let requested_instance = session.hello.instance_id in
       let requested_client = session.client in
       let rec read offset parts bytes =
         if bytes >= limit
         then return (Ok (String.concat (List.rev parts), true))
         else (
           let max_bytes = Int.min V1.max_artifact_bytes (limit - bytes) in
           let%bind page =
             request session.diagnostics_file (fun () ->
               Http.Client.read_artifact
                 requested_client
                 { instance_id = requested_instance
                 ; artifact = artifact.id
                 ; offset
                 ; max_bytes
                 })
           in
           match page with
           | Error message -> return (Error message)
           | Ok page when page.eof ->
             return (Ok (String.concat (List.rev (page.data :: parts)), false))
           | Ok page ->
             read page.next_offset (page.data :: parts) (bytes + String.length page.data))
       in
       session.status <- "fetching artifact " ^ artifact.metadata.display_name ^ "...";
       let%map result = read 0 [] 0 in
       if V1.Daemon_instance_id.equal requested_instance session.hello.instance_id
          && Option.value_map session.selected_artifact ~default:false ~f:(fun id ->
            Artifact_id.equal id artifact.id)
       then (
         match result with
         | Error message -> session.status <- "artifact retrieval failed: " ^ message
         | Ok (content, truncated) ->
           session.artifact_view <- Some { artifact = artifact.id; content; truncated };
           session.status
           <- (if truncated then "artifact view truncated at 1 MiB" else "artifact loaded")))
;;

let hierarchy_candidate session =
  match selected_job session with
  | Some job when State.is_generation_job job -> Some job
  | Some _ | None -> current_generation session
;;

let index_hierarchy (hierarchy : Hierarchy.t) =
  let nodes = Hashtbl.create (module String) in
  let children = Hashtbl.create (module String) in
  List.iter hierarchy.nodes ~f:(fun node ->
    Hashtbl.set nodes ~key:node.key ~data:node;
    Option.iter node.parent ~f:(fun parent ->
      Hashtbl.add_multi children ~key:parent ~data:node));
  Hashtbl.to_alist children
  |> List.iter ~f:(fun (parent, entries) ->
    Hashtbl.set
      children
      ~key:parent
      ~data:
        (List.sort entries ~compare:(fun a b ->
           Option.compare String.compare a.instance_name b.instance_name)));
  nodes, children
;;

let hierarchy_children children parent =
  Hashtbl.find children parent |> Option.value ~default:[]
;;

let inspect_hierarchy session =
  match hierarchy_candidate session with
  | None ->
    session.status <- "no RTL generation result is available for hierarchy inspection";
    return ()
  | Some job when not (Job.State.equal job.state Complete) ->
    session.status
    <- (match job.state with
        | Queued | Starting | Running -> "hierarchy pending in " ^ Job_id.to_string job.id
        | Failed ->
          "hierarchy unavailable because generation failed in " ^ Job_id.to_string job.id
        | Cancelled ->
          "hierarchy unavailable because generation was cancelled in "
          ^ Job_id.to_string job.id
        | Complete -> assert false);
    return ()
  | Some job ->
    (match hierarchy_artifact_for_job session job with
     | None ->
       session.status
       <- "structured hierarchy unsupported for generation " ^ Job_id.to_string job.id;
       return ()
     | Some artifact ->
       (match session.hierarchy_view with
        | Some view when Artifact_id.equal view.hierarchy.artifact artifact.id ->
          session.hierarchy_view <- None;
          session.status <- "closed hierarchy view";
          return ()
        | _ ->
          let requested_instance = session.hello.instance_id in
          session.status <- "fetching hierarchy for " ^ Job_id.to_string job.id ^ "...";
          let%map response =
            request session.diagnostics_file (fun () ->
              Http.Client.read_hierarchy
                session.client
                { instance_id = requested_instance; artifact = artifact.id })
          in
          if not
               (V1.Daemon_instance_id.equal requested_instance session.hello.instance_id)
          then ()
          else (
            match response with
            | Error message ->
              Hashtbl.set session.hierarchy_errors ~key:artifact.id ~data:message;
              session.status <- "hierarchy retrieval failed: " ^ message
            | Ok payload ->
              let hierarchy = payload.hierarchy in
              if not
                   (Artifact_id.equal hierarchy.artifact artifact.id
                    && Job_id.equal hierarchy.generating_job job.id)
              then
                session.status <- "hierarchy response identity did not match the request"
              else (
                Hashtbl.remove session.hierarchy_errors artifact.id;
                let nodes, children = index_hierarchy hierarchy in
                session.hierarchy_view
                <- Some
                     { hierarchy
                     ; nodes
                     ; children
                     ; selected_key = hierarchy.root
                     ; expanded = String.Set.singleton hierarchy.root
                     ; scroll = 0
                     ; pane_scroll = 0
                     };
                session.status <- "hierarchy loaded"))))
;;

let visible_hierarchy_nodes view =
  let rec visit depth key =
    match Hashtbl.find view.nodes key with
    | None -> []
    | Some node ->
      let children =
        if Set.mem view.expanded key
        then
          hierarchy_children view.children key
          |> List.concat_map ~f:(fun child -> visit (depth + 1) child.key)
        else []
      in
      (depth, node) :: children
  in
  visit 0 view.hierarchy.root
;;

let move_hierarchy_selection session delta =
  Option.iter session.hierarchy_view ~f:(fun view ->
    let nodes = visible_hierarchy_nodes view in
    let current =
      List.findi nodes ~f:(fun _ (_, node) -> String.equal node.key view.selected_key)
      |> Option.value_map ~default:0 ~f:fst
    in
    let next = Int.max 0 (Int.min (List.length nodes - 1) (current + delta)) in
    Option.iter (List.nth nodes next) ~f:(fun (_, node) ->
      view.selected_key <- node.key;
      view.pane_scroll <- 0))
;;

let toggle_hierarchy_expansion session =
  Option.iter session.hierarchy_view ~f:(fun view ->
    if not (List.is_empty (hierarchy_children view.children view.selected_key))
    then
      view.expanded
      <- (if Set.mem view.expanded view.selected_key
          then Set.remove view.expanded view.selected_key
          else Set.add view.expanded view.selected_key))
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
       session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
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

let project_lines session ~width =
  match session.opened, current_project session with
  | None, _ ->
    [ "Project: none"
    ; "Open one with --project-root ROOT"
    ; "Generic Dune workspace: unavailable"
    ]
  | Some opened, Some project ->
    let contexts =
      match opened.workspace.contexts with
      | [] -> "none reported"
      | contexts -> String.concat contexts ~sep:", "
    in
    let root_label = "Root: " in
    [ "Project: " ^ project.name
    ; root_label
      ^ Presentation.middle_truncate
          ~width:(width - String.length root_label)
          (Project_root.to_absolute_path opened.project.root)
    ; sprintf
        "Environment: %s (Dune %s)"
        session.environment_label
        opened.environment.dune_version
    ; "Contexts: " ^ contexts
    ]
  | Some _, None -> [ "Project state unavailable; reconnect to resync" ]
;;

let integration_lines session =
  match current_project session with
  | None -> [ "Integration: unavailable" ]
  | Some project ->
    let component = function
      | Project_integration.Component_status.Absent -> "absent"
      | Available { version = None } -> "available"
      | Available { version = Some version } -> sprintf "available v%d" version
      | Unusable { reason } -> "unusable: " ^ reason
    in
    let discovery =
      project_jobs session
      |> List.find ~f:(fun job ->
        String.equal job.Job.kind.namespace "project-driver"
        && String.equal job.kind.name "describe")
      |> Option.value_map ~default:"not requested" ~f:(fun job ->
        Job.State.to_string job.state ^ " (" ^ Job_id.to_string job.id ^ ")")
    in
    let targets =
      if List.is_empty project.targets
      then [ "  Targets: none" ]
      else
        List.map project.targets ~f:(fun target ->
          sprintf
            "%s Target: %s (top %s) [%s]"
            (if Option.value_map session.selected_target ~default:false ~f:(fun id ->
                  Target_id.equal id target.id)
             then ">"
             else " ")
            target.name
            target.top
            (Target_id.to_string target.id))
    in
    let configurations =
      if List.is_empty project.configurations
      then [ "  Configurations: none" ]
      else
        List.map project.configurations ~f:(fun config ->
          sprintf
            "%s Configuration: %s [%s]"
            (if Option.value_map
                  session.selected_configuration
                  ~default:false
                  ~f:(fun id -> Configuration_id.equal id config.id)
             then ">"
             else " ")
            config.name
            (Configuration_id.to_string config.id))
    in
    [ sprintf
        "Integration: %s  manifest=%s  driver=%s"
        (Project_integration.Level.to_string project.integration.level)
        (component project.integration.manifest)
        (component project.integration.driver)
    ; "Discovery: " ^ discovery
    ]
    @ targets
    @ configurations
;;

let hierarchy_status_lines session =
  match current_generation session with
  | None -> [ "Hardware hierarchy: unavailable; generate RTL for this selection" ]
  | Some job ->
    (match job.state with
     | Queued | Starting | Running ->
       [ sprintf
           "Hardware hierarchy: pending (%s, %s)"
           (Job_id.to_string job.id)
           (Job.State.to_string job.state)
       ]
     | Failed ->
       [ "Hardware hierarchy: latest generation failed (" ^ Job_id.to_string job.id ^ ")"
       ]
     | Cancelled ->
       [ "Hardware hierarchy: latest generation was cancelled ("
         ^ Job_id.to_string job.id
         ^ ")"
       ]
     | Complete ->
       (match hierarchy_artifact_for_job session job with
        | None -> [ "Hardware hierarchy: unsupported for this completed result" ]
        | Some artifact ->
          (match Hashtbl.find session.hierarchy_errors artifact.id with
           | Some message -> [ "Hardware hierarchy: unavailable: " ^ message ]
           | None ->
             [ "Hardware hierarchy output from "
               ^ Job_id.to_string job.id
               ^ " (h inspect)"
             ])))
;;

let hierarchy_view_lines session view ~height =
  let hierarchy = view.hierarchy in
  let current =
    State.hierarchy_is_current
      hierarchy
      ~latest:(current_generation session)
      ~target:session.selected_target
      ~configuration:session.selected_configuration
  in
  let project = current_project session in
  let target =
    Option.bind project ~f:(fun project ->
      List.find project.targets ~f:(fun target ->
        Target_id.equal target.id hierarchy.target))
    |> Option.value_map ~default:(Target_id.to_string hierarchy.target) ~f:(fun target ->
      target.name)
  in
  let configuration =
    Option.bind project ~f:(fun project ->
      List.find project.configurations ~f:(fun configuration ->
        Configuration_id.equal configuration.id hierarchy.configuration))
    |> Option.value_map
         ~default:(Configuration_id.to_string hierarchy.configuration)
         ~f:(fun configuration -> configuration.name)
  in
  let visible = visible_hierarchy_nodes view in
  let selected_index =
    List.findi visible ~f:(fun _ (_, node) -> String.equal node.key view.selected_key)
    |> Option.value_map ~default:0 ~f:fst
  in
  let tree_height = Int.max 1 (height - 13) in
  if selected_index < view.scroll
  then view.scroll <- selected_index
  else if selected_index >= view.scroll + tree_height
  then view.scroll <- selected_index - tree_height + 1;
  let tree =
    visible
    |> Fn.flip List.drop view.scroll
    |> Fn.flip List.take tree_height
    |> List.map ~f:(fun (depth, node) ->
      let children = hierarchy_children view.children node.key in
      let marker =
        if List.is_empty children
        then " "
        else if Set.mem view.expanded node.key
        then "-"
        else "+"
      in
      let name = Option.value node.instance_name ~default:"<root>" in
      sprintf
        "%s%s%s %s : %s"
        (if String.equal node.key view.selected_key then ">" else " ")
        (String.make (depth * 2) ' ')
        marker
        name
        node.circuit_name)
  in
  let inspector =
    match Hashtbl.find view.nodes view.selected_key with
    | None -> [ "Node: unavailable" ]
    | Some node ->
      let ports ports =
        match ports with
        | [] -> "none"
        | ports ->
          List.map ports ~f:(fun port ->
            sprintf "%s[%d]" port.Hierarchy.Port.name port.width)
          |> String.concat ~sep:", "
      in
      let metadata =
        match node.metadata with
        | [] -> "none"
        | metadata ->
          List.map metadata ~f:(fun item -> item.name ^ "=" ^ item.value)
          |> String.concat ~sep:", "
      in
      [ "Node instance: " ^ Option.value node.instance_name ~default:"<root>"
      ; "Circuit: " ^ node.circuit_name
      ; "Key: " ^ node.key
      ; "Inputs: " ^ ports node.input_ports
      ; "Outputs: " ^ ports node.output_ports
      ; "Metadata: " ^ metadata
      ; "Signals/source: unavailable in structural hierarchy"
      ]
  in
  let lines =
    [ sprintf "HARDWARE HIERARCHY [%s]" (if current then "current" else "historical")
    ; sprintf "Result: job %s" (Job_id.to_string hierarchy.generating_job)
    ; sprintf "Target: %s" target
    ; sprintf "Configuration: %s" configuration
    ; sprintf "Tree [%d/%d]" view.scroll (Int.max 0 (List.length visible - tree_height))
    ]
    @ tree
    @ inspector
  in
  view.pane_scroll <- Int.min view.pane_scroll (Int.max 0 (List.length lines - height));
  List.drop lines view.pane_scroll
;;

let artifact_lines session =
  let artifacts = project_artifacts session in
  match current_project session, artifacts with
  | _, [] -> [ "Artifacts: none" ]
  | None, _ -> [ "Artifacts: unavailable" ]
  | Some project, artifacts ->
    "ARTIFACTS"
    :: List.map artifacts ~f:(fun artifact ->
      let target =
        Option.bind artifact.target ~f:(fun id ->
          List.find project.targets ~f:(fun target -> Target_id.equal target.id id))
        |> Option.value_map ~default:"no target" ~f:(fun target -> target.name)
      in
      let configuration =
        Option.bind artifact.configuration ~f:(fun id ->
          List.find project.configurations ~f:(fun config ->
            Configuration_id.equal config.id id))
        |> Option.value_map ~default:"no configuration" ~f:(fun config -> config.name)
      in
      sprintf
        "%s %s (%s) | %s / %s | job %s | [%s]"
        (if Option.value_map session.selected_artifact ~default:false ~f:(fun id ->
              Artifact_id.equal id artifact.id)
         then ">"
         else " ")
        artifact.metadata.display_name
        (Artifact.Kind.to_string artifact.kind)
        target
        configuration
        (Job_id.to_string artifact.generating_job)
        (Artifact_id.to_string artifact.id))
;;

let connection_detail_lines session ~width =
  let field label value = label :: Presentation.wrap_value ~width ~indent:"  " value in
  let root value = "Root:" :: Presentation.wrap_path ~width ~indent:"  " value in
  field "Endpoint:" (Http.Client.endpoint session.client)
  @ field "Daemon instance:" (V1.Daemon_instance_id.to_string session.hello.instance_id)
  @ field "Protocol:" (sprintf "v%d" V1.version)
  @ field "Connection:" session.status
  @
  match session.opened with
  | None ->
    field "Project:" "none" @ field "Requested environment:" session.environment_label
  | Some opened ->
    let project = Option.value (current_project session) ~default:opened.project in
    let component = function
      | Project_integration.Component_status.Absent -> "absent"
      | Available { version = None } -> "available"
      | Available { version = Some version } -> sprintf "available v%d" version
      | Unusable { reason } -> "unusable: " ^ reason
    in
    field "Project:" project.name
    @ root (Project_root.to_absolute_path opened.project.root)
    @ field "Requested environment:" session.environment_label
    @ field "Resolved environment:" opened.environment.provenance
    @ field "Dune version:" opened.environment.dune_version
    @ field "Manifest integration:" (component project.integration.manifest)
    @ field "Driver integration:" (component project.integration.driver)
;;

let render_legacy session ({ Bonsai_term.Dimensions.width; height } as dimensions) =
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
        [ sprintf
            "Hardcaml Workbench | %s | %s"
            session.status
            (Http.Client.endpoint session.client)
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
          [ ""; "SELECTED JOB"; "  " ^ Job_id.to_string job.id ]
          @ List.map (Presentation.job_outcome_lines job) ~f:(fun line -> "  " ^ line)
      in
      let controls =
        if session.show_connection_details
        then
          "d project | [/] details | b/t jobs | n/m select | g RTL | a/v artifact | h \
           hierarchy | i refresh | j/k job | c cancel | r reconnect | q exit"
        else
          "b/t jobs | n/m select | g RTL | a/v artifact | h hierarchy | u/o node | e \
           expand | [/] pane | i refresh | j/k job | c cancel | d details | r reconnect \
           | q exit"
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
        let lines =
          if session.show_connection_details
          then (
            let lines = connection_detail_lines session ~width:left_width in
            let visible_lines = Int.max 1 (top_height - 1) in
            let maximum_scroll = Int.max 0 (List.length lines - visible_lines) in
            session.connection_details_scroll
            <- Int.min maximum_scroll session.connection_details_scroll;
            [ sprintf
                "CONNECTION DETAILS [%d/%d]"
                session.connection_details_scroll
                maximum_scroll
            ]
            @ (lines
               |> Fn.flip List.drop session.connection_details_scroll
               |> Fn.flip List.take visible_lines))
          else (
            match session.hierarchy_view with
            | Some view -> hierarchy_view_lines session view ~height:top_height
            | None ->
              [ "PROJECT / GENERIC DUNE WORKSPACE" ]
              @ project_lines session ~width:left_width
              @ [ ""; "WORKBENCH INTEGRATION" ]
              @ integration_lines session
              @ [ "" ]
              @ hierarchy_status_lines session
              @ [ "" ]
              @ artifact_lines session
              @ [ ""; "DUNE ITEMS" ]
              @ workspace_rows)
        in
        pane ~width:left_width ~height:top_height lines
      in
      let jobs_pane =
        pane
          ~width:right_width
          ~height:top_height
          ([ "JOBS" ] @ detail @ [ "" ] @ job_rows)
      in
      let upper =
        View.hcat
          [ project_pane
          ; View.rectangle ~fill:'|' ~width:1 ~height:top_height ()
          ; jobs_pane
          ]
      in
      let console_title, console =
        match session.artifact_view with
        | Some view ->
          let label =
            selected_artifact session
            |> Option.value_map
                 ~default:(Artifact_id.to_string view.artifact)
                 ~f:(fun artifact -> artifact.metadata.display_name)
          in
          ( "RTL ARTIFACT: " ^ label
          , (String.split_lines view.content
             @ if view.truncated then [ "[artifact view truncated at 1 MiB]" ] else [])
            |> Fn.flip List.take console_height )
        | None ->
          ( "LIVE STDOUT / STDERR"
          , (match selected_job session with
             | None -> [ "  (select a job to read logs)" ]
             | Some job ->
               let state = log_state session job.id in
               let records =
                 List.concat_map state.records ~f:(fun record ->
                   let tag =
                     match record.stream with
                     | V1.Read_log.Stream.Stdout -> "[stdout] "
                     | Stderr -> "[stderr] "
                   in
                   String.split_lines record.data |> List.map ~f:(fun line -> tag ^ line))
               in
               (match state.fetch with
                | Presentation.Log_fetch.Error message when not (List.is_empty records) ->
                  records @ [ "[log retrieval failed] " ^ message ]
                | _ when not (List.is_empty records) -> records
                | fetch ->
                  Presentation.empty_log_notice ~job_state:job.state ~fetch
                  |> Option.to_list
                  |> List.map ~f:(fun line -> "  " ^ line))
               |> Fn.flip take_end console_height) )
      in
      View.vcat
        [ View.vcat (List.map header ~f:(fun line -> View.text (fit width line)))
        ; upper
        ; View.text (String.make width '-')
        ; View.text console_title
        ; pane ~width ~height:console_height console
        ; View.text (fit width controls)
        ])
  in
  View.zcat [ content; background ]
;;

let host_data session : Host_view.data =
  let runs =
    Option.value_map session.asic ~default:[] ~f:(fun asic ->
      List.map asic.runs ~f:(fun run -> run.run, run.status))
  in
  let log_lines id =
    let state = log_state session id in
    let rows =
      List.concat_map state.records ~f:(fun record ->
        let tag =
          match record.stream with
          | V1.Read_log.Stream.Stdout -> "[stdout] "
          | Stderr -> "[stderr] "
        in
        String.split_lines record.data |> List.map ~f:(fun line -> tag ^ line))
    in
    if not (List.is_empty rows)
    then (
      match state.fetch with
      | Presentation.Log_fetch.Error error -> rows @ [ "[log retrieval failed] " ^ error ]
      | _ -> rows)
    else (
      let job_state =
        List.find (project_jobs session) ~f:(fun job -> Job_id.equal job.id id)
        |> Option.value_map ~default:Job.State.Queued ~f:(fun job -> job.state)
      in
      Presentation.empty_log_notice ~job_state ~fetch:state.fetch |> Option.to_list)
  in
  let run_lines = Host_view.run_lines session.asic in
  let asic_lines =
    match session.asic with
    | None -> [ "ASIC provider not loaded — palette: Discover ASIC" ]
    | Some asic ->
      [ (if asic.configured
         then "Project-owned ASIC flows (Space c c: discover / describe / plan / launch)"
         else "No ASIC provider configured for this project")
      ]
      @ List.map asic.operations ~f:(fun op ->
        sprintf
          "%s: %s %s%s"
          op.kind
          op.state
          (Option.value_map
             op.run
             ~default:
               (if String.equal op.kind "run"
                then
                  if String.equal op.state "executing" || String.equal op.state "queued"
                  then "(awaiting allocation — no run ID yet)"
                  else "(no allocated run reference)"
                else "(project/read operation)")
             ~f:Host_view.run_label)
          (Option.value_map op.error ~default:"" ~f:(fun e -> " — " ^ e)))
      @ Option.value_map asic.preview ~default:[] ~f:(fun p ->
        [ "PREVIEW " ^ p.plan_identity
        ; "Selection: " ^ Sexp.to_string_hum (Asic.Selection.sexp_of_t p.selection)
        ]
        @ String.split_lines p.plan_json)
      @ Option.value_map asic.description_json ~default:[] ~f:(fun json ->
        "FLOW CAPABILITIES" :: String.split_lines json)
      @ Option.to_list asic.cache_error
  in
  { project = current_project session
  ; jobs = project_jobs session
  ; runs
  ; log_lines
  ; run_lines
  ; status = session.status
  ; environment = session.environment_label
  ; asic_lines
  }
;;

let render session dimensions =
  match session.host.registry with
  | None
    when Option.is_some session.opened
         && List.mem session.hello.capabilities "workspace" ~equal:String.equal ->
    Host_view.render session.host (host_data session) dimensions
  | None -> render_legacy session dimensions
  | Some _
    when Option.is_some session.hierarchy_view
         || Option.is_some session.artifact_view
         || session.show_connection_details -> render_legacy session dimensions
  | Some _ -> Host_view.render session.host (host_data session) dimensions
;;

(* Baseline capture.

   This is a development hook, not a second UI. It builds a [session] directly from a
   deterministic fixture and calls the same [render] the interactive client calls, then
   serialises the resulting [View.t] with Notty. Nothing above this point changes, so the
   captures show the production layout rather than a reimplementation of it. *)

let session_of_baseline_fixture (fixture : Baseline_fixture.t) =
  let session =
    { requested_endpoint = Some fixture.endpoint
    ; project_root = Some (Project_root.to_absolute_path fixture.opened.project.root)
    ; environment_selection = fixture.opened.environment.selection
    ; environment_label = fixture.environment_label
    ; diagnostics_file = None
    ; client = Http.Client.create fixture.endpoint
    ; hello = fixture.hello
    ; opened = Some fixture.opened
    ; snapshot = fixture.snapshot
    ; selected = 0
    ; selected_target = fixture.selected_target
    ; selected_configuration = fixture.selected_configuration
    ; selected_artifact = fixture.selected_artifact
    ; artifact_view = None
    ; hierarchy_view = None
    ; hierarchy_errors = Artifact_id.Table.create ()
    ; logs = Job_id.Table.create ()
    ; status = fixture.status
    ; polling = false
    ; reconnect_delay_ms = 250
    ; last_dimensions = None
    ; show_connection_details = fixture.show_connection_details
    ; connection_details_scroll = 0
    ; host = Host.empty
    ; registry_busy = false
    ; asic = None
    ; asic_request_id = 0
    ; asic_applied_id = 0
    ; view_on_allocation = None
    ; remembered_selection = None
    ; preferences_loaded = true
    ; preference_saves = Deferred.unit
    ; asic_reads = Asic_intents.empty
    }
  in
  reconcile_selection session;
  preserve_selected_job session fixture.selected_job;
  List.iter fixture.logs ~f:(fun { job; records; fetch } ->
    let state = log_state session job in
    state.records <- records;
    state.next_offset
    <- List.fold records ~init:0 ~f:(fun offset record ->
         Int.max offset (record.offset + 1));
    state.fetch <- fetch);
  Option.iter fixture.artifact_view ~f:(fun { artifact; content; truncated } ->
    session.artifact_view <- Some { artifact; content; truncated });
  Option.iter fixture.hierarchy ~f:(fun (hierarchy, state) ->
    let nodes, children = index_hierarchy hierarchy in
    session.hierarchy_view
    <- Some
         { hierarchy
         ; nodes
         ; children
         ; selected_key = state.selected_key
         ; expanded = String.Set.of_list state.expanded
         ; scroll = 0
         ; pane_scroll = 0
         });
  session
;;

let capture_dimensions =
  [ { Bonsai_term.Dimensions.width = 80; height = 24 }
  ; { Bonsai_term.Dimensions.width = 120; height = 40 }
  ]
;;

let render_to_string session dimensions ~cap =
  let { Bonsai_term.Dimensions.width; height } = dimensions in
  let buffer = Buffer.create (width * height * 2) in
  Notty.Render.to_buffer
    buffer
    cap
    (0, 0)
    (width, height)
    (Bonsai_term.View.Private.notty_image (render session dimensions));
  Buffer.contents buffer
;;

let capture_baseline_frames ~directory =
  Core_unix.mkdir_p directory;
  let written =
    List.concat_map Baseline_fixture.all ~f:(fun fixture ->
      List.concat_map capture_dimensions ~f:(fun dimensions ->
        let { Bonsai_term.Dimensions.width; height } = dimensions in
        let stem = sprintf "%s.%dx%d" fixture.name width height in
        (* A fresh session per capture: [render] reconciles scroll offsets in place, so a
           reused session would carry the previous size's state into the next capture. *)
        [ ( stem ^ ".txt"
          , render_to_string
              (session_of_baseline_fixture fixture)
              dimensions
              ~cap:Notty.Cap.dumb
            ^ "\n" )
        ; ( stem ^ ".ansi"
          , render_to_string
              (session_of_baseline_fixture fixture)
              dimensions
              ~cap:Notty.Cap.ansi )
        ]))
  in
  List.iter written ~f:(fun (name, contents) ->
    Out_channel.write_all (Filename.concat directory name) ~data:contents);
  List.iter Baseline_fixture.all ~f:(fun fixture ->
    printf "%s: %s\n" fixture.name fixture.summary);
  printf "wrote %d files to %s\n" (List.length written) directory
;;

let key_is char = function
  | Bonsai_term.Event.Key.ASCII value -> Char.equal char value
  | Uchar value -> Uchar.equal value (Uchar.of_char char)
  | _ -> false
;;

let host_catalog session =
  Host.catalog
    session.host
    ~project:(current_project session)
    ~jobs:(project_jobs session)
  @ Option.value_map session.remembered_selection ~default:[] ~f:(fun selection ->
    let available =
      Option.value_map session.asic ~default:false ~f:(fun asic ->
        Launch_preferences.available selection asic.flows)
    in
    [ Host.command
        ?unavailable:
          (if available
           then None
           else
             Some
               "Remembered flow/profile is not currently discovered; discover it \
                explicitly")
        "asic.plan-remembered"
        (sprintf
           "Plan remembered inputs: %s / %s → %s"
           selection.flow
           selection.profile
           selection.endpoint)
        "run synth last used"
        (Asic (Plan selection))
    ])
  @ Option.value_map session.asic ~default:[] ~f:(fun asic ->
    List.concat_map asic.flows ~f:(fun flow ->
      Host.command
        ("asic.describe." ^ flow.id)
        ("Describe ASIC flow " ^ flow.id)
        "endpoints parameters"
        (Asic (Describe flow.id))
      :: List.map flow.profiles ~f:(fun profile ->
        Host.command
          ("asic.plan." ^ flow.id ^ "." ^ profile)
          ("Plan ASIC " ^ flow.id ^ " / " ^ profile ^ " (enter endpoint)")
          "run synth preview"
          (Edit_plan (flow.id, profile))))
    @ Option.value_map asic.preview ~default:[] ~f:(fun preview ->
      let label =
        sprintf
          "%s / %s → %s [%s]"
          preview.selection.flow
          preview.selection.profile
          preview.selection.endpoint
          preview.plan_identity
      in
      [ Host.command
          "asic.launch"
          ("Launch " ^ label)
          "run synth"
          (Launch_asic (preview, false))
      ; Host.command
          ?unavailable:
            (if Option.is_some session.view_on_allocation
             then Some "Another launch-and-view is awaiting allocation"
             else None)
          "asic.launch-view"
          ("Launch and view in captured context: " ^ label)
          "run select"
          (Launch_asic (preview, true))
      ])
    @ Host.asic_cancel_commands asic
    @ List.concat_map asic.runs ~f:(fun run ->
      [ Host.command
          ("asic.refresh." ^ Host_view.run_label run.run)
          ("Refresh evidence " ^ Host_view.run_label run.run)
          "validate source"
          (Asic (Refresh run.run))
      ]))
;;

let execute_host session captured action ~exit =
  let open Bonsai_term in
  let async f =
    Effect.of_deferred_thunk (fun () ->
      if Host.current session.host captured
      then f ()
      else (
        session.host
        <- { session.host with
             notice = "Command target changed before dispatch; reopen palette"
           };
        return ()))
  in
  if not (Host.current session.host captured)
  then (
    session.host
    <- { session.host with notice = "Command target changed; reopen palette" };
    Effect.Ignore)
  else (
    match action with
    | Host.Registry mutation -> async (fun () -> mutate_workspace session mutation)
    | Switch id ->
      session.host <- Host.switch session.host id;
      Effect.Ignore
    | Apply_default_layout ->
      async (fun () ->
        match session.host.registry with
        | None -> return ()
        | Some registry ->
          add_default_tiles
            session
            registry
            (Workspace.workspace registry captured.workspace))
    | Build -> async (fun () -> submit session `Build)
    | Test -> async (fun () -> submit session `Test)
    | Cancel id ->
      async (fun () ->
        let requested_instance = session.hello.instance_id in
        let%map result =
          request session.diagnostics_file (fun () ->
            Http.Client.cancel_job
              session.client
              { instance_id = requested_instance; job = id })
        in
        if V1.Daemon_instance_id.equal requested_instance session.hello.instance_id
        then (
          match result with
          | Error message -> session.host <- { session.host with notice = message }
          | Ok payload ->
            session.snapshot <- State.add_job_if_absent session.snapshot payload.job))
    | Refresh_integration -> async (fun () -> refresh_integration session)
    | Generate_rtl (target, configuration) ->
      (* The captured IDs are revalidated against discovery, never replaced by the
         currently highlighted target or a first-flow fallback. *)
      let valid =
        Option.value_map (current_project session) ~default:false ~f:(fun project ->
          List.exists project.targets ~f:(fun t -> Target_id.equal t.id target)
          && List.exists project.configurations ~f:(fun c ->
            Configuration_id.equal c.id configuration && Target_id.equal c.target target))
      in
      if valid
      then (
        session.selected_target <- Some target;
        session.selected_configuration <- Some configuration;
        async (fun () ->
          match current_project session with
          | None -> return ()
          | Some project ->
            let instance_id = session.hello.instance_id in
            let%map result =
              request session.diagnostics_file (fun () ->
                Http.Client.generate_rtl
                  session.client
                  { instance_id
                  ; project = project.id
                  ; target
                  ; configuration
                  ; submission_key = submission_key "generate-rtl"
                  })
            in
            if V1.Daemon_instance_id.equal instance_id session.hello.instance_id
            then (
              match result with
              | Error message ->
                session.host
                <- { session.host with notice = "RTL generation failed: " ^ message }
              | Ok payload ->
                session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
                session.host
                <- { session.host with
                     notice = "Submitted RTL as " ^ Job_id.to_string payload.job.id
                   })))
      else (
        session.host
        <- { session.host with notice = "Captured RTL target is no longer available" };
        Effect.Ignore)
    | Inspect_artifact -> async (fun () -> inspect_artifact session)
    | Inspect_hierarchy -> async (fun () -> inspect_hierarchy session)
    | Discover_asic -> async (fun () -> asic_request session Discover)
    | Asic (Plan selection as operation) ->
      async (fun () ->
        let%bind () = save_preferences session selection in
        asic_request session operation)
    | Asic (Cancel key as operation) ->
      async (fun () ->
        if Option.value_map session.asic ~default:false ~f:(fun snapshot ->
             List.exists snapshot.operations ~f:(fun operation ->
               String.equal operation.key key && Asic_intents.cancellable operation))
        then asic_request session operation
        else (
          session.host
          <- { session.host with
               notice = "ASIC operation is no longer active and owned: " ^ key
             };
          return ()))
    | Asic operation -> async (fun () -> asic_request session operation)
    | Edit_plan (flow, profile) ->
      let query =
        Option.value_map session.remembered_selection ~default:"" ~f:(fun selection ->
          if String.equal selection.flow flow && String.equal selection.profile profile
          then String.concat (selection.endpoint :: selection.assignments) ~sep:" "
          else "")
      in
      session.host
      <- { session.host with
           palette =
             Some
               { capture = captured
               ; commands = []
               ; query
               ; index = 0
               ; argument = Some (flow, profile)
               }
         ; notice =
             "Enter ENDPOINT [name=value ...]; Describe flow lists capabilities. No \
              fallback."
         };
      Effect.Ignore
    | Launch_asic (preview, view) ->
      if not
           (Option.value_map session.asic ~default:false ~f:(fun asic ->
              Option.equal Asic.Preview.equal asic.preview (Some preview)))
      then (
        session.host
        <- { session.host with
             notice = "ASIC preview invalidated; prepare the plan again"
           };
        Effect.Ignore)
      else (
        let key = submission_key "asic-run" in
        async (fun () ->
          if view && Option.is_some session.view_on_allocation
          then (
            session.host
            <- { session.host with
                 notice = "Another launch-and-view is awaiting allocation"
               };
            return ())
          else (
            if view
            then
              Option.iter (Host.launch_target session.host) ~f:(fun target ->
                session.view_on_allocation <- Some (key, target));
            asic_request session (Run { key; preview }))))
    | Local_headers | Resume_log ->
      Option.iter session.host.focus ~f:(fun id ->
        let local = Host.local session.host id in
        let local =
          match action with
          | Local_headers -> { local with headers = not local.headers }
          | _ -> { local with follow = true; scroll = 0 }
        in
        session.host <- Host.set_local session.host id local);
      Effect.Ignore
    | Toggle_chrome ->
      session.host <- { session.host with chrome = not session.host.chrome };
      Effect.Ignore
    | Set_appearance appearance ->
      session.host <- Host.set_appearance session.host appearance;
      Effect.Ignore
    | Set_layout_mode layout_mode ->
      session.host <- { session.host with layout_mode };
      Effect.Ignore
    | Exit -> exit ())
;;

let browse_host session delta =
  Option.filter (Host.focused session.host) ~f:(fun tile ->
    String.equal tile.kind "run-selector" || Host.job_attempt_kind tile.kind)
  |> Option.iter ~f:(fun tile ->
    let local = Host.local session.host tile.id in
    let values =
      if String.equal tile.kind "run-selector"
      then
        (host_data session).runs
        |> List.filter ~f:(fun (r, label) ->
          String.is_substring
            (String.lowercase (Host_view.run_label r ^ " " ^ label))
            ~substring:(String.lowercase local.filter))
        |> List.map ~f:(fun (run, _) -> Host_view.run_label run)
      else
        project_jobs session
        |> List.filter ~f:(fun job ->
          (not (String.equal tile.kind "project-tests"))
          || (String.equal job.kind.namespace "dune" && String.equal job.kind.name "test"))
        |> List.map ~f:(fun job -> Job_id.to_string job.id)
    in
    let index =
      Option.bind local.cursor ~f:(fun cursor ->
        List.findi values ~f:(fun _ value -> String.equal cursor value)
        |> Option.map ~f:fst)
      |> Option.value ~default:(if delta > 0 then -1 else 1)
    in
    let index = Int.max 0 (Int.min (List.length values - 1) (index + delta)) in
    let cursor = List.nth values index in
    let visible = Int.max 1 (tile.requested_geometry.height - 2) in
    let scroll =
      if String.equal tile.kind "run-selector"
      then
        if index < local.scroll
        then index
        else if index >= local.scroll + visible
        then index - visible + 1
        else local.scroll
      else 0
    in
    session.host <- Host.set_local session.host tile.id { local with cursor; scroll })
;;

let host_handler session event ~exit : unit Bonsai_term.Effect.t option =
  let open Bonsai_term in
  let modal =
    Option.is_some session.host.palette
    || session.host.editing_filter
    || session.host.paste
  in
  let input = Host.decode_event event in
  let prefix = session.host.prefix > 0 in
  let captured = Host.capture session.host in
  let host, effect =
    Option.value_map input ~default:(session.host, Host.No_effect) ~f:(fun input ->
      Host.input session.host input ~commands:(host_catalog session))
  in
  session.host <- host;
  match effect with
  | Host.Execute (capture, action) -> Some (execute_host session capture action ~exit)
  | Host.Activate ->
    Option.iter (Host.focused host) ~f:(fun tile ->
      if String.equal tile.kind "run-selector"
      then (
        let local = Host.local host tile.id in
        let run =
          Option.bind session.asic ~f:(fun asic ->
            List.find asic.runs ~f:(fun r ->
              Option.equal String.equal local.cursor (Some (Host_view.run_label r.run))))
        in
        Option.iter run ~f:(fun r ->
          Option.iter (Host.select_run host (Some r.run)) ~f:(fun mutation ->
            don't_wait_for (mutate_workspace session mutation)))));
    Some Effect.Ignore
  | Host.No_effect
    when modal
         || prefix
         || Option.is_some host.palette
         || host.editing_filter
         || host.prefix > 0 -> Some Effect.Ignore
  | Host.No_effect ->
    let dispatch id =
      Option.bind captured ~f:(fun capture ->
        List.find (host_catalog session) ~f:(fun command -> String.equal command.id id)
        |> Option.map ~f:(fun command ->
          execute_host session capture command.action ~exit))
    in
    (match input with
     | Some (Character 'b') -> dispatch "project.build"
     | Some (Character 't') -> dispatch "project.test"
     | Some (Character 'i') -> dispatch "project.discover"
     | Some (Character 'g') ->
       Option.bind session.selected_configuration ~f:(fun id ->
         dispatch ("rtl." ^ Configuration_id.to_string id))
       |> Option.value ~default:Effect.Ignore
       |> Option.some
     | Some (Character 'h') ->
       Option.iter (Host.focused session.host) ~f:(fun tile ->
         Option.iter (Host.local session.host tile.id).cursor ~f:(fun id ->
           Option.iter
             (List.findi (project_jobs session) ~f:(fun _ job ->
                String.equal (Job_id.to_string job.id) id))
             ~f:(fun (index, _) -> session.selected <- index)));
       dispatch "hierarchy.inspect"
     | Some (Character 'c') ->
       (match Host.focused session.host with
        | None -> Some Effect.Ignore
        | Some tile when not (Host.job_attempt_kind tile.kind) -> Some Effect.Ignore
        | Some tile ->
          Option.bind (Host.local session.host tile.id).cursor ~f:(fun id ->
            dispatch ("job.cancel." ^ id))
          |> Option.value ~default:Effect.Ignore
          |> Option.some)
     | Some (Character 'j') | Some Next ->
       browse_host session 1;
       Some Effect.Ignore
     | Some (Character 'k') | Some Previous ->
       browse_host session (-1);
       Some Effect.Ignore
     | Some (Character (('1' | '2') as ch)) ->
       let name = if Char.equal ch '1' then "Overview" else "Timing" in
       Option.bind session.host.registry ~f:(fun s ->
         List.find s.workspaces ~f:(fun w -> String.equal w.name name))
       |> Option.iter ~f:(fun w -> session.host <- Host.switch session.host w.id);
       Some Effect.Ignore
     | Some (Character (('[' | ']') as ch)) ->
       Option.iter session.host.focus ~f:(fun id ->
         let l = Host.local session.host id in
         session.host
         <- Host.set_local
              session.host
              id
              { l with
                follow = false
              ; scroll = Int.max 0 (l.scroll + if Char.equal ch '[' then -1 else 1)
              });
       Some Effect.Ignore
     | Some Focus -> Some Effect.Ignore
     | _ -> None)
;;

let fs0_fixture scenario =
  (* Explicit synthetic data, only reachable from the capture hook. Production startup
     always obtains both registry and runs from their daemon services. *)
  let session = session_of_baseline_fixture (List.hd_exn Baseline_fixture.all) in
  let a = Fs0_fixture.run_a
  and b = Fs0_fixture.run_b in
  session.asic <- Some Fs0_fixture.snapshot;
  let registry =
    Workspace.initial
      ~session_id:(Workspace.Session_id.of_string "explicit-synthetic-fs0")
  in
  let overview = List.hd_exn registry.workspaces
  and timing = List.last_exn registry.workspaces in
  let apply s mutation =
    Workspace.apply
      s
      (Mutate { expected_revision = s.Workspace.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let registry =
    List.fold registry.tiles ~init:registry ~f:(fun s tile ->
      let width, height =
        if Workspace.Workspace_id.equal tile.workspace timing.id then 28, 6 else 32, 8
      in
      apply s (Resize_tile { tile = tile.id; geometry = { x = 0; y = 0; width; height } }))
  in
  let registry =
    List.fold
      [ overview.id, "synthesis", 64, 10
      ; overview.id, "execution", 48, 8
      ; overview.id, "project-tests", 48, 8
      ; overview.id, "logs", 64, 8
      ; overview.id, "navigation", 64, 6
      ; timing.id, "timing", 64, 10
      ; timing.id, "logs", 64, 8
      ]
      ~init:registry
      ~f:(fun s (workspace, kind, width, height) ->
        apply
          s
          (Create_tile { workspace; kind; geometry = { x = 0; y = 0; width; height } }))
  in
  let registry =
    apply
      registry
      (Select_run
         { workspace = overview.id
         ; context = registry.main_context
         ; expected_selection_revision = 0
         ; run = Some a
         })
  in
  let registry =
    if String.equal scenario "independent"
    then apply registry (Make_independent timing.id)
    else registry
  in
  let registry =
    if String.equal scenario "pinned" || String.equal scenario "pinned-synthesis"
    then (
      let registry =
        List.filter registry.tiles ~f:(fun tile ->
          String.equal tile.kind "timing" || String.equal tile.kind "synthesis")
        |> List.fold ~init:registry ~f:(fun registry tile ->
          apply registry (Set_tile_binding { tile = tile.id; binding = Pin_run a }))
      in
      apply
        registry
        (Select_run
           { workspace = overview.id
           ; context = registry.main_context
           ; expected_selection_revision = 1
           ; run = Some b
           }))
    else if String.equal scenario "synthesis-b"
    then
      apply
        registry
        (Select_run
           { workspace = overview.id
           ; context = registry.main_context
           ; expected_selection_revision = 1
           ; run = Some b
           })
    else registry
  in
  session.host <- Host.receive Host.empty registry;
  List.iter registry.tiles ~f:(fun tile ->
    if String.equal tile.kind "logs"
       || String.equal tile.kind "project-tests"
       || String.equal tile.kind "execution"
    then
      session.host
      <- Host.set_local
           session.host
           tile.id
           { Host.default_local with
             cursor =
               Option.map (selected_job session) ~f:(fun job -> Job_id.to_string job.id)
           });
  if String.equal scenario "timing"
     || String.equal scenario "independent"
     || String.equal scenario "pinned"
  then session.host <- Host.switch session.host timing.id;
  let focus_kind =
    match scenario with
    | "timing" | "pinned" -> Some "timing"
    | "synthesis-a" | "synthesis-b" | "pinned-synthesis" -> Some "synthesis"
    | "tests" -> Some "project-tests"
    | "logs" -> Some "logs"
    | _ -> None
  in
  Option.iter focus_kind ~f:(fun kind ->
    Option.iter
      (List.find (Host.tiles session.host) ~f:(fun tile -> String.equal tile.kind kind))
      ~f:(fun tile -> session.host <- { session.host with focus = Some tile.id }));
  if String.equal scenario "palette"
  then
    List.iter [ ' '; 'c'; 'c' ] ~f:(fun ch ->
      let host, _ =
        Host.input session.host (Character ch) ~commands:(host_catalog session)
      in
      session.host <- host);
  session.status <- "SYNTHETIC FS0 FIXTURE — no tool evidence";
  session
;;

let capture_fs0_frames ~directory =
  Core_unix.mkdir_p directory;
  List.iter
    [ "overview"
    ; "timing"
    ; "independent"
    ; "pinned"
    ; "palette"
    ; "tests"
    ; "logs"
    ; "synthesis-a"
    ; "synthesis-b"
    ; "pinned-synthesis"
    ]
    ~f:(fun scenario ->
      List.iter
        (capture_dimensions @ [ { Bonsai_term.Dimensions.width = 32; height = 8 } ])
        ~f:(fun dimensions ->
          List.iter
            [ "txt", Notty.Cap.dumb; "ansi", Notty.Cap.ansi ]
            ~f:(fun (extension, cap) ->
              let file =
                sprintf
                  "fs0-%s.%dx%d.%s"
                  scenario
                  dimensions.width
                  dimensions.height
                  extension
              in
              Out_channel.write_all
                (Filename.concat directory file)
                ~data:(render_to_string (fs0_fixture scenario) dimensions ~cap ^ "\n"))))
;;

let capture_appearance_frames ~directory =
  Core_unix.mkdir_p directory;
  List.iter Appearance.Preset.all ~f:(fun preset ->
    List.iter
      [ "synthesis-a"; "timing"; "pinned-synthesis"; "palette" ]
      ~f:(fun scenario ->
        List.iter Appearance.Density.all ~f:(fun density ->
          List.iter capture_dimensions ~f:(fun dimensions ->
            List.iter
              [ "txt", Notty.Cap.dumb; "ansi", Notty.Cap.ansi ]
              ~f:(fun (extension, cap) ->
                let session = fs0_fixture scenario in
                session.host
                <- Host.set_appearance
                     session.host
                     { Appearance.default with preset; density; icons = Unicode };
                let name =
                  sprintf
                    "%s-%s-%s.%dx%d.%s"
                    (Appearance.Preset.key preset)
                    (Appearance.Density.key density)
                    scenario
                    dimensions.width
                    dimensions.height
                    extension
                in
                Out_channel.write_all
                  (Filename.concat directory name)
                  ~data:(render_to_string session dimensions ~cap ^ "\n"))))));
  printf "Captured experimental A-E skins (synthetic data) in %s\n%!" directory
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
      let hosted =
        if Option.is_some session.host.registry
           && Option.is_none session.hierarchy_view
           && Option.is_none session.artifact_view
           && not session.show_connection_details
        then host_handler session event ~exit
        else None
      in
      match hosted with
      | Some effect -> effect
      | None ->
        (match event with
         | Key_press { key; mods = [] } when key_is 'q' key -> exit ()
         | Key_press { key; mods = [ Ctrl ] } when key_is 'c' key || key_is 'C' key ->
           exit ()
         | Key_press { key; mods = [] } when key_is 'b' key ->
           Effect.of_deferred_thunk (fun () -> submit session `Build)
         | Key_press { key; mods = [] } when key_is 't' key ->
           Effect.of_deferred_thunk (fun () -> submit session `Test)
         | Key_press { key; mods = [] } when key_is 'c' key ->
           Effect.of_deferred_thunk (fun () -> cancel_selected session)
         | Key_press { key; mods = [] } when key_is 'i' key ->
           Effect.of_deferred_thunk (fun () -> refresh_integration session)
         | Key_press { key; mods = [] } when key_is 'n' key ->
           cycle_target session;
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'm' key ->
           cycle_configuration session;
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'g' key ->
           Effect.of_deferred_thunk (fun () -> generate_rtl session)
         | Key_press { key; mods = [] } when key_is 'a' key ->
           cycle_artifact session;
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'v' key ->
           Effect.of_deferred_thunk (fun () -> inspect_artifact session)
         | Key_press { key; mods = [] } when key_is 'h' key ->
           Effect.of_deferred_thunk (fun () -> inspect_hierarchy session)
         | Key_press { key; mods = [] } when key_is 'u' key ->
           move_hierarchy_selection session (-1);
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'o' key ->
           move_hierarchy_selection session 1;
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'e' key ->
           toggle_hierarchy_expansion session;
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'j' key ->
           let count = List.length (project_jobs session) in
           session.selected <- Int.min (Int.max 0 (count - 1)) (session.selected + 1);
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'k' key ->
           session.selected <- Int.max 0 (session.selected - 1);
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'd' key ->
           session.show_connection_details <- not session.show_connection_details;
           session.connection_details_scroll <- 0;
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is '[' key ->
           if session.show_connection_details
           then
             session.connection_details_scroll
             <- Int.max 0 (session.connection_details_scroll - 1)
           else
             Option.iter session.hierarchy_view ~f:(fun view ->
               view.pane_scroll <- Int.max 0 (view.pane_scroll - 1));
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is ']' key ->
           if session.show_connection_details
           then session.connection_details_scroll <- session.connection_details_scroll + 1
           else
             Option.iter session.hierarchy_view ~f:(fun view ->
               view.pane_scroll <- view.pane_scroll + 1);
           Effect.Ignore
         | Key_press { key; mods = [] } when key_is 'r' key ->
           Effect.of_deferred_thunk (fun () -> reconnect session)
         | _ -> Effect.Ignore))
  in
  ~view, ~handler
;;

let print_opened session =
  reconcile_selection session;
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
  List.iter (integration_lines session) ~f:print_endline;
  List.iter (artifact_lines session) ~f:print_endline;
  List.iter (hierarchy_status_lines session) ~f:print_endline
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
      let%bind updated = poll_updates session ~timeout_ms:200 in
      (match updated with
       | Error message -> return (Error message)
       | Ok (`Applied | `Resynced | `Stale) ->
         let current =
           List.find session.snapshot.jobs ~f:(fun candidate ->
             Job_id.equal candidate.id job.id)
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

let resolve_selection values selector ~name ~id ~kind =
  match selector with
  | None -> List.hd values |> Result.of_option ~error:(sprintf "no %s is available" kind)
  | Some selector ->
    let matches =
      List.filter values ~f:(fun value ->
        String.equal selector (name value) || String.equal selector (id value))
    in
    (match matches with
     | [ value ] -> Ok value
     | [] -> Error (sprintf "%s %S was not found" kind selector)
     | _ -> Error (sprintf "%s selector %S is ambiguous" kind selector))
;;

let wait_for_discovery_if_needed session =
  match current_project session with
  | Some project when not (List.is_empty project.targets) -> return (Ok ())
  | _ ->
    let discovery =
      project_jobs session
      |> List.find ~f:(fun job ->
        String.equal job.kind.namespace "project-driver"
        && String.equal job.kind.name "describe")
    in
    (match discovery with
     | None -> return (Error "project has no discovered targets")
     | Some job when Job.is_terminal job ->
       return (Error "project discovery did not produce a target")
     | Some job ->
       let%map result = wait_for_job session job in
       Result.bind result ~f:(fun job ->
         if Job.State.equal job.state Complete
         then Ok ()
         else
           Error (sprintf "discovery ended in state %s" (Job.State.to_string job.state))))
;;

let run_plain_generate session ~target_selector ~configuration_selector ~wait =
  let%bind discovered = wait_for_discovery_if_needed session in
  match discovered with
  | Error message -> return (Or_error.error_string message)
  | Ok () ->
    reconcile_selection session;
    (match current_project session with
     | None ->
       return (Or_error.error_string "--action generate-rtl requires --project-root")
     | Some project ->
       (match
          resolve_selection
            project.targets
            target_selector
            ~name:(fun target -> target.Target.name)
            ~id:(fun target -> Target_id.to_string target.id)
            ~kind:"target"
        with
        | Error message -> return (Or_error.error_string message)
        | Ok target ->
          let configurations =
            List.filter project.configurations ~f:(fun configuration ->
              Target_id.equal configuration.target target.id)
          in
          (match
             resolve_selection
               configurations
               configuration_selector
               ~name:(fun configuration -> configuration.Configuration.name)
               ~id:(fun configuration -> Configuration_id.to_string configuration.id)
               ~kind:"configuration"
           with
           | Error message -> return (Or_error.error_string message)
           | Ok configuration ->
             session.selected_target <- Some target.id;
             session.selected_configuration <- Some configuration.id;
             let key = submission_key "generate-rtl" in
             let%bind submitted =
               request session.diagnostics_file (fun () ->
                 Http.Client.generate_rtl
                   session.client
                   { instance_id = session.hello.instance_id
                   ; project = project.id
                   ; target = target.id
                   ; configuration = configuration.id
                   ; submission_key = key
                   })
             in
             (match submitted with
              | Error message -> return (Or_error.error_string message)
              | Ok payload ->
                session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
                printf
                  "Submitted RTL job %s for target %s / configuration %s\n%!"
                  (Job_id.to_string payload.job.id)
                  target.name
                  configuration.name;
                if not wait
                then return (Ok ())
                else (
                  let%map finished = wait_for_job session payload.job in
                  match finished with
                  | Error message -> Or_error.error_string message
                  | Ok job when not (Job.State.equal job.state Complete) ->
                    Or_error.error_string
                      (sprintf "job ended in state %s" (Job.State.to_string job.state))
                  | Ok job ->
                    printf "Job %s: Complete\n" (Job_id.to_string job.id);
                    List.iter job.artifacts ~f:(fun id ->
                      match
                        List.find session.snapshot.artifacts ~f:(fun artifact ->
                          Artifact_id.equal artifact.id id)
                      with
                      | None ->
                        printf
                          "Artifact %s: metadata unavailable\n"
                          (Artifact_id.to_string id)
                      | Some artifact ->
                        printf
                          "Artifact %s: %s (%s, %s bytes)\n"
                          (Artifact_id.to_string artifact.id)
                          artifact.metadata.display_name
                          (Artifact.Kind.to_string artifact.kind)
                          (Option.value_map
                             artifact.metadata.size_in_bytes
                             ~default:"unknown"
                             ~f:Int.to_string));
                    Ok ())))))
;;

let run_plain_artifact session artifact_id =
  let artifact = Artifact_id.of_string artifact_id in
  let rec read offset =
    let%bind page =
      request session.diagnostics_file (fun () ->
        Http.Client.read_artifact
          session.client
          { instance_id = session.hello.instance_id
          ; artifact
          ; offset
          ; max_bytes = V1.max_artifact_bytes
          })
    in
    match page with
    | Error message -> return (Or_error.error_string message)
    | Ok page ->
      Out_channel.output_string stdout page.data;
      Out_channel.flush stdout;
      if page.eof then return (Ok ()) else read page.next_offset
  in
  read 0
;;

let run_plain_hierarchy session artifact_id =
  let artifact = Artifact_id.of_string artifact_id in
  let%map response =
    request session.diagnostics_file (fun () ->
      Http.Client.read_hierarchy
        session.client
        { instance_id = session.hello.instance_id; artifact })
  in
  match response with
  | Error message -> Or_error.error_string message
  | Ok payload ->
    let hierarchy = payload.hierarchy in
    let nodes, children = index_hierarchy hierarchy in
    printf "Hierarchy artifact: %s\n" (Artifact_id.to_string hierarchy.artifact);
    printf "Generating job: %s\n" (Job_id.to_string hierarchy.generating_job);
    printf "Target: %s\n" (Target_id.to_string hierarchy.target);
    printf "Configuration: %s\n" (Configuration_id.to_string hierarchy.configuration);
    let rec print_node depth key =
      match Hashtbl.find nodes key with
      | None -> ()
      | Some node ->
        printf
          "%s%s : %s [%s]\n"
          (String.make (depth * 2) ' ')
          (Option.value node.instance_name ~default:"<root>")
          node.circuit_name
          node.key;
        hierarchy_children children key
        |> List.iter ~f:(fun child -> print_node (depth + 1) child.key)
    in
    print_node 0 hierarchy.root;
    Ok ()
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
       session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
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

let run_plain_refresh session ~wait =
  match current_project session with
  | None -> return (Or_error.error_string "--refresh-integration requires --project-root")
  | Some project ->
    let%bind refreshed =
      request session.diagnostics_file (fun () ->
        Http.Client.refresh_integration
          session.client
          { instance_id = session.hello.instance_id; project = project.id })
    in
    (match refreshed with
     | Error message -> return (Or_error.error_string message)
     | Ok payload ->
       session.snapshot <- State.add_job_if_absent session.snapshot payload.job;
       printf "Submitted integration refresh job %s\n%!" (Job_id.to_string payload.job.id);
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
           List.iter (integration_lines session) ~f:print_endline;
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
  | Some "generate-rtl" -> Ok (Some `Generate_rtl)
  | Some _ -> Or_error.error_string "--action must be build, test, or generate-rtl"
;;

let run_legacy
  ~endpoint
  ~project_root
  ~environment
  ~plain
  ~action
  ~target
  ~configuration
  ~artifact
  ~hierarchy
  ~refresh_integration:refresh_requested
  ~wait
  ~diagnostics_file
  ()
  =
  let diagnostics_file =
    Option.first_some diagnostics_file (Sys.getenv "HARDCAML_WORKBENCH_DIAGNOSTICS")
  in
  match parse_environment environment, parse_action action with
  | Error error, _ | _, Error error -> return (Error error)
  | Ok (environment_selection, environment_label), Ok action ->
    if (Option.is_some action
        || Option.is_some artifact
        || Option.is_some hierarchy
        || refresh_requested)
       && not plain
    then
      return
        (Or_error.error_string
           "--action, --artifact, --hierarchy, and --refresh-integration are available \
            only with --plain")
    else if List.count
              [ Option.is_some action
              ; Option.is_some artifact
              ; Option.is_some hierarchy
              ; refresh_requested
              ]
              ~f:Fn.id
            > 1
    then
      return
        (Or_error.error_string
           "choose one of --action, --artifact, --hierarchy, or --refresh-integration")
    else if wait && Option.is_none action && not refresh_requested
    then
      return (Or_error.error_string "--wait requires --action or --refresh-integration")
    else if (Option.is_some action || refresh_requested) && Option.is_none project_root
    then
      return
        (Or_error.error_string
           "--action and --refresh-integration require --project-root")
    else if (Option.is_some target || Option.is_some configuration)
            && not (Option.equal Poly.equal action (Some `Generate_rtl))
    then
      return
        (Or_error.error_string "--target/--configuration require --action generate-rtl")
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
        reconcile_selection session;
        if plain || not (Core_unix.isatty Core_unix.stdout)
        then (
          print_opened session;
          match action, artifact, hierarchy, refresh_requested with
          | None, None, None, false -> return (Ok ())
          | Some ((`Build | `Test) as action), None, None, false ->
            run_plain_action session action ~wait
          | Some `Generate_rtl, None, None, false ->
            run_plain_generate
              session
              ~target_selector:target
              ~configuration_selector:configuration
              ~wait
          | None, Some artifact, None, false -> run_plain_artifact session artifact
          | None, None, Some hierarchy, false -> run_plain_hierarchy session hierarchy
          | None, None, None, true -> run_plain_refresh session ~wait
          | _ -> assert false)
        else
          Monitor.try_with_or_error (fun () ->
            Bonsai_term.start_with_exit ~dispose:true ~mouse:No_mouse_events (tui session))
          >>| Or_error.join
          >>| Result.map_error ~f:(fun error ->
            append_diagnostic diagnostics_file ("terminal error: " ^ error_message error);
            error))
;;

type plain_operation =
  | Asic_operation of Asic.Operation.t
  | Workspace_operation of Workspace.Operation.t

let rpc_call session thunk =
  Monitor.try_with_or_error thunk
  >>| Or_error.join
  >>| function
  | Ok response -> response
  | Error error ->
    let message = "Terminal transport failure: " ^ Error.to_string_hum error in
    append_diagnostic session.diagnostics_file message;
    Error (V1.Error.create Internal_failure message)
;;

let run_plain_asic session operation ~wait ~timeout_seconds =
  let project = (Option.value_exn session.opened).project.id in
  let instance_id = session.hello.instance_id in
  let call operation =
    rpc_call session (fun () ->
      Http.Client.asic session.client { instance_id; project; operation })
  in
  let last = ref None in
  let finish response failure = Asic.Response.sexp_of_t response, failure in
  let rec poll keys response =
    match response with
    | Error error -> return (finish response (Some (protocol_error error)))
    | Ok snapshot ->
      last := Some snapshot;
      let keys = Plain_rpc.watched_keys operation keys snapshot in
      (match Plain_rpc.progress ~wait keys snapshot with
       | Failed message -> return (finish response (Some message))
       | Complete ->
         let failure =
           match operation with
           | Asic.Operation.Plan selection when wait ->
             if Option.value_map snapshot.preview ~default:false ~f:(fun preview ->
                  Asic.Selection.equal preview.selection selection)
             then None
             else
               Some
                 "Requested ASIC plan completed but its preview is absent or superseded"
           | _ -> None
         in
         return (finish response failure)
       | Pending ->
         let%bind () = Clock.after (Time_float.Span.of_ms 200.) in
         let%bind response = call Get in
         poll keys response)
  in
  let perform () =
    let%bind response = call operation in
    let keys =
      Result.ok response |> Option.value_map ~default:[] ~f:(Plain_rpc.keys operation)
    in
    poll keys response
  in
  if not wait
  then perform ()
  else (
    match%map
      Clock.with_timeout (Time_float.Span.of_sec timeout_seconds) (perform ())
    with
    | `Result result -> result
    | `Timeout ->
      let message =
        sprintf
          "ASIC operation wait timed out after %g seconds; daemon work was not cancelled"
          timeout_seconds
      in
      let response =
        Option.value_map
          !last
          ~default:(Error (V1.Error.create Internal_failure message))
          ~f:(fun snapshot -> Ok snapshot)
      in
      finish response (Some message))
;;

let run_plain_workspace session operation =
  let project = (Option.value_exn session.opened).project.id in
  let%map response =
    rpc_call session (fun () ->
      Http.Client.workspace
        session.client
        { instance_id = session.hello.instance_id; project; operation })
  in
  ( Workspace.Response.sexp_of_t response
  , match response with
    | Ok _ -> None
    | Error error -> Some (protocol_error error) )
;;

let run
  ~endpoint
  ~project_root
  ~environment
  ~plain
  ~api
  ~asic_operation
  ~workspace_operation
  ~wait_timeout_seconds
  ~action
  ~target
  ~configuration
  ~artifact
  ~hierarchy
  ~refresh_integration
  ~wait
  ~diagnostics_file
  ()
  =
  let fail message =
    if api
    then
      printf
        "%s\n%!"
        (Sexp.to_string_mach
           (Workspace.Response.sexp_of_t
              (Error (V1.Error.create Invalid_request message))));
    return (Or_error.error_string message)
  in
  let has_operation =
    Option.is_some asic_operation || Option.is_some workspace_operation
  in
  if not has_operation
  then
    if api
    then fail "--api requires --asic-operation or --workspace-operation"
    else if Option.is_some wait_timeout_seconds
    then fail "--wait-timeout-seconds requires an ASIC operation and --wait"
    else
      run_legacy
        ~endpoint
        ~project_root
        ~environment
        ~plain
        ~action
        ~target
        ~configuration
        ~artifact
        ~hierarchy
        ~refresh_integration
        ~wait
        ~diagnostics_file
        ()
  else if List.count
            [ Option.is_some asic_operation
            ; Option.is_some workspace_operation
            ; Option.is_some action
            ; Option.is_some artifact
            ; Option.is_some hierarchy
            ; refresh_integration
            ]
            ~f:Fn.id
          <> 1
  then
    fail
      "Choose exactly one operation: --asic-operation, --workspace-operation, --action, \
       --artifact, --hierarchy, or --refresh-integration"
  else if not (plain || api)
  then fail "Typed operations require --plain or --api"
  else if Option.is_none project_root
  then fail "Typed operations require --project-root"
  else if Option.is_some target || Option.is_some configuration
  then fail "--target/--configuration apply only to --action generate-rtl"
  else if Option.is_some workspace_operation && wait
  then fail "Workspace operations are synchronous; omit --wait"
  else if Option.is_some wait_timeout_seconds
          && ((not wait) || Option.is_none asic_operation)
  then fail "--wait-timeout-seconds requires an ASIC operation and --wait"
  else (
    let timeout_seconds = Option.value wait_timeout_seconds ~default:60. in
    if not (Float.is_finite timeout_seconds && Float.(timeout_seconds > 0.))
    then fail "Wait timeout must be a finite positive number of seconds"
    else (
      let decoded =
        Or_error.try_with (fun () ->
          match asic_operation, workspace_operation with
          | Some sexp, None ->
            Asic_operation (Asic.Operation.t_of_sexp (Sexp.of_string sexp))
          | None, Some sexp ->
            Workspace_operation (Workspace.Operation.t_of_sexp (Sexp.of_string sexp))
          | _ -> assert false)
      in
      match decoded, parse_environment environment with
      | Error error, _ | _, Error error -> fail (Error.to_string_hum error)
      | Ok operation, Ok (environment_selection, environment_label) ->
        let diagnostics_file =
          Option.first_some diagnostics_file (Sys.getenv "HARDCAML_WORKBENCH_DIAGNOSTICS")
        in
        let%bind created =
          create_session
            ~endpoint
            ~project_root
            ~environment_selection
            ~environment_label
            ~diagnostics_file
        in
        (match created with
         | Error message ->
           if api
           then
             printf
               "%s\n%!"
               (Sexp.to_string_mach
                  (Workspace.Response.sexp_of_t
                     (Error (V1.Error.create Internal_failure message))));
           return (Or_error.error_string message)
         | Ok session ->
           if not api then print_opened session;
           let%map sexp, failure =
             match operation with
             | Asic_operation operation ->
               run_plain_asic session operation ~wait ~timeout_seconds
             | Workspace_operation operation -> run_plain_workspace session operation
           in
           printf "%s\n%!" (Sexp.to_string_mach sexp);
           (match failure with
            | None -> Ok ()
            | Some message -> Or_error.error_string message))))
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
     and api =
       flag
         "--api"
         no_arg
         ~doc:" emit exactly one typed RPC response sexp; no status preamble"
     and asic_operation =
       flag
         "--asic-operation"
         (optional string)
         ~doc:"SEXP typed Asic.Operation; requires --project-root and --plain or --api"
     and workspace_operation =
       flag
         "--workspace-operation"
         (optional string)
         ~doc:
           "SEXP typed Workspace.Operation; requires --project-root and --plain or --api"
     and wait_timeout_seconds =
       flag
         "--wait-timeout-seconds"
         (optional float)
         ~doc:
           "SECONDS bounded ASIC --wait budget (default 60); does not cancel daemon work"
     and action =
       flag
         "--action"
         (optional string)
         ~doc:"build|test|generate-rtl submit one action in plain mode"
     and target = flag "--target" (optional string) ~doc:"NAME|ID target for generate-rtl"
     and configuration =
       flag
         "--configuration"
         (optional string)
         ~doc:"NAME|ID configuration for generate-rtl"
     and artifact =
       flag
         "--artifact"
         (optional string)
         ~doc:"ID retrieve artifact content in plain mode"
     and hierarchy =
       flag
         "--hierarchy"
         (optional string)
         ~doc:"ARTIFACT_ID retrieve structured hierarchy in plain mode"
     and refresh_integration =
       flag
         "--refresh-integration"
         no_arg
         ~doc:" queue project-driver discovery refresh in plain mode"
     and wait =
       flag
         "--wait"
         no_arg
         ~doc:" wait for a plain action, or bounded typed ASIC operation completion"
     and diagnostics_file =
       flag
         "--diagnostics-file"
         (optional string)
         ~doc:"FILE append dimensions and caught errors outside the active terminal"
     and capture_baseline =
       flag
         "--capture-baseline"
         (optional string)
         ~doc:
           "DIR render the deterministic UI fixtures into DIR and exit (development \
            baseline capture; no daemon or project needed)"
     and capture_fs0 =
       flag
         "--capture-fs0"
         (optional string)
         ~doc:
           "DIR capture actual workspace renderer with explicitly synthetic FS0 fixtures"
     and capture_appearance =
       flag
         "--capture-appearance"
         (optional string)
         ~doc:"DIR capture experimental A-E skins over identical synthetic fixtures"
     in
     match capture_appearance, capture_fs0, capture_baseline with
     | (Some _, _, _ | _, Some _, _ | _, _, Some _) when api ->
       fun () ->
         let message = "--api cannot be combined with capture hooks" in
         printf
           "%s\n%!"
           (Sexp.to_string_mach
              (Workspace.Response.sexp_of_t
                 (Error (V1.Error.create Invalid_request message))));
         return (Or_error.error_string message)
     | Some directory, _, _ ->
       fun () ->
         capture_appearance_frames ~directory;
         return (Ok ())
     | None, Some directory, _ ->
       fun () ->
         capture_fs0_frames ~directory;
         return (Ok ())
     | None, None, Some directory ->
       (* The capture renders fixtures; it neither connects to a daemon nor opens a
          project, so it never enters [run] and none of the session flags apply. *)
       fun () ->
       capture_baseline_frames ~directory;
       return (Ok ())
     | None, None, None ->
       run
         ~endpoint
         ~project_root
         ~environment
         ~plain
         ~api
         ~asic_operation
         ~workspace_operation
         ~wait_timeout_seconds
         ~action
         ~target
         ~configuration
         ~artifact
         ~hierarchy
         ~refresh_integration
         ~wait
         ~diagnostics_file)
;;

let () = Command_unix.run command
