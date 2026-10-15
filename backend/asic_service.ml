open! Core
open! Async
open Hardcaml_workbench_protocol
module Config = Hardcaml_workbench_project_integration.Asic_config
module Adapter = Hardcaml_workbench_adapters.Asic_adapter
module Public = Asic_public

module Stored = struct
  type t =
    { version : int
    ; identity : string
    ; runs : Asic.Run.t list
    ; submissions : (string * Asic.Preview.t * string option) list
    ; index : (string * string) list
    ; terminal_attempts : (string * string) list [@sexp.default []]
    }
  [@@deriving sexp]
end

module Summary_blob = struct
  type t =
    { version : int
    ; normalized_digest : string
    ; summary : Asic.Summary.t
    }
  [@@deriving sexp]
end

let summary_digest summary =
  Public.digest (Sexp.to_string_mach (Asic.Summary.sexp_of_t summary))
;;

(* v1 predates metrics; v2 predates terminal results. Reconstruct each version's exact
   canonical record shape after decoding with defaults. Keeping the blob path namespace
   permits old L2 entries to reopen without IO to the provider. Absent terminal evidence
   requires explicit adoption. *)
let decode_summary_blob sexp =
  let blob = Summary_blob.t_of_sexp sexp in
  let valid =
    match blob.version with
    | 3 | 4 -> String.equal blob.normalized_digest (summary_digest blob.summary)
    | (1 | 2) as version ->
      let legacy =
        match Asic.Summary.sexp_of_t blob.summary with
        | Sexp.List fields ->
          Sexp.List
            (List.filter fields ~f:(function
              | Sexp.List (Sexp.Atom "metrics" :: _) when version = 1 -> false
              | Sexp.List (Sexp.Atom "terminal" :: _) -> false
              | _ -> true))
        | _ -> failwith "Expected summary record"
      in
      (version <> 1 || List.is_empty blob.summary.metrics)
      && Option.is_none blob.summary.terminal
      && String.equal blob.normalized_digest (Public.digest (Sexp.to_string_mach legacy))
    | _ -> false
  in
  Public.require valid "Corrupt/incompatible normalized summary";
  Public.require (List.length blob.summary.metrics <= 64) "Metric cache exceeds budget";
  Option.iter blob.summary.terminal ~f:(fun terminal ->
    Public.require
      (List.length terminal.metrics <= 64
       && List.length terminal.checks <= 64
       && String.length terminal.evidence <= 160 * 1024)
      "Terminal cache exceeds budget");
  let summary = blob.summary in
  (* Before v4 the last checkpoint was projected as synthesis, even for physical
     executions. Keep old caches readable but never relabel routing evidence. A refresh
     recovers explicit synthesis evidence from the full public report. *)
  let explicit_synthesis =
    Or_error.try_with (fun () ->
      Poly.equal
        (Public.field
           "boundary"
           (Public.field "reference" (Public.decode summary.producer)))
        (`String "synthesis"))
    |> Result.ok
    |> Option.value ~default:false
  in
  if blob.version < 4 && not explicit_synthesis
  then
    { summary with
      cell_count = None
    ; cells = []
    ; metrics = []
    ; producer = "no synthesis checkpoint in legacy projection"
    }
  else summary
;;

type task =
  { cancel : unit Ivar.t
  ; mutable pending : Asic.Pending.t
  ; mutable completion : unit Deferred.t
  }

type reservation =
  { preview : Asic.Preview.t
  ; result : (unit, exn) Result.t Deferred.t
  }

type project =
  { root : string
  ; environment : V1.Environment_selection.t
  ; config : Config.t option
  ; identity : string
  ; mutable runs : Asic.Run.t list
  ; mutable submissions : (string * Asic.Preview.t * string option) list
  ; mutable index : (string * string) list
  ; mutable terminal_attempts : (string * string) list
  ; hot : Asic.Summary.t String.Table.t
  ; mutable recency : string list
  ; tasks : task String.Table.t
  ; reservations : reservation String.Table.t
  ; mutable flows : Asic.Flow.t list
  ; mutable description : string option
  ; mutable preview : Asic.Preview.t option
  ; mutable desired_plan : Asic.Selection.t option
  ; mutable desired_description : string option
  ; read_tails : unit Deferred.t String.Table.t
  ; mutable provider_check : (unit, exn) Result.t Deferred.t option
  ; mutable cache_error : string option
  ; mutable registry_writable : bool
  ; mutable save_tail : unit Deferred.t
  }

type t =
  { state_dir : string
  ; projects : (project, exn) Result.t Deferred.t String.Table.t
  ; queries : unit Throttle.t
  ; executions : unit Throttle.t
  ; mutable closing : bool
  }

let create ~state_dir =
  { state_dir
  ; projects = String.Table.create ()
  ; queries = Throttle.create ~continue_on_error:true ~max_concurrent_jobs:4
  ; executions = Throttle.create ~continue_on_error:true ~max_concurrent_jobs:1
  ; closing = false
  }
;;

let path t identity suffix =
  Filename.concat t.state_dir ("asic-" ^ Public.digest identity ^ suffix)
;;

let registry_path t p = path t p.identity ".sexp"
let summary_prefix p = "asic-" ^ Public.digest p.identity ^ "-summary-v1-"

let summary_path t p digest =
  Filename.concat t.state_dir (summary_prefix p ^ Public.digest digest ^ ".summary.sexp")
;;

let atomic_write t filename data =
  Core_unix.mkdir_p t.state_dir ~perm:0o700;
  let temporary = Filename_unix.temp_file ~in_dir:t.state_dir ".asic-" ".tmp" in
  Exn.protect
    ~finally:(fun () ->
      if Poly.equal (Sys_unix.file_exists temporary) `Yes then Core_unix.unlink temporary)
    ~f:(fun () ->
      Out_channel.write_all temporary ~data;
      Core_unix.rename ~src:temporary ~dst:filename)
;;

let read_bounded filename limit =
  let stat = Core_unix.stat filename in
  if Int64.(stat.st_size > of_int limit) then failwith "ASIC cache file exceeds budget";
  In_channel.read_all filename
;;

let read_public_bounded = Asic_evidence_file.read_bounded

let save_registry ?reservation t p =
  let previous = p.save_tail in
  let outcome =
    let%bind () = previous in
    Monitor.try_with (fun () ->
      Public.require
        p.registry_writable
        "ASIC registry is corrupt/incompatible; cannot save submissions";
      (* Capture at execution time, not enqueue time: earlier queued writes may commit new
         reservations while we wait for the single registry writer. *)
      let submissions =
        match reservation with
        | None -> p.submissions
        | Some (key, (preview : Asic.Preview.t)) ->
          Public.require
            (List.length p.submissions < 256)
            "ASIC submission budget exhausted";
          Public.require
            (String.length preview.plan_json <= 256 * 1024
             && List.sum (module Int) p.submissions ~f:(fun (_, p, _) ->
                  String.length p.Asic.Preview.plan_json)
                + String.length preview.plan_json
                < 3 * 1024 * 1024)
            "ASIC retained preview budget exhausted";
          (key, preview, None) :: p.submissions
      in
      let stored : Stored.t =
        { version = 1
        ; identity = p.identity
        ; runs = p.runs
        ; submissions
        ; index = p.index
        ; terminal_attempts = p.terminal_attempts
        }
      in
      let data = Sexp.to_string (Stored.sexp_of_t stored) in
      let%map () = In_thread.run (fun () -> atomic_write t (registry_path t p) data) in
      (* No uncommitted key is ever visible to another save or Run. Commit without
         yielding after successful rename, preserving concurrent run-reference edits. *)
      Option.iter reservation ~f:(fun (key, preview) ->
        p.submissions <- (key, preview, None) :: p.submissions))
  in
  let work =
    outcome
    >>| fun result ->
    match result with
    | Ok () -> ()
    | Error exn -> p.cache_error <- Some (Exn.to_string exn)
  in
  p.save_tail <- work;
  outcome
;;

let persist t p =
  let%map (_ : (unit, exn) Result.t) = save_registry t p in
  ()
;;

let load_project t ~root ~environment =
  let%bind config =
    In_thread.run (fun () ->
      let filename = Filename.concat root Config.filename in
      match Sys_unix.file_exists filename with
      | `No -> None
      | `Unknown -> failwith "Cannot inspect ASIC configuration"
      | `Yes -> Some (Config.parse_string (read_bounded filename 65536) |> Or_error.ok_exn))
  in
  let%bind () =
    In_thread.run (fun () ->
      (* Resolve for the storage-separation check only, never for executable argv. *)
      let rec physical path =
        match Sys_unix.file_exists path with
        | `Yes -> Filename_unix.realpath path
        | `Unknown -> failwith "Cannot validate ASIC cache separation"
        | `No ->
          let parent = physical (Filename.dirname path) in
          (match Filename.basename path with
           | "." -> parent
           | ".." -> Filename.dirname parent
           | name -> Filename.concat parent name)
      in
      Option.iter config ~f:(fun (config : Config.t) ->
        let cache = physical t.state_dir
        and results = physical config.results_root in
        Public.require
          (not
             (String.equal results "/"
              || String.equal cache results
              || String.is_prefix cache ~prefix:(results ^ "/")))
          "Workbench ASIC cache must be outside provider results"))
  in
  let identity =
    Sexp.to_string_mach
      [%sexp
        (root : string)
        , (environment : V1.Environment_selection.t)
        , (config : Config.t option)]
  in
  let p =
    { root
    ; environment
    ; config
    ; identity
    ; runs = []
    ; submissions = []
    ; index = []
    ; terminal_attempts = []
    ; hot = String.Table.create ()
    ; recency = []
    ; tasks = String.Table.create ()
    ; reservations = String.Table.create ()
    ; flows = []
    ; description = None
    ; preview = None
    ; desired_plan = None
    ; desired_description = None
    ; read_tails = String.Table.create ()
    ; provider_check = None
    ; cache_error = None
    ; registry_writable = true
    ; save_tail = Deferred.unit
    }
  in
  let%bind loaded =
    Monitor.try_with (fun () ->
      In_thread.run (fun () ->
        let filename = registry_path t p in
        if Poly.equal (Sys_unix.file_exists filename) `No
        then None
        else
          Some
            (Stored.t_of_sexp (Sexp.of_string (read_bounded filename (4 * 1024 * 1024))))))
  in
  (match loaded with
   | Error exn ->
     p.registry_writable <- false;
     p.cache_error <- Some ("Registry unavailable: " ^ Exn.to_string exn)
   | Ok None -> ()
   | Ok (Some s) ->
     if s.version <> 1
        || (not (String.equal s.identity identity))
        || List.length s.runs > 256
        || List.length s.index > 128
        || List.length s.submissions > 256
        || List.length s.terminal_attempts > 256
     then (
       p.registry_writable <- false;
       p.cache_error <- Some "Incompatible ASIC registry")
     else (
       p.runs <- s.runs;
       p.submissions <- s.submissions;
       p.index <- s.index;
       p.terminal_attempts <- s.terminal_attempts));
  (* This is our explicitly configured, single-writer derived cache directory, never a
     provider directory. Recover only our own namespace's orphan blobs. *)
  let retained =
    List.map p.index ~f:(fun (_, digest) -> Filename.basename (summary_path t p digest))
  in
  let%map cleanup =
    Monitor.try_with (fun () ->
      In_thread.run (fun () ->
        if p.registry_writable && Poly.equal (Sys_unix.file_exists t.state_dir) `Yes
        then
          List.iter (Sys_unix.ls_dir t.state_dir) ~f:(fun name ->
            if String.is_prefix name ~prefix:(summary_prefix p)
               && String.is_suffix name ~suffix:".summary.sexp"
               && not (List.mem retained name ~equal:String.equal)
            then Core_unix.unlink (Filename.concat t.state_dir name))))
  in
  (match cleanup with
   | Ok () -> ()
   | Error exn -> p.cache_error <- Some (Exn.to_string exn));
  p
;;

let config p = Option.value_exn p.config ~message:"Project has no ASIC configuration"
let invoke p f = f (config p) ~root:p.root ~environment:p.environment

let query t _p cancel invocation =
  Throttle.enqueue t.queries (fun () ->
    Public.require (not (Deferred.is_determined cancel)) "ASIC query cancelled";
    let%map output =
      Asic_process.run
        ~seconds:30.
        ~cancel
        ~on_process:ignore
        ~on_line:(fun _ -> Deferred.unit)
        invocation
    in
    Public.decode output)
;;

let check_provider t p cancel =
  let checked =
    match p.provider_check with
    | Some checked -> checked
    | None ->
      let checked =
        Monitor.try_with (fun () ->
          let%map metadata = query t p cancel (invoke p Adapter.metadata) in
          Public.metadata metadata)
      in
      p.provider_check <- Some checked;
      checked
  in
  checked
  >>| function
  | Ok () -> ()
  | Error exn ->
    p.provider_check <- None;
    raise exn
;;

let run_id (reference : Asic.Reference.t) = reference.stream_id

let find_run (p : project) (run : Run_ref.t) : Asic.Run.t =
  List.find p.runs ~f:(fun r -> Run_ref.equal r.Asic.Run.run run)
  |> Option.value_exn ~message:"Unknown registered ASIC run"
;;

let replace_run (p : project) (r : Asic.Run.t) =
  p.runs
  <- r
     :: List.filter p.runs ~f:(fun (old : Asic.Run.t) ->
       not (Run_ref.equal old.run r.run))
;;

let register t (p : project) ?selection (reference : Asic.Reference.t) =
  ignore (Public.absolute reference.Asic.Reference.attempt : string);
  Public.require (not (String.is_empty reference.stream_id)) "Empty stream ID";
  let id = run_id reference in
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id; build = None; label = None }
  in
  match List.find p.runs ~f:(fun r -> Run_ref.equal r.Asic.Run.run run) with
  | Some r ->
    Public.require
      (Asic.Reference.equal r.reference reference)
      "Conflicting public run reference";
    return r
  | None ->
    Public.require (List.length p.runs < 256) "Registered ASIC run budget (256) exhausted";
    let r : Asic.Run.t =
      { run
      ; reference
      ; selection
      ; cursor = 0
      ; status = "allocated"
      ; execution_file = None
      ; error = None
      }
    in
    replace_run p r;
    let%map () = persist t p in
    r
