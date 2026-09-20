open! Core
open Hardcaml_workbench_protocol
open Hardcaml_workbench_project_integration

let manifest body = Manifest.parse_string body

let%expect_test "manifest defaults and explicit references" =
  List.iter
    [ "(lang hardcaml-workbench 1) (project (name demo)) (dune)"
    ; "(lang hardcaml-workbench 1) (project (name demo)) (dune (driver \
       ./workbench/driver.exe) (build_alias app/@build) (test_alias @check))"
    ]
    ~f:(fun input -> print_s [%sexp (manifest input : (Manifest.t, string) Result.t)]);
  [%expect
    {|
    (Ok
     ((project_name demo) (driver ()) (build_alias @all) (test_alias @runtest)))
    (Ok
     ((project_name demo) (driver (./workbench/driver.exe))
      (build_alias app/@build) (test_alias @check))) |}]
;;

let%expect_test "manifest rejects versions, duplicates, unknowns, and escaping references"
  =
  List.iter
    [ "(lang hardcaml-workbench 2) (project (name demo)) (dune)"
    ; "(lang hardcaml-workbench 1) (project (name a) (name b)) (dune)"
    ; "(lang hardcaml-workbench 1) (project (name demo)) (dune (mystery x))"
    ; "(lang hardcaml-workbench 1) (project (name demo)) (dune (driver ./../x.exe))"
    ; "(lang hardcaml-workbench 1) (project (name demo)) (dune (test_alias ../@x))"
    ]
    ~f:(fun input -> print_s [%sexp (manifest input : (Manifest.t, string) Result.t)]);
  [%expect
    {|
    (Error
     "lang: unsupported hardcaml-workbench manifest version 2 (supported: 1)")
    (Error "name: field is duplicated")
    (Error "dune.mystery: unknown field")
    (Error "dune.driver: expected ./path with no empty, '.' or '..' component")
    (Error
     "dune.test_alias: expected @name or path/@name with no empty, '.' or '..' path component") |}]
;;

let response ?(version = 1) ?(capabilities = [ "describe" ]) ?(targets = []) configs =
  { Driver_protocol.Describe_response.protocol_version = version
  ; capabilities
  ; targets
  ; configurations = configs
  }
;;

let%expect_test "driver compatibility distinguishes empty and unsupported" =
  let check value =
    let result =
      Driver_protocol.validate value
      |> Result.map ~f:(fun response -> List.length response.targets)
    in
    print_s ([%sexp_of: (int, string) Result.t] result)
  in
  check (response []);
  check (response ~capabilities:[ "future" ] []);
  check (response ~version:2 []);
  [%expect
    {|
    (Ok 0)
    (Error "driver does not advertise required capability describe")
    (Error "unsupported driver protocol version 2 (supported: 1)") |}]
;;

let%expect_test "driver validates keys and configuration references" =
  let target key : Driver_protocol.Target.t =
    { key
    ; name = "Counter"
    ; top = "counter"
    ; backend = "simulation"
    ; clocks = []
    ; facts = []
    }
  in
  let config target : Driver_protocol.Configuration.t =
    { key = "default"; target; name = "Default"; description = None }
  in
  List.iter
    [ response ~targets:[ target "bad/key" ] []
    ; response ~targets:[ target "counter"; target "counter" ] []
    ; response ~targets:[ target "counter" ] [ config "missing" ]
    ]
    ~f:(fun value ->
      print_s
        ([%sexp_of: (Driver_protocol.Describe_response.t, string) Result.t]
           (Driver_protocol.validate value)));
  [%expect
    {|
    (Error "target key \"bad/key\" is invalid")
    (Error "target key \"counter\" is duplicated")
    (Error "configuration \"default\" refers to unknown target key \"missing\"")
    |}]
;;

let%expect_test "driver framing rejects malformed and oversized stdout" =
  print_s
    [%sexp
      (Driver_protocol.parse "diagnostic before (())"
       : (Driver_protocol.Describe_response.t, string) Result.t)];
  print_s
    [%sexp
      (Driver_protocol.parse (String.make (Driver_protocol.max_stdout_bytes + 1) 'x')
       : (Driver_protocol.Describe_response.t, string) Result.t)];
  [%expect
    {|
    (Error
      "malformed driver describe response: (Failure\
     \n \"Sexplib.Sexp.of_string: got multiple S-expressions where only one was expected.\")")
    (Error "driver stdout exceeded 1048576 bytes")
    |}]
;;

let generate_response ?(path = "counter.v") ?(target = "counter") configuration =
  { Driver_protocol.Generate_rtl_response.protocol_version = 1
  ; target
  ; configuration
  ; outputs =
      [ { Driver_protocol.Output.path
        ; namespace = "hardcaml"
        ; name = "verilog"
        ; role = Artifact.Role.Deliverable
        ; media = Some "text/x-verilog"
        ; display_name = "counter.v"
        ; description = None
        }
      ]
  ; tools = [ { name = "ocaml"; version = Some "5.2.0" } ]
  ; build = None
  ; run = None
  }
;;

let%expect_test "generate-rtl validates request identity and output handoff" =
  let check response =
    let result =
      response
      |> Driver_protocol.Generate_rtl_response.sexp_of_t
      |> Sexp.to_string_mach
      |> Driver_protocol.parse_generate ~target:"counter" ~configuration:"four-bit"
      |> Result.map ~f:(fun response -> List.length response.outputs)
    in
    print_s ([%sexp_of: (int, string) Result.t] result)
  in
  check (generate_response "four-bit");
  check (generate_response ~target:"other" "four-bit");
  check (generate_response "eight-bit");
  check (generate_response ~path:"../escape.v" "four-bit");
  check { (generate_response "four-bit") with outputs = [] };
  [%expect
    {|
    (Ok 1)
    (Error "generate-rtl result target does not match the request")
    (Error "generate-rtl result configuration does not match the request")
    (Error "output path \"../escape.v\" is not a normalized relative path")
    (Error "generate-rtl result declared no outputs") |}]
;;
