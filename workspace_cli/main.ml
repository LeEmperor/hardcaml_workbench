(** Operates only on an already-open project's registry. No project discovery, provider
    requests, job submission or automatic conflict retries. *)
open! Core

open! Async
open Hardcaml_workbench_protocol
module Client = Hardcaml_workbench_native_http.Client
module W = Workspace
module T = Workspace_template

let protocol_ok = function
  | Ok value -> value
  | Error (error : V1.Error.t) -> raise_s [%sexp (error : V1.Error.t)]
;;

let connection =
  let open Command.Let_syntax in
  let%map_open endpoint = flag "-endpoint" (required string) ~doc:"URL Running daemon URL"
  and project = flag "-project" (required string) ~doc:"ID Already-open project ID" in
  Client.create endpoint, Project_id.of_string project
;;

let connect (client, project) =
  let%bind hello = Client.hello client >>| Or_error.ok_exn in
  let request operation =
    Client.workspace
      client
      { W.Request.instance_id = hello.instance_id; project; operation }
    >>| Or_error.ok_exn
    >>| protocol_ok
  in
  let%map snapshot = request Get in
  snapshot, request
;;

let emit template =
  let text = T.encode template |> Or_error.ok_exn in
  Writer.write (Lazy.force Writer.stdout) text
;;

let list =
  Command.async
    ~summary:"List window and workspace IDs and names for an already-open project"
    (let open Command.Let_syntax in
     let%map_open connection in
     fun () ->
       let open Deferred.Let_syntax in
       let%map snapshot, _ = connect connection in
       List.iter snapshot.windows ~f:(fun window ->
         printf "window\t%s\t%S\n" (W.Window_id.to_string window.id) window.name;
         List.iter snapshot.workspaces ~f:(fun workspace ->
           if W.Window_id.equal workspace.window window.id
           then
             printf
               "  workspace\t%s\t%S\n"
               (W.Workspace_id.to_string workspace.id)
               workspace.name)))
;;

let export =
  Command.async
    ~summary:"Export a workspace's portable layout to stdout"
    (let open Command.Let_syntax in
     let%map_open connection
     and source = anon ("WORKSPACE-ID" %: string) in
     fun () ->
       let open Deferred.Let_syntax in
       let%map snapshot, _ = connect connection in
       W.export_template snapshot (W.Workspace_id.of_string source) |> protocol_ok |> emit)
;;

let instantiate
  (snapshot : W.Snapshot.t)
  (request : W.Operation.t -> W.Snapshot.t Deferred.t)
  ~window
  ~name
  template
  =
  let template =
    match name with
    | None -> template
    | Some name -> { template with T.name }
  in
  T.validate template |> Or_error.ok_exn;
  let%map next =
    request
      (W.Operation.Mutate
         { expected_revision = snapshot.W.Snapshot.revision
         ; mutation =
             Instantiate_template { window = W.Window_id.of_string window; template }
         })
  in
  let created =
    List.find_exn next.workspaces ~f:(fun w ->
      not
        (List.exists snapshot.workspaces ~f:(fun old -> W.Workspace_id.equal old.id w.id)))
  in
  printf "%s\n" (W.Workspace_id.to_string created.id)
;;

let destination =
  let open Command.Let_syntax in
  let%map_open window = flag "-window" (required string) ~doc:"ID Destination window ID"
  and name =
    flag "-name" (optional string) ~doc:"NAME Override template workspace name"
  in
  window, name
;;

(** Read at most one byte beyond the accepted size, including for growing files or
    streams. [with_file] closes the descriptor on both success and size rejection. *)
let read_template_file file =
  Reader.with_file file ~f:(fun reader ->
    let buffer = Bytes.create (T.max_encoded_bytes + 1) in
    let%map result = Reader.really_read reader buffer in
    match result with
    | `Ok -> failwith "Workspace template exceeds 1 MiB"
    | `Eof length -> Bytes.sub buffer ~pos:0 ~len:length |> Bytes.to_string)
;;

let import =
  Command.async
    ~summary:"Instantiate a template file atomically; print the new workspace ID"
    (let open Command.Let_syntax in
     let%map_open connection
     and destination
     and file = anon ("TEMPLATE.sexp" %: string) in
     fun () ->
       let open Deferred.Let_syntax in
       let%bind text = read_template_file file in
       let template = T.decode text |> Or_error.ok_exn in
       let%bind snapshot, request = connect connection in
       let window, name = destination in
       instantiate snapshot request ~window ~name template)
;;

let clone =
  Command.async
    ~summary:"Clone a workspace layout into a new Main-linked workspace"
    (let open Command.Let_syntax in
     let%map_open connection
     and destination
     and source = anon ("WORKSPACE-ID" %: string) in
     fun () ->
       let open Deferred.Let_syntax in
       let%bind snapshot, request = connect connection in
       let template =
         W.export_template snapshot (W.Workspace_id.of_string source) |> protocol_ok
       in
       let window, name = destination in
       instantiate snapshot request ~window ~name template)
;;

let starter =
  Command.async
    ~summary:"Write a generic or asic starter template to stdout (offline)"
    (let open Command.Let_syntax in
     let%map_open kind = anon ("generic|asic" %: string) in
     fun () ->
       emit
         (match kind with
          | "generic" -> T.generic
          | "asic" -> T.asic
          | _ -> failwith "Expected generic or asic");
       Deferred.unit)
;;

let () =
  Command_unix.run
    (Command.group
       ~summary:"Portable, versioned workspace layouts"
       [ "list", list
       ; "export", export
       ; "import", import
       ; "clone", clone
       ; "starter", starter
       ])
;;
