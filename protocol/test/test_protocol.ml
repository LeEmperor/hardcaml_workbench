(** Checks on the shared protocol schemas.

    These cover the representation rules the architecture states, rather than the shape of
    any particular value: an unavailable metric must not read as a measurement, completion
    must not read as closure, and a dirty working tree must not read as an exact source
    identity. The round-trip checks exist because the schemas are derived for both sexp
    and bin_io before the transport is chosen, and a schema that serialized only one way
    would not be noticed until then. *)

open! Core
open Hardcaml_workbench_protocol

(** Values are printed with a label, so a block that asserts on several of them stays
    readable and a diff says which one moved. *)
let show label sexp = print_s [%message label ~_:(sexp : Sexp.t)]

let timestamp =
  Timestamp.of_time_ns (Time_ns.of_int_ns_since_epoch 1_700_000_000_000_000_000)
;;

let project_id = Project_id.of_string "project-1"
let target_id = Target_id.of_string "target-1"
let job_id = Job_id.of_string "job-1"
let artifact_id = Artifact_id.of_string "artifact-1"
let fpga = Backend_id.of_string "fpga"
let vivado = { Tool_version.tool = "vivado"; version = Some "2023.2" }

let project =
  { Project.id = project_id
  ; root = Project_root.of_absolute_path "/home/user/devel/mac"
  ; name = "mac"
  ; integration =
      { Project_integration.level = Manifest
      ; manifest = Available { version = Some 1 }
      ; driver = Unusable { reason = "driver executable failed to build" }
      }
  ; targets =
      [ { Target.id = target_id
        ; name = "mac"
        ; top = "Mac.create"
        ; backend = fpga
        ; clocks = [ { name = "clock_i"; period_ns = Some 4.0; description = None } ]
        ; facts =
            [ { namespace = "vivado"
              ; name = "part"
              ; value = String "xc7a100tcsg324-1"
              ; display = None
              }
            ]
        }
      ]
  ; configurations =
      [ { Configuration.id = Configuration_id.of_string "configuration-1"
        ; target = target_id
        ; name = "default"
        ; description = None
        }
      ]
  }
;;

let%expect_test "a generic Dune project has no targets, which is not a discovery failure" =
  let generic =
    { project with
      integration = Project_integration.generic_dune
    ; targets = []
    ; configurations = []
    }
  in
  show "integration" [%sexp (generic.integration : Project_integration.t)];
  show "targets are empty" [%sexp (List.is_empty generic.targets : bool)];
  [%expect
    {|
    (integration ((level Generic_dune) (manifest Absent) (driver Absent)))
    ("targets are empty" true)
    |}]
;;

let%expect_test "an unusable driver degrades the integration level, not the project" =
  let level =
    Project_integration.level_of_components
      ~manifest:(Available { version = Some 1 })
      ~driver:(Unusable { reason = "driver executable failed to build" })
  in
  show "level" [%sexp (level : Project_integration.Level.t)];
  show "declared level" [%sexp (project.integration.level : Project_integration.Level.t)];
  [%expect {|
    (level Manifest)
    ("declared level" Manifest)
    |}]
;;

let%expect_test "an undeclared target fact is unknown rather than defaulted" =
  let target = List.hd_exn project.targets in
  show
    "declared part"
    [%sexp (Target.fact target ~namespace:"vivado" ~name:"part" : Target_fact.t option)];
  show
    "undeclared technology"
    [%sexp
      (Target.fact target ~namespace:"asic" ~name:"technology" : Target_fact.t option)];
  [%expect
    {|
    ("declared part"
     (((namespace vivado) (name part) (value (String xc7a100tcsg324-1))
       (display ()))))
    ("undeclared technology" ())
    |}]
;;

let%expect_test "a project round-trips through sexp" =
  show
    "equal after round trip"
    [%sexp (Project.equal project (Project.t_of_sexp (Project.sexp_of_t project)) : bool)];
  [%expect {| ("equal after round trip" true) |}]
;;

