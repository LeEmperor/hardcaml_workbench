(** Compatibility entry point; all geometry now lives alongside the OCaml preset
    definitions. New callers should use [Layout.compute] with a stable preset. *)
module Shared = Hardcaml_workbench_workspaces

type t = Shared.Layout.t =
  | Grid of Hardcaml_workbench_protocol.Workspace.Geometry.t list
  | Compact

let compute ~width ~height ~kinds =
  Shared.Layout.compute Shared.Overview.definition ~width ~height ~kinds
;;
