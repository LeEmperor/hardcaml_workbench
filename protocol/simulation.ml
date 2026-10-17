open! Core

(** FS2 v1. Provider framing and lifecycle rules are frozen in
    [docs/fs2_simulation_contract.md]. No OS or scheduler behavior belongs here. *)
let version = 1

let rpc_path = "/api/v1/simulation"

module Limits = struct
  let config_bytes = 16 * 1024
  let discovery_bytes = 1024 * 1024
  let suites = 64
  let cases = 1024
  let parameters = 32
  let key_bytes = 128
  let string_bytes = 4096
  let event_bytes = 16 * 1024
  let stream_bytes = 16 * 1024 * 1024
  let events = 100_000
  let retained_events = 256
  let artifacts = 128
  let artifact_bytes = 64 * 1024 * 1024
  let attempt_artifact_bytes = 256 * 1024 * 1024
  let byte_page = 64 * 1024
  let history_attempts = 100
  let history_bytes = 16 * 1024 * 1024
  let history_artifact_bytes = 512 * 1024 * 1024
  let history_page = 25
end

module Parameter = struct
  type t =
    { key : string
    ; label : string
    ; default : string
    ; choices : string list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Case = struct
  type t =
    { id : string
    ; label : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Suite = struct
  type t =
    { id : string
    ; label : string
    ; cases : Case.t list
    ; parameters : Parameter.t list
    ; default_seed : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Discovery = struct
  type t =
    { protocol_version : int
    ; suites : Suite.t list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Asic_input = struct
  (** Explicit evidence only; never inferred from a terminal's current selection. *)
  type t =
    { run : Run_ref.t
    ; attempt : string
    ; artifact_id : string
    ; sha256 : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Selection = struct
  type t =
    { suite : string
    ; cases : string list
    ; seed : string
    ; parameters : (string * string) list
    ; asic_inputs : Asic_input.t list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Parent = struct
  type t =
    { attempt_id : string
    ; job : Job_id.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Captured = struct
  type t =
    { selection : Selection.t
    ; discovery_digest : string
    ; provider_executable : string
    ; provider_args : string list
    ; environment : V1.Environment_selection.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Case_status = struct
  type t =
    | Pending
    | Running
    | Passed
    | Failed
    | Skipped
    | Incomplete
  [@@deriving bin_io, compare, equal, sexp]
end

module Outcome = struct
  type t =
    | Unknown
    | Passed
    | Failed
    | Incomplete
  [@@deriving bin_io, compare, equal, sexp]
end

module Lifecycle = struct
  type t =
    | Queued
    | Running
    | Finished
    | Cancelled
    | Interrupted
  [@@deriving bin_io, compare, equal, sexp]
end

module Progress = struct
  type t =
    { case_id : string option
    ; completed : int
    ; total : int option
    ; unit_ : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Provider = struct
  module Request = struct
    type t =
      { protocol_version : int
      ; attempt_id : string
      ; selection : Selection.t
      }
    [@@deriving bin_io, compare, equal, sexp]
  end

  module Artifact = struct
    type t =
      { id : string
      ; case_id : string option
      ; label : string
      ; kind : string
      ; media_type : string
      ; path : string
      }
    [@@deriving bin_io, compare, equal, sexp]
  end

  module Event = struct
    module Case_finished = struct
      type t =
        { case_id : string
        ; status : Case_status.t
        ; message : string option
        }
      [@@deriving bin_io, compare, equal, sexp]
    end

    type payload =
      | Started
      | Case_started of string
      | Progress of Progress.t
      | Case_finished of Case_finished.t
      | Artifact of Artifact.t
      | Finished of Outcome.t
    [@@deriving bin_io, compare, equal, sexp]

    type t =
      { protocol_version : int
      ; attempt_id : string
      ; sequence : int
      ; payload : payload
      }
    [@@deriving bin_io, compare, equal, sexp]
  end
end

module Artifact = struct
  module Availability = struct
    type t =
      | Available
      | Missing
      | Changed
      | Rejected of string
    [@@deriving bin_io, compare, equal, sexp]
  end

  type t =
    { id : string
    ; attempt_id : string
    ; case_id : string option
    ; label : string
    ; kind : string
    ; media_type : string
    ; size : int option
    ; sha256 : string option
    ; availability : Availability.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Case_result = struct
  type t =
    { case_id : string
    ; status : Case_status.t
    ; message : string option
    ; progress : Progress.t option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Attempt = struct
  type t =
    { id : string
    ; job : Job_id.t
    ; project_root : string
    ; created_at : string
    ; parent : Parent.t option
    ; captured : Captured.t
    ; lifecycle : Lifecycle.t
    ; outcome : Outcome.t
    ; exit_code : int option
    ; diagnostic : string option
    ; progress : Progress.t option
    ; cases : Case_result.t list
    ; artifacts : Artifact.t list
    ; next_sequence : int
    ; recent_events : Provider.Event.t list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Summary = struct
  type t =
    { id : string
    ; job : Job_id.t
    ; suite : string
    ; seed : string
    ; created_at : string
    ; parent : Parent.t option
    ; lifecycle : Lifecycle.t
    ; outcome : Outcome.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Byte_page = struct
  type t =
    { attempt_id : string
    ; artifact_id : string
    ; sha256 : string
    ; offset : int
    ; next_offset : int
    ; total_size : int
    ; eof : bool
    ; bytes_hex : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Operation = struct
  type t =
    | Get
    | Discover
    | Launch of
        { submission_key : string
        ; discovery_digest : string
        ; selection : Selection.t
        }
    | Rerun of
        { submission_key : string
        ; attempt_id : string
        ; cases : string list
        }
    | Observe of string
    | History of
        { before : string option
        ; limit : int
        }
    | Cancel of string
    | Read_artifact_bytes of
        { attempt_id : string
        ; artifact_id : string
        ; sha256 : string
        ; offset : int
        ; limit : int
        }
  [@@deriving bin_io, compare, equal, sexp]
end

module Snapshot = struct
  type t =
    { configured : bool
    ; discovery : Discovery.t option
    ; discovery_digest : string option
    ; discovery_job : Job_id.t option
    ; discovery_error : string option
    ; attempts : Summary.t list
    ; next_before : string option
    ; detail : Attempt.t option
    ; byte_page : Byte_page.t option
    ; history_error : string option
    }
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
