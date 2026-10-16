open! Core
open Hardcaml_workbench_protocol

(** Explicit synthetic evidence shared by the actual-renderer tests and FS0 frame
    captures. This module is never used to populate a connected session. *)
let run_a : Run_ref.t =
  { backend = Backend_id.of_string "asic"; id = "fixture-A"; build = None; label = None }
;;

let run_b = { run_a with id = "fixture-B" }

let execution_file (run : Run_ref.t) =
  "/explicit/synthetic/fs0/" ^ run.id ^ "/execution.sexp"
;;

let run run : Asic.Run.t =
  { run
  ; reference = { attempt = "/explicit/synthetic/fs0/" ^ run.id; stream_id = run.id }
  ; selection = None
  ; cursor = 1
  ; status = "completed"
  ; execution_file = Some (execution_file run)
  ; error = None
  }
;;

let summary run cell_count cells : Asic.Summary.t =
  { run
  ; source_digest = "synthetic-digest-" ^ run.Run_ref.id
  ; execution_file = execution_file run
  ; plan_identity = None
  ; cell_count = Some cell_count
  ; cells
  ; timing = []
  ; metrics = []
  ; terminal = None
  ; completion = "completed"
  ; acceptance = "not evaluated (synthetic fixture)"
  ; producer = "SYNTHETIC FS0 FIXTURE"
  ; observed_at = "fixed fixture observation"
  ; freshness = Cached_unverified
  }
;;

let snapshot : Asic.Snapshot.t =
  { configured = true
  ; flows = []
  ; description_json = None
  ; preview = None
  ; runs = [ run run_a; run run_b ]
  ; operations = []
  ; summaries =
      [ summary run_a 50 [ "NAND2", 35; "DFF", 15 ]
      ; summary run_b 73 [ "NAND2", 50; "DFF", 23 ]
      ]
  ; cache_error = None
  ; finalizations = []
  ; artifacts = []
  ; artifact_pages = []
  ; artifact_byte_pages = []
  ; inspections = []
  ; inspection_details = []
  }
;;
