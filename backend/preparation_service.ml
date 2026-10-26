open! Core
open! Async
open Hardcaml_workbench_protocol
open Preparation
module Config = Hardcaml_workbench_project_integration.Preparation_config
module Adapter = Hardcaml_workbench_adapters.Preparation_adapter

type attempt =
  { mutable value : Attempt.t
  ; mutable cancelled : bool
  ; ready : unit Ivar.t
  ; config : Config.t
  }

type project =
  { mutable attempts : attempt list
  ; submissions : (string, string * attempt) Hashtbl.t
  }

type t =
  { projects : (string, project) Hashtbl.t
  ; mutable next_id : int
  ; build :
      Config.t
      -> root:string
      -> environment:V1.Environment_selection.t
      -> Hardcaml_workbench_adapters.Dune_adapter.Invocation.t
  ; emit :
      Config.t
      -> root:string
      -> environment:V1.Environment_selection.t
      -> selection:Selection.t
      -> expected_plan_identity:string option
      -> Hardcaml_workbench_adapters.Dune_adapter.Invocation.t
  }

let create ?(build = Adapter.build) ?(emit = Adapter.emit) () =
  { projects = Hashtbl.create (module String); next_id = 0; build; emit }
;;

exception Rpc_error of V1.Error.t

let rpc_error kind message = raise (Rpc_error (V1.Error.create kind message))

