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
module Synthesis_view = Terminal_presentation.Synthesis_view
module Terminal_result_view = Terminal_presentation.Terminal_result_view
module Plain_rpc = Terminal_presentation.Plain_rpc
module Launch_preferences = Terminal_presentation.Launch_preferences
module Presentation_preferences = Terminal_presentation.Presentation_preferences
module Asic_intents = Terminal_presentation.Asic_intents
module Artifact_view = Terminal_presentation.Artifact_view
module Artifact_export = Terminal_presentation.Artifact_export
module Artifact_binary_export = Terminal_presentation.Artifact_binary_export
module Inspection_view = Terminal_presentation.Inspection_view
module Timing_workspace = Terminal_presentation.Timing_workspace
module Fs0_fixture = Terminal_presentation.Fs0_fixture
module Simulation_view = Terminal_presentation.Simulation_view
module Simulation_export = Terminal_presentation.Simulation_export
module Planned_run = Terminal_presentation.Planned_run
module Stage_action = Terminal_presentation.Stage_action

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
  ; mutable presentation_preferences_loaded : string option
      (* Pending first-registry restoration only; consumed before ordinary polling. *)
  ; mutable presentation_preferences : Presentation_preferences.t option
  ; mutable presentation_preference_notice : string option
  ; mutable preference_saves : unit Deferred.t
  ; mutable asic_reads : Asic_intents.t
  ; mutable remembered_acceptance : string
  ; mutable artifact_viewer : string option
  ; mutable artifact_binary_viewer : string option
  ; mutable artifact_export_busy : bool
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
      ; presentation_preferences_loaded = None
      ; presentation_preferences = None
      ; presentation_preference_notice = None
      ; preference_saves = Deferred.unit
      ; asic_reads = Asic_intents.empty
      ; remembered_acceptance = ""
      ; artifact_viewer = None
      ; artifact_binary_viewer = None
      ; artifact_export_busy = false
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

let plan_scope session (project : Project.t) =
  Sexp.to_string_mach
    (Sexp.List
       [ V1.Daemon_instance_id.sexp_of_t session.hello.instance_id
       ; Project_id.sexp_of_t project.id
       ])
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
    session.host
    <- { session.host with
         planned_run = Planned_run.reset session.host.planned_run ~scope:""
       };
    session.asic <- None;
    session.selected_target <- None;
    session.selected_configuration <- None;
    session.selected_artifact <- None;
    session.artifact_view <- None;
    session.hierarchy_view <- None
  | Some project ->
    let planned_run =
      Planned_run.reset session.host.planned_run ~scope:(plan_scope session project)
    in
    if not (phys_equal planned_run session.host.planned_run) then session.asic <- None;
    session.host <- { session.host with planned_run };
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

let read_job_log_id session (job : Job_id.t option) =
  match job with
  | None -> return ()
  | Some job ->
    let state = log_state session job in
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
             ; job
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

let read_job_log session job =
  read_job_log_id session (Option.map job ~f:(fun (j : Job.t) -> j.id))
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

let preference_context session =
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
  project_key, state_directory
;;

let preference_location session =
  let project_key, state_directory = preference_context session in
  project_key, Launch_preferences.path ~state_directory ~project_key
;;

let presentation_preference_error session message error =
  let message = message ^ ": " ^ Error.to_string_hum error in
  session.presentation_preference_notice <- Some message;
  append_diagnostic session.diagnostics_file message
;;

let load_presentation_preferences session =
  if Option.is_none session.opened
  then return ()
  else (
    match Or_error.try_with (fun () -> preference_context session) with
    | Error error ->
      presentation_preference_error
        session
        "Could not load presentation preferences; using defaults (file left untouched)"
        error;
      return ()
    | Ok (project_key, state_directory) ->
      if Option.equal
           String.equal
           session.presentation_preferences_loaded
           (Some project_key)
      then return ()
      else (
        (* Reopening a changed canonical project/environment must not carry the previous
           context's presentation into the new registry. *)
        if Option.is_some session.presentation_preferences_loaded
        then
          session.host
          <- { session.host with
               appearance = Appearance.default
             ; layout_mode = Fit
             ; chrome = true
             ; locals = []
             };
        session.presentation_preferences_loaded <- Some project_key;
        session.presentation_preferences <- None;
        session.presentation_preference_notice <- None;
        let%map result =
          In_thread.run (fun () ->
            Or_error.try_with (fun () ->
              Presentation_preferences.load ~state_directory ~project_key))
        in
        match result with
        | Ok preferences ->
          session.presentation_preferences
          <- (if Option.is_none session.host.registry then preferences else None);
          Option.iter preferences ~f:(fun preferences ->
            session.host <- Presentation_preferences.apply preferences session.host)
        | Error error ->
          presentation_preference_error
            session
            "Could not load presentation preferences; using defaults (file left \
             untouched)"
            error))
;;

let save_presentation_preferences session =
  (* Capture before yielding, so polling and later keypresses cannot change this save. *)
  match Or_error.try_with (fun () -> preference_context session) with
  | Error error ->
    presentation_preference_error session "Could not save presentation preferences" error;
    return ()
  | Ok (project_key, state_directory) ->
    let preferences = Presentation_preferences.capture ~project_key session.host in
    session.presentation_preferences <- None;
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
              Presentation_preferences.save ~state_directory preferences))
        in
        if Option.equal
             String.equal
             session.presentation_preferences_loaded
             (Some project_key)
        then (
          match result with
          | Ok () -> session.presentation_preference_notice <- None
          | Error error ->
            presentation_preference_error
              session
              "Could not save presentation preferences"
              error))
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
    | Ok selection ->
      session.remembered_selection <- selection;
      session.host <- { session.host with remembered_selection = selection }
    | Error error ->
      append_diagnostic
        session.diagnostics_file
        ("preference load: " ^ Error.to_string_hum error))
;;

let save_preferences session selection =
  session.remembered_selection <- Some selection;
  session.host <- { session.host with remembered_selection = Some selection };
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

let synthesis_summary session tile =
  Option.bind session.host.registry ~f:(fun registry ->
    Workspace.resolve_tile registry tile.Workspace.Tile.id
    |> Result.ok
    |> Option.bind ~f:(fun reference -> reference.run)
    |> Option.bind ~f:(fun run ->
      Option.bind session.asic ~f:(fun asic ->
        List.find asic.summaries ~f:(fun summary ->
          Run_ref.equal summary.Asic.Summary.run run))))
;;

let terminal_result_context session tile =
  Option.bind session.host.registry ~f:(fun registry ->
    Workspace.resolve_tile registry tile.Workspace.Tile.id
    |> Result.ok
    |> Option.bind ~f:(fun reference -> reference.run)
    |> Option.map ~f:(fun run -> run, synthesis_summary session tile))
;;

let reconcile_synthesis session =
  Option.iter session.host.registry ~f:(fun registry ->
    let timing =
      List.filter_map session.host.timing ~f:(fun (id, view) ->
        let workspace =
          List.find registry.workspaces ~f:(fun w ->
            String.equal id (Workspace.Workspace_id.to_string w.id))
        in
        Option.bind workspace ~f:(fun workspace ->
          let context = Workspace.context registry workspace.context in
          Option.map context.selected_run ~f:(fun run ->
            let view =
              if Run_ref.equal run view.Inspection_view.run
                 && Option.equal
                      String.equal
                      view.workspace_epoch
                      (Some (Host.timing_epoch registry workspace.id))
              then view
              else
                Timing_workspace.create
                  ~generation:(view.generation + 1)
                  ~run
                  ~stage:view.stage
            in
            let view =
              { view with
                Inspection_view.workspace_epoch =
                  Some (Host.timing_epoch registry workspace.id)
              }
            in
            ( id
            , Option.value_map
                session.asic
                ~default:view
                ~f:(Inspection_view.reconcile view) ))))
    in
    session.host <- { session.host with timing };
    List.iter registry.tiles ~f:(fun tile ->
      let local = Host.local session.host tile.id in
      let artifacts =
        Option.bind local.artifacts ~f:(fun view ->
          Workspace.resolve_tile registry tile.id
          |> Result.ok
          |> Option.bind ~f:(fun reference ->
            Artifact_view.reconcile_scope view ~scope:reference.run)
          |> Option.map ~f:(fun view ->
            let view =
              Option.value_map
                session.asic
                ~default:view
                ~f:(Artifact_view.reconcile view)
            in
            Option.value_map session.last_dimensions ~default:view ~f:(fun dimensions ->
              Artifact_view.clamp view ~width:dimensions.width ~height:dimensions.height)))
      in
      let inspection =
        Option.bind local.inspection ~f:(fun view ->
          Workspace.resolve_tile registry tile.id
          |> Result.ok
          |> Option.bind ~f:(fun reference ->
            Inspection_view.reconcile_scope view ~scope:reference.run)
          |> Option.map ~f:(fun view ->
            let view =
              Option.value_map
                session.asic
                ~default:view
                ~f:(Inspection_view.reconcile view)
            in
            Option.value_map session.last_dimensions ~default:view ~f:(fun dimensions ->
              let width, height = Host_view.inspection_viewport dimensions in
              Inspection_view.clamp view ~width ~height)))
      in
      session.host
      <- Host.set_local session.host tile.id { local with artifacts; inspection };
      if String.equal tile.kind "synthesis"
      then (
        let local = Host.local session.host tile.id in
        let synthesis =
          Synthesis_view.State.reconcile
            local.synthesis
            ~summary:(synthesis_summary session tile)
            ~filter:local.filter
        in
        session.host <- Host.set_local session.host tile.id { local with synthesis })
      else if String.equal tile.kind "stage-checklist"
      then (
        let local = Host.local session.host tile.id in
        let run =
          Workspace.resolve_tile registry tile.id
          |> Result.ok
          |> Option.bind ~f:(fun reference -> reference.run)
        in
        let stages =
          Option.value_map run ~default:[] ~f:(fun run ->
            Terminal_presentation.Overview_tiles.observed_stages ~asic:session.asic ~run)
        in
        session.host
        <- Host.set_local session.host tile.id (Host.reconcile_stages local ~run ~stages))
      else if Terminal_result_view.supports tile.kind
      then (
        let local = Host.local session.host tile.id in
        let terminal_result =
          match terminal_result_context session tile with
          | None -> Terminal_result_view.State.empty
          | Some (run, summary) ->
            Terminal_result_view.State.reconcile local.terminal_result ~run ~summary
        in
        session.host <- Host.set_local session.host tile.id { local with terminal_result })))