;;

let hot p (summary : Asic.Summary.t) =
  let id = summary.run.id in
  Hashtbl.set p.hot ~key:id ~data:summary;
  p.recency <- id :: List.filter p.recency ~f:(fun key -> not (String.equal id key));
  let retained = List.take p.recency 32
  and evicted = List.drop p.recency 32 in
  List.iter evicted ~f:(Hashtbl.remove p.hot);
  p.recency <- retained
;;

let expected_plan p (run : Run_ref.t) =
  List.find_map p.submissions ~f:(fun (_, preview, id) ->
    if Option.equal String.equal id (Some run.id)
    then Some preview.Asic.Preview.plan_identity
    else None)
;;

let expected_bundle p (run : Run_ref.t) =
  List.find_map p.submissions ~f:(fun (_, preview, id) ->
    if Option.equal String.equal id (Some run.Run_ref.id)
    then
      Public.optional_text
        (Public.field "bundle_identity" (Public.decode preview.Asic.Preview.plan_json))
    else None)
;;

let serialized p key f =
  let previous = Hashtbl.find p.read_tails key |> Option.value ~default:Deferred.unit in
  let done_ = Ivar.create () in
  Hashtbl.set p.read_tails ~key ~data:(Ivar.read done_);
  Monitor.protect
    ~finally:(fun () ->
      Ivar.fill_exn done_ ();
      Deferred.unit)
    (fun () ->
      let%bind () = previous in
      f ())
