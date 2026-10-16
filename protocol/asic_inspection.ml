open! Core

module Row = struct
  type t =
    { id : string
    ; category : string
    ; producer : string
    ; corner : string option
    ; group : string option
    ; name : string
    ; value : float option
    ; unit_ : string option
    ; status : string
    ; source : string
    ; fields : (string * string) list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Index = struct
  type t =
    { run : Run_ref.t
    ; execution_file : string
    ; execution_sha256 : string
    ; domain : string
    ; stage : string
    ; source_digest : string
    ; rows : Row.t list
    ; diagnostics : string list
    ; truncated : bool
    ; cached_unverified : bool
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Detail = struct
  type t =
    { run : Run_ref.t
    ; domain : string
    ; stage : string
    ; source_digest : string
    ; row_id : string
    ; text : string
    ; error : string option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

(** Canonical sexp identities avoid collisions from punctuation in run/row IDs. All
    consumers use these same keys for scheduling and completion waits. *)
let index_key ~run ~domain ~stage =
  "inspection:"
  ^ Sexp.to_string_mach [%sexp (run : Run_ref.t), (domain : string), (stage : string)]
;;

let detail_key ~run ~domain ~stage ~source_digest ~row_id =
  "inspection-detail:"
  ^ Sexp.to_string_mach
      [%sexp
        (run : Run_ref.t)
        , (domain : string)
        , (stage : string)
        , (source_digest : string)
        , (row_id : string)]
;;
