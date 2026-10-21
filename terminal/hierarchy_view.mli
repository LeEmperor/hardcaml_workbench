open! Core
open Hardcaml_workbench_protocol

(** Shared, immutable structural evidence. Build once per loaded artifact, then share
    between independent consumers. This is a display index, not protocol validation;
    callers must retain the existing bounded reader and identity checks. *)
type evidence

(** Immutable, artifact-scoped navigation. *)
type t

val evidence : Hierarchy.t -> evidence

(** Start at the declared root, initially expanded. *)
val create : evidence -> t

(** Original evidence, including the elaboration top and exact provenance. *)
val hierarchy : t -> Hierarchy.t

val selected_key : t -> string
val selected_node : t -> Hierarchy.Node.t option
val move : t -> int -> t
val toggle : t -> t
val visible : t -> (int * Hierarchy.Node.t) list

(** At most [height] compact tree rows, including the selected node when it exists and
    [height > 0]. Labels are terminal-safe; original evidence is preserved. *)
val rows : t -> height:int -> string list

(** Select a reachable key in this artifact, expanding its ancestors. Unknown keys leave
    the view unchanged; keys are never resolved across artifacts. *)
val select : t -> string -> t