;;

let change_terminal_result session f =
  reconcile_synthesis session;
  Option.iter (Host.focused session.host) ~f:(fun tile ->
    if Terminal_result_view.supports tile.kind
    then (
      let local = Host.local session.host tile.id in
      session.host
      <- Host.set_local
           session.host
           tile.id
           { local with terminal_result = f local.terminal_result }))
;;

let change_synthesis session f =
  reconcile_synthesis session;
  Option.iter (Host.focused session.host) ~f:(fun tile ->
    if String.equal tile.kind "synthesis"
    then (
      let local = Host.local session.host tile.id in
      let (next : Host.local) = f tile local in
      let next =
        if Synthesis_view.Mode.equal
             (Synthesis_view.State.mode local.synthesis)
             (Synthesis_view.State.mode next.synthesis)
        then next
        else { next with scroll = 0; metrics_scope = None }
      in
      session.host <- Host.set_local session.host tile.id next))
;;

let workspace_request session operation =
  match current_project session with
  | None -> return ()
  | Some project ->
    let instance_id = session.hello.instance_id in
    let client = session.client in
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.workspace client { instance_id; project = project.id; operation })
    in
    if phys_equal client session.client
       && V1.Daemon_instance_id.equal instance_id session.hello.instance_id
       && Option.value_map (current_project session) ~default:false ~f:(fun p ->
         Project_id.equal p.id project.id)
    then (
      match response with
      | Error message ->
        session.host <- { session.host with notice = "Workspace: " ^ message }
      | Ok snapshot ->
        let host, pending =
          Presentation_preferences.receive
            session.presentation_preferences
            session.host
            snapshot
        in
        session.host <- host;
        session.presentation_preferences <- pending;
        reconcile_synthesis session)
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

let capture_artifact_request session (tile : Workspace.Tile.t) view operation =
  Option.bind (current_project session) ~f:(fun project ->
    Artifact_view.capture
      view
      ~instance_id:session.hello.instance_id
      ~project:project.id
      operation
    |> Option.map ~f:(fun ticket -> tile.id, ticket))
;;

let asic_request ?artifact_request ?inspection_request ?plan_request session operation =
  match current_project session with
  | None -> return ()
  | Some project ->
    let instance_id = session.hello.instance_id in
    let client = session.client in
    let artifact_identity =
      Option.map artifact_request ~f:(fun (id, _) ->
        (Host.local session.host id).identity)
    in
    let inspection_identity =
      Option.map inspection_request ~f:(fun (id, _) ->
        (Host.local session.host id).identity)
    in
    session.asic_request_id <- session.asic_request_id + 1;
    let request_id = session.asic_request_id in
    let scope = plan_scope session project in
    let planned_run = Planned_run.reset session.host.planned_run ~scope in
    let planned_run, plan_ticket =
      match operation with
      | Asic.Operation.Plan _ when Option.is_some plan_request ->
        planned_run, plan_request
      | Asic.Operation.Plan selection ->
        let planned_run, ticket = Planned_run.begin_plan planned_run selection in
        planned_run, Some ticket
      | _ -> planned_run, None
    in
    let planned_run, launch_ticket =
      match operation with
      | Asic.Operation.Run { key; preview } ->
        let planned_run, ticket = Planned_run.begin_launch planned_run ~key preview in
        planned_run, Some ticket
      | _ -> planned_run, None
    in
    session.host <- { session.host with planned_run };
    let%map response =
      request session.diagnostics_file (fun () ->
        Http.Client.asic client { instance_id; project = project.id; operation })
    in
    let current =
      phys_equal client session.client
      && V1.Daemon_instance_id.equal instance_id session.hello.instance_id
      && Option.value_map (current_project session) ~default:false ~f:(fun p ->
        Project_id.equal p.id project.id)
    in
    let plan_current =
      Option.value_map plan_ticket ~default:true ~f:(fun ticket ->
        Planned_run.current_ticket session.host.planned_run ticket)
    in
    if current
    then
      Option.iter launch_ticket ~f:(fun ticket ->
        session.host
        <- { session.host with
             planned_run =
               Planned_run.launch_receipt
                 session.host.planned_run
                 ticket
                 ~floor:(session.asic_request_id + 1)
                 (Result.map response ~f:(fun _ -> ()))
           });
    if current
    then
      Option.iter plan_ticket ~f:(fun ticket ->
        (* IDs order request issuance, not daemon snapshot capture. A higher-ID Get can
           still have read the old same-selection completed task before Plan reached the
           daemon. Require a request issued after the receipt. *)
        let floor = session.asic_request_id + 1 in
        session.host
        <- { session.host with
             planned_run =
               Planned_run.receipt
                 session.host.planned_run
                 ticket
                 ~floor
                 (Result.map response ~f:(fun _ -> ()))
           });
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
    (* Artifact receipts belong to a tile-local intention, not the newest Get request. A
       later poll must not suppress a matching transport failure or acknowledge a
       different retry/reopened inspector. *)
    if current
    then
      Option.iter artifact_request ~f:(fun (tile_id, ticket) ->
        reconcile_synthesis session;
        let local = Host.local session.host tile_id in
        if Option.exists artifact_identity ~f:(phys_equal local.identity)
        then
          Option.iter local.artifacts ~f:(fun view ->
            let artifacts =
              Artifact_view.apply_response
                view
                ticket
                ~instance_id:session.hello.instance_id
                ~project:project.id
                (Result.map response ~f:(fun _ -> ()))
            in
            session.host
            <- Host.set_local
                 session.host
                 tile_id
                 { local with artifacts = Some artifacts }));
    if current
    then
      Option.iter inspection_request ~f:(fun (tile_id, ticket) ->
        reconcile_synthesis session;
        if Option.exists
             inspection_identity
             ~f:(phys_equal (Host.local session.host tile_id).identity)
        then
          Option.iter (Host.inspection session.host tile_id) ~f:(fun view ->
            let inspection =
              Inspection_view.apply_response
                view
                ticket
                (Result.map response ~f:(fun _ -> ()))
            in
            session.host <- Host.set_inspection session.host tile_id (Some inspection)));
    if request_id >= session.asic_applied_id && current
    then (
      match response with
      | Error message ->
        if Option.is_none artifact_request && plan_current
        then session.host <- { session.host with notice = "ASIC: " ^ message }
      | Ok snapshot ->
        session.asic_applied_id <- request_id;
        session.asic <- Some snapshot;
        session.host
        <- { session.host with
             planned_run =
               Planned_run.receive session.host.planned_run ~revision:request_id snapshot
           };
        reconcile_synthesis session);
    if current && Option.is_some artifact_request then reconcile_synthesis session
;;

let artifact_export_notice session tile_id message =
  let message = Artifact_view.safe message in
  session.host <- { session.host with notice = message };
  let local = Host.local session.host tile_id in
  Option.iter local.artifacts ~f:(fun view ->
    session.host
    <- Host.set_local
         session.host
         tile_id
         { local with artifacts = Some { view with external_notice = Some message } });
  append_diagnostic session.diagnostics_file message
;;

let export_artifact_text session tile_id ~viewer (reference : Asic_artifact.Reference.t) =
  let target =
    Host_view.run_label reference.run ^ " / " ^ Artifact_view.safe reference.label
  in
  let notice message =
    artifact_export_notice session tile_id (message ^ " — " ^ target)
  in
  if session.artifact_export_busy
  then (
    notice "Another external text export is in progress";
    return ())
  else (
    match current_project session with
    | None ->
      notice "Export requires an open project";
      return ()
    | Some project ->
      session.artifact_export_busy <- true;
      let client = session.client in
      let instance_id = session.hello.instance_id in
      let project_id = project.id in
      notice "Exporting sanitized text (≤16 MiB, ≤120 seconds)";
      Monitor.protect
        ~finally:(fun () ->
          session.artifact_export_busy <- false;
          return ())
        (fun () ->
          let call operation =
            let%map response =
              request session.diagnostics_file (fun () ->
                Http.Client.asic client { instance_id; project = project_id; operation })
            in
            Result.map_error response ~f:Error.of_string
          in
          let fetch ~(reference : Asic_artifact.Reference.t) ~offset ~limit ~check =
            let key =
              Asic_artifact.read_key
                ~run:reference.run
                ~artifact_id:reference.id
                ~offset
                ~limit
            in
            let rec poll remaining response =
              check ();
              let owner_current =
                V1.Daemon_instance_id.equal instance_id session.hello.instance_id
                && Option.value_map (current_project session) ~default:false ~f:(fun p ->
                  Project_id.equal p.id project_id)
              in
              if not owner_current
              then return (Or_error.error_string "Export daemon/project changed")
              else (
                match response with
                | Error error -> return (Error error)
                | Ok (snapshot : Asic.Snapshot.t) ->
                  if not
                       (List.exists
                          snapshot.artifacts
                          ~f:(Artifact_export.same_reference reference))
                  then
                    return
                      (Or_error.error_string
                         "Export artifact reference changed or expired")
                  else (
                    match Plain_rpc.progress ~wait:true [ key ] snapshot with
                    | Failed error -> return (Or_error.error_string error)
                    | Complete ->
                      return
                        (List.find snapshot.artifact_pages ~f:(fun page ->
                           Run_ref.equal page.run reference.run
                           && String.equal page.artifact_id reference.id
                           && String.equal
                                page.terminal_attempt
                                reference.terminal_attempt
                           && String.equal page.sha256 reference.sha256
                           && page.offset = offset
                           && page.limit = limit)
                         |> Or_error.of_option
                              ~error:
                                (Error.of_string
                                   "Export page expired or identity changed; retry \
                                    explicitly"))
                    | Pending ->
                      if remaining = 0
                      then
                        return
                          (Or_error.error_string
                             "Export read observation budget exhausted")
                      else (
                        let%bind () = Clock.after (Time_float.Span.of_ms 100.) in
                        check ();
                        let%bind response = call Get in
                        poll (remaining - 1) response)))
            in
            check ();
            let%bind response =
              call
                (Read_artifact
                   { run = reference.run; artifact_id = reference.id; offset; limit })
            in
            poll 1200 response
          in
          let publish payload =
            let%map result = Artifact_export.publish_private payload in
            Result.iter result ~f:(fun path ->
              notice
                ("Sanitized text saved: " ^ path ^ " (retained; metadata.sexp alongside)"));
            result
          in
          let%map result =
            Artifact_export.run
              ~viewer
              ~reference
              ~fetch
              ~publish
              ~launch:Artifact_export.launch_viewer
          in
          match result with
          | Ok path ->
            notice ("Sanitized text: " ^ path ^ " (retained; metadata.sexp alongside)")
          | Error error ->
            notice
              ("External text export failed: "
               ^ Artifact_view.safe (Error.to_string_hum error))))
