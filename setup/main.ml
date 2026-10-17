open! Core
module Initialization = Hardcaml_workbench_setup.Initialization

let report_error message =
  eprintf "hardcaml-workbench-init: %s\n%!" message;
  exit 1
;;

let command =
  Command.basic
    ~summary:"Initialize Hardcaml Workbench in an existing Dune directory"
    ~readme:(fun () ->
      "Creates only hardcaml-workbench.sexp, without replacing existing files.\n\
       ROOT must directly contain dune-project; relative roots use the current directory.\n\
       The project name defaults to ROOT's directory name. No ancestor discovery,\n\
       build, git, driver or provider execution is performed. Driver and aliases\n\
       are saved references; their targets do not need to exist yet.")
    (let%map_open.Command root =
       flag "--root" (required string) ~doc:"DIR explicit existing Dune directory"
     and project_name =
       flag "--project-name" (optional string) ~doc:"NAME project display name"
     and driver =
       flag "--driver" (optional string) ~doc:"./PATH optional Dune driver executable"
     and build_alias =
       flag "--build-alias" (optional string) ~doc:"ALIAS Dune build alias (default @all)"
     and test_alias =
       flag
         "--test-alias"
         (optional string)
         ~doc:"ALIAS Dune test alias (default @runtest)"
     and dry_run =
       flag
         "--dry-run"
         no_arg
         ~doc:" validate and print the manifest without writing files"
     in
     fun () ->
       match
         Initialization.prepare ~root ?project_name ?driver ?build_alias ?test_alias ()
       with
       | Error message -> report_error message
       | Ok plan ->
         if dry_run
         then printf "%s%!" (Initialization.contents plan)
         else (
           match Initialization.publish plan with
           | Error message -> report_error message
           | Ok () -> printf "Created %s\n%!" (Initialization.path plan)))
;;

let () = Command_unix.run command
