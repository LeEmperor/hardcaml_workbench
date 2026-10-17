open! Core
open Hardcaml_workbench_protocol

(** Explicit provider actions take priority. Otherwise replace only the endpoint of
    captured remembered/observed inputs, or use the declared catalog default pair. No
    status-based endpoint guesses, effects, or fallback from stale selections. *)
val resolve
  :  stage:Asic.Stage.t
  -> remembered:Asic.Selection.t option
  -> observed:Asic.Selection.t option
  -> snapshot:Asic.Snapshot.t option
  -> (Asic.Selection.t, string) Result.t
