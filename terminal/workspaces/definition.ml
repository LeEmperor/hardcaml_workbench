open! Core
open Hardcaml_workbench_protocol

type t =
  { id : string
  ; name : string
  ; tiles : Common.tile list
  ; layout : Common.tree
  }
[@@deriving sexp]

let specs t = List.map t.tiles ~f:(fun tile -> tile.Common.kind, tile.geometry)

let template t : Workspace_template.t =
  { version = Workspace_template.version
  ; name = t.name
  ; preset = Some t.id
  ; views =
      List.map t.tiles ~f:(fun tile ->
        let g = tile.Common.geometry in
        { Workspace_template.View.kind = tile.kind
        ; hidden = false
        ; geometry = { x = g.x; y = g.y; width = g.width; height = g.height }
        })
  }
;;

let apply t ~workspace =
  Workspace.Mutation.Apply_preset { workspace; preset = t.id; tiles = specs t }
;;

let reset t ~workspace =
  Workspace.Mutation.Reset_arrangement { workspace; preset = t.id; tiles = specs t }
;;

let restore t ~workspace =
  Workspace.Mutation.Restore_default_layout { workspace; preset = t.id; tiles = specs t }
;;

let presentation t ~kind =
  List.find_map t.tiles ~f:(fun tile ->
    if String.equal kind tile.Common.kind then Some tile.presentation else None)
;;