;;

let observe_unlocked t p cancel (run : Run_ref.t) =
  Public.require
    (not (Deferred.is_determined cancel))
    "ASIC observation stopped; reconnect with Observe";
  let%bind () = check_provider t p cancel in
  let r = find_run p run in
  let%bind updates =
    query
      t
      p
      cancel
      (invoke p (fun c ~root ~environment ->
         Adapter.updates c ~root ~environment r.reference ~after:r.cursor))
  in
  let cursor = Public.updates r updates in
  let%bind inspection =
    query
      t
      p
      cancel
      (invoke p (fun c ~root ~environment ->
         Adapter.inspect c ~root ~environment r.reference))
  in
  let next, final = Public.inspection r ~cursor inspection in
  Public.require
    (not (Deferred.is_determined cancel))
    "ASIC observation stopped; reconnect with Observe";
  let methodology =
    Public.envelope
      (Public.field "methodology" inspection)
      "hardcaml-asic.historical-methodology"
      1
  in
  let reference =
    match Public.field "state" methodology with
    | `String "pending" -> Public.field "launch" methodology
    | `String "recorded" -> Public.field "reference" methodology
    | _ -> failwith "Missing historical methodology"
  in
  Public.require
    (Poly.equal (Public.field "attempt_id" reference) (`String r.reference.stream_id))
    "Historical methodology attempt mismatch";
  Option.iter (expected_plan p run) ~f:(fun identity ->
    let actual =
      match Public.field "state" methodology with
      | `String "pending" ->
        Public.field "expected_plan_identity" (Public.field "launch" methodology)
      | `String "recorded" -> Public.field "plan_identity" methodology
      | _ -> failwith "Missing historical methodology"
    in
    Public.require
      (Poly.equal actual (`String identity))
      "Inspection plan identity mismatch");
  (* Serial/coalesced observation per run prevents a late cursor from regressing it. *)
  let current = find_run p run in
  if current.cursor <= next.cursor
  then (
    replace_run p next;
    if current.cursor < next.cursor
       || not (Option.equal String.equal current.execution_file next.execution_file)
    then
      Option.iter (Hashtbl.find p.hot run.id) ~f:(fun s ->
        hot
          p
          { s with
            freshness =
              (if Option.is_none next.execution_file && final
               then Missing_source
               else Cached_unverified)
          }));
  let%map () = persist t p in
  final