let load_config root =
  let%map result =
    Monitor.try_with_or_error (fun () ->
      In_thread.run (fun () ->
        let path = Filename.concat root Config.filename in
        match Sys_unix.file_exists path with
        | `No -> None
        | `Yes | `Unknown ->
          Some (Config.parse_string (In_channel.read_all path) |> Or_error.ok_exn)))
  in
  match result with
  | Ok None -> Availability.Unavailable Not_configured, None
  | Ok (Some config) -> Available, Some config
  | Error error -> Unavailable (Invalid_configuration (Error.to_string_hum error)), None
;;

let active a =
  match a.value.outcome with
  | Building | Emitting -> true
  | _ -> false
;;

let job_failure (job : Job.t) =
  Option.first_some
    job.failure
    (Some
       (sprintf
          "%s process %s (%s)"
          job.kind.name
          (Sexp.to_string_hum (Job.State.sexp_of_t job.state))
          (Sexp.to_string_hum ([%sexp_of: Job.Exit_status.t option] job.exit_status))))
;;

let handle
  t
  ~root
  ~project_key
  ~environment
  ~schedule
  ~wait
  ~get_job
  ~cancel
  ~import
  operation
  =
  let project =
    Hashtbl.find_or_add t.projects project_key ~default:(fun () ->
      { attempts = []; submissions = Hashtbl.create (module String) })
  in
  let snapshot ?requested_attempt availability =
    let history =
      List.map project.attempts ~f:(fun a ->
        let refresh job = Option.bind job ~f:(fun job -> get_job job.Job.id) in
        { a.value with
          build_job = refresh a.value.build_job
        ; emission_job = refresh a.value.emission_job
        })
    in
    { Snapshot.availability
    ; session_only = true
    ; requested_attempt
    ; latest = List.hd history
    ; history
    }
  in
  let%map handled =
    Monitor.try_with (fun () ->
      let%bind availability, config = load_config root in
      match operation with
      | Operation.Get -> return (snapshot availability)
      | Cancel id ->
        let a =
          match List.find project.attempts ~f:(fun a -> String.equal a.value.id id) with
          | None -> rpc_error Not_found "Unknown preparation attempt"
          | Some a -> a
        in
        if not (active a)
        then return (snapshot ~requested_attempt:id availability)
        else (
          a.cancelled <- true;
          let%bind () = Ivar.read a.ready in
          let%bind () =
            Deferred.List.iter
              (List.filter_opt [ a.value.build_job; a.value.emission_job ])
              ~how:`Sequential
              ~f:(fun job -> cancel job.Job.id)
          in
          a.value <- { a.value with outcome = Cancelled; bundle = None };
          return (snapshot ~requested_attempt:id availability))
      | Prepare { submission_key; selection; expected_plan_identity } ->
        if String.is_empty submission_key
        then rpc_error Invalid_request "Empty submission key";
        (match
           Or_error.try_with (fun () ->
             Preparation_receipt.validate_selection selection expected_plan_identity)
         with
         | Error error -> rpc_error Invalid_request (Error.to_string_hum error)
         | Ok () -> ());
        let payload =
          Sexp.to_string_mach
            ([%sexp_of: Selection.t * string option] (selection, expected_plan_identity))
        in
        (match Hashtbl.find project.submissions submission_key with
         | Some (previous, a) ->
           if not (String.equal previous payload)
           then rpc_error Conflict "Submission key already used for a different selection";
           let%map () = Ivar.read a.ready in
           snapshot ~requested_attempt:a.value.id availability
         | None ->
           (match
              List.find project.attempts ~f:(fun a ->
                active a
                && (not a.cancelled)
                && Selection.equal a.value.selection selection
                && Option.value_map config ~default:false ~f:(Config.equal a.config)
                && Option.equal
                     String.equal
                     a.value.expected_plan_identity
                     expected_plan_identity)
            with
            | Some a ->
              Hashtbl.set project.submissions ~key:submission_key ~data:(payload, a);
              let%map () = Ivar.read a.ready in
              snapshot ~requested_attempt:a.value.id availability
            | None ->
              let config =
                match config with
                | Some c -> c
                | None ->
                  rpc_error
                    Unsupported_operation
                    "Source bundle preparation is not configured"
              in
              t.next_id <- t.next_id + 1;
              let a =
                { value =
                    { Attempt.id = sprintf "preparation-%d" t.next_id
                    ; selection
                    ; selection_identity =
                        Preparation_receipt.sha256 (project_key ^ "\000" ^ payload)
                    ; expected_plan_identity
                    ; source_root = root
                    ; build_target = config.build_target
                    ; source_executable = Config.source_executable config ~root
                    ; environment
                    ; results_root = config.results_root
                    ; timeout_seconds = config.timeout_seconds
                    ; created_at = Timestamp.of_time_ns (Time_ns.now ())
                    ; outcome = Building
                    ; build_job = None
                    ; emission_job = None
                    ; bundle = None
                    ; diagnostic = None
                    }
                ; cancelled = false
                ; ready = Ivar.create ()
                ; config
                }
              in
              project.attempts <- a :: project.attempts;
              Hashtbl.set project.submissions ~key:submission_key ~data:(payload, a);
              let task invocation ~stdout ~drain ~finish : Simulation_task.t =
                { invocation
                ; timeout_seconds = config.timeout_seconds
                ; start = (fun () -> ())
                ; preflight =
                    (fun () ->
                      let%map _, current = load_config root in
                      if a.cancelled then failwith "Preparation cancelled before launch";
                      if not (Option.equal Config.equal current (Some config))
                      then
                        failwith
                          "Preparation configuration changed before launch; submit a new \
                           attempt")
                ; stdout
                ; drain
                ; finish
                ; poll = (fun () -> true)
                ; fail =
                    (fun message -> a.value <- { a.value with diagnostic = Some message })
                }
              in
              let%bind scheduled =
                Monitor.try_with_or_error (fun () ->
                  let build_task =
                    task
                      (t.build config ~root ~environment)
                      ~stdout:ignore
                      ~drain:(fun () -> return ())
                      ~finish:(fun ~cancelled:_ _ -> a.value.diagnostic)
                  in
                  schedule ~name:"build" ~cancelled:(fun () -> a.cancelled) build_task)
              in
              (match scheduled with
               | Error error ->
                 a.value
                 <- { a.value with
                      outcome = Build_failed
                    ; diagnostic = Some (Error.to_string_hum error)
                    };
                 Ivar.fill_if_empty a.ready ();
                 return (snapshot ~requested_attempt:a.value.id availability)
               | Ok build ->
                 a.value <- { a.value with build_job = Some build };
                 Ivar.fill_if_empty a.ready ();
                 don't_wait_for
                   (let%map result =
                      Monitor.try_with (fun () ->
                        let%bind () =
                          if a.cancelled then cancel build.id else return ()
                        in
                        let%bind built = wait build.id in
                        a.value <- { a.value with build_job = Some built };
                        if a.cancelled || Job.State.equal built.state Cancelled
                        then (
                          a.value <- { a.value with outcome = Cancelled };
                          return ())
                        else if not (Job.State.equal built.state Complete)
                        then (
                          a.value
                          <- { a.value with
                               outcome = Build_failed
                             ; diagnostic =
                                 Option.first_some a.value.diagnostic (job_failure built)
                             };
                          return ())
                        else (
                          a.value
                          <- { a.value with outcome = Emitting; diagnostic = None };
                          let buffer = Buffer.create 4096 in
                          let overflow = ref false in
                          let validation_error = ref None in
                          let pending_bundle = ref None in
                          let emission =
                            task
                              (t.emit
                                 config
                                 ~root
                                 ~environment
                                 ~selection
                                 ~expected_plan_identity)
                              ~stdout:(fun data ->
                                if Buffer.length buffer + String.length data
                                   > 16 * 1024 * 1024
                                then overflow := true
                                else Buffer.add_string buffer data)
                              ~drain:(fun () -> return ())
                              ~finish:(fun ~cancelled:_ _ ->
                                Option.first_some !validation_error a.value.diagnostic)
                          in
                          (* The supervisor calls drain after reaping and before marking
                             Complete. *)
                          let emission =
                            { emission with
                              drain =
                                (fun () ->
                                  if !overflow
                                  then (
                                    validation_error
                                    := Some "Emission receipt exceeded byte budget";
                                    return ())
                                  else if a.cancelled || Option.is_some a.value.diagnostic
                                  then return ()
                                  else (
                                    let%bind validated =
                                      In_thread.run (fun () ->
                                        Preparation_receipt.validate
                                          config
                                          ~selection
                                          ~expected_plan_identity
                                          (Buffer.contents buffer))
                                    in
                                    match validated with
                                    | Error error ->
                                      validation_error := Some (Error.to_string_hum error);
                                      return ()
                                    | Ok _
                                      when a.cancelled
                                           || Option.is_some a.value.diagnostic ->
                                      return ()
                                    | Ok validated ->
                                      let%map imported =
                                        import
                                          ~job:(Option.value_exn a.value.emission_job).id
                                          ~valid:(fun () ->
                                            (not a.cancelled)
                                            && Option.is_none a.value.diagnostic)
                                          ~output_dir:validated.bundle.output_dir
                                          ~files:validated.files
                                      in
                                      (match imported with
                                       | Error error ->
                                         validation_error
                                         := Some (Error.to_string_hum error)
                                       | Ok artifacts ->
                                         pending_bundle
                                         := Some { validated.bundle with artifacts })))
                            }
                          in
                          let%bind emitted =
                            schedule
                              ~name:"emit"
                              ~cancelled:(fun () -> a.cancelled)
                              emission
                          in
                          a.value <- { a.value with emission_job = Some emitted };
                          let%bind () =
                            if a.cancelled then cancel emitted.id else return ()
                          in
                          let%map emitted = wait emitted.id in
                          let outcome =
                            if a.cancelled || Job.State.equal emitted.state Cancelled
                            then Outcome.Cancelled
                            else if Job.State.equal emitted.state Complete
                                    && Option.is_some !pending_bundle
                            then Completed
                            else Emission_failed
                          in
                          a.value
                          <- { a.value with
                               emission_job = Some emitted
                             ; outcome
                             ; bundle =
                                 (if Outcome.equal outcome Completed
                                  then !pending_bundle
                                  else None)
                             ; diagnostic =
                                 (if Outcome.equal outcome Completed
                                  then None
                                  else
                                    Option.first_some
                                      !validation_error
                                      (Option.first_some
                                         a.value.diagnostic
                                         (job_failure emitted)))
                             }))
                    in
                    match result with
                    | Ok () -> ()
                    | Error exn ->
                      a.value
                      <- { a.value with
                           outcome = (if a.cancelled then Cancelled else Emission_failed)
                         ; diagnostic = Some (Exn.to_string exn)
                         });
                 return (snapshot ~requested_attempt:a.value.id availability)))))
  in
  match handled with
  | Ok value -> Ok value
  | Error exn ->
    (match Monitor.extract_exn exn with
     | Rpc_error error -> Error error
     | exn -> Error (V1.Error.create Internal_failure (Exn.to_string exn)))
;;
