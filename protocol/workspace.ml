(** Authoritative project-session state, independent of provider files and client
    navigation. IDs survive restart. [revision] orders all accepted mutations; context
    [selection_revision] orders selection within one context. Clients must capture both
    context identity and revision for queries, and discard responses whose
    binding/selection no longer matches. Requested geometry is persisted; dimensions,
    clamping, focus, browsing/filter/scroll and active workspace are local.

    RPC: validate instance/project before passing [operation] to the workspace service
    with a stable root/environment project key. [Get] also bootstraps a session with
    Overview and Timing linked to Main. *)
open! Core

module Session_id = Id.Make (struct
    let module_name = "Workspace.Session_id"
  end)

module Window_id = Id.Make (struct
    let module_name = "Workspace.Window_id"
  end)

module Workspace_id = Id.Make (struct
    let module_name = "Workspace.Workspace_id"
  end)

module Tile_id = Id.Make (struct
    let module_name = "Workspace.Tile_id"
  end)

module Context_id = Id.Make (struct
    let module_name = "Workspace.Context_id"
  end)

module Geometry = struct
  type t =
    { x : int
    ; y : int
    ; width : int
    ; height : int
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Binding = struct
  (** A pinned run remains a live provider reference, not a frozen result. Missing
      provider runs must be displayed unavailable; never substitute another run. *)
  type t =
    | Follow
    | Pin_run of Run_ref.t
  [@@deriving bin_io, compare, equal, sexp]
end

module Context = struct
  type t =
    { id : Context_id.t
    ; name : string
    ; selected_run : Run_ref.t option
    ; selection_revision : int
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Window = struct
  type t =
    { id : Window_id.t
    ; name : string
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Arrangement = struct
  type t =
    { id : Workspace_id.t
    ; window : Window_id.t
    ; name : string
    ; context : Context_id.t
    ; binding_revision : int
    ; zoomed_tile : Tile_id.t option
    ; preset : string option [@sexp.default None]
    }
  [@@deriving bin_io, compare, equal, sexp]

  (** Infer only when the field is absent on disk. Explicit [None] denotes a custom
      arrangement; renaming a migrated arrangement never re-runs name inference. *)
  let t_of_sexp sexp =
    let value = t_of_sexp sexp in
    let present =
      match sexp with
      | Sexp.List fields ->
        List.exists fields ~f:(function
          | Sexp.List (Sexp.Atom "preset" :: _) -> true
          | _ -> false)
      | _ -> false
    in
    if present
    then value
    else
      { value with
        preset =
          (match value.name with
           | "Overview" -> Some "overview"
           | "Timing" -> Some "timing"
           | "Testing" -> Some "testing"
           | _ -> None)
      }
  ;;
end

module Tile = struct
  (** [kind] is an extensible view identifier, e.g. "run-selector". List order determines
      tile order; geometry is in client-interpreted layout cells. *)
  type t =
    { id : Tile_id.t
    ; workspace : Workspace_id.t
    ; kind : string
    ; binding : Binding.t
    ; hidden : bool
    ; requested_geometry : Geometry.t
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Snapshot = struct
  type t =
    { schema_version : int
    ; session_id : Session_id.t
    ; revision : int
    ; next_id : int
    ; main_context : Context_id.t
    ; contexts : Context.t list
    ; windows : Window.t list
    ; workspaces : Arrangement.t list
    ; tiles : Tile.t list
    }
  [@@deriving bin_io, compare, equal, sexp]
end

module Mutation = struct
  type t =
    | Select_run of
        { workspace : Workspace_id.t
        ; context : Context_id.t
        ; expected_selection_revision : int
        ; run : Run_ref.t option
        }
    | Make_independent of Workspace_id.t
    | Link_context of
        { workspace : Workspace_id.t
        ; context : Context_id.t
        }
    | Rename_context of
        { context : Context_id.t
        ; name : string
        }
    | Create_window of { name : string }
    | Create_workspace of
        { window : Window_id.t
        ; name : string
        ; context : Context_id.t
        }
    | Rename_workspace of
        { workspace : Workspace_id.t
        ; name : string
        }
    | Move_workspace of
        { workspace : Workspace_id.t
        ; window : Window_id.t
        }
    | Create_tile of
        { workspace : Workspace_id.t
        ; kind : string
        ; geometry : Geometry.t
        }
    | Set_tile_binding of
        { tile : Tile_id.t
        ; binding : Binding.t
        }
    | Set_tile_hidden of
        { tile : Tile_id.t
        ; hidden : bool
        }
    | Move_tile of
        { tile : Tile_id.t
        ; workspace : Workspace_id.t
        }
    | Resize_tile of
        { tile : Tile_id.t
        ; geometry : Geometry.t
        }
    | Reorder_tile of
        { tile : Tile_id.t
        ; before : Tile_id.t option
        }
    | Set_zoom of
        { workspace : Workspace_id.t
        ; tile : Tile_id.t option
        }
    | Instantiate_template of
        { window : Window_id.t
        ; template : Workspace_template.t
        }
    | Apply_preset of
        { workspace : Workspace_id.t
        ; preset : string
        ; tiles : (string * Geometry.t) list
        }
    | Reset_arrangement of
        { workspace : Workspace_id.t
        ; preset : string
        ; tiles : (string * Geometry.t) list
        }
  [@@deriving bin_io, compare, equal, sexp]
end

module Operation = struct
  (** Every mutation is compare-and-swap against the complete snapshot. A conflict
      requires [Get] and deliberate retry; it must not silently retarget selection. *)
  type t =
    | Get
    | Mutate of
        { expected_revision : int
        ; mutation : Mutation.t
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

let schema_version = 1

exception Invalid_state of V1.Error.t

let reject kind message = raise (Invalid_state (V1.Error.create kind message))
let require condition message = if not condition then reject Invalid_request message

let find values ~f what =
  match List.find values ~f with
  | Some value -> value
  | None -> reject Not_found ("Missing workspace registry reference: " ^ what)
;;

let context (s : Snapshot.t) id =
  find s.contexts ~f:(fun c -> Context_id.equal c.Context.id id) "context"
;;

let workspace (s : Snapshot.t) id =
  find s.workspaces ~f:(fun w -> Workspace_id.equal w.Arrangement.id id) "workspace"
;;

let window (s : Snapshot.t) id =
  find s.windows ~f:(fun w -> Window_id.equal w.Window.id id) "window"
;;

let tile (s : Snapshot.t) id =
  find s.tiles ~f:(fun t -> Tile_id.equal t.Tile.id id) "tile"
;;

let protect f =
  try Ok (f ()) with
  | Invalid_state error -> Error error
;;

let valid_geometry (g : Geometry.t) =
  require
    (g.x >= 0 && g.y >= 0 && g.width > 0 && g.height > 0)
    "Requested geometry requires nonnegative position and positive size"
;;

let valid_name name = require (not (String.is_empty (String.strip name))) "Empty name"

let valid_run (run : Run_ref.t) =
  valid_name (Backend_id.to_string run.backend);
  valid_name run.id
;;

let valid_template template =
  match Workspace_template.validate template with
  | Ok () -> ()
  | Error error -> reject Invalid_request (Error.to_string_hum error)
;;

let validate (s : Snapshot.t) =
  protect (fun () ->
    require (s.schema_version = schema_version) "Unsupported workspace snapshot schema";
    require (s.revision >= 0 && s.next_id > 0) "Invalid registry revision/ID counter";
    valid_name (Session_id.to_string s.session_id);
    let unique ids =
      List.iter ids ~f:valid_name;
      require
        (List.length (List.dedup_and_sort ids ~compare:String.compare) = List.length ids)
        "Duplicate registry identity"
    in
    unique (List.map s.contexts ~f:(fun c -> Context_id.to_string c.Context.id));
    unique (List.map s.windows ~f:(fun w -> Window_id.to_string w.Window.id));
    unique (List.map s.workspaces ~f:(fun w -> Workspace_id.to_string w.Arrangement.id));
    unique (List.map s.tiles ~f:(fun t -> Tile_id.to_string t.Tile.id));
    ignore (context s s.main_context : Context.t);
    List.iter s.contexts ~f:(fun c ->
      valid_name c.name;
      Option.iter c.selected_run ~f:valid_run;
      require
        (c.selection_revision >= 0 && c.selection_revision <= s.revision)
        "Invalid context selection revision");
    List.iter s.windows ~f:(fun w -> valid_name w.name);
    List.iter s.workspaces ~f:(fun w ->
      valid_name w.name;
      Option.iter w.preset ~f:valid_name;
      ignore (window s w.window : Window.t);
      ignore (context s w.context : Context.t);
      require
        (w.binding_revision >= 0 && w.binding_revision <= s.revision)
        "Invalid workspace binding revision";
      Option.iter w.zoomed_tile ~f:(fun id ->
        let t = tile s id in
        require
          (Workspace_id.equal t.workspace w.id && not t.hidden)
          "Zoom must reference a visible tile in the workspace"));
    List.iter s.tiles ~f:(fun t ->
      valid_name t.kind;
      (match t.binding with
       | Follow -> ()
       | Pin_run run -> valid_run run);
      ignore (workspace s t.workspace : Arrangement.t);
      valid_geometry t.requested_geometry))
;;

(** Pure initial template. The caller supplies a globally unique session seed, once, and
    persists it. No provider run is chosen implicitly. *)
let initial ~session_id : Snapshot.t =
  let main_context = Context_id.of_string "context-1" in
  let window = Window_id.of_string "window-2" in
  let overview = Workspace_id.of_string "workspace-3" in
  let timing = Workspace_id.of_string "workspace-4" in
  let arrangement id name : Arrangement.t =
    { id
    ; window
    ; name
    ; context = main_context
    ; binding_revision = 0
    ; zoomed_tile = None
    ; preset = Some (String.lowercase name)
    }
  in
  let selector id workspace width height : Tile.t =
    { id = Tile_id.of_string id
    ; workspace
    ; kind = "run-selector"
    ; binding = Follow
    ; hidden = false
    ; requested_geometry = { x = 0; y = 0; width; height }
    }
  in
  { schema_version
  ; session_id
  ; revision = 0
  ; next_id = 7
  ; main_context
  ; contexts =
      [ { id = main_context; name = "Main"; selected_run = None; selection_revision = 0 }
      ]
  ; windows = [ { id = window; name = "Primary" } ]
  ; workspaces = [ arrangement overview "Overview"; arrangement timing "Timing" ]
  ; tiles = [ selector "tile-5" overview 80 20; selector "tile-6" timing 40 8 ]
  }
;;

let update_workspace (s : Snapshot.t) id ~f =
  ignore (workspace s id : Arrangement.t);
  { s with
    workspaces =
      List.map s.workspaces ~f:(fun w -> if Workspace_id.equal w.id id then f w else w)
  }
;;

let update_tile (s : Snapshot.t) id ~f =
  ignore (tile s id : Tile.t);
  { s with
    tiles = List.map s.tiles ~f:(fun t -> if Tile_id.equal t.id id then f t else t)
  }
;;

let clear_zoom (s : Snapshot.t) id =
  { s with
    workspaces =
      List.map s.workspaces ~f:(fun w ->
        if Option.equal Tile_id.equal w.zoomed_tile (Some id)
        then { w with zoomed_tile = None }
        else w)
  }
;;

let allocate (s : Snapshot.t) prefix =
  let used =
    List.map s.contexts ~f:(fun c -> Context_id.to_string c.id)
    @ List.map s.windows ~f:(fun w -> Window_id.to_string w.id)
    @ List.map s.workspaces ~f:(fun w -> Workspace_id.to_string w.id)
    @ List.map s.tiles ~f:(fun t -> Tile_id.to_string t.id)
  in
  let rec loop n =
    require (n < Int.max_value) "Registry identity counter exhausted";
    let id = prefix ^ "-" ^ Int.to_string n in
    if List.mem used id ~equal:String.equal then loop (n + 1) else id, n + 1
  in
  let id, next_id = loop s.next_id in
  id, { s with next_id }
;;

(** Export only the ordered layout. Pins, selections, context identities and zoom never
    cross this boundary. Import always creates a new Main-linked workspace. *)
let export_template (s : Snapshot.t) id =
  Result.bind (validate s) ~f:(fun () ->
    protect (fun () ->
      let w = workspace s id in
      let template : Workspace_template.t =
        { version = Workspace_template.version
        ; name = w.name
        ; views =
            List.filter_map s.tiles ~f:(fun t ->
              if not (Workspace_id.equal t.workspace id)
              then None
              else (
                let g = t.requested_geometry in
                Some
                  { Workspace_template.View.kind = t.kind
                  ; hidden = t.hidden
                  ; geometry = { x = g.x; y = g.y; width = g.width; height = g.height }
                  }))
        }
      in
      valid_template template;
      template))
;;

let apply_mutation (s : Snapshot.t) (mutation : Mutation.t) =
  match mutation with
  | Select_run { workspace = id; context = context_id; expected_selection_revision; run }
    ->
    let w = workspace s id in
    let c = context s context_id in
    if (not (Context_id.equal w.context context_id))
       || c.selection_revision <> expected_selection_revision
    then reject Conflict "Stale context binding or selection revision";
    require (c.selection_revision < Int.max_value) "Selection revision exhausted";
    { s with
      contexts =
        List.map s.contexts ~f:(fun c ->
          if Context_id.equal c.id context_id
          then
            { c with selected_run = run; selection_revision = c.selection_revision + 1 }
          else c)
    }
  | Make_independent id ->
    let w = workspace s id in
    let c = context s w.context in
    let fresh, s = allocate s "context" in
    let fresh = Context_id.of_string fresh in
    let s =
      { s with
        contexts =
          s.contexts
          @ [ { c with
                id = fresh
              ; name = w.name ^ " independent"
              ; selection_revision = 0
              }
            ]
      }
    in
    update_workspace s id ~f:(fun w ->
      { w with context = fresh; binding_revision = s.revision })
  | Link_context { workspace = id; context = context_id } ->
    ignore (context s context_id : Context.t);
    update_workspace s id ~f:(fun w ->
      { w with context = context_id; binding_revision = s.revision })
  | Rename_context { context = id; name } ->
    valid_name name;
    ignore (context s id : Context.t);
    { s with
      contexts =
        List.map s.contexts ~f:(fun c ->
          if Context_id.equal c.id id then { c with name } else c)
    }
  | Create_window { name } ->
    valid_name name;
    let id, s = allocate s "window" in
    { s with windows = s.windows @ [ { id = Window_id.of_string id; name } ] }
  | Create_workspace { window = window_id; name; context = context_id } ->
    valid_name name;
    ignore (window s window_id : Window.t);
    ignore (context s context_id : Context.t);
    let id, s = allocate s "workspace" in
    { s with
      workspaces =
        s.workspaces
        @ [ { id = Workspace_id.of_string id
            ; name
            ; window = window_id
            ; context = context_id
            ; binding_revision = s.revision
            ; zoomed_tile = None
            ; preset = None
            }
          ]
    }
  | Rename_workspace { workspace = id; name } ->
    valid_name name;
    update_workspace s id ~f:(fun w -> { w with name })
  | Move_workspace { workspace = id; window = window_id } ->
    ignore (window s window_id : Window.t);
    update_workspace s id ~f:(fun w -> { w with window = window_id })
  | Create_tile { workspace = workspace_id; kind; geometry } ->
    ignore (workspace s workspace_id : Arrangement.t);
    valid_name kind;
    valid_geometry geometry;
    let id, s = allocate s "tile" in
    { s with
      tiles =
        s.tiles
        @ [ { id = Tile_id.of_string id
            ; workspace = workspace_id
            ; kind
            ; binding = Follow
            ; hidden = false
            ; requested_geometry = geometry
            }
          ]
    }
  | Set_tile_binding { tile = id; binding } ->
    update_tile s id ~f:(fun t -> { t with binding })
  | Set_tile_hidden { tile = id; hidden } ->
    let s = if hidden then clear_zoom s id else s in
    update_tile s id ~f:(fun t -> { t with hidden })
  | Move_tile { tile = id; workspace = workspace_id } ->
    ignore (workspace s workspace_id : Arrangement.t);
    let s = clear_zoom s id in
    update_tile s id ~f:(fun t -> { t with workspace = workspace_id })
  | Resize_tile { tile = id; geometry } ->
    valid_geometry geometry;
    update_tile s id ~f:(fun t -> { t with requested_geometry = geometry })
  | Reorder_tile { tile = id; before } ->
    let moved = tile s id in
    Option.iter before ~f:(fun before ->
      let target = tile s before in
      require (not (Tile_id.equal id before)) "Cannot reorder a tile before itself";
      require
        (Workspace_id.equal moved.workspace target.workspace)
        "Reorder requires same workspace");
    let others = List.filter s.tiles ~f:(fun t -> not (Tile_id.equal t.id id)) in
    let rec insert = function
      | [] -> [ moved ]
      | t :: rest when Option.equal Tile_id.equal before (Some t.Tile.id) ->
        moved :: t :: rest
      | t :: rest -> t :: insert rest
    in
    { s with tiles = insert others }
  | Set_zoom { workspace = id; tile = zoomed_tile } ->
    Option.iter zoomed_tile ~f:(fun tile_id ->
      let t = tile s tile_id in
      require
        (Workspace_id.equal t.workspace id && not t.hidden)
        "Zoom requires a visible tile in this workspace");
    update_workspace s id ~f:(fun w -> { w with zoomed_tile })
  | Instantiate_template { window = window_id; template } ->
    valid_template template;
    ignore (window s window_id : Window.t);
    let id, s = allocate s "workspace" in
    let id = Workspace_id.of_string id in
    let s =
      { s with
        workspaces =
          s.workspaces
          @ [ { id
              ; window = window_id
              ; name = template.name
              ; context = s.main_context
              ; binding_revision = s.revision
              ; zoomed_tile = None
              ; preset = None
              }
            ]
      }
    in
    List.fold template.views ~init:s ~f:(fun s view ->
      let fresh, s = allocate s "tile" in
      let g = view.geometry in
      { s with
        tiles =
          s.tiles
          @ [ { id = Tile_id.of_string fresh
              ; workspace = id
              ; kind = view.kind
              ; binding = Follow
              ; hidden = view.hidden
              ; requested_geometry =
                  { x = g.x; y = g.y; width = g.width; height = g.height }
              }
            ]
      })
  | Apply_preset { workspace = id; preset; tiles }
  | Reset_arrangement { workspace = id; preset; tiles } ->
    valid_name preset;
    ignore (workspace s id : Arrangement.t);
    let reset =
      match mutation with
      | Reset_arrangement _ -> true
      | _ -> false
    in
    let _, s =
      List.fold tiles ~init:([], s) ~f:(fun (claimed, s) (kind, geometry) ->
        valid_name kind;
        valid_geometry geometry;
        match
          List.find s.tiles ~f:(fun t ->
            Workspace_id.equal t.workspace id
            && String.equal t.kind kind
            && not (List.mem claimed t.id ~equal:Tile_id.equal))
        with
        | Some t ->
          let s =
            if reset
            then update_tile s t.id ~f:(fun t -> { t with requested_geometry = geometry })
            else s
          in
          t.id :: claimed, s
        | None ->
          let fresh, s = allocate s "tile" in
          let tile_id = Tile_id.of_string fresh in
          ( tile_id :: claimed
          , { s with
              tiles =
                s.tiles
                @ [ { Tile.id = tile_id
                    ; workspace = id
                    ; kind
                    ; binding = Follow
                    ; hidden = false
                    ; requested_geometry = geometry
                    }
                  ]
            } ))
    in
    (* Neither operation deletes/rebinds/unhides existing tiles, changes context, reorders
       user extras, nor clears zoom. Apply is strictly additive; reset additionally
       restores the first matching tile's requested geometry. *)
    update_workspace s id ~f:(fun w -> { w with preset = Some preset })
;;

(** Pure CAS reducer. Invalid snapshots/references and stale writes are explicit errors;
    on error the caller retains the original snapshot without modification. *)
let apply (s : Snapshot.t) (operation : Operation.t) : Response.t =
  Result.bind (validate s) ~f:(fun () ->
    protect (fun () ->
      match operation with
      | Get -> s
      | Mutate { expected_revision; mutation } ->
        if expected_revision <> s.revision
        then reject Conflict "Stale workspace snapshot revision";
        require (s.revision < Int.max_value) "Snapshot revision exhausted";
        let next = apply_mutation { s with revision = s.revision + 1 } mutation in
        (match validate next with
         | Ok () -> next
         | Error error -> raise (Invalid_state error))))
;;

module View_reference = struct
  (** Conservative query fence: any registry mutation invalidates this token. Include the
      provider query/result identity separately in data cache keys. *)
  type t =
    { session_id : Session_id.t
    ; snapshot_revision : int
    ; tile : Tile_id.t
    ; context : Context_id.t option
    ; selection_revision : int option
    ; run : Run_ref.t option
    }
  [@@deriving bin_io, compare, equal, sexp]
end

let resolve_tile (s : Snapshot.t) id =
  protect (fun () ->
    let t = tile s id in
    let context_id, selection_revision, run =
      match t.binding with
      | Pin_run run -> None, None, Some run
      | Follow ->
        let w = workspace s t.workspace in
        let c = context s w.context in
        Some c.id, Some c.selection_revision, c.selected_run
    in
    ({ session_id = s.session_id
     ; snapshot_revision = s.revision
     ; tile = id
     ; context = context_id
     ; selection_revision
     ; run
     }
     : View_reference.t))
;;

let view_is_current snapshot reference =
  match resolve_tile snapshot reference.View_reference.tile with
  | Error _ -> false
  | Ok current -> View_reference.equal current reference
;;
