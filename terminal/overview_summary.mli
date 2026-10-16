open! Core
open Hardcaml_workbench_protocol

(** Compact presentation over existing typed evidence. No IO, parsing producer JSON,
    guessed stage attribution, derived acceptance, or implicit requests. *)
val supports : string -> bool

(** [stage_id] is an exact provider identity; omitted defaults to [kind]. Foreign-run
    summaries are ignored. Aggregate metrics are explicitly labelled as such. Rows keep
    full run/digest/producer/source provenance in [details] for inspection. *)
val rows
  :  ?stage_id:string
  -> kind:string
  -> run:Run_ref.t
  -> summary:Asic.Summary.t option
  -> stages:Asic.Stage.t list
  -> unit
  -> Overview_tiles.row list
