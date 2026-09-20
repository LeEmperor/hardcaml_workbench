open! Core
open Hardcaml_workbench_adapters
open Hardcaml_workbench_protocol

let%expect_test "selected environments produce complete argv" =
  let root = "/work/project" in
  print_s
    [%sexp
      (Dune_adapter.probe_invocation ~root V1.Environment_selection.Inherit_daemon
       : Dune_adapter.Invocation.t)];
  print_s
    [%sexp
      (Dune_adapter.inspect_invocation ~root (Opam_switch "project-switch")
       : Dune_adapter.Invocation.t)];
  [%expect
    {|
    ((executable dune) (argv (dune --version)) (cwd /work/project)
     (environment Inherit_daemon))
    ((executable opam)
     (argv
      (opam exec --switch=project-switch --set-switch -- dune describe workspace
       --root /work/project --format=sexp --lang=0.1))
     (cwd /work/project) (environment (Opam_switch project-switch))) |}]
;;

let%expect_test "Dune version validation" =
  List.iter [ "3.22.0\n"; "4.0.1"; "3.21.9"; "not-a-version" ] ~f:(fun output ->
    print_s [%sexp (Dune_adapter.parse_probe_output output : (string, string) Result.t)]);
  [%expect
    {|
    (Ok 3.22.0)
    (Ok 4.0.1)
    (Error "Dune 3.22 or newer is required; selected environment has 3.21.9")
    (Error "Could not parse Dune version: not-a-version") |}]
;;

let%expect_test "workspace parser preserves generic item kinds" =
  let workspace =
    {|
    ((root /work/project)
     (build_context _build/default)
     (executables
      ((names (tool helper))
       (modules ())))
      (library
       ((name project_lib)
        (local true)
        (source_dir lib)))
      (library
       ((name installed_dependency)
        (local false)
        (source_dir /opam/lib/dependency)))
      (documentation
      ((package project))))
    |}
  in
  print_s
    [%sexp
      (Dune_adapter.parse_workspace workspace
       : (V1.Dune_workspace.Inspection.t, string) Result.t)];
  [%expect
    {|
    (Ok
     ((contexts (default))
      (items
       (((kind executables) (names (tool helper)) (source_path ()))
        ((kind library) (names (project_lib)) (source_path (lib)))
        ((kind documentation) (names ()) (source_path ())))))) |}]
;;

let%expect_test "typed actions translate without a shell" =
  let print action =
    print_s
      [%sexp
        (Dune_adapter.action_invocation
           ~root:"/work/project"
           ~environment:(Opam_switch "project-switch")
           action
         : Dune_adapter.Invocation.t)]
  in
  print Build;
  print Test;
  [%expect
    {|
    ((executable opam)
     (argv
      (opam exec --switch=project-switch --set-switch -- dune build --root
       /work/project --no-buffer @all))
     (cwd /work/project) (environment (Opam_switch project-switch)))
    ((executable opam)
     (argv
      (opam exec --switch=project-switch --set-switch -- dune runtest --root
       /work/project --no-buffer))
     (cwd /work/project) (environment (Opam_switch project-switch)))
    |}]
;;

let%expect_test "workspace parser rejects unversioned shapes" =
  List.iter [ "atom"; "((root /work/project))"; "((build_context))" ] ~f:(fun output ->
    print_s
      [%sexp
        (Dune_adapter.parse_workspace output
         : (V1.Dune_workspace.Inspection.t, string) Result.t)]);
  [%expect
    {|
    (Error "Invalid Dune workspace lang 0.1 output: expected a workspace record")
    (Error "Invalid Dune workspace lang 0.1 output: missing build_context")
    (Error
     "Invalid Dune workspace lang 0.1 output: malformed build_context entry")
    |}]
;;