let%expect_test "an unavailable metric is neither zero nor a pass" =
  let missing =
    { Metric.name = "worst_negative_slack"
    ; value = Unavailable { reason = "timing report not produced: implementation failed" }
    ; unit = Some "ns"
    ; tool = vivado
    ; stage = "implementation"
    ; corner = Some "slow"
    ; source = None
    }
  in
  show "value is available" [%sexp (Metric.Value.is_available missing.value : bool)];
  show "value" [%sexp (missing.value : Metric.Value.t)];
  [%expect
    {|
    ("value is available" false)
    (value
     (Unavailable (reason "timing report not produced: implementation failed")))
    |}]
;;

let%expect_test "completion, goals, and verification stay separate" =
  let result =
    { Structured_result.completion =
        [ { name = "synthesis"; requested = true; status = Completed }
        ; { name = "implementation"; requested = true; status = Completed }
        ; { name = "drc"; requested = false; status = Not_run }
        ]
    ; goals =
        [ { Metric.name = "worst_negative_slack"
          ; value = Float (-0.312)
          ; unit = Some "ns"
          ; tool = vivado
          ; stage = "implementation"
          ; corner = Some "slow"
          ; source = Some artifact_id
          }
        ]
    ; verification =
        [ { Check.name = "drc"
          ; status = Not_run { reason = "not requested" }
          ; tool = vivado
          ; stage = "implementation"
          ; source = None
          }
        ]
    }
  in
  (* Every requested stage finished, and the design still missed timing and was never
     checked. A single job status would have to misreport two of the three. *)
  show
    "every requested stage completed"
    [%sexp (Structured_result.all_requested_stages_completed result : bool)];
  show
    "goals"
    [%sexp (List.map result.goals ~f:(fun metric -> metric.value) : Metric.Value.t list)];
  show
    "verification"
    [%sexp
      (List.map result.verification ~f:(fun check -> check.status) : Check.Status.t list)];
  [%expect
    {|
    ("every requested stage completed" true)
    (goals ((Float -0.312)))
    (verification ((Not_run (reason "not requested"))))
    |}]
;;

let%expect_test "a dirty working tree does not identify the inputs" =
  let dirty =
    { Provenance.Source_identity.git_commit = Some "0b5e1c9"
    ; working_tree = Dirty
    ; design_hash = Some "sha256:2f1a"
    ; preserved_inputs = [ artifact_id ]
    }
  in
  show
    "dirty tree identifies inputs"
    [%sexp (Provenance.Source_identity.identifies_inputs_exactly dirty : bool)];
  show
    "clean tree identifies inputs"
    [%sexp
      (Provenance.Source_identity.identifies_inputs_exactly
         { dirty with working_tree = Clean }
       : bool)];
  show
    "inputs preserved for reproduction"
    [%sexp (dirty.preserved_inputs : Artifact_id.t list)];
  [%expect
    {|
    ("dirty tree identifies inputs" false)
    ("clean tree identifies inputs" true)
    ("inputs preserved for reproduction" (artifact-1))
    |}]
;;

let provenance =
  { Provenance.project_root = project.root
  ; target = Some target_id
  ; configuration = None
  ; build = None
  ; run = None
  ; generating_job = job_id
  ; requested_tools = [ { Tool_version.tool = "vivado"; version = Some "2023.1" } ]
  ; actual_tools = [ vivado ]
  ; environment =
      [ { Environment_identity.component = "os"; identity = Some "ubuntu-24.04" } ]
  ; source = Provenance.Source_identity.unknown ~reason:"root is not version controlled"
  ; created_at = timestamp
  }
;;

let%expect_test "requested and actual tool versions stay distinguishable" =
  show "requested" [%sexp (provenance.requested_tools : Tool_version.t list)];
  show "actual" [%sexp (provenance.actual_tools : Tool_version.t list)];
  [%expect
    {|
    (requested (((tool vivado) (version (2023.1)))))
    (actual (((tool vivado) (version (2023.2)))))
    |}]
;;