;;

let observe t p cancel (run : Run_ref.t) =
  serialized p ("observe:" ^ run.Run_ref.id) (fun () -> observe_unlocked t p cancel run)
;;

let materialize_unlocked ?attempt t p cancel (run : Run_ref.t) =
  Public.require (not (Deferred.is_determined cancel)) "ASIC report read cancelled";
  let%bind () = check_provider t p cancel in
  let r = find_run p run in
  match r.execution_file with
  | None ->
    Option.iter (Hashtbl.find p.hot run.id) ~f:(fun s ->
      hot p { s with freshness = Missing_source });
    failwith "No public execution_file reference available"
  | Some execution_file ->
    let%bind result =
      Monitor.try_with (fun () ->
        let%bind report =
          query
            t
            p
            cancel
            (invoke p (fun c ~root ~environment ->
               Adapter.report c ~root ~environment execution_file))
        in
        Option.iter (expected_bundle p run) ~f:(fun bundle ->
          Public.require
            (Poly.equal
               (Public.field "bundle_identity" (Public.field "methodology" report))
               (`String bundle))
            "Report bundle identity mismatch");
        let summary =
          Public.summary r ~expected_plan:(expected_plan p run) ~execution_file report
        in
        let attempt =
          match attempt with
          | Some _ -> attempt
          | None -> List.Assoc.find p.terminal_attempts run.id ~equal:String.equal
        in
        match attempt with
        | None -> return summary
        | Some attempt ->
          let%bind receipt =
            query
              t
              p
              cancel
              (invoke p (fun c ~root ~environment ->
                 Adapter.inspect_finalization c ~root ~environment attempt))
          in
          let results_file = Public.terminal_results_file receipt in
          let%map terminal =
            In_thread.run (fun () ->
              let execution_file = Filename_unix.realpath execution_file in
              let execution_bytes =
                read_public_bounded execution_file (8 * 1024 * 1024)
              in
              let results_bytes = read_public_bounded results_file (128 * 1024) in
              let terminal =
                Public.terminal_result
                  ~attempt
                  ~execution_file
                  ~execution_bytes
                  ~report
                  ~receipt
                  ~results_bytes
              in
              let snapshot_bytes =
                Option.map (Public.declared_clock_snapshot report) ~f:(fun (path, _) ->
                  read_public_bounded path (256 * 1024))
              in
              let clock = Public.declared_clock_metric ~report ~receipt ~snapshot_bytes in
              { terminal with metrics = terminal.metrics @ [ clock ] })
          in
          { summary with
            terminal = Some terminal
          ; source_digest =
              Public.digest
                (summary.source_digest
                 ^ terminal.evidence
                 ^ Sexp.to_string_mach ([%sexp_of: Asic.Metric.t list] terminal.metrics))
          })
    in
    (match result with
     | Error exn ->
       Option.iter (Hashtbl.find p.hot run.id) ~f:(fun s ->
         hot p { s with freshness = Refresh_failed (Exn.to_string exn) });
       raise exn
     | Ok summary ->
       Public.require
         (not (Deferred.is_determined cancel))
         "ASIC report read cancelled before publication";
       let current = find_run p run in
       Public.require
         (current.cursor = r.cursor
          && Option.equal String.equal current.execution_file r.execution_file)
         "Observation advanced during report read; refresh again";
       let data = Sexp.to_string (Asic.Summary.sexp_of_t summary) in
       Public.require
         (String.length data <= 256 * 1024)
         "Normalized ASIC summary exceeds 256KiB";
       let blob : Summary_blob.t =
         { version = 4; normalized_digest = summary_digest summary; summary }
       in
       let data = Sexp.to_string (Summary_blob.sexp_of_t blob) in
       hot p summary;
       let%bind saved =
         Monitor.try_with (fun () ->
           In_thread.run (fun () ->
             atomic_write t (summary_path t p summary.source_digest) data))
       in
       let%bind () =
         match saved with
         | Error exn ->
           p.cache_error <- Some (Exn.to_string exn);
           Deferred.unit
         | Ok () ->
           let old_index = p.index in
           p.index
           <- (run.id, summary.source_digest)
              :: List.filter p.index ~f:(fun (id, _) -> not (String.equal id run.id));
           p.index <- List.take p.index 128;
           let retained = List.map p.index ~f:snd in
           In_thread.run (fun () ->
             List.iter old_index ~f:(fun (_, digest) ->
               if not (List.mem retained digest ~equal:String.equal)
               then (
                 try Core_unix.unlink (summary_path t p digest) with
                 | _ -> ())))
       in
       Option.iter summary.terminal ~f:(fun terminal ->
         p.terminal_attempts
         <- (run.id, terminal.attempt)
            :: List.filter p.terminal_attempts ~f:(fun (id, _) ->
              not (String.equal id run.id)));
       persist t p)
;;

let materialize ?attempt t p cancel (run : Run_ref.t) =
  (* Global publication ordering also protects L2 eviction from deleting a digest
     concurrently reintroduced by another registered run. *)
  serialized p "report-publication" (fun () ->
    materialize_unlocked ?attempt t p cancel run)
;;

let load_summary t p cancel (run : Run_ref.t) =
  match Hashtbl.find p.hot run.Run_ref.id with
  | Some summary ->
    hot p summary;
    Deferred.unit
  | None ->
    let%bind loaded =
      Monitor.try_with (fun () ->
        match List.Assoc.find p.index run.id ~equal:String.equal with
        | None -> return None
        | Some digest ->
          In_thread.run (fun () ->
            let s =
              decode_summary_blob
                (Sexp.of_string
                   (read_bounded (summary_path t p digest) ((256 * 1024) + 1024)))
            in
            Public.require
              (Run_ref.equal s.run run && String.equal s.source_digest digest)
              "Wrong L2 summary identity";
            Some { s with freshness = Cached_unverified }))
    in
    (match loaded with
     | Ok (Some summary) ->
       if not (Hashtbl.mem p.hot run.id) then hot p summary;
       Deferred.unit
     | Ok None | Error _ ->
       let%bind (_ : bool) = observe t p cancel run in
       materialize t p cancel run)
;;

let snapshot p : Asic.Snapshot.t =
  { configured = Option.is_some p.config
  ; flows = p.flows
  ; description_json = p.description
  ; preview = p.preview
  ; runs = p.runs
  ; operations =
      (Hashtbl.data p.tasks |> List.map ~f:(fun t -> t.pending))
      @ (Hashtbl.keys p.reservations
         |> List.filter_map ~f:(fun key ->
           if Hashtbl.mem p.tasks ("run:" ^ key)
           then None
           else
             Some
               { Asic.Pending.key = "run:" ^ key
               ; kind = "run"
               ; state = "reserving"
               ; run = None
               ; error = None
               }))
      @ List.filter_map p.submissions ~f:(fun (key, _, id) ->
        if Hashtbl.mem p.tasks ("run:" ^ key) || Hashtbl.mem p.reservations key
        then None
        else
          Some
            { Asic.Pending.key = "run:" ^ key
            ; kind = "run"
            ; state = "detached"
            ; run =
                Option.bind id ~f:(fun id ->
                  List.find_map p.runs ~f:(fun r ->
                    if String.equal r.Asic.Run.run.id id then Some r.run else None))
            ; error =
                Some
                  "Submission reserved; execution ownership unavailable. Observe \
                   registered reference; never relaunch implicitly."
            })
  ; summaries = Hashtbl.data p.hot
  ; cache_error = p.cache_error
  }
;;

let schedule t p ~key ~kind ~execution f =
  Public.require (not t.closing) "ASIC service shutting down";
  match Hashtbl.find p.tasks key with
  | Some task
    when String.equal task.pending.state "pending"
         || String.equal task.pending.state "executing" -> ()
  | _ ->
    if Hashtbl.length p.tasks >= 64
    then
      Hashtbl.filter_inplace p.tasks ~f:(fun task ->
        String.equal task.pending.state "pending"
        || String.equal task.pending.state "executing");
    Public.require (Hashtbl.length p.tasks < 64) "ASIC pending operation budget exhausted";
    let task =
      { cancel = Ivar.create ()
      ; completion = Deferred.unit
      ; pending = { Asic.Pending.key; kind; state = "pending"; run = None; error = None }
      }
    in
    Hashtbl.set p.tasks ~key ~data:task;
    let work () =
      let%map result =
        Monitor.try_with (fun () ->
          Public.require (not (Ivar.is_full task.cancel)) "ASIC operation cancelled";
          task.pending <- { task.pending with state = "executing" };
          f task)
      in
      task.pending
      <- (match result with
          | Ok () -> { task.pending with state = "completed" }
          | Error exn ->
            { task.pending with state = "failed"; error = Some (Exn.to_string exn) })
    in
    let completion = if execution then Throttle.enqueue t.executions work else work () in
    task.completion <- completion;
    don't_wait_for completion
;;

let observation_key (run : Run_ref.t) = "observe:" ^ run.id

let reserve_and_schedule t p ~key ~preview launch =
  Public.require (not t.closing) "ASIC service shutting down";
  let await result =
    result
    >>| function
    | Ok () -> ()
    | Error exn -> raise exn
  in
  match Hashtbl.find p.reservations key with
  | Some reservation ->
    Public.require
      (Asic.Preview.equal reservation.preview preview)
      "Submission key reused with different preview";
    await reservation.result
  | None ->
    (match List.find p.submissions ~f:(fun (old, _, _) -> String.equal key old) with
     | Some (_, old, _) ->
       Public.require
         (Asic.Preview.equal old preview)
         "Submission key reused with different preview";
       Deferred.unit
     | None ->
       Public.require
         (Hashtbl.length p.reservations < 64)
         "ASIC in-flight reservation budget exhausted";
       let outcome = Ivar.create () in
       let result = Ivar.read outcome in
       Hashtbl.set p.reservations ~key ~data:{ preview; result };
       let work =
         Monitor.try_with (fun () ->
           let%map saved = save_registry ~reservation:(key, preview) t p in
           match saved with
           | Error exn -> raise exn
           | Ok () -> launch ())
       in
       don't_wait_for
         (work
          >>| fun result ->
          (* Failure before commit leaves no key to roll back. Existing waiters all
             receive this exact outcome; a later request may safely retry the key. *)
          Hashtbl.remove p.reservations key;
          Ivar.fill_exn outcome result);
       await result)
;;

let handle_operation t p operation =
  let enqueue ~key ~kind f =
    schedule t p ~key ~kind ~execution:false (fun task -> f (Ivar.read task.cancel))
  in
  let public_query ~key ~kind invocation apply =
    enqueue ~key ~kind (fun cancel ->
      let%bind () = check_provider t p cancel in
      let%map value = query t p cancel invocation in
      apply value)
  in
  match operation with
  | Asic.Operation.Get -> Deferred.unit
  | Cancel key ->
    let task =
      match Hashtbl.find p.tasks key with
      | Some task -> task
      | None -> Hashtbl.find_exn p.tasks ("run:" ^ key)
    in
    Ivar.fill_if_empty task.cancel ();
    Option.iter task.pending.run ~f:(fun run ->
      Option.iter
        (Hashtbl.find p.tasks (observation_key run))
        ~f:(fun observer -> Ivar.fill_if_empty observer.cancel ()));
    Deferred.unit
  | Discover ->
    public_query ~key:"discover" ~kind:"discover" (invoke p Adapter.discover) (fun j ->
      p.flows <- Public.flows j);
    Deferred.unit
  | Describe flow ->
    p.desired_description <- Some flow;
    p.description <- None;
    public_query
      ~key:("describe:" ^ flow)
      ~kind:"describe"
      (invoke p (fun c ~root ~environment -> Adapter.describe c ~root ~environment flow))
      (fun j ->
        let j = Public.envelope j "hardcaml-asic.flow-describe" 1 in
        if Option.equal String.equal p.desired_description (Some flow)
        then p.description <- Some (Yojson.Safe.to_string j));
    Deferred.unit
  | Plan selection ->
    p.desired_plan <- Some selection;
    p.preview <- None;
    public_query
      ~key:
        ("plan:"
         ^ Public.digest (Sexp.to_string_mach (Asic.Selection.sexp_of_t selection)))
      ~kind:"plan"
      (invoke p (fun c ~root ~environment -> Adapter.plan c ~root ~environment selection))
      (fun j ->
        let preview = Public.preview selection j in
        if Option.equal Asic.Selection.equal p.desired_plan (Some selection)
        then p.preview <- Some preview);
    Deferred.unit
  | Register reference ->
    let%map (_ : Asic.Run.t) = register t p reference in
    ()
  | Observe run ->
    ignore (find_run p run : Asic.Run.t);
    enqueue ~key:(observation_key run) ~kind:"observe" (fun cancel ->
      observe t p cancel run >>| fun _ -> ());
    Deferred.unit
  | Load_summary run | Refresh run ->
    ignore (find_run p run : Asic.Run.t);
    let refresh =
      match operation with
      | Refresh _ -> true
      | _ -> false
    in
    enqueue
      ~key:((if refresh then "refresh:" else "summary:") ^ run.id)
      ~kind:(if refresh then "refresh" else "summary")
      (fun cancel ->
        serialized p ("summaryop:" ^ run.id) (fun () ->
          let%bind result =
            Monitor.try_with (fun () ->
              if refresh
              then (
                let%bind (_ : bool) = observe t p cancel run in
                materialize t p cancel run)
              else load_summary t p cancel run)
          in
          match result with
          | Ok () -> Deferred.unit
          | Error exn ->
            Option.iter (Hashtbl.find p.hot run.id) ~f:(fun s ->
              if not (Asic.Summary.Freshness.equal s.freshness Missing_source)
              then hot p { s with freshness = Refresh_failed (Exn.to_string exn) });
            raise exn));
    Deferred.unit
  | Inspect_finalization { run; attempt } ->
    ignore (find_run p run : Asic.Run.t);
    ignore (Public.absolute attempt : string);
    Public.require (String.length attempt <= 4096) "Finalization reference exceeds budget";
    enqueue
      ~key:("finalization:" ^ run.id ^ ":" ^ Public.digest attempt)
      ~kind:"finalization"
      (fun cancel ->
        serialized p ("summaryop:" ^ run.id) (fun () ->
          Monitor.try_with (fun () ->
            let%bind (_ : bool) = observe t p cancel run in
            materialize ~attempt t p cancel run)
          >>| function
          | Ok () -> ()
          | Error exn ->
            Option.iter (Hashtbl.find p.hot run.id) ~f:(fun s ->
              hot p { s with freshness = Refresh_failed (Exn.to_string exn) });
            raise exn));
    Deferred.unit
  | Run { key; preview } ->
    Public.require
      p.registry_writable
      "ASIC registry unavailable; submission deduplication cannot be established";
    Public.require
      ((not (String.is_empty key)) && String.length key <= 256)
      "Invalid ASIC submission key";
    ignore
      (Public.preview preview.selection (Public.decode preview.plan_json)
       : Asic.Preview.t);
    Public.require
      (String.equal
         preview.plan_identity
         (Public.text (Public.field "plan_identity" (Public.decode preview.plan_json))))
      "Preview identity mismatch";
    reserve_and_schedule t p ~key ~preview (fun () ->
      schedule t p ~key:("run:" ^ key) ~kind:"run" ~execution:true (fun task ->
        (* The entire execution task, including metadata and its automatic reader, shares
           one deadline. Allocation must not reset the execution budget. *)
        let deadline = Clock.after (Time_float.Span.of_sec 1800.) in
        let cancel = Deferred.any [ Ivar.read task.cancel; deadline ] in
        let%bind () = check_provider t p cancel in
        let%bind () =
          if String.equal preview.selection.endpoint "synthesis"
          then Deferred.unit
          else (
            let%map description =
              query
                t
                p
                cancel
                (invoke p (fun c ~root ~environment ->
                   Adapter.describe c ~root ~environment preview.selection.flow))
            in
            Public.validate_physical_selection preview.selection description)
        in
        let allocated = ref None in
        let delivered_execution = ref None in
        let validate_delivery run =
          Option.iter !delivered_execution ~f:(fun delivered ->
            let r = find_run p run in
            Public.require
              (Option.equal String.equal r.execution_file (Some delivered))
              "Launcher/inspection execution reference mismatch")
        in
        let on_line line =
          let j = Public.decode line in
          match Public.field "event" j with
          | `String "observation_allocated" ->
            Public.require (Option.is_none !allocated) "Duplicate allocation";
            let reference = Public.allocation j in
            let%bind r = register t p ~selection:preview.selection reference in
            allocated := Some r.run;
            task.pending <- { task.pending with run = Some r.run };
            p.submissions
            <- List.map p.submissions ~f:(fun (k, v, id) ->
                 k, v, if String.equal k key then Some r.run.id else id);
            let%map () = persist t p in
            (* Start observation before waiting for launcher EOF. *)
            if not (Deferred.is_determined cancel)
            then
              schedule
                t
                p
                ~key:(observation_key r.run)
                ~kind:"observe"
                ~execution:false
                (fun observer ->
                   observer.pending <- { observer.pending with run = Some r.run };
                   let cancel = Deferred.any [ Ivar.read observer.cancel; cancel ] in
                   let check_reader () =
                     Public.require
                       (not (Deferred.is_determined cancel))
                       "Automatic observation stopped: execution deadline/cancellation; \
                        reconnect with Observe"
                   in
                   let rec loop remaining =
                     check_reader ();
                     Public.require
                       (remaining > 0)
                       "Observation budget exhausted; reconnect with Observe";
                     let%bind final = observe t p cancel r.run in
                     check_reader ();
                     if final
                     then (
                       validate_delivery r.run;
                       materialize t p cancel r.run)
                     else (
                       let%bind () =
                         Deferred.any [ Clock.after (Time_float.Span.of_sec 1.); cancel ]
                       in
                       loop (remaining - 1))
                   in
                   let%bind result = Monitor.try_with (fun () -> loop 1800) in
                   match result with
                   | Ok () -> Deferred.unit
                   | Error exn ->
                     let current = find_run p r.run in
                     replace_run
                       p
                       { current with
                         error =
                           Some
                             ("Observation stopped; provider outcome not inferred: "
                              ^ Exn.to_string exn)
                       };
                     let%bind () = persist t p in
                     raise exn)
          | `String "observation_terminal" ->
            ignore (Public.envelope j "hardcaml-asic.stage-observation" 1 : Yojson.Safe.t);
            delivered_execution
            := Option.map
                 (Public.optional_text (Public.field "execution_file" j))
                 ~f:Public.absolute;
            Deferred.unit
          | _ ->
            let run =
              Option.value_exn !allocated ~message:"Launcher output before allocation"
            in
            Public.execution_summary (find_run p run) preview j;
            delivered_execution
            := Option.map
                 (Public.optional_text (Public.field "execution_file" j))
                 ~f:Public.absolute;
            Deferred.unit
        in
        let%bind result =
          Monitor.try_with (fun () ->
             Asic_process.run
               (* The adopted producer needs its child termination grace, five-second
                  container cleanup window, and terminal receipt publication before
                  escalation. Queries retain the shorter default grace. *)
               ~stop_grace_seconds:15.
               ~seconds:1800.
              ~cancel
              ~on_process:ignore
              ~on_line
              (invoke p (fun c ~root ~environment ->
                 Adapter.run c ~root ~environment preview)))
        in
        (match result with
         | Ok _ -> ()
         | Error _ ->
           Option.iter !allocated ~f:(fun run ->
             Option.iter
               (Hashtbl.find p.tasks (observation_key run))
               ~f:(fun observer -> Ivar.fill_if_empty observer.cancel ())));
        let%bind () = persist t p in
        match result with
        | Error exn -> raise exn
        | Ok _ ->
          let run =
            Option.value_exn !allocated ~message:"Launcher exited without allocation"
          in
          let r = find_run p run in
          if not (List.mem [ "allocated"; "observing" ] r.status ~equal:String.equal)
          then validate_delivery run;
          Deferred.unit))
;;

let handle t ~root ~environment operation : Asic.Response.t Deferred.t =
  Monitor.try_with (fun () ->
    Public.require (not t.closing) "ASIC service shutting down";
    Public.require (Filename.is_absolute root) "ASIC project root must be absolute";
    Public.require
      (Filename.is_absolute t.state_dir)
      "ASIC state directory must be absolute";
    let key =
      Sexp.to_string_mach
        [%sexp (root : string), (environment : V1.Environment_selection.t)]
    in
    Public.require
      (Hashtbl.mem t.projects key || Hashtbl.length t.projects < 32)
      "ASIC project working-set budget exhausted (32)";
    let loaded =
      Hashtbl.find_or_add t.projects key ~default:(fun () ->
        Monitor.try_with (fun () -> load_project t ~root ~environment))
    in
    let%bind result = loaded in
    let p =
      match result with
      | Ok p -> p
      | Error exn -> raise exn
    in
    let%map () = handle_operation t p operation in
    snapshot p)
  >>| function
  | Ok snapshot -> Ok snapshot
  | Error exn -> Error (V1.Error.create Invalid_request (Exn.to_string exn))
;;

(** Client detach does not call this. Daemon shutdown cancels/reaps owned launchers and
    bounded readers, then flushes registered references. Reconnected readers never signal
    a historical producer PID. *)
let shutdown t =
  t.closing <- true;
  Deferred.List.iter (Hashtbl.data t.projects) ~how:`Parallel ~f:(fun loaded ->
    match%bind loaded with
    | Error _ -> Deferred.unit
    | Ok p ->
      let%bind () =
        Deferred.all_unit
          (List.map (Hashtbl.data p.reservations) ~f:(fun r -> r.result >>| fun _ -> ()))
      in
      Hashtbl.iter p.tasks ~f:(fun task -> Ivar.fill_if_empty task.cancel ());
      let%bind () =
        Deferred.all_unit
          (List.map (Hashtbl.data p.tasks) ~f:(fun task -> task.completion))
      in
      p.save_tail)
;;

let rec completion t =
  Deferred.List.iter (Hashtbl.data t.projects) ~how:`Parallel ~f:(fun loaded ->
    match%bind loaded with
    | Error _ -> Deferred.unit
    | Ok p ->
      let%bind () =
        Deferred.all_unit
          (List.map (Hashtbl.data p.reservations) ~f:(fun r -> r.result >>| fun _ -> ()))
      in
      let%bind () =
        Deferred.all_unit
          (List.map (Hashtbl.data p.tasks) ~f:(fun task -> task.completion))
      in
      p.save_tail)
  >>= fun () ->
  let%bind active =
    Deferred.List.map (Hashtbl.data t.projects) ~how:`Parallel ~f:(fun loaded ->
      let%map result = loaded in
      match result with
      | Error _ -> false
      | Ok p ->
        (not (Hashtbl.is_empty p.reservations))
        || Hashtbl.exists p.tasks ~f:(fun task ->
          String.equal task.pending.state "pending"
          || String.equal task.pending.state "executing"))
  in
  if List.exists active ~f:Fn.id then completion t else Deferred.unit
;;