;;

let export_artifact_binary session tile_id ~viewer (reference : Asic_artifact.Reference.t)
  =
  let notice = artifact_export_notice session tile_id in
  if session.artifact_export_busy
  then (
    notice "Another artifact export is in progress";
    return ())
  else (
    match current_project session with
    | None ->
      notice "Binary export requires an open project";
      return ()
    | Some project ->
      session.artifact_export_busy <- true;
      let instance_id = session.hello.instance_id in
      let client = session.client in
      let owner_current () =
        V1.Daemon_instance_id.equal instance_id session.hello.instance_id
        && Option.value_map (current_project session) ~default:false ~f:(fun p ->
          Project_id.equal p.id project.id)
      in
      Monitor.protect
        ~finally:(fun () ->
          session.artifact_export_busy <- false;
          return ())
        (fun () ->
          let call operation =
            let%map result =
              request session.diagnostics_file (fun () ->
                Http.Client.asic client { instance_id; project = project.id; operation })
            in
            Result.map_error result ~f:Error.of_string
          in
          let fetch ~(reference : Asic_artifact.Reference.t) ~offset ~limit ~check =
            let key =
              Asic_artifact.byte_read_key
                ~run:reference.run
                ~artifact_id:reference.id
                ~offset
                ~limit
            in
            let rec poll remaining response =
              check ();
              if not (owner_current ())
              then return (Or_error.error_string "Binary export owner changed")
              else (
                match response with
                | Error e -> return (Error e)
                | Ok (snapshot : Asic.Snapshot.t) ->
                  if not
                       (List.exists
                          snapshot.artifacts
                          ~f:(Artifact_export.same_reference reference))
                  then
                    return
                      (Or_error.error_string "Binary export reference changed or expired")
                  else (
                    match Plain_rpc.progress ~wait:true [ key ] snapshot with
                    | Failed e -> return (Or_error.error_string e)
                    | Complete ->
                      return
                        (List.find snapshot.artifact_byte_pages ~f:(fun p ->
                           Run_ref.equal p.run reference.run
                           && String.equal p.artifact_id reference.id
                           && String.equal p.terminal_attempt reference.terminal_attempt
                           && String.equal p.sha256 reference.sha256
                           && p.offset = offset
                           && p.limit = limit)
                         |> Or_error.of_option
                              ~error:
                                (Error.of_string
                                   "Exact binary page expired; retry explicitly"))
                    | Pending ->
                      if remaining = 0
                      then
                        return
                          (Or_error.error_string
                             "Binary page observation budget exhausted")
                      else (
                        let%bind () = Clock.after (Time_float.Span.of_ms 100.) in
                        check ();
                        let%bind response = call Get in
                        poll (remaining - 1) response)))
            in
            check ();
            let%bind response =
              call
                (Read_artifact_bytes
                   { run = reference.run; artifact_id = reference.id; offset; limit })
            in
            poll 1200 response
          in
          notice "Exporting exact binary (≤16 MiB); verifying SHA256 before launch";
          let%map result =
            Artifact_binary_export.run
              ~viewer
              ~reference
              ~fetch
              ~publish:Artifact_binary_export.publish_private
              ~launch:(fun ~prog ~args ->
                if owner_current ()
                then Artifact_export.launch_viewer ~prog ~args
                else
                  return
                    (Or_error.error_string "Binary export owner changed before launch"))
          in
          match result with
          | Ok path ->
            notice ("Verified binary retained: " ^ path ^ " (metadata.sexp alongside)")
          | Error e -> notice ("Binary export failed: " ^ Error.to_string_hum e)))
;;

let add_default_tiles session (registry : Workspace.Snapshot.t) workspace =
  ignore (registry : Workspace.Snapshot.t);
  match Host.definition workspace with
  | None -> return ()
  | Some definition ->
    mutate_workspace
      session
      (Hardcaml_workbench_workspaces.Definition.apply definition ~workspace:workspace.id)
;;

let initialize_host_layout session =
  match session.host.registry with
  | Some registry when not registry.defaults_initialized ->
    workspace_request session Hardcaml_workbench_workspaces.Presets.bootstrap
  | _ -> return ()
;;

let simulation_request session tile_id operation =
  match current_project session with
  | None -> return ()
  | Some project ->
    let instance_id = session.hello.instance_id in
    let local = Host.local session.host tile_id in
    let client = session.client in
    let view = Simulation_view.begin_request local.simulation in
    session.host <- Host.set_local session.host tile_id { local with simulation = view };
    let%bind response =
      request session.diagnostics_file (fun () ->
        Http.Client.simulation client { instance_id; project = project.id; operation })
    in
    if phys_equal client session.client
       && phys_equal local.identity (Host.local session.host tile_id).identity
       && V1.Daemon_instance_id.equal instance_id session.hello.instance_id
       && Option.value_map (current_project session) ~default:false ~f:(fun p ->
         Project_id.equal p.id project.id)
    then (
      let local = Host.local session.host tile_id in
      let simulation =
        Simulation_view.receive
          local.simulation
          ~ticket:view.request
          ~selected:view.attempt
          operation
          response
      in
      session.host <- Host.set_local session.host tile_id { local with simulation };
      match Simulation_view.detail simulation with
      | Some d when simulation.logs ->
        (match List.find (project_jobs session) ~f:(fun j -> Job_id.equal j.id d.job) with
         | Some job -> read_job_log session (Some job)
         | None ->
           (log_state session d.job).fetch
           <- Presentation.Log_fetch.Error
                "Job logs unavailable in this daemon; normalized historical results \
                 remain readable";
           return ())
      | _ -> return ())
    else return ()
;;

