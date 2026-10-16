open! Core
open Hardcaml_workbench_protocol
module Wire = Hardcaml_workbench_protocol.Asic_inspection

val index_limit : int
val detail_limit : int
val validate_selection : domain:string -> stage:string -> unit
val validate_digest : string -> unit
val validate_row_id : string -> unit
val execution_hash : registered:Asic.Run.t -> execution_file:string -> string

val parse_index
  :  registered:Asic.Run.t
  -> execution_file:string
  -> execution_sha256:string
  -> domain:string
  -> stage:string
  -> Yojson.Safe.t
  -> Wire.Index.t

val parse_detail
  :  registered:Asic.Run.t
  -> index:Wire.Index.t
  -> row_id:string
  -> Yojson.Safe.t
  -> Wire.Detail.t

(** Synchronous bounded L2 IO; callers serialize publication and run in a worker thread.
    Cache files use nonblocking descriptor opens, regular-file validation, and an actual
    read-byte budget, including growth after the descriptor's initial size check. This
    cache lookup never contacts the provider or requires source files to remain available.
    The service's explicit [Inspect] action uses a valid L1/L2 entry when [refresh=false],
    falling back to a bounded read-only provider query on a cache miss or invalid entry.
    [refresh=true] always queries. Rendering never loads inspection. *)
val load
  :  state_dir:string
  -> identity:string
  -> run:Run_ref.t
  -> execution_file:string
  -> domain:string
  -> stage:string
  -> Wire.Index.t

(** [rebuild_invalid] permits an explicit provider-backed inspection read to atomically
    replace a corrupt derived cache after validating the new index and execution bytes.
    Ordinary cache IO retains strict corruption errors. *)
val save
  :  ?rebuild_invalid:bool
  -> state_dir:string
  -> identity:string
  -> Wire.Index.t
  -> unit
