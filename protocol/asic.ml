open! Core

module Selection = struct
  type t =
    { flow : string
    ; profile : string
    ; endpoint : string
    ; assignments : string list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Flow = struct
  type t =
    { id : string
    ; profiles : string list
    ; default_profile : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Reference = struct
  (** Exact public allocation references, never reconstructed from directory names. *)
  type t =
    { attempt : string
    ; stream_id : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Metric = struct
  (** Only explicitly understood public metrics are projected. [source] is JSON: the
      supplied stage source object, or terminal results path/hash/field plus complete
      supplied metric context and resolved source, or verified historical snapshot
      reference/configuration for a declared constraint. Checkpoint-wide stage attribution
      remains in [Summary.producer]. Unavailable is never zero or a pass. *)
  type t =
    { key : string
    ; label : string
    ; value : float option
    ; unit_ : string option
    ; availability : string
    ; source : string option
    }
  [@@deriving bin_io, compare, equal, sexp]

  let declared_clock_period_key = "declared_clock_period"
end

module Check = struct
  type t =
    { name : string
    ; status : string
    ; reason : string option
    ; source : string option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Terminal_result = struct
  type t =
    { attempt : string
    ; results_file : string
    ; results_digest : string
    ; operation_status : string
    ; physical_completion : string
    ; acceptance : string
    ; timing_goal : string
    ; metrics : Metric.t list
    ; checks : Check.t list
    ; evidence : string
    }
  [@@deriving bin_io, compare, equal, sexp]

  (** A declared constraint, not a measured clock. [None] also covers legacy caches whose
      terminal projection predates declared-clock evidence. *)
  let declared_clock_period (t : t) =
    List.find t.metrics ~f:(fun metric ->
      String.equal metric.Metric.key Metric.declared_clock_period_key)
  ;;
end

module Summary = struct
  module Freshness = struct
    type t =
      | Validated
      | Cached_unverified
      | Missing_source
      | Refresh_failed of string
    [@@deriving bin_io, compare, equal, sexp]
  end

  type t =
    { run : Run_ref.t
    ; source_digest : string
    ; execution_file : string
    ; plan_identity : string option
    ; cell_count : int option
    ; cells : (string * int) list
    ; metrics : Metric.t list [@sexp.default []]
    ; terminal : Terminal_result.t option [@sexp.default None]
    ; timing : (string * float * string) list
    ; completion : string
    ; acceptance : string
    ; producer : string
    ; observed_at : string
    ; freshness : Freshness.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Run = struct
  type t =
    { run : Run_ref.t
    ; reference : Reference.t
    ; selection : Selection.t option
    ; cursor : int
    ; status : string
    ; execution_file : string option
    ; error : string option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Pending = struct
  type t =
    { key : string
    ; kind : string
    ; state : string
    ; run : Run_ref.t option
    ; error : string option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Preview = struct
  type t =
    { selection : Selection.t
    ; plan_identity : string
    ; plan_json : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Snapshot = struct
  type t =
    { configured : bool
    ; flows : Flow.t list
    ; description_json : string option
    ; preview : Preview.t option
    ; runs : Run.t list
    ; operations : Pending.t list
    ; summaries : Summary.t list
    ; cache_error : string option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Operation = struct
  (** Queries schedule bounded/coalesced background work and return a snapshot promptly.
      Poll [Get] for completion. [Run.key] is an idempotency key; reuse with different
      arguments is an error. Disconnecting a client never cancels daemon-owned work.
      Summary selection does not launch tools. [Refresh] explicitly validates source
      evidence, including the last explicitly adopted finalization attempt. An ordinary
      [Load_summary] may return cached/unverified evidence. [Inspect_finalization] adopts
      an existing public operation reference; it never starts finalization. *)
  type t =
    | Get
    | Discover
    | Describe of string
    | Plan of Selection.t
    | Run of
        { key : string
        ; preview : Preview.t
        }
    | Register of Reference.t
    | Observe of Run_ref.t
    | Load_summary of Run_ref.t
    | Refresh of Run_ref.t
    | Inspect_finalization of
        { run : Run_ref.t
        ; attempt : string
        }
    | Cancel of string
  [@@deriving bin_io, compare, equal, sexp]
end

module Request = struct
  type t =
    { instance_id : V1.Daemon_instance_id.t
    ; project : Project_id.t
    ; operation : Operation.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Response = struct
  type t = (Snapshot.t, V1.Error.t) Result.t [@@deriving bin_io, compare, equal, sexp]
end
