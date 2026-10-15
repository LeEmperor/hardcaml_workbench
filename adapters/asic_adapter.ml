open! Core
open Hardcaml_workbench_protocol
module Config = Hardcaml_workbench_project_integration.Asic_config

let invocation ~root ~environment executable args : Dune_adapter.Invocation.t =
  let argv = Dune_adapter.command_prefix environment @ (executable :: args) in
  { executable = List.hd_exn argv; argv; cwd = root; environment }
;;

let project config ~root ~environment args =
  invocation ~root ~environment config.Config.project_executable ("flow" :: args)
;;

let provider config ~root ~environment args =
  invocation ~root ~environment config.Config.provider_executable args
;;

let discover config ~root ~environment =
  project config ~root ~environment [ "list"; "--json" ]
;;

let describe config ~root ~environment flow =
  project config ~root ~environment [ "describe"; "--flow"; flow; "--json" ]
;;

let selection_args ~root (s : Asic.Selection.t) =
  [ "--flow"
  ; s.flow
  ; "--profile"
  ; s.profile
  ; "--endpoint"
  ; s.endpoint
  ; "--source-root"
  ; root
  ; "--json"
  ]
  @ List.concat_map s.assignments ~f:(fun value -> [ "--set"; value ])
;;

let plan config ~root ~environment selection =
  project config ~root ~environment ("plan" :: selection_args ~root selection)
;;

let run config ~root ~environment (preview : Asic.Preview.t) =
  let optional flag value =
    Option.value_map value ~default:[] ~f:(fun v -> [ flag; v ])
  in
  project
    config
    ~root
    ~environment
    ([ "run" ]
     @ selection_args ~root preview.selection
     @ [ "--expected-plan-identity"
       ; preview.plan_identity
       ; "--provider"
       ; config.Config.provider_executable
       ; "--results-root"
       ; config.results_root
       ; "--toolchain"
       ; config.toolchain
       ]
     @ optional "--python" config.python
     @ optional "--support-tools" config.support_tools
     @ optional "--pdk-root" config.pdk_root
     @ optional "--timeout" (Option.map config.stage_timeout_seconds ~f:Int.to_string))
;;

let metadata config ~root ~environment =
  provider config ~root ~environment [ "--version"; "--json" ]
;;

let inspect config ~root ~environment (r : Asic.Reference.t) =
  provider config ~root ~environment [ "observation"; "inspect"; r.attempt; "--json" ]
;;

let updates config ~root ~environment (r : Asic.Reference.t) ~after =
  provider
    config
    ~root
    ~environment
    [ "observation"
    ; "read-updates"
    ; r.attempt
    ; "--stream-id"
    ; r.stream_id
    ; "--after"
    ; Int.to_string after
    ; "--json"
    ]
;;

let report config ~root ~environment execution_file =
  provider config ~root ~environment [ "report"; execution_file; "--json" ]
;;

let inspect_finalization config ~root ~environment attempt =
  provider config ~root ~environment [ "finalization-inspect"; attempt; "--json" ]
;;
