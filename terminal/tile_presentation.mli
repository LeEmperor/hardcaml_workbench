open! Core

module Badge : sig
  type t =
    | Exceptions
    | Always
    | Hidden
  [@@deriving equal, sexp]
end

type t =
  { header : bool
  ; title : bool
  ; badge : Badge.t
  ; run_reference : bool
  ; freshness : bool
  ; hints : bool
  ; frame : bool
  ; padding : int
  ; run_selector_rows : int
  }
[@@deriving equal, sexp]

(** [None] inherits, including after a runtime reset-to-inherit. These are appearance
    values only; the host owns their lifetime and must not mutate semantic bindings. *)
type overrides =
  { header : bool option
  ; title : bool option
  ; badge : Badge.t option
  ; run_reference : bool option
  ; freshness : bool option
  ; hints : bool option
  ; frame : bool option
  ; padding : int option
  ; run_selector_rows : int option
  }
[@@deriving equal, sexp]

val inherit_ : overrides
val defaults : t
val navigation : overrides
val apply : t -> overrides -> t
val resolve : app:overrides -> workspace:overrides -> tile:overrides -> t

module Binding : sig
  (** Presentation facts supplied by the host, never inferred from available evidence. *)
  type t =
    | Follow
    | Pinned
    | Project
  [@@deriving equal, sexp]
end

val show_badge : t -> Binding.t -> bool

(** Badge visibility is independent of the header/title: hiding a heading must not
    implicitly hide a pin. Put visible badges in a separate row when header is off. *)
val show_title : t -> bool
