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

module Stage = struct
  module Status = struct
    type t =
      | Pending
      | Running
      | Completed
      | Failed
      | Skipped
      | Cancelled
      | Not_requested
      | Unsupported
      | Unknown of string
    [@@deriving bin_io, compare, equal, sexp]
  end

  (** Explicit provider observations only. An action prepares a new named-flow run through
      its endpoint using ordinary [Plan]/[Run], never a restart in this run. *)
  type t =
    { id : string
    ; name : string
    ; status : Status.t
    ; requested : bool
    ; reason : string option
    ; action : Selection.t option
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
    ; stages : Stage.t list [@sexp.default []]
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

module Acceptance = struct
  type t =
    { support_tools : string
    ; precheck_python : string
    ; testbench : string
    ; testbench_top : string
    ; replay_trace : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Finalization = struct
  type t =
    { key : string
    ; run : Run_ref.t
    ; execution_file : string
    ; acceptance_requested : bool
    ; attempt : string option
    ; state : string
    ; phase : string option
    ; operation_status : string option
    ; acceptance : string option
    ; error : string option
    ; owned : bool
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
    ; finalizations : Finalization.t list [@sexp.default []]
    ; artifacts : Asic_artifact.Reference.t list [@sexp.default []]
    ; artifact_pages : Asic_artifact.Page.t list [@sexp.default []]
    ; artifact_byte_pages : Asic_artifact.Byte_page.t list [@sexp.default []]
    ; inspections : Asic_inspection.Index.t list [@sexp.default []]
    ; inspection_details : Asic_inspection.Detail.t list [@sexp.default []]
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
      an existing public operation reference; it never starts finalization. [Finalize]
      reserves exact inputs persistently before scheduling the sole owned producer.
      [Observe_finalization] is read-only and never reacquires process ownership.
      [Inspect] with [refresh=false] uses the bounded derived inspection cache or a
      bounded cold public read; [refresh=true] revalidates public evidence. Neither starts
      EDA. [Inspect_detail] fences the exact index digest and row. Artifact reads accept
      only catalog IDs for the current adopted terminal attempt, never client paths. *)
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
    | Finalize of
        { key : string
        ; run : Run_ref.t
        ; execution_file : string
        ; acceptance : Acceptance.t option
        }
    | Observe_finalization of string
    | List_artifacts of Run_ref.t
    | Inspect of
        { run : Run_ref.t
        ; domain : string
        ; stage : string
        ; refresh : bool
        }
    | Inspect_detail of
        { run : Run_ref.t
        ; domain : string
        ; stage : string
        ; source_digest : string
        ; row_id : string
        }
    | Read_artifact_bytes of
        { run : Run_ref.t
        ; artifact_id : string
        ; offset : int
        ; limit : int
        }
    | Read_artifact of
        { run : Run_ref.t
        ; artifact_id : string
        ; offset : int
        ; limit : int
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
