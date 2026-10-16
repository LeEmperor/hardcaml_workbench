open! Core
open! Async
open Hardcaml_workbench_protocol

type t

(** One service per daemon; no I/O until [handle]. State directory must be absolute,
    single-writer and separate from provider results. *)
val create : state_dir:string -> t

(** Parent validates instance/project before calling. Provider work is scheduled;
    subsequent [Get] snapshots expose completion. Client detach never cancels work. *)
val handle
  :  t
  -> root:string
  -> environment:V1.Environment_selection.t
  -> Asic.Operation.t
  -> Asic.Response.t Deferred.t

(** Await current work, including readers spawned by outstanding allocations. Intended for
    acceptance/barriers, not the interactive read path. *)
val completion : t -> unit Deferred.t

(** Pure, already-loaded observation for a reservation fence. Never loads configuration,
    starts work, waits or performs I/O. *)
val peek_snapshot
  :  t
  -> root:string
  -> environment:V1.Environment_selection.t
  -> Asic.Snapshot.t option

(** Daemon shutdown only: cancel and reap owned processes and flush registry writes.
    Historical producers are never signalled by reader cancellation/shutdown. *)
val shutdown : t -> unit Deferred.t