let artifact =
  { Artifact.id = artifact_id
  ; kind =
      { namespace = "vivado"
      ; name = "timing_summary"
      ; role = Report
      ; media = Some "text/plain"
      }
  ; project = project_id
  ; target = Some target_id
  ; configuration = None
  ; generating_job = job_id
  ; build = None
  ; run = None
  ; availability = Available
  ; metadata =
      { display_name = "Timing summary"
      ; description = None
      ; size_in_bytes = Some 18_204
      ; provenance
      }
  }
;;

let%expect_test "an artifact exposes no filesystem location" =
  (* The project root appears in provenance because it is how a user recognizes which
     checkout a result came from. No path below it may appear anywhere in the value: an
     artifact is retrieved from the daemon by identifier. *)
  let serialized = Sexp.to_string (Artifact.sexp_of_t artifact) in
  show
    "mentions a path below the root"
    [%sexp (String.is_substring serialized ~substring:"/home/user/devel/mac/" : bool)];
  show "retrieved by" [%sexp (artifact.id : Artifact_id.t)];
  [%expect
    {|
    ("mentions a path below the root" false)
    ("retrieved by" artifact-1)
    |}]
;;

let%expect_test "an artifact round-trips through sexp and bin_io" =
  show
    "equal after sexp round trip"
    [%sexp
      (Artifact.equal artifact (Artifact.t_of_sexp (Artifact.sexp_of_t artifact)) : bool)];
  let buffer = Bin_prot.Common.create_buf (Artifact.bin_size_t artifact) in
  let written = Artifact.bin_write_t buffer ~pos:0 artifact in
  let read_back = Artifact.bin_read_t buffer ~pos_ref:(ref 0) in
  show "bin_io wrote bytes" [%sexp (written > 0 : bool)];
  show "equal after bin_io round trip" [%sexp (Artifact.equal artifact read_back : bool)];
  [%expect
    {|
    ("equal after sexp round trip" true)
    ("bin_io wrote bytes" true)
    ("equal after bin_io round trip" true)
    |}]
;;

let job =
  Job.create
    ~id:job_id
    ~kind:{ Job.Kind.namespace = "dune"; name = "build" }
    ~project:project_id
    ~created_at:timestamp
;;

let%expect_test "a submitted job starts queued with nothing claimed about its outcome" =
  show "state" [%sexp (job.state : Job.State.t)];
  show "exit status" [%sexp (job.exit_status : Job.Exit_status.t option)];
  show "structured result" [%sexp (job.result : Structured_result.t option)];
  show "is terminal" [%sexp (Job.is_terminal job : bool)];
  [%expect
    {|
    (state Queued)
    ("exit status" ())
    ("structured result" ())
    ("is terminal" false)
    |}]
;;

let%expect_test "a launch failure is distinguishable from a nonzero exit" =
  let launch_failed =
    { job with
      state = Failed
    ; exit_status = Some (Launch_failed { reason = "dune: command not found" })
    ; finished_at = Some timestamp
    }
  in
  let exited_nonzero =
    { job with
      state = Failed
    ; exit_status = Some (Exited 1)
    ; finished_at = Some timestamp
    }
  in
  show "launch failed" [%sexp (launch_failed.exit_status : Job.Exit_status.t option)];
  show "exited nonzero" [%sexp (exited_nonzero.exit_status : Job.Exit_status.t option)];
  show
    "the two compare equal"
    [%sexp
      (Option.equal
         Job.Exit_status.equal
         launch_failed.exit_status
         exited_nonzero.exit_status
       : bool)];
  [%expect
    {|
    ("launch failed" ((Launch_failed (reason "dune: command not found"))))
    ("exited nonzero" ((Exited 1)))
    ("the two compare equal" false)
    |}]
;;

let%expect_test "a job round-trips through sexp" =
  let job = { job with state = Running; started_at = Some timestamp } in
  show
    "equal after round trip"
    [%sexp (Job.equal job (Job.t_of_sexp (Job.sexp_of_t job)) : bool)];
  [%expect {| ("equal after round trip" true) |}]
;;
