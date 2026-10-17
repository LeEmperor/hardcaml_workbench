open! Core
module Manifest = Hardcaml_workbench_project_integration.Manifest

type t =
  { root : string
  ; path : string
  ; contents : string
  }

let root t = t.root
let path t = t.path
let contents t = t.contents

let filesystem_result f =
  match Or_error.try_with f with
  | Ok result -> result
  | Error error -> Error (Error.to_string_hum error)
;;

let exists path =
  try
    ignore (Core_unix.lstat path : Core_unix.stats);
    true
  with
  | Core_unix.Unix_error (ENOENT, _, _) -> false
;;

let regular_file path =
  try
    match (Core_unix.stat path).st_kind with
    | S_REG -> true
    | _ -> false
  with
  | Core_unix.Unix_error (ENOENT, _, _) -> false
;;

let existing_error path =
  sprintf "refusing to overwrite existing %s; inspect or edit it explicitly" path
;;

let prepare ~root ?project_name ?driver ?build_alias ?test_alias () =
  filesystem_result (fun () ->
    if String.is_empty (String.strip root)
    then Error "root: must explicitly name an existing Dune directory"
    else (
      let root = Filename_unix.realpath root in
      match (Core_unix.stat root).st_kind with
      | S_DIR ->
        if not (regular_file (Filename.concat root "dune-project"))
        then
          Error
            (sprintf "root: %s must directly contain a regular dune-project file" root)
        else (
          let path = Filename.concat root Manifest.filename in
          if exists path
          then Error (existing_error path)
          else (
            let project_name =
              Option.value_or_thunk project_name ~default:(fun () ->
                match Filename.basename root with
                | "" | "/" | "." -> "hardcaml-project"
                | name -> name)
            in
            if String.is_empty (String.strip project_name)
            then Error "project.name: must not be empty or whitespace"
            else (
              let manifest : Manifest.t =
                { project_name
                ; driver
                ; build_alias =
                    Option.value build_alias ~default:Manifest.default_build_alias
                ; test_alias =
                    Option.value test_alias ~default:Manifest.default_test_alias
                }
              in
              let contents = Manifest.to_string manifest in
              let%map.Result (_ : Manifest.t) = Manifest.parse_string contents in
              { root; path; contents })))
      | _ -> Error (sprintf "root: %s is not a directory" root)))
;;

let publish t =
  filesystem_result (fun () ->
    let temporary, channel =
      Filename_unix.open_temp_file
        ~in_dir:t.root
        ~perm:0o600
        ".hardcaml-workbench-init-"
        ".sexp"
    in
    Exn.protect
      ~f:(fun () ->
        Out_channel.output_string channel t.contents;
        Out_channel.flush channel;
        Core_unix.fsync (Core_unix.descr_of_out_channel channel);
        Out_channel.close channel;
        try
          (* Unlike rename, link never replaces any existing directory entry. The complete
             file is visible at once, including to concurrent readers. *)
          Core_unix.link ~force:false ~target:temporary ~link_name:t.path ();
          Ok ()
        with
        | Core_unix.Unix_error (EEXIST, _, _) -> Error (existing_error t.path))
      ~finally:(fun () ->
        Out_channel.close_no_err channel;
        Core_unix.unlink temporary))
;;
