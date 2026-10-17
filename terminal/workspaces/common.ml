open! Core
open Hardcaml_workbench_protocol

(** Sparse, terminal-independent presentation defaults. [None] inherits app policy. These
    never create providers, change binding, or carry backend evidence. *)
type presentation =
  { title : bool option
  ; binding_badge : string option
  ; run_reference : bool option
  ; freshness : bool option
  ; hints : bool option
  ; frame : bool option
  ; padding : int option
  ; visible_rows : int option
  ; compact_summary : bool option [@sexp.default None]
  ; horizontal_stages : bool option [@sexp.default None]
  }
[@@deriving sexp]

type tile =
  { kind : string
  ; geometry : Workspace.Geometry.t
  ; presentation : presentation
  }
[@@deriving sexp]

let inherit_presentation =
  { title = None
  ; binding_badge = None
  ; run_reference = None
  ; freshness = None
  ; hints = None
  ; frame = None
  ; padding = None
  ; visible_rows = None
  ; compact_summary = None
  ; horizontal_stages = None
  }
;;

let tile ?(width = 80) ?(height = 10) ?(presentation = inherit_presentation) kind =
  { kind; geometry = { Workspace.Geometry.x = 0; y = 0; width; height }; presentation }
;;

let navigation =
  tile
    ~height:1
    ~presentation:
      { inherit_presentation with
        title = Some false
      ; binding_badge = Some "hidden"
      ; hints = Some false
      ; frame = Some false
      ; padding = Some 0
      }
    "workspace-tabs"
;;

let session = tile ~width:28 ~height:7 "live-status"

let selector =
  tile
    ~height:7
    ~presentation:{ inherit_presentation with visible_rows = Some 4 }
    "run-selector"
;;

let checklist = tile ~width:28 ~height:10 "stage-checklist"

(** Composable slicing tree. A leaf claims the first unclaimed occurrence of its kind.
    Remaining duplicate/custom tiles are placed as extras, never discarded. *)
type tree =
  | Leaf of
      { kind : string
      ; min_width : int
      ; min_height : int
      ; weight : int
      }
  | Stack of tree list
  | Columns of tree list
  | Weighted_columns of (int * tree) list
  | Narrow of tree
[@@deriving sexp]

let leaf ?(height = 6) ?(weight = 1) kind =
  Leaf { kind; min_width = 24; min_height = height; weight }
;;

let navigation_leaf = leaf ~height:1 ~weight:0 "workspace-tabs"
let session_leaf = leaf ~height:7 ~weight:0 "live-status"
let selector_leaf = leaf ~height:7 ~weight:0 "run-selector"
let checklist_leaf = leaf ~height:9 "stage-checklist"

let shell ~sidebar ~evidence =
  Stack
    [ navigation_leaf
    ; Columns
        [ Narrow (Stack (session_leaf :: sidebar))
        ; Stack [ selector_leaf; Stack evidence ]
        ]
    ]
;;