let refresh_simulation session =
  Host.tiles session.host
  |> List.filter ~f:(fun tile -> String.equal tile.kind "simulation")
  |> Deferred.List.iter ~how:`Sequential ~f:(fun tile ->
    let view = (Host.local session.host tile.id).simulation in
    match view.attempt with
    | _ when view.busy -> return ()
    | Some id -> simulation_request session tile.id (Observe id)
    | None when not view.older -> simulation_request session tile.id Get
    | None -> return ())
;;

let refresh_host session =
  let%bind () = load_preferences session in
  let%bind () = load_presentation_preferences session in
  let%bind () = workspace_request session Get in
  let%bind () = initialize_host_layout session in
  let%bind () = refresh_simulation session in
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
  (* Visible evidence and active runs share the same bounded read-intent scheduler. *)
  let runs =
    Host.evidence_runs session.host
    @ Option.value_map session.asic ~default:[] ~f:(fun snapshot ->
      List.filter_map snapshot.runs ~f:(fun run ->
        if Asic_intents.live_status run.status then Some run.run else None))
  in
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
    let project_changed =
      not
        (Option.equal
           Project_id.equal
           (Option.map session.opened ~f:(fun opened -> opened.project.id))
           (Option.map opened ~f:(fun opened -> opened.project.id)))
    in
    session.client <- client;
    session.hello <- hello;
    session.opened <- opened;
    session.snapshot <- snapshot;
    session.host
    <- Host.reconnect session.host ~replacement:(instance_changed || project_changed);
    (* The same project's authoritative evidence remains valid while the first new
       transport poll is pending; dropping it would reset stage/result browsing. *)
    if instance_changed || project_changed then session.asic <- None;
    if instance_changed || project_changed
    then (
      session.view_on_allocation <- None;
      session.asic_reads <- Asic_intents.empty);
    if instance_changed || project_changed
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
    let%bind response =
      request session.diagnostics_file (fun () ->
        Http.Client.refresh_integration
          session.client
          { instance_id = session.hello.instance_id; project = project.id })
    in
    (match response with
     | Error message ->
       session.status <- "integration refresh failed: " ^ message;
       return ()
     | Ok { job = None } ->
       let%map result = resync session ~instance_id:session.hello.instance_id in
       session.status
       <- (match result with
           | Ok () -> "integration manifest reloaded (no driver declared)"
           | Error message -> "integration refresh resync failed: " ^ message)
     | Ok { job = Some job } ->
       session.snapshot <- State.add_job_if_absent session.snapshot job;
       session.selected <- 0;
       session.status <- "integration refresh queued as " ^ Job_id.to_string job.id;
       return ())
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
      @ List.concat_map asic.finalizations ~f:Host_view.finalization_lines
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
  ; run_context = Host_view.request_context session.asic
  ; summary =
      (fun run ->
        Option.bind session.asic ~f:(fun asic ->
          List.find asic.summaries ~f:(fun summary ->
            Run_ref.equal summary.Asic.Summary.run run)))
  ; status = session.status
  ; environment = session.environment_label
  ; asic_lines
  ; asic = session.asic
  }
;;

let render session dimensions =
  let render_host () =
    session.last_dimensions <- Some dimensions;
    reconcile_synthesis session;
    let host =
      match session.presentation_preference_notice with
      | None -> session.host
      | Some notice ->
        { session.host with
          chrome = true
        ; notice =
            String.concat
              ~sep:" | "
              (List.filter [ notice; session.host.notice ] ~f:(Fn.non String.is_empty))
        }
    in
    Host_view.render host (host_data session) dimensions
  in
  match session.host.registry with
  | None
    when Option.is_some session.opened
         && List.mem session.hello.capabilities "workspace" ~equal:String.equal ->
    render_host ()
  | None -> render_legacy session dimensions
  | Some _
    when Option.is_some session.hierarchy_view
         || Option.is_some session.artifact_view
         || session.show_connection_details -> render_legacy session dimensions
  | Some _ -> render_host ()
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
    ; presentation_preferences_loaded = Some "fixture"
    ; presentation_preferences = None
    ; presentation_preference_notice = None
    ; preference_saves = Deferred.unit
    ; asic_reads = Asic_intents.empty
    ; remembered_acceptance = ""
    ; artifact_viewer = None
    ; artifact_binary_viewer = None
    ; artifact_export_busy = false
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
  @ (match Host.focused session.host with
     | Some tile when String.equal tile.kind "simulation" ->
       let v = (Host.local session.host tile.id).simulation in
       let cmd id title operation =
         Host.command
           ("simulation." ^ id)
           ("Simulation: " ^ title)
           "suite cases seed history"
           (Host.Simulation (tile.id, operation))
       in
       [ cmd "discover" "Discover suites explicitly" Discover
       ; cmd "history" "Newest history page" (History { before = None; limit = 25 })
       ]
       @ Option.value_map v.snapshot ~default:[] ~f:(fun s ->
         Option.value_map s.next_before ~default:[] ~f:(fun before ->
           [ cmd
               "older"
               "Older history page"
               (History { before = Some before; limit = 25 })
           ])
         @ List.map s.attempts ~f:(fun a ->
           cmd ("open." ^ a.id) ("Reopen " ^ a.id ^ " " ^ a.suite) (Observe a.id))
         @ Option.value_map s.discovery ~default:[] ~f:(fun d ->
           List.map d.suites ~f:(fun suite ->
             Host.command
               ("simulation.launch." ^ suite.id)
               ("Simulation: Launch form " ^ suite.label)
               "seed parameters cases"
               (Simulation_form
                  ( tile.id
                  , Option.value s.discovery_digest ~default:""
                  , suite
                  , submission_key "simulation" )))))
       @ Option.value_map (Simulation_view.detail v) ~default:[] ~f:(fun d ->
         [ cmd "cancel" ("Cancel " ^ d.id) (Cancel d.id)
         ; Host.command
             "simulation.logs"
             "Simulation: Toggle stream-labelled job logs"
             "stdout stderr"
             (Simulation_logs tile.id)
         ]
         @ List.map d.cases ~f:(fun c ->
           Host.command
             ("simulation.case." ^ c.case_id)
             ("Simulation: Select case " ^ c.case_id)
             "detail failure"
             (Simulation_case (tile.id, c.case_id)))
         @ (let failed =
              List.filter_map d.cases ~f:(fun c ->
                if Simulation.Case_status.equal c.status Failed
                then Some c.case_id
                else None)
            in
            if List.is_empty failed
            then []
            else
              [ cmd
                  "rerun-failed"
                  "Rerun all failed (original inputs; current project)"
                  (Rerun
                     { submission_key = submission_key "simulation-rerun"
                     ; attempt_id = d.id
                     ; cases = failed
                     })
              ])
         @ Option.value_map v.case_id ~default:[] ~f:(fun id ->
           [ cmd
               "rerun-case"
               ("Rerun case " ^ id ^ " (original inputs; current project)")
               (Rerun
                  { submission_key = submission_key "simulation-rerun"
                  ; attempt_id = d.id
                  ; cases = [ id ]
                  })
           ])
         @ List.concat_map d.artifacts ~f:(fun a ->
           [ Host.command
               ("simulation.export." ^ a.id)
               ("Simulation: Export exact bytes " ^ a.label)
               "trace waveform"
               (Simulation_export (a, false))
           ; Host.command
               ("simulation.viewer." ^ a.id)
               ("Simulation: Open external viewer " ^ a.label)
               "trace waveform"
               (Simulation_export (a, true))
           ]))
     | _ -> [])
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
  @ Host.launch_commands
      session.host
      ~preview:(Option.bind session.asic ~f:(fun asic -> asic.preview))
      ~view_pending:(Option.is_some session.view_on_allocation)
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
    @ Host.asic_cancel_commands asic
    @ List.map asic.finalizations ~f:(fun finalization ->
      Host.command
        ("asic.finalize-observe." ^ finalization.key)
        ("Reconnect finalization " ^ finalization.key ^ " (read-only)")
        "observe phase acceptance status"
        (Asic (Observe_finalization finalization.key)))
    @ List.concat_map asic.runs ~f:(fun run ->
      [ Host.command
          ("asic.refresh." ^ Host_view.run_label run.run)
          ("Refresh evidence " ^ Host_view.run_label run.run)
          "validate source"
          (Asic (Refresh run.run))
      ; Host.command
          ("asic.inspect-finalization." ^ Host_view.run_label run.run)
          ("Inspect finalization for "
           ^ Host_view.run_label run.run
           ^ " (enter exact attempt)")
          "import terminal results timing physical checks read-only"
          (Edit_finalization run.run)
      ; Host.command
          ("asic.artifacts." ^ Host_view.run_label run.run)
          ("Browse reports/artifacts " ^ Host_view.run_label run.run)
          "catalog report bounded text"
          (Browse_artifacts run.run)
      ]
      @ List.map Inspection_view.defaults ~f:(fun (domain, stage) ->
        Host.command
          ("asic.inspection." ^ domain ^ "." ^ Host_view.run_label run.run)
          ("Inspect "
           ^ (if String.equal domain "timing" then "timing paths" else domain)
           ^ " "
           ^ Host_view.run_label run.run
           ^ " · "
           ^ stage)
          "typed rows endpoints corner group producer"
          (Browse_inspection (run.run, domain, stage)))
      @ Option.value_map run.execution_file ~default:[] ~f:(fun execution_file ->
        [ Host.command
            ("asic.finalize." ^ Host_view.run_label run.run)
            ("Finalize (collect) " ^ Host_view.run_label run.run)
            "collect terminal reports"
            (Finalize_collect (run.run, execution_file))
        ; Host.command
            ("asic.finalize-accept." ^ Host_view.run_label run.run)
            ("Finalize and accept " ^ Host_view.run_label run.run)
            "explicit collateral testbench replay"
            (Edit_acceptance (run.run, execution_file))
        ])))
;;

let open_timing_workspace session ~(run : Run_ref.t) ~stage =
  let instance = session.hello.instance_id in
  let project = Option.map (current_project session) ~f:(fun p -> p.Project.id) in
  match session.host.registry, Host.active session.host with
  | Some initial, Some active ->
    let name = "Timing · captured " ^ run.id ^ " · " ^ submission_key "inspect" in
    let valid () =
      V1.Daemon_instance_id.equal instance session.hello.instance_id
      && Option.equal
           Project_id.equal
           project
           (Option.map (current_project session) ~f:(fun p -> p.Project.id))
      && Option.exists session.host.registry ~f:(fun s ->
        Workspace.Session_id.equal initial.session_id s.session_id)
    in
    let%bind workspace =
      match Host.matching_timing initial ~run with
      | Some workspace -> return (Some workspace.id)
      | None ->
        let%bind () =
          mutate_workspace
            session
            (Create_workspace { window = active.window; name; context = active.context })
        in
        if not (valid ())
        then return None
        else (
          match session.host.registry with
          | None -> return None
          | Some current ->
            (match
               List.find current.workspaces ~f:(fun w ->
                 String.equal w.name name
                 && not
                      (List.exists initial.workspaces ~f:(fun old ->
                         Workspace.Workspace_id.equal old.id w.id)))
             with
             | None -> return None
             | Some workspace ->
               let%bind () = mutate_workspace session (Make_independent workspace.id) in
               if not (valid ())
               then return None
               else (
                 match session.host.registry with
                 | None -> return None
                 | Some registry ->
                   if not
                        (List.exists registry.workspaces ~f:(fun current ->
                           Workspace.Workspace_id.equal current.id workspace.id))
                   then return None
                   else (
                     let workspace = Workspace.workspace registry workspace.id in
                     let context = Workspace.context registry workspace.context in
                     (* Never select through a shared context if independence was
                        rejected. *)
                     if Workspace.Context_id.equal context.id registry.main_context
                        || List.exists initial.contexts ~f:(fun old ->
                          Workspace.Context_id.equal old.id context.id)
                        || List.count registry.workspaces ~f:(fun w ->
                             Workspace.Context_id.equal w.context context.id)
                           <> 1
                     then return None
                     else (
                       let%map () =
                         mutate_workspace
                           session
                           (Select_run
                              { workspace = workspace.id
                              ; context = context.id
                              ; expected_selection_revision = context.selection_revision
                              ; run = Some run
                              })
                       in
                       Some workspace.id)))))
    in
    (match workspace with
     | None -> return ()
     | Some workspace when valid () ->
       let%bind () =
         mutate_workspace
           session
           (Hardcaml_workbench_workspaces.Definition.apply
              Hardcaml_workbench_workspaces.Timing.definition
              ~workspace)
       in
       if not (valid ())
       then return ()
       else (
         match session.host.registry with
         | None -> return ()
         | Some registry ->
           (match Host.matching_timing ~workspace registry ~run with
            | Some matching when Workspace.Workspace_id.equal matching.id workspace ->
              (match
                 List.find registry.tiles ~f:(fun tile ->
                   Workspace.Workspace_id.equal tile.workspace workspace
                   && String.equal tile.kind "timing-paths"
                   && Option.value_map
                        matching.zoomed_tile
                        ~default:true
                        ~f:(Workspace.Tile_id.equal tile.id)
                   && not tile.hidden)
               with
               | None -> return ()
               | Some tile ->
                 let generation =
                   List.Assoc.find
                     session.host.timing
                     (Workspace.Workspace_id.to_string workspace)
                     ~equal:String.equal
                   |> Option.value_map ~default:1 ~f:(fun view ->
                     view.Inspection_view.generation + 1)
                 in
                 let view =
                   Host.timing session.host tile
                   |> Option.filter ~f:(fun view ->
                     String.equal view.stage stage && Run_ref.equal view.run run)
                   |> Option.value
                        ~default:(Timing_workspace.create ~generation ~run ~stage)
                 in
                 let view =
                   { view with
                     Inspection_view.workspace_epoch =
                       Some (Host.timing_epoch registry workspace)
                   }
                 in
                 let view =
                   Option.value_map
                     session.asic
                     ~default:view
                     ~f:(Inspection_view.reconcile view)
                 in
                 session.host
                 <- Host.set_timing (Host.switch session.host workspace) tile view;
                 session.host
                 <- Host.set_local
                      session.host
                      tile.id
                      { (Host.local session.host tile.id) with
                        artifacts = None
                      ; inspection = None
                      };
                 session.host
                 <- { session.host with
                      focus = Some tile.id
                    ; notice = "Timing investigation · captured run " ^ run.id
                    };
                 (* Already-loaded observations are sufficient; opening does not
                    re-extract. *)
                 if Option.is_some view.index
                 then return ()
                 else (
                   let operation = Inspection_view.operation view in
                   asic_request
                     ~inspection_request:(tile.id, Inspection_view.capture view operation)
                     session
                     operation))
            | _ -> return ()))
     | Some _ -> return ())
  | _ -> return ()
;;

let execute_host session captured action ~exit =
  let open Bonsai_term in
  let captured_client = session.client in
  let captured_project = Option.map (current_project session) ~f:(fun p -> p.id) in
  let async ?(on_rejected = ignore) f =
    Effect.of_deferred_thunk (fun () ->
      if Host.current session.host captured
         && phys_equal captured_client session.client
         && Option.equal
              Project_id.equal
              captured_project
              (Option.map (current_project session) ~f:(fun p -> p.id))
      then f ()
      else (
        on_rejected ();
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
    | Host.Simulation (tile, operation) ->
      let local = Host.local session.host tile in
      (match operation with
       | Observe id ->
         session.host
         <- Host.set_local
              session.host
              tile
              { local with
                simulation = Simulation_view.select local.simulation id
              ; scroll = 0
              }
       | _ -> ());
      async (fun () -> simulation_request session tile operation)
    | Simulation_case (tile, case_id) ->
      let local = Host.local session.host tile in
      session.host
      <- Host.set_local
           session.host
           tile
           { local with
             simulation = { local.simulation with case_id = Some case_id }
           ; scroll = 0
           };
      Effect.Ignore
    | Simulation_logs tile ->
      let local = Host.local session.host tile in
      session.host
      <- Host.set_local
           session.host
           tile
           { local with
             simulation = { local.simulation with logs = not local.simulation.logs }
           };
      Effect.Ignore
    | Simulation_form (tile, digest, suite, key) ->
      let form = Simulation_view.Form.create suite in
      session.host
      <- { session.host with
           palette =
             Some
               { capture = captured
               ; commands = []
               ; query = Simulation_view.Form.query form
               ; index = 0
               ; argument = Some (Simulation_selection (tile, digest, key, form))
               }
         };
      Effect.Ignore
    | Simulation_edit (tile, digest, key, form) ->
      session.host
      <- { session.host with
           notice = ""
         ; palette =
             Some
               { capture = captured
               ; commands = []
               ; query = Simulation_view.Form.query form
               ; index = 0
               ; argument = Some (Simulation_selection (tile, digest, key, form))
               }
         };
      Effect.Ignore
    | Simulation_export (artifact, open_viewer) ->
      let tile = Option.map (Host.focused session.host) ~f:(fun t -> t.id) in
      let notice message =
        let message =
          Artifact_view.safe
            (sprintf "Simulation %s / %s: %s" artifact.attempt_id artifact.id message)
        in
        session.host <- { session.host with notice = message };
        Option.iter tile ~f:(fun id ->
          let local = Host.local session.host id in
          session.host
          <- Host.set_local
               session.host
               id
               { local with simulation = { local.simulation with notice = Some message } })
      in
      async (fun () ->
        if session.artifact_export_busy
        then (
          notice "Another artifact export is in progress";
          return ())
        else (
          session.artifact_export_busy <- true;
          Monitor.protect
            ~finally:(fun () ->
              session.artifact_export_busy <- false;
              return ())
            (fun () ->
              match current_project session with
              | None -> return ()
              | Some project ->
                let instance_id = session.hello.instance_id in
                let client = session.client in
                let current () =
                  phys_equal client session.client
                  && V1.Daemon_instance_id.equal instance_id session.hello.instance_id
                  && Option.value_map
                       (current_project session)
                       ~default:false
                       ~f:(fun p -> Project_id.equal p.id project.id)
                in
                let viewer =
                  if open_viewer then session.artifact_binary_viewer else None
                in
                if open_viewer && Option.is_none viewer
                then (
                  notice
                    "Configure --simulation-viewer /absolute/viewer for simulation traces";
                  return ())
                else (
                  notice
                    "Exporting simulation bytes (<=64 MiB); verifying identity and SHA256";
                  let%map result =
                    Simulation_export.run
                      ~artifact
                      ~current
                      ~viewer
                      ~fetch:(fun ~offset ~limit ->
                        let%map r =
                          request session.diagnostics_file (fun () ->
                            Http.Client.simulation
                              client
                              { instance_id
                              ; project = project.id
                              ; operation =
                                  Read_artifact_bytes
                                    { attempt_id = artifact.attempt_id
                                    ; artifact_id = artifact.id
                                    ; sha256 = Option.value artifact.sha256 ~default:""
                                    ; offset
                                    ; limit
                                    }
                              })
                        in
                        match r with
                        | Error e -> Or_error.error_string e
                        | Ok s ->
                          Or_error.of_option
                            s.byte_page
                            ~error:(Error.of_string "Missing simulation byte page"))
                      ~publish:Simulation_export.publish_private
                      ~launch:Artifact_export.launch_viewer
                  in
                  notice
                    (match result with
                     | Ok path -> "Verified simulation bytes retained: " ^ path
                     | Error e -> "Simulation export: " ^ Error.to_string_hum e)))))
    | Host.Registry mutation -> async (fun () -> mutate_workspace session mutation)
    | Switch id ->
      session.host <- Host.switch session.host id;
      Effect.Ignore
    | Create_testing_workspace ->
      async (fun () ->
        match session.host.registry, Host.active session.host with
        | Some registry, Some active
          when not
                 (List.exists registry.workspaces ~f:(fun w ->
                    Option.equal String.equal w.preset (Some "testing"))) ->
          let%bind () =
            mutate_workspace
              session
              (Create_workspace
                 { window = active.window
                 ; name = "Testing"
                 ; context = registry.main_context
                 })
          in
          (match session.host.registry with
           | Some current
             when Workspace.Session_id.equal current.session_id registry.session_id ->
             (match
                List.find current.workspaces ~f:(fun w ->
                  String.equal w.name "Testing"
                  && not
                       (List.exists registry.workspaces ~f:(fun old ->
                          Workspace.Workspace_id.equal old.id w.id)))
              with
              | None -> return ()
              | Some workspace ->
                let%map () =
                  mutate_workspace
                    session
                    (Hardcaml_workbench_workspaces.Definition.apply
                       Hardcaml_workbench_workspaces.Testing.definition
                       ~workspace:workspace.id)
                in
                session.host <- Host.switch session.host workspace.id)
           | _ -> return ())
        | _ -> return ())
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
    | Prepare_stage (stage, run) ->
      let remembered = session.remembered_selection in
      let observed =
        Option.bind session.asic ~f:(fun snapshot ->
          List.find snapshot.runs ~f:(fun execution -> Run_ref.equal execution.run run)
          |> Option.bind ~f:(fun execution -> execution.selection))
      in
      let generation = session.host.stage_generation + 1 in
      let instance = session.hello.instance_id in
      let message =
        "Preparing NEW run through "
        ^ stage.id
        ^ "; discovering capabilities if needed; reopen palette when ready"
      in
      session.host
      <- { session.host with
           stage_generation = generation
         ; stage_preparation = Some message
         ; notice = message
         };
      let current () =
        Host.current session.host captured
        && phys_equal captured_client session.client
        && V1.Daemon_instance_id.equal instance session.hello.instance_id
        && Option.equal
             Project_id.equal
             captured_project
             (Option.map (current_project session) ~f:(fun p -> p.id))
        && generation = session.host.stage_generation
      in
      let fail reason =
        if generation = session.host.stage_generation
        then
          session.host
          <- { session.host with stage_preparation = Some reason; notice = reason }
      in
      async
        ~on_rejected:(fun () -> fail "Stage preparation target changed; press r again")
        (fun () ->
          let missing () =
            Option.value_map session.asic ~default:true ~f:(fun snapshot ->
              let flow =
                match Option.first_some remembered observed with
                | Some selection -> Some selection.Asic.Selection.flow
                | None -> Option.map snapshot.catalog_default ~f:(fun pair -> pair.flow)
              in
              not
                (List.exists snapshot.flows ~f:(fun candidate ->
                   Option.equal String.equal flow (Some candidate.id)
                   && List.mem
                        candidate.fresh_stage_endpoints
                        stage.id
                        ~equal:String.equal)))
          in
          let rec discover remaining =
            if (not (current ())) || remaining = 0
            then return ()
            else if (not (missing ()))
                    && not
                         (Option.exists session.asic ~f:(fun snapshot ->
                            List.exists snapshot.operations ~f:(fun op ->
                              String.equal op.kind "discover" && Plain_rpc.active op)))
            then return ()
            else (
              let%bind () = Clock.after (Time_float.Span.of_ms 100.) in
              if not (current ())
              then return ()
              else (
                let%bind () = asic_request session Get in
                discover (remaining - 1)))
          in
          let%bind () =
            if Option.is_none stage.action && missing ()
            then (
              let%bind () = asic_request session Discover in
              discover 50)
            else return ()
          in
          if not (current ())
          then (
            fail "Stage preparation superseded or context changed; press r again";
            return ())
          else (
            match
              Stage_action.resolve ~stage ~remembered ~observed ~snapshot:session.asic
            with
            | Error reason ->
              fail ("Stage preparation failed: " ^ reason ^ "; press r to retry");
              return ()
            | Ok selection ->
              let planned_run, ticket =
                Planned_run.begin_plan session.host.planned_run selection
              in
              session.host
              <- { session.host with
                   planned_run
                 ; stage_preparation = None
                 ; remembered_selection = Some selection
                 ; notice =
                     "Planning NEW run; Space c c: Launch when ready (reopen palette)"
                 };
              let response = asic_request ~plan_request:ticket session (Plan selection) in
              let%bind () = save_preferences session selection in
              response))
    | Unavailable_launch ->
      session.host
      <- { session.host with
           notice =
             "Captured launch was unavailable; reopen palette to capture the ready \
              preview"
         };
      Effect.Ignore
    | Asic (Plan selection as operation) ->
      (match current_project session with
       | None -> Effect.Ignore
       | Some project ->
         (* Fence at command acceptance, before effect dispatch or preference I/O can
            yield to a poll, a newer Plan, or Launch. *)
         let planned_run =
           Planned_run.reset session.host.planned_run ~scope:(plan_scope session project)
         in
         let planned_run, ticket = Planned_run.begin_plan planned_run selection in
         session.host
         <- { session.host with
              planned_run
            ; stage_preparation = None
            ; stage_generation = session.host.stage_generation + 1
            };
         async
           ~on_rejected:(fun () ->
             session.host
             <- { session.host with
                  planned_run =
                    Planned_run.receipt
                      session.host.planned_run
                      ticket
                      ~floor:Int.max_value
                      (Error "Command target changed before Plan dispatch")
                })
           (fun () ->
             if not (Planned_run.current_ticket session.host.planned_run ticket)
             then return ()
             else (
               let response = asic_request ~plan_request:ticket session operation in
               let%bind () = save_preferences session selection in
               response)))
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
    | Asic (Finalize { acceptance = Some acceptance; _ } as operation) ->
      session.remembered_acceptance
      <- Sexp.to_string_mach (Asic.Acceptance.sexp_of_t acceptance);
      async (fun () -> asic_request session operation)
    | Asic operation -> async (fun () -> asic_request session operation)
    | Finalize_collect (run, execution_file) ->
      async (fun () ->
        let key = submission_key "finalize" in
        asic_request session (Finalize { key; run; execution_file; acceptance = None }))
    | Browse_artifacts run ->
      (match Host.focused session.host, session.host.registry with
       | Some tile, Some registry ->
         let scope =
           Workspace.resolve_tile registry tile.id
           |> Result.ok
           |> Option.bind ~f:(fun r -> r.run)
         in
         let local = Host.local session.host tile.id in
         let generation = local.artifact_generation + 1 in
         let view =
           Artifact_view.create
             ?scope
             ~generation
             ~viewer_configured:(Option.is_some session.artifact_viewer)
             ~binary_viewer_configured:(Option.is_some session.artifact_binary_viewer)
             run
         in
         let operation = Asic.Operation.List_artifacts run in
         let artifact_request = capture_artifact_request session tile view operation in
         session.host
         <- Host.set_local
              session.host
              tile.id
              { local with
                artifacts = Some view
              ; inspection = None
              ; artifact_generation = generation
              };
         async (fun () -> asic_request ?artifact_request session operation)
       | _ -> Effect.Ignore)
    | Browse_inspection (run, "timing", stage) ->
      async (fun () -> open_timing_workspace session ~run ~stage)
    | Browse_inspection (run, domain, stage) ->
      (match Host.focused session.host, session.host.registry with
       | Some tile, Some registry ->
         let scope =
           Workspace.resolve_tile registry tile.id
           |> Result.ok
           |> Option.bind ~f:(fun r -> r.run)
         in
         let local = Host.local session.host tile.id in
         let generation = local.inspection_generation + 1 in
         let view = Inspection_view.create ?scope ~generation ~run ~domain ~stage () in
         session.host
         <- Host.set_local
              session.host
              tile.id
              { local with
                inspection = Some view
              ; inspection_generation = generation
              ; artifacts = None
              };
         let operation = Inspection_view.operation view in
         let inspection_request = tile.id, Inspection_view.capture view operation in
         async (fun () -> asic_request ~inspection_request session operation)
       | _ -> Effect.Ignore)
    | Edit_acceptance (run, execution_file) ->
      let key = submission_key "finalize-accept" in
      session.host
      <- { session.host with
           palette =
             Some
               { capture = captured
               ; commands = []
               ; query = session.remembered_acceptance
               ; index = 0
               ; argument = Some (Host.Acceptance (run, execution_file, key))
               }
         ; notice =
             "Explicit collateral required; Enter finalizes and accepts the captured \
              execution"
         };
      Effect.Ignore
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
               ; argument = Some (Host.Plan_endpoint (flow, profile))
               }
         ; notice =
             "Enter ENDPOINT [name=value ...]; Describe flow lists capabilities. No \
              fallback."
         };
      Effect.Ignore
    | Edit_finalization run ->
      session.host
      <- { session.host with
           palette =
             Some
               { capture = captured
               ; commands = []
               ; query = ""
               ; index = 0
               ; argument = Some (Host.Finalization_attempt run)
               }
         ; notice =
             "Enter the exact returned finalization operation attempt; no reference is \
              guessed"
         };
      Effect.Ignore
    | Launch_asic (preview, view) ->
      let ready () =
        Option.is_none session.host.stage_preparation
        && Planned_run.launchable session.host.planned_run preview
        && Option.value_map session.asic ~default:false ~f:(fun asic ->
          Option.equal Asic.Preview.equal asic.preview (Some preview))
      in
      let invalidated () =
        session.host
        <- { session.host with
             notice =
               "ASIC preview unavailable or launch unresolved; inspect plan/launch state \
                before retrying explicitly"
           }
      in
      if not (ready ())
      then (
        invalidated ();
        Effect.Ignore)
      else (
        let key = submission_key "asic-run" in
        async (fun () ->
          if not (ready ())
          then (
            invalidated ();
            return ())
          else if view && Option.is_some session.view_on_allocation
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
    | Set_presentation (id, presentation) ->
      let host, save = Host.set_presentation session.host id presentation in
      session.host <- host;
      session.host
      <- { session.host with
           notice = "Presentation override: headers retained; reset inherits defaults"
         };
      if save
      then Effect.of_deferred_thunk (fun () -> save_presentation_preferences session)
      else Effect.Ignore
    | Local_headers | Resume_log ->
      Option.iter session.host.focus ~f:(fun id ->
        let local = Host.local session.host id in
        let local =
          match action with
          | Local_headers ->
            let tile = Option.value_exn (Host.focused session.host) in
            { local with
              presentation =
                { local.presentation with
                  header = Some (not (Host.policy session.host tile).header)
                }
            }
          | _ -> { local with follow = true; scroll = 0 }
        in
        session.host <- Host.set_local session.host id local);
      (match action with
       | Local_headers ->
         Effect.of_deferred_thunk (fun () -> save_presentation_preferences session)
       | _ -> Effect.Ignore)
    | Toggle_chrome ->
      session.host <- { session.host with chrome = not session.host.chrome };
      Effect.of_deferred_thunk (fun () -> save_presentation_preferences session)
    | Set_appearance appearance ->
      session.host <- Host.set_appearance session.host appearance;
      Effect.of_deferred_thunk (fun () -> save_presentation_preferences session)
    | Set_layout_mode layout_mode ->
      session.host <- { session.host with layout_mode };
      Effect.of_deferred_thunk (fun () -> save_presentation_preferences session)
    | Synthesis_mode mode ->
      change_synthesis session (fun _ local ->
        { local with synthesis = Synthesis_view.State.set_mode local.synthesis mode });
      Effect.Ignore
    | Synthesis_sort sort ->
      change_synthesis session (fun _ local ->
        { local with synthesis = Synthesis_view.State.set_sort local.synthesis sort });
      Effect.Ignore
    | Synthesis_cycle_sort ->
      change_synthesis session (fun _ local ->
        { local with synthesis = Synthesis_view.State.cycle_sort local.synthesis });
      Effect.Ignore
    | Synthesis_clear_filter ->
      change_synthesis session (fun _ local -> { local with filter = "" });
      reconcile_synthesis session;
      Effect.Ignore
    | Exit -> exit ())
;;

let scroll_host session delta =
  reconcile_synthesis session;
  match Host.focused session.host with
  | Some tile when String.equal tile.kind "planned-run" ->
    let local = Host.local session.host tile.id in
    Option.iter session.last_dimensions ~f:(fun dimensions ->
      let _, _, layout = Host_view.tile_layout session.host dimensions in
      Option.iter
        (List.find layout ~f:(fun (t, _) -> Workspace.Tile_id.equal t.id tile.id))
        ~f:(fun (_, geometry) ->
          let _, _, _, width, height =
            Host_view.body_geometry
              session.host
              tile
              ~width:geometry.width
              ~height:geometry.height
          in
          let count =
            Host_view.rows
              (Host.set_local session.host tile.id { local with scroll = 0 })
              (host_data session)
              tile
              ~width
              ~height
            |> List.length
          in
          let bound = Int.max 0 (count - height) in
          let scroll =
            Int64.(max zero (min (of_int bound) (of_int local.scroll + of_int delta)))
            |> Int64.to_int_exn
          in
          session.host <- Host.set_local session.host tile.id { local with scroll }))
  | _ ->
    Option.iter session.last_dimensions ~f:(fun dimensions ->
      session.host
      <- Host_view.scroll_focused session.host (host_data session) dimensions ~delta)
;;

let browse_host session delta =
  let checklist =
    Option.filter (Host.focused session.host) ~f:(fun tile ->
      String.equal tile.kind "stage-checklist")
  in
  (match checklist with
   | Some tile when not (Host.local session.host tile.id).utility_detail ->
     Option.iter session.host.registry ~f:(fun registry ->
       Workspace.resolve_tile registry tile.id
       |> Result.ok
       |> Option.bind ~f:(fun reference -> reference.run)
       |> Option.iter ~f:(fun run ->
         let stages =
           Terminal_presentation.Overview_tiles.observed_stages ~asic:session.asic ~run
         in
         session.host <- Host.browse_stages session.host tile.id ~run ~stages ~delta))
   | _ -> scroll_host session delta);
  change_synthesis session (fun tile local ->
    let synthesis =
      match Synthesis_view.State.mode local.synthesis with
      | Details | Metrics | Evidence -> local.synthesis
      | Summary | Cells ->
        Synthesis_view.State.move
          local.synthesis
          ~summary:(synthesis_summary session tile)
          ~filter:local.filter
          ~delta
        |> fun state -> Synthesis_view.State.set_mode state Cells
    in
    { local with synthesis });
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
    let visible =
      Option.bind session.last_dimensions ~f:(fun dimensions ->
        let _, _, layout = Host_view.tile_layout session.host dimensions in
        List.find layout ~f:(fun (t, _) -> Workspace.Tile_id.equal t.id tile.id)
        |> Option.map ~f:(fun (_, g) ->
          let _, _, _, _, height =
            Host_view.body_geometry session.host tile ~width:g.width ~height:g.height
          in
          if String.equal tile.kind "run-selector"
          then Int.min height (Host.policy session.host tile).run_selector_rows
          else height))
      |> Option.value ~default:(tile.requested_geometry.height - 2)
      |> (fun height ->
           if String.equal tile.kind "run-selector"
           then Int.min height (Host.policy session.host tile).run_selector_rows
           else height)
      |> Int.max 1
    in
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

let host_handler_regular session event ~exit : unit Bonsai_term.Effect.t option =
  let open Bonsai_term in
  let modal =
    Option.is_some session.host.palette
    || session.host.editing_filter
    || session.host.paste
  in
  let input = Host.decode_event event in
  let workspace_navigation =
    Option.exists (Host.focused session.host) ~f:(fun tile ->
      String.equal tile.kind "workspace-tabs")
    && Option.exists input ~f:(function
      | Host.Character ('j' | 'k') | Next | Previous | Enter -> true
      | _ -> false)
  in
  let prefix = session.host.prefix > 0 in
  let captured = Host.capture session.host in
  let host, effect =
    Option.value_map input ~default:(session.host, Host.No_effect) ~f:(fun input ->
      Host.input session.host input ~commands:(host_catalog session))
  in
  session.host <- host;
  if host.editing_filter
  then
    change_synthesis session (fun _ local ->
      { local with synthesis = Synthesis_view.State.set_mode local.synthesis Cells });
  reconcile_synthesis session;
  match effect with
  | Host.Execute (capture, action) -> Some (execute_host session capture action ~exit)
  | Host.Activate ->
    Option.iter (Host.focused host) ~f:(fun tile ->
      if List.mem
           [ "stage-checklist"; "live-status"; "planned-run" ]
           tile.kind
           ~equal:String.equal
      then
        session.host
        <- Host.set_local
             session.host
             tile.id
             { (Host.local session.host tile.id) with utility_detail = true; scroll = 0 });
    change_terminal_result session Terminal_result_view.State.inspect;
    change_synthesis session (fun _ local ->
      let mode =
        match Synthesis_view.State.mode local.synthesis with
        | Summary -> Synthesis_view.Mode.Cells
        | Cells -> Details
        | Details -> Details
        | Metrics -> Metrics
        | Evidence -> Evidence
      in
      { local with synthesis = Synthesis_view.State.set_mode local.synthesis mode });
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
  | Host.No_effect when workspace_navigation -> Some Effect.Ignore
  | Host.No_effect ->
    let dispatch id =
      Option.bind captured ~f:(fun capture ->
        List.find (host_catalog session) ~f:(fun command -> String.equal command.id id)
        |> Option.map ~f:(fun command ->
          execute_host session capture command.action ~exit))
    in
    (match input with
     | Some (Character (('j' | 'k' | 'n' | 'p' | 'l') as key))
       when Option.value_map (Host.focused session.host) ~default:false ~f:(fun t ->
              String.equal t.kind "simulation") ->
       let tile = Option.value_exn (Host.focused session.host) in
       let local = Host.local session.host tile.id in
       let v = local.simulation in
       let choose values selected delta =
         let index =
           Option.bind selected ~f:(fun id ->
             List.findi values ~f:(fun _ s -> String.equal id s) |> Option.map ~f:fst)
           |> Option.value ~default:(if delta > 0 then -1 else 1)
         in
         List.nth values (Int.max 0 (Int.min (List.length values - 1) (index + delta)))
       in
       if Char.equal key 'j' || Char.equal key 'k'
       then (
         let values =
           Option.value_map v.snapshot ~default:[] ~f:(fun s ->
             List.map s.attempts ~f:(fun a -> a.id))
         in
         match
           choose values v.attempt (if Char.equal key 'j' then 1 else -1), captured
         with
         | Some id, Some capture ->
           Some (execute_host session capture (Simulation (tile.id, Observe id)) ~exit)
         | _ -> Some Effect.Ignore)
       else (
         let simulation =
           if Char.equal key 'l'
           then { v with logs = not v.logs }
           else (
             let values =
               Option.value_map (Simulation_view.detail v) ~default:[] ~f:(fun d ->
                 List.map d.cases ~f:(fun c -> c.case_id))
             in
             { v with
               case_id = choose values v.case_id (if Char.equal key 'n' then 1 else -1)
             })
         in
         session.host
         <- Host.set_local session.host tile.id { local with simulation; scroll = 0 };
         Some Effect.Ignore)
     | Some (Character 'b') -> dispatch "project.build"
     | Some (Character 't') -> dispatch "project.test"
     | Some (Character 'i') -> dispatch "project.discover"
     | Some (Character 's') -> dispatch "synthesis.cycle-sort"
     | Some (Character 'e') ->
       (match Host.focused session.host with
        | Some tile when Terminal_result_view.supports tile.kind ->
          change_terminal_result session Terminal_result_view.State.inspect;
          Some Effect.Ignore
        | _ -> dispatch "synthesis.evidence")
     | Some (Character 'm') -> dispatch "synthesis.metrics"
     | Some (Character 'r')
       when Option.exists (Host.focused session.host) ~f:(fun tile ->
              String.equal tile.kind "stage-checklist") ->
       let selected =
         Option.bind (Host.focused session.host) ~f:(fun tile ->
           Option.bind session.host.registry ~f:(fun registry ->
             Workspace.resolve_tile registry tile.id
             |> Result.ok
             |> Option.bind ~f:(fun reference -> reference.run)
             |> Option.bind ~f:(fun run ->
               let stages =
                 Terminal_presentation.Overview_tiles.observed_stages
                   ~asic:session.asic
                   ~run
               in
               Host.stage_cursor (Host.local session.host tile.id) ~run ~stages
               |> Option.map ~f:(fun stage -> stage, run))))
       in
       (match selected, captured with
        | Some (stage, run), Some capture ->
          session.host
          <- { session.host with
               notice =
                 "Preparing NEW run; when preview ready: Space c c → Launch / Launch and \
                  view"
             };
          Some (execute_host session capture (Prepare_stage (stage, run)) ~exit)
        | None, _ ->
          session.host
          <- { session.host with notice = "No explicit stage observation selected" };
          Some Effect.Ignore
        | Some _, None ->
          session.host
          <- { session.host with
               notice = "Stage action unavailable: workspace not loaded"
             };
          Some Effect.Ignore)
     | Some Escape ->
       Option.iter (Host.focused session.host) ~f:(fun tile ->
         let local = Host.local session.host tile.id in
         if local.utility_detail
         then
           session.host
           <- Host.set_local
                session.host
                tile.id
                { local with utility_detail = false; scroll = 0 });
       change_terminal_result session Terminal_result_view.State.back;
       change_synthesis session (fun _ local ->
         { local with synthesis = Synthesis_view.State.back local.synthesis });
       Some Effect.Ignore
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
     | Some (Character ('1' .. '9' as ch)) ->
       let index = Char.to_int ch - Char.to_int '1' in
       Option.bind session.host.registry ~f:(fun s -> List.nth s.workspaces index)
       |> Option.iter ~f:(fun w -> session.host <- Host.switch session.host w.id);
       Some Effect.Ignore
     | Some (Character (('[' | ']') as ch)) ->
       (match Host.focused session.host with
        | Some tile
          when Terminal_result_view.supports tile.kind
               || String.equal tile.kind "simulation"
               || String.equal tile.kind "synthesis"
               || String.equal tile.kind "live-status"
               || String.equal tile.kind "planned-run"
               || String.equal tile.kind "stage-checklist" ->
          scroll_host session (if Char.equal ch '[' then -1 else 1)
        | _ ->
          Option.iter session.host.focus ~f:(fun id ->
            let l = Host.local session.host id in
            session.host
            <- Host.set_local
                 session.host
                 id
                 { l with
                   follow = false
                 ; scroll = Int.max 0 (l.scroll + if Char.equal ch '[' then -1 else 1)
                 }));
       Some Effect.Ignore
     | Some (Focus | Focus_previous) -> Some Effect.Ignore
     | _ -> None)
;;

let host_handler_overlays session event ~exit =
  let focused =
    Option.bind (Host.focused session.host) ~f:(fun tile ->
      Option.map (Host.local session.host tile.id).artifacts ~f:(fun view -> tile, view))
  in
  let input = Host.decode_event event in
  let inspection =
    Option.bind (Host.focused session.host) ~f:(fun tile ->
      Option.map (Host.inspection session.host tile.id) ~f:(fun view -> tile, view))
  in
  let bypass =
    Option.is_some session.host.palette
    || session.host.editing_filter
    || session.host.paste
    || session.host.prefix > 0
    ||
    match input with
    | Some (Host.Focus | Focus_previous | Paste_start | Paste_end) -> true
    | Some (Character ' ') ->
      not (Option.exists inspection ~f:(fun (_, view) -> view.editing))
    | _ -> false
  in
  match inspection, focused with
  | Some (tile, view), _ when not bypass ->
    let action =
      if view.editing
      then (
        match input with
        | Some Host.Enter -> Some Inspection_view.Open
        | Some Escape -> Some Back
        | Some Backspace -> Some Backspace
        | Some (Character c) -> Some (Character c)
        | Some (Text text) -> Some (Text text)
        | _ -> None)
      else (
        match event, input with
        | _, Some Host.Enter -> Some Inspection_view.Open
        | _, Some Escape -> Some Back
        | _, Some (Next | Character 'j') -> Some Down
        | _, Some (Previous | Character 'k') -> Some Up
        | _, Some (Character 'n') -> Some Page_down
        | _, Some (Character 'N') -> Some Page_up
        | _, Some (Character '/') -> Some Filter
        | _, Some (Character 's') -> Some Sort
        | _, Some (Character 'c') -> Some (Cycle Corner)
        | _, Some (Character 'g') -> Some (Cycle Group)
        | _, Some (Character 'p') -> Some (Cycle Producer)
        | _, Some (Character 'v') -> Some Near
        | _, Some (Character 't') -> Some Stage
        | _, Some (Character 'r') -> Some Refresh
        | _, Some (Character 'd') -> Some Info
        | Key_press { key = Arrow `Right; mods = [] }, _ -> Some Page_down
        | Key_press { key = Arrow `Left; mods = [] }, _ -> Some Page_up
        | _ -> None)
    in
    let operation =
      Option.bind action ~f:(fun action ->
        let width, height =
          Option.value_map session.last_dimensions ~default:(80, 24) ~f:(fun dimensions ->
            if Option.is_none (Host.timing_pane session.host tile)
            then Host_view.inspection_viewport dimensions
            else (
              let _, _, layout = Host_view.tile_layout session.host dimensions in
              List.find layout ~f:(fun (candidate, _) ->
                Workspace.Tile_id.equal candidate.id tile.id)
              |> Option.value_map ~default:(80, 24) ~f:(fun (_, geometry) ->
                let _, _, _, width, height =
                  Host_view.body_geometry
                    session.host
                    tile
                    ~width:geometry.width
                    ~height:geometry.height
                in
                width, height)))
        in
        let inspection, operation =
          match Host.timing_pane session.host tile with
          | None -> Inspection_view.input ~width ~height view action
          | Some pane ->
            let local = Host.local session.host tile.id in
            let view, scroll, operation =
              Timing_workspace.input ~pane ~scroll:local.scroll ~width ~height view action
            in
            let view =
              Option.value_map
                session.asic
                ~default:view
                ~f:(Inspection_view.reconcile view)
            in
            let operation =
              match operation with
              | Some (Asic.Operation.Inspect_detail _) when Option.is_some view.detail ->
                None
              | other -> other
            in
            session.host <- Host.set_local session.host tile.id { local with scroll };
            Some view, operation
        in
        let local = Host.local session.host tile.id in
        let inspection_generation =
          Option.value_map inspection ~default:local.inspection_generation ~f:(fun v ->
            v.generation)
        in
        session.host <- Host.set_inspection session.host tile.id inspection;
        if Option.is_none (Host.timing_pane session.host tile)
        then
          session.host
          <- Host.set_local
               session.host
               tile.id
               { (Host.local session.host tile.id) with inspection_generation };
        Option.bind operation ~f:(fun operation ->
          Option.map inspection ~f:(fun view ->
            operation, (tile.id, Inspection_view.capture view operation))))
    in
    Some
      (Option.value_map
         operation
         ~default:Bonsai_term.Effect.Ignore
         ~f:(fun (operation, inspection_request) ->
           Bonsai_term.Effect.of_deferred_thunk (fun () ->
             asic_request ~inspection_request session operation)))
  | _, Some (tile, view)
    when (not bypass)
         &&
         match input with
         | Some (Character 'b') -> true
         | _ -> false ->
    let reference =
      match view.reading with
      | Some r -> Some r.artifact
      | None -> List.nth view.catalog view.selected
    in
    let selected =
      let open Or_error.Let_syntax in
      let%bind viewer =
        Or_error.of_option
          session.artifact_binary_viewer
          ~error:
            (Error.of_string
               "Binary view disabled; configure --artifact-binary-viewer \
                ABSOLUTE_EXECUTABLE")
      in
      let%bind reference =
        Or_error.of_option
          reference
          ~error:(Error.of_string "Select a known physical file")
      in
      let%bind () =
        if List.exists view.catalog ~f:(Artifact_export.same_reference reference)
        then Ok ()
        else Or_error.error_string "Artifact reference changed"
      in
      let%map () = Artifact_binary_export.eligible reference in
      viewer, reference
    in
    (match selected with
     | Error e ->
       artifact_export_notice session tile.id (Error.to_string_hum e);
       Some Bonsai_term.Effect.Ignore
     | Ok (viewer, reference) ->
       Some
         (Bonsai_term.Effect.of_deferred_thunk (fun () ->
            export_artifact_binary session tile.id ~viewer reference)))
  | _, Some (tile, view)
    when (not bypass)
         &&
         match input with
         | Some (Character 'x') -> true
         | _ -> false ->
    (match Artifact_view.external_reference view ~viewer:session.artifact_viewer with
     | Error error ->
       artifact_export_notice session tile.id (Error.to_string_hum error);
       Some Bonsai_term.Effect.Ignore
     | Ok (viewer, reference) ->
       Some
         (Bonsai_term.Effect.of_deferred_thunk (fun () ->
            export_artifact_text session tile.id ~viewer reference)))
  | _, Some (tile, view) when not bypass ->
    let action =
      match event, input with
      | _, Some Host.Enter -> Some Artifact_view.Open
      | _, Some Escape -> Some Back
      | Key_press { key = Arrow `Right; mods = [] }, _ | _, Some (Character 'n') ->
        Some Next
      | Key_press { key = Arrow `Left; mods = [] }, _ | _, Some (Character 'p') ->
        Some Previous
      | _, Some (Next | Character 'j') -> Some Down
      | _, Some (Previous | Character 'k') -> Some Up
      | _ -> None
    in
    let operation =
      Option.bind action ~f:(fun action ->
        let width, height =
          Option.value_map session.last_dimensions ~default:(80, 24) ~f:(fun dimensions ->
            dimensions.width, dimensions.height)
        in
        let artifacts, operation = Artifact_view.input ~width ~height view action in
        let local = Host.local session.host tile.id in
        let artifact_generation =
          Option.value_map artifacts ~default:local.artifact_generation ~f:(fun view ->
            view.generation)
        in
        session.host
        <- Host.set_local
             session.host
             tile.id
             { local with artifacts; artifact_generation };
        Option.map operation ~f:(fun operation ->
          let artifact_request =
            Option.bind artifacts ~f:(fun view ->
              capture_artifact_request session tile view operation)
          in
          operation, artifact_request))
    in
    Some
      (Option.value_map
         operation
         ~default:Bonsai_term.Effect.Ignore
         ~f:(fun (operation, artifact_request) ->
           Bonsai_term.Effect.of_deferred_thunk (fun () ->
             asic_request ?artifact_request session operation)))
  | _ -> host_handler_regular session event ~exit
;;

let host_handler session event ~exit =
  if Host.is_interrupt event
  then Some (exit ())
  else (
    reconcile_synthesis session;
    match Host.route_inspection_filter_event session.host event with
    | Filter_interrupt -> Some (exit ())
    | Filter_handled host ->
      session.host <- host;
      Some Bonsai_term.Effect.Ignore
    | Filter_pass -> host_handler_overlays session event ~exit)
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
  if String.equal scenario "aesthetic-overview"
  then (
    let registry =
      apply
        registry
        (Create_workspace
           { window = overview.window; name = "Testing"; context = registry.main_context })
    in
    let registry =
      List.fold
        [ "live-status"; "workspace-tabs"; "stage-checklist" ]
        ~init:registry
        ~f:(fun registry kind ->
          apply
            registry
            (Create_tile
               { workspace = overview.id
               ; kind
               ; geometry = { x = 0; y = 0; width = 36; height = 12 }
               }))
    in
    session.host <- Host.receive session.host registry);
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
      [ "aesthetic-overview"; "synthesis-a"; "timing"; "pinned-synthesis"; "palette" ]
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
  (* Session navigation is currently mutable. Give those mutations a reactive invalidation
     edge instead of waiting for the display clock to repaint. The clock below remains for
     time-dependent displays, not input acknowledgement. *)
  let revision, update_revision = Bonsai.state' 0 graph in
  let invalidate update = update (fun revision -> revision + 1) in
  let poll =
    Bonsai.map update_revision ~f:(fun update ->
      Effect.bind
        (Effect.of_deferred_thunk (fun () -> refresh session))
        ~f:(fun () -> invalidate update))
  in
  Bonsai.Clock.every
    ~when_to_start_next_effect:`Wait_period_after_previous_effect_finishes_blocking
    ~trigger_on_activate:true
    (Bonsai.return (Time_ns.Span.of_ms 500.))
    poll
    graph;
  let view =
    Bonsai.map3
      dimensions
      (Bonsai.Clock.approx_now ~tick_every:(Time_ns.Span.of_ms 100.) graph)
      revision
      ~f:(fun dimensions _now _revision -> render session dimensions)
  in
  let handle (event : Event.t) =
    if Host.is_interrupt event
    then exit ()
    else (
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
  let handler =
    Bonsai.map update_revision ~f:(fun update event ->
      let effect = handle event in
      (* Publish local state immediately; publish any deferred response when it completes
         too. Do not await a provider/HTTP read before local feedback. *)
      Effect.Many
        [ invalidate update; Effect.bind effect ~f:(fun () -> invalidate update) ])
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
     | Ok { job = None } ->
       let%map result = resync session ~instance_id:session.hello.instance_id in
       (match result with
        | Error message -> Or_error.error_string message
        | Ok () ->
          printf "Integration manifest reloaded (no driver declared)\n%!";
          List.iter (integration_lines session) ~f:print_endline;
          Ok ())
     | Ok { job = Some job } ->
       session.snapshot <- State.add_job_if_absent session.snapshot job;
       printf "Submitted integration refresh job %s\n%!" (Job_id.to_string job.id);
       if not wait
       then return (Ok ())
       else (
         let%map finished = wait_for_job session job in
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
  ~artifact_viewer
  ~artifact_binary_viewer
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
        session.artifact_viewer <- artifact_viewer;
        session.artifact_binary_viewer <- artifact_binary_viewer;
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
            let%bind result =
              Bonsai_term.start_with_exit
                ~dispose:true
                ~mouse:No_mouse_events
                (tui session)
            in
            let%map () = session.preference_saves in
            result)
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
  ~artifact_viewer
  ~artifact_binary_viewer
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
        ~artifact_viewer
        ~artifact_binary_viewer
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
     and artifact_viewer =
       flag
         "--artifact-viewer"
         (optional
            (Command.Arg_type.create (fun path ->
               Artifact_export.executable path |> Or_error.ok_exn)))
         ~doc:
           "ABSOLUTE_EXECUTABLE enable x to export sanitized ASIC text to a private \
            local .txt and open it (no shell; disabled by default)"
     and artifact_binary_viewer =
       flag
         "--artifact-binary-viewer"
         ~aliases:[ "--simulation-viewer" ]
         (optional
            (Command.Arg_type.create (fun path ->
               Artifact_binary_export.executable path |> Or_error.ok_exn)))
         ~doc:
           "ABSOLUTE_EXECUTABLE external viewer for verified ASIC binary files (b) and \
            simulation traces (palette, <=64 MiB); alias --simulation-viewer; receives \
            one private terminal-host path, no shell; disabled by default"
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
         ~diagnostics_file
         ~artifact_viewer
         ~artifact_binary_viewer)
;;

let () = Command_unix.run command
