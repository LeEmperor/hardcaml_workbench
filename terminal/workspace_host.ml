open! Core
open Hardcaml_workbench_protocol
module W = Workspace

(** Only presentation state lives here. Registry writes are effects returned to the
    transport owner; a keypress never optimistically mutates the registry. *)
type local =
  { cursor : string option
  ; filter : string
  ; scroll : int
  ; follow : bool
  ; headers : bool
  ; synthesis : Synthesis_view.State.t
  ; terminal_result : Terminal_result_view.State.t
  ; artifacts : Artifact_view.t option
  ; artifact_generation : int
  ; inspection : Inspection_view.t option
  ; inspection_generation : int
  ; simulation : Simulation_view.t
  }

type layout_mode =
  | Fit
  | Preferred
[@@deriving equal, sexp]

type action =
  | Registry of W.Mutation.t
  | Switch of W.Workspace_id.t
  | Build
  | Test
  | Cancel of Job_id.t
  | Refresh_integration
  | Generate_rtl of Target_id.t * Configuration_id.t
  | Inspect_artifact
  | Inspect_hierarchy
  | Discover_asic
  | Asic of Asic.Operation.t
  | Edit_plan of string * string
  | Edit_finalization of Run_ref.t
  | Edit_acceptance of Run_ref.t * string
  | Finalize_collect of Run_ref.t * string
  | Browse_artifacts of Run_ref.t
  | Browse_inspection of Run_ref.t * string * string
  | Launch_asic of Asic.Preview.t * bool
  | Apply_default_layout
  | Local_headers
  | Resume_log
  | Toggle_chrome
  | Set_appearance of Appearance.t
  | Set_layout_mode of layout_mode
  | Synthesis_mode of Synthesis_view.Mode.t
  | Synthesis_sort of Synthesis.Sort.t
  | Synthesis_cycle_sort
  | Synthesis_clear_filter
  | Exit
  | Simulation of W.Tile_id.t * Simulation.Operation.t
  | Simulation_form of W.Tile_id.t * string * Simulation.Suite.t * string
  | Simulation_edit of W.Tile_id.t * string * string * Simulation_view.Form.t
  | Simulation_case of W.Tile_id.t * string
  | Simulation_logs of W.Tile_id.t
  | Simulation_export of Simulation.Artifact.t * bool

type command =
  { id : string
  ; title : string
  ; aliases : string
  ; action : action
  ; unavailable : string option
  }

type capture =
  { session : W.Session_id.t
  ; revision : int
  ; workspace : W.Workspace_id.t
  }

type argument =
  | Plan_endpoint of string * string
  | Finalization_attempt of Run_ref.t
  | Acceptance of Run_ref.t * string * string
  | Simulation_selection of W.Tile_id.t * string * string * Simulation_view.Form.t

type palette =
  { capture : capture
  ; commands : command list
  ; query : string
  ; index : int
  ; argument : argument option
  }

type t =
  { registry : W.Snapshot.t option
  ; active : W.Workspace_id.t option
  ; focus : W.Tile_id.t option
  ; locals : (string * local) list
  ; palette : palette option
  ; prefix : int
  ; paste : bool
  ; inspection_paste : W.Tile_id.t option
  ; chrome : bool
  ; notice : string
  ; editing_filter : bool
  ; workspace_focus : (string * W.Tile_id.t option) list
  ; appearance : Appearance.t
  ; layout_mode : layout_mode
  }

let empty =
  { registry = None
  ; active = None
  ; focus = None
  ; locals = []
  ; palette = None
  ; prefix = 0
  ; paste = false
  ; inspection_paste = None
  ; chrome = true
  ; notice = "Loading workspace registry"
  ; editing_filter = false
  ; workspace_focus = []
  ; appearance = Appearance.default
  ; layout_mode = Fit
  }
;;

let default_local =
  { cursor = None
  ; filter = ""
  ; scroll = 0
  ; follow = true
  ; headers = true
  ; synthesis = Synthesis_view.State.empty
  ; terminal_result = Terminal_result_view.State.empty
  ; artifacts = None
  ; artifact_generation = 0
  ; inspection = None
  ; inspection_generation = 0
  ; simulation = Simulation_view.empty
  }
;;

let local t id =
  List.Assoc.find t.locals (W.Tile_id.to_string id) ~equal:String.equal
  |> Option.value ~default:default_local
;;

let set_local t id value =
  { t with
    locals = List.Assoc.add t.locals ~equal:String.equal (W.Tile_id.to_string id) value
  }
;;

let active t =
  Option.bind t.registry ~f:(fun s ->
    Option.bind t.active ~f:(fun id ->
      List.find s.workspaces ~f:(fun w -> W.Workspace_id.equal w.id id)))
;;

let tiles t =
  match t.registry, active t with
  | Some s, Some w ->
    List.filter s.tiles ~f:(fun tile ->
      W.Workspace_id.equal tile.workspace w.id
      && (not tile.hidden)
      && Option.value_map w.zoomed_tile ~default:true ~f:(W.Tile_id.equal tile.id))
  | _ -> []
;;

let focused t =
  Option.bind t.focus ~f:(fun id ->
    List.find (tiles t) ~f:(fun tile -> W.Tile_id.equal tile.id id))
;;

let receive t (s : W.Snapshot.t) =
  match t.registry with
  | Some previous
    when W.Session_id.equal previous.session_id s.session_id
         && previous.revision > s.revision -> t
  | _ ->
    let active =
      Option.filter t.active ~f:(fun id ->
        List.exists s.workspaces ~f:(fun w -> W.Workspace_id.equal w.id id))
      |> fun selected ->
      Option.first_some selected (Option.map (List.hd s.workspaces) ~f:(fun w -> w.id))
    in
    let notice =
      match t.palette with
      | Some { argument = Some (Simulation_selection _); _ } -> t.notice
      | _ -> ""
    in
    let t = { t with registry = Some s; active; notice } in
    let focus =
      Option.filter t.focus ~f:(fun id ->
        List.exists (tiles t) ~f:(fun tile -> W.Tile_id.equal tile.id id))
      |> fun selected ->
      Option.first_some selected (Option.map (List.hd (tiles t)) ~f:(fun tile -> tile.id))
    in
    { t with focus }
;;

let capture t =
  match t.registry, active t with
  | Some s, Some w ->
    Some { session = s.session_id; revision = s.revision; workspace = w.id }
  | _ -> None
;;

let switch t id =
  let workspace_focus =
    Option.value_map t.active ~default:t.workspace_focus ~f:(fun old ->
      List.Assoc.add
        t.workspace_focus
        ~equal:String.equal
        (W.Workspace_id.to_string old)
        t.focus)
  in
  let focus =
    List.Assoc.find workspace_focus ~equal:String.equal (W.Workspace_id.to_string id)
    |> Option.join
  in
  let t = { t with active = Some id; focus; workspace_focus } in
  Option.value_map t.registry ~default:t ~f:(receive t)
;;

let current t c =
  match capture t with
  | None -> false
  | Some now ->
    W.Session_id.equal c.session now.session
    && c.revision = now.revision
    && W.Workspace_id.equal c.workspace now.workspace
;;

let command ?unavailable id title aliases action =
  { id; title; aliases; action; unavailable }
;;

let set_appearance t appearance = { t with appearance }

let appearance_commands t =
  let make key label selected appearance =
    command
      ("appearance." ^ key)
      ("Appearance: " ^ label ^ if selected then " [active]" else "")
      "theme style skin colors icons density preset"
      (Set_appearance appearance)
  in
  List.map Appearance.Preset.all ~f:(fun preset ->
    make
      ("preset." ^ Appearance.Preset.key preset)
      (Appearance.Preset.label preset)
      (Appearance.Preset.equal preset t.appearance.preset)
      { t.appearance with preset })
  @ List.map Appearance.Color.all ~f:(fun color ->
    make
      ("color." ^ Appearance.Color.key color)
      ("Color " ^ Appearance.Color.label color)
      (Appearance.Color.equal color t.appearance.color)
      { t.appearance with color })
  @ List.map Appearance.Icons.all ~f:(fun icons ->
    make
      ("icons." ^ Appearance.Icons.key icons)
      ("Icons " ^ Appearance.Icons.label icons)
      (Appearance.Icons.equal icons t.appearance.icons)
      { t.appearance with icons })
  @ List.map Appearance.Density.all ~f:(fun density ->
    make
      ("density." ^ Appearance.Density.key density)
      ("Density " ^ Appearance.Density.label density)
      (Appearance.Density.equal density t.appearance.density)
      { t.appearance with density })
;;

let%test_unit "appearance commands change only client-local style" =
  let registry = W.initial ~session_id:(W.Session_id.of_string "appearance-test") in
  let host = receive empty registry in
  let host =
    { host with
      appearance = { host.appearance with color = Restrained; icons = Unicode }
    }
  in
  let tile = List.hd_exn registry.tiles in
  let host =
    set_local host tile.id { default_local with scroll = 7; filter = "retained" }
  in
  let commands = appearance_commands host in
  let command =
    List.find_exn commands ~f:(fun c -> String.equal c.id "appearance.preset.studio")
  in
  match command.action with
  | Set_appearance appearance ->
    let changed = set_appearance host appearance in
    assert (Appearance.Preset.equal changed.appearance.preset Studio);
    assert (Appearance.Color.equal changed.appearance.color Restrained);
    assert (Appearance.Icons.equal changed.appearance.icons Unicode);
    assert (phys_equal changed.registry host.registry);
    assert (phys_equal changed.active host.active);
    assert (phys_equal changed.focus host.focus);
    assert (phys_equal changed.locals host.locals)
  | _ -> assert false
;;

let asic_cancel_commands (snapshot : Asic.Snapshot.t) =
  List.filter_map snapshot.operations ~f:(fun operation ->
    if Asic_intents.cancellable operation
    then
      Some
        (command
           ("asic.cancel." ^ operation.key)
           ("Cancel ASIC operation " ^ operation.key)
           "stop"
           (Asic (Cancel operation.key)))
    else None)
;;

let project_scoped_kind kind =
  List.mem
    [ "simulation"
    ; "execution"
    ; "project-tests"
    ; "logs"
    ; "project"
    ; "navigation"
    ; "asic"
    ]
    kind
    ~equal:String.equal
;;

let job_attempt_kind kind =
  List.mem [ "execution"; "project-tests"; "logs" ] kind ~equal:String.equal
;;

let evidence_runs t =
  match t.registry with
  | None -> []
  | Some registry ->
    tiles t
    |> List.filter ~f:(fun tile ->
      (not (project_scoped_kind tile.kind)) && not (String.equal tile.kind "run-selector"))
    |> List.filter_map ~f:(fun tile ->
      W.resolve_tile registry tile.id
      |> Result.ok
      |> Option.bind ~f:(fun reference -> reference.run))
    |> List.dedup_and_sort ~compare:Run_ref.compare
;;

let default_tile_specs ~workspace_name =
  if String.equal workspace_name "Timing"
  then [ "run-selector", 28, 6; "timing", 64, 12; "logs", 64, 10 ]
  else
    [ "run-selector", 32, 12
    ; "synthesis", 64, 10
    ; "placement", 40, 10
    ; "cts", 40, 10
    ; "routing", 40, 10
    ; "timing", 40, 10
    ; "checks", 40, 10
    ; "finalization", 40, 10
    ; "asic", 64, 10
    ; "execution", 48, 10
    ; "project-tests", 48, 10
    ; "logs", 64, 10
    ; "navigation", 64, 6
    ]
;;

(** Additive preset: hidden tiles count as existing. Never rewrite a saved binding,
    selection, requested geometry, ordering, zoom, or context to install a preset. *)
let missing_default_tiles (snapshot : W.Snapshot.t) (workspace : W.Arrangement.t) =
  default_tile_specs ~workspace_name:workspace.name
  |> List.filter_map ~f:(fun (kind, width, height) ->
    if List.exists snapshot.tiles ~f:(fun tile ->
         W.Workspace_id.equal tile.workspace workspace.id && String.equal tile.kind kind)
    then None
    else
      Some
        (W.Mutation.Create_tile
           { workspace = workspace.id; kind; geometry = { x = 0; y = 0; width; height } }))
;;

let catalog t ~(project : Project.t option) ~(jobs : Job.t list) =
  let needs_project =
    if Option.is_none project then Some "Open a project first" else None
  in
  let base =
    [ command
        ?unavailable:needs_project
        "project.build"
        "Build project"
        "dune build"
        Build
    ; command
        ?unavailable:needs_project
        "project.test"
        "Run project tests"
        "simulation dune test"
        Test
    ; command
        ?unavailable:needs_project
        "project.discover"
        "Refresh hardware integration"
        "driver discover"
        Refresh_integration
    ; command
        ?unavailable:needs_project
        "asic.discover"
        "Discover ASIC flows and runs"
        "synthesis provider"
        Discover_asic
    ; command
        "artifact.inspect"
        "Inspect selected RTL artifact"
        "read output"
        Inspect_artifact
    ; command "hierarchy.inspect" "Inspect hardware hierarchy" "tree" Inspect_hierarchy
    ; command "host.chrome" "Toggle host chrome" "header footer" Toggle_chrome
    ; command
        "layout.fit"
        "Layout: Fit tiles to window"
        "dashboard fill screen grid"
        (Set_layout_mode Fit)
    ; command
        "layout.preferred"
        "Layout: Requested tile sizes"
        "shelf preferred geometry"
        (Set_layout_mode Preferred)
    ; command "host.exit" "Exit client" "quit" Exit
    ]
    @ appearance_commands t
    @ List.filter_map jobs ~f:(fun job ->
      if Job.is_terminal job
      then None
      else
        Some
          (command
             ("job.cancel." ^ Job_id.to_string job.id)
             ("Cancel job " ^ Job_id.to_string job.id)
             "stop attempt"
             (Cancel job.id)))
    @ Option.value_map project ~default:[] ~f:(fun project ->
      List.concat_map project.targets ~f:(fun target ->
        List.filter_map project.configurations ~f:(fun config ->
          if not (Target_id.equal config.target target.id)
          then None
          else
            Some
              (command
                 ("rtl." ^ Configuration_id.to_string config.id)
                 ("Generate RTL: " ^ target.name ^ " / " ^ config.name)
                 "hardware"
                 (Generate_rtl (target.id, config.id))))))
  in
  match t.registry, active t with
  | Some s, Some w ->
    let mutation id title action =
      command id title "workspace tile layout" (Registry action)
    in
    let geometry : W.Geometry.t = { x = 0; y = 0; width = 40; height = 10 } in
    base
    @ List.map s.workspaces ~f:(fun w ->
      command
        ("workspace." ^ W.Workspace_id.to_string w.id)
        ("Switch to " ^ w.name)
        "overview timing"
        (Switch w.id))
    @ [ mutation
          "context.independent"
          "Make workspace independent"
          (Make_independent w.id)
      ; mutation
          "context.main"
          "Relink workspace to Main"
          (Link_context { workspace = w.id; context = s.main_context })
      ; mutation
          "tile.unzoom"
          "Unzoom workspace"
          (Set_zoom { workspace = w.id; tile = None })
      ; command
          "workspace.default-layout"
          "Apply default layout (add missing tiles)"
          "preset synthesis"
          Apply_default_layout
      ]
    @ List.map
        [ "run-selector"
        ; "placement"
        ; "cts"
        ; "routing"
        ; "checks"
        ; "finalization"
        ; "execution"
        ; "project-tests"
        ; "simulation"
        ; "logs"
        ; "timing"
        ; "synthesis"
        ; "asic"
        ; "project"
        ; "navigation"
        ]
        ~f:(fun kind ->
          mutation
            ("tile.add." ^ kind)
            ("Add " ^ kind ^ " tile")
            (Create_tile { workspace = w.id; kind; geometry }))
    @ List.filter_map s.tiles ~f:(fun tile ->
      if not (W.Workspace_id.equal tile.workspace w.id && tile.hidden)
      then None
      else
        Some
          (mutation
             ("tile.restore." ^ W.Tile_id.to_string tile.id)
             ("Restore " ^ tile.kind ^ " " ^ W.Tile_id.to_string tile.id)
             (Set_tile_hidden { tile = tile.id; hidden = false })))
    @ Option.value_map (focused t) ~default:[] ~f:(fun tile ->
      let id = tile.id in
      let g = tile.requested_geometry in
      let run = Result.ok (W.resolve_tile s id) |> Option.bind ~f:(fun r -> r.run) in
      [ mutation
          "tile.hide"
          "Hide focused tile"
          (Set_tile_hidden { tile = id; hidden = true })
      ; mutation
          "tile.zoom"
          "Zoom focused tile"
          (Set_zoom { workspace = w.id; tile = Some id })
      ; mutation
          "tile.follow"
          "Unpin tile (follow context)"
          (Set_tile_binding { tile = id; binding = Follow })
      ; command
          ?unavailable:
            (if project_scoped_kind tile.kind || String.equal tile.kind "run-selector"
             then Some "This tile does not display run-scoped evidence"
             else if Option.is_none run
             then Some "No selected run to pin"
             else None)
          "tile.pin"
          "Pin tile to selected run (live reference)"
          "reference"
          (Registry
             (Set_tile_binding
                { tile = id
                ; binding =
                    Option.value_map run ~default:W.Binding.Follow ~f:(fun r -> Pin_run r)
                }))
      ; mutation
          "tile.wider"
          "Resize tile wider"
          (Resize_tile { tile = id; geometry = { g with width = g.width + 8 } })
      ; mutation
          "tile.narrower"
          "Resize tile narrower"
          (Resize_tile
             { tile = id; geometry = { g with width = Int.max 8 (g.width - 8) } })
      ; mutation
          "tile.taller"
          "Resize tile taller"
          (Resize_tile { tile = id; geometry = { g with height = g.height + 4 } })
      ; mutation
          "tile.shorter"
          "Resize tile shorter"
          (Resize_tile
             { tile = id; geometry = { g with height = Int.max 3 (g.height - 4) } })
      ; mutation
          "tile.last"
          "Reorder tile to end"
          (Reorder_tile { tile = id; before = None })
      ; command "tile.headers" "Toggle focused tile header" "appearance" Local_headers
      ; command "logs.follow" "Resume log follow" "tail" Resume_log
      ]
      @ (if not (String.equal tile.kind "synthesis")
         then []
         else
           [ command
               "synthesis.summary"
               "Synthesis: Summary"
               "cells overview"
               (Synthesis_mode Summary)
           ; command
               "synthesis.cells"
               "Synthesis: Browse cell table"
               "resources breakdown inspect"
               (Synthesis_mode Cells)
           ; command
               "synthesis.details"
               "Synthesis: Inspect selected cell"
               "resource row detail"
               (Synthesis_mode Details)
           ; command
               "synthesis.metrics"
               "Synthesis: Inspect metrics"
               "resources diagnostics counters checkpoint boundary m"
               (Synthesis_mode Metrics)
           ; command
               "synthesis.evidence"
               "Synthesis: Inspect full evidence"
               "producer source provenance report path json"
               (Synthesis_mode Evidence)
           ; command
               "synthesis.clear-filter"
               "Synthesis: Clear cell filter"
               "reset search"
               Synthesis_clear_filter
           ; command
               "synthesis.cycle-sort"
               "Synthesis: Cycle table sort"
               "order count name"
               Synthesis_cycle_sort
           ]
           @ List.map Synthesis.Sort.all ~f:(fun sort ->
             let key, title =
               match sort with
               | Count_desc -> "count-desc", "count descending"
               | Count_asc -> "count-asc", "count ascending"
               | Name_asc -> "name-asc", "name ascending"
               | Name_desc -> "name-desc", "name descending"
             in
             command
               ("synthesis.sort." ^ key)
               ("Synthesis: Sort " ^ title)
               "cells table order"
               (Synthesis_sort sort)))
      @ List.filter_map s.workspaces ~f:(fun destination ->
        if W.Workspace_id.equal destination.id w.id
        then None
        else
          Some
            (mutation
               ("tile.move." ^ W.Workspace_id.to_string destination.id)
               ("Move focused tile to " ^ destination.name)
               (Move_tile { tile = id; workspace = destination.id }))))
  | _ -> base
;;

let matches p =
  let words =
    String.split (String.lowercase p.query) ~on:' '
    |> List.filter ~f:(Fn.non String.is_empty)
  in
  List.filter p.commands ~f:(fun c ->
    List.for_all words ~f:(fun word ->
      String.is_substring
        (String.lowercase (c.title ^ " " ^ c.aliases ^ " " ^ c.id))
        ~substring:word))
;;

type input =
  | Character of char
  | Text of string
  | Enter
  | Escape
  | Backspace
  | Clear_filter
  | Next
  | Previous
  | Focus
  | Paste_start
  | Paste_end

type effect =
  | Execute of capture * action
  | Activate
  | No_effect

(* Notty's raw mode disables ISIG. This escape route must run BEFORE any modal or
   bracketed-paste capture, including capture waiting for a missing end marker. *)
let is_interrupt (event : Bonsai_term.Event.t) =
  match event with
  | Key_press { key; mods } ->
    List.exists mods ~f:(function
      | Ctrl -> true
      | _ -> false)
    &&
      (match key with
      | ASCII ('c' | 'C') -> true
      | Uchar value ->
        Uchar.equal value (Uchar.of_char 'c') || Uchar.equal value (Uchar.of_char 'C')
      | _ -> false)
  | _ -> false
;;

let%test_unit "interrupt is independent of filter/palette/paste state and key encoding" =
  let open Bonsai_term.Event in
  List.iter
    [ Key.ASCII 'c'; ASCII 'C'; Uchar (Uchar.of_char 'c') ]
    ~f:(fun key -> assert (is_interrupt (Key_press { key; mods = [ Ctrl ] })));
  assert (not (is_interrupt (Key_press { key = ASCII 'c'; mods = [] })));
  assert (not (is_interrupt (Paste `Start)))
;;

let decode_event (event : Bonsai_term.Event.t) : input option =
  match event with
  | Paste `Start -> Some Paste_start
  | Paste `End -> Some Paste_end
  | Key_press { key = ASCII ('u' | 'U'); mods = [ Ctrl ] } -> Some Clear_filter
  | Key_press { key = Uchar value; mods = [ Ctrl ] }
    when Uchar.equal value (Uchar.of_char 'u') || Uchar.equal value (Uchar.of_char 'U') ->
    Some Clear_filter
  | Key_press { key; mods = [] } ->
    (match key with
     | ASCII ch -> Some (Character ch)
     | Uchar u when Uchar.to_scalar u < 128 ->
       Some (Character (Char.of_int_exn (Uchar.to_scalar u)))
     | Uchar u -> Some (Text (Uchar.Utf8.to_string u))
     | Enter -> Some Enter
     | Escape -> Some Escape
     | Backspace -> Some Backspace
     | Tab -> Some Focus
     | Arrow `Down -> Some Next
     | Arrow `Up -> Some Previous
     | _ -> None)
  | _ -> None
;;

let finalization_form t =
  Option.exists t.palette ~f:(fun p ->
    match p.argument with
    | Some (Finalization_attempt _ | Acceptance _ | Simulation_selection _) -> true
    | _ -> false)
;;

let reference_limit t =
  match Option.bind t.palette ~f:(fun p -> p.argument) with
  | Some (Simulation_selection (_, _, _, form)) when form.field = 0 -> 256 * 1024
  | _ -> 4096
;;

let printable_utf8 text =
  let rec loop offset =
    if offset >= String.length text
    then true
    else (
      let decoded = Stdlib.String.get_utf_8_uchar text offset in
      let scalar = Stdlib.Uchar.to_int (Stdlib.Uchar.utf_decode_uchar decoded) in
      Stdlib.Uchar.utf_decode_is_valid decoded
      && scalar >= 32
      && (not (scalar >= 127 && scalar < 160))
      && scalar <> 0x2028
      && scalar <> 0x2029
      && loop (offset + Stdlib.Uchar.utf_decode_length decoded))
  in
  loop 0
;;

let reject_reference_text t =
  ( { t with
      notice = "Finalization reference rejects newline/control or invalid UTF-8 text"
    }
  , No_effect )
;;

let append_reference t text =
  if not (printable_utf8 text)
  then reject_reference_text t
  else (
    match t.palette with
    | None -> t, No_effect
    | Some p ->
      let remaining = Int.max 0 (reference_limit t - String.length p.query) in
      let rec prefix offset =
        if offset >= String.length text
        then offset
        else (
          let length =
            Stdlib.Uchar.utf_decode_length (Stdlib.String.get_utf_8_uchar text offset)
          in
          if offset + length > remaining then offset else prefix (offset + length))
      in
      let length = prefix 0 in
      let query = p.query ^ String.prefix text length in
      ( { t with
          palette = Some { p with query; index = 0 }
        ; notice =
            (if length < String.length text
             then
               "Finalization reference limited to 4096 bytes; excess text rejected at \
                UTF-8 boundary"
             else t.notice)
        }
      , No_effect ))
;;

let drop_last_codepoint text =
  let rec loop offset previous =
    if offset >= String.length text
    then String.prefix text previous
    else (
      let length =
        Stdlib.Uchar.utf_decode_length (Stdlib.String.get_utf_8_uchar text offset)
      in
      loop (offset + length) offset)
  in
  loop 0 0
;;

type inspection_filter_result =
  | Filter_interrupt
  | Filter_handled of t
  | Filter_pass

(** This gate runs before global paste/command handling. The starting tile owns the entire
    bracketed paste, including when polling changes focus or removes its view. No result
    from this gate carries a command or provider operation. *)
let route_inspection_filter_event t (event : Bonsai_term.Event.t) =
  if is_interrupt event
  then Filter_interrupt
  else (
    let target =
      match t.inspection_paste with
      | Some id -> Some (id, (local t id).inspection)
      | None
        when (not t.paste)
             && Option.is_none t.palette
             && (not t.editing_filter)
             && t.prefix = 0 ->
        Option.bind (focused t) ~f:(fun tile ->
          Option.bind (local t tile.id).inspection ~f:(fun view ->
            if view.editing then Some (tile.id, Some view) else None))
      | None -> None
    in
    match target with
    | None -> Filter_pass
    | Some (id, view) ->
      let decoded = decode_event event in
      let captured = Option.is_some t.inspection_paste in
      let t, view =
        match decoded, view with
        | Some Paste_end, view ->
          ( { t with paste = false; inspection_paste = None }
          , Option.map view ~f:(fun view -> { view with Inspection_view.pasting = false })
          )
        | _, None ->
          ( { t with
              notice =
                "Inspection filter paste owner changed; payload ignored until end marker"
            }
          , None )
        | Some Paste_start, Some view when not captured ->
          ( { t with paste = true; inspection_paste = Some id; prefix = 0 }
          , Some { view with pasting = true; filter_notice = None } )
        | Some (Character c), Some view ->
          t, Some (Inspection_view.append_filter_text view (String.of_char c))
        | Some (Text text), Some view ->
          t, Some (Inspection_view.append_filter_text view text)
        | _, Some view when captured -> t, Some (Inspection_view.reject_filter_text view)
        | Some (Enter | Escape), Some view -> t, Some { view with editing = false }
        | Some Clear_filter, Some view ->
          t, Some { view with filter = ""; filter_notice = None }
        | Some Backspace, Some view ->
          t, Some { view with filter = drop_last_codepoint view.filter }
        | _, Some view ->
          (match event with
           | Key_press _ -> t, Some (Inspection_view.reject_filter_text view)
           | _ -> t, Some view)
      in
      let t =
        match view with
        | None -> t
        | Some view ->
          let local_state = local t id in
          set_local
            t
            id
            { local_state with inspection = Some (Inspection_view.normalize view) }
      in
      Filter_handled t)
;;

let%test_unit "production inspection filter gate captures bracketed endpoint paste \
               without dispatching hotkeys"
  =
  let open Bonsai_term.Event in
  let registry =
    W.initial ~session_id:(W.Session_id.of_string "inspection-paste-events")
  in
  let tile = List.hd_exn registry.tiles in
  let view =
    { (Inspection_view.create ~run:Fs0_fixture.run_a ~domain:"timing" ~stage:"signoff" ()) with
      editing = true
    }
  in
  let host = receive empty registry in
  let host =
    set_local
      { host with focus = Some tile.id; chrome = false }
      tile.id
      { default_local with inspection = Some view }
  in
  let send host event =
    match route_inspection_filter_event host event with
    | Filter_handled host -> host
    | Filter_interrupt | Filter_pass -> assert false
  in
  let key key = Key_press { key; mods = [] } in
  let view host = Option.value_exn (local host tile.id).inspection in
  let host = send host (Paste `Start) in
  assert (host.paste && Option.is_some host.inspection_paste && (view host).pasting);
  let payload = "endpoint/out[3]/Q jtr / ; q b (Inspect refresh)" in
  let host =
    String.fold payload ~init:host ~f:(fun host c -> send host (key (ASCII c)))
  in
  let host = send host (key (Uchar (Uchar.of_scalar_exn 0x754c))) in
  assert (String.equal (view host).filter (payload ^ "界"));
  assert (String.equal (view host).stage "signoff");
  assert ((view host).generation = 0 && Option.is_none (view host).requested);
  assert (Option.is_none host.palette && host.prefix = 0);
  let previous = (view host).filter in
  let host =
    List.fold
      [ key Enter
      ; key (ASCII '\n')
      ; key (ASCII '\r')
      ; key (ASCII '\000')
      ; key Escape
      ; key Backspace
      ; key Tab
      ; Key_press { key = ASCII 'r'; mods = [ Ctrl ] }
      ]
      ~init:host
      ~f:send
  in
  assert (
    String.equal (view host).filter previous && (view host).editing && (view host).pasting);
  assert (Option.is_some (view host).filter_notice);
  List.iter
    [ Key.ASCII 'c'; ASCII 'C'; Uchar (Uchar.of_char 'c') ]
    ~f:(fun key ->
      match route_inspection_filter_event host (Key_press { key; mods = [ Ctrl ] }) with
      | Filter_interrupt -> ()
      | _ -> assert false);
  let owner_changed = { host with focus = None } in
  let owner_changed = send owner_changed (key (ASCII 'j')) in
  assert (String.equal (view owner_changed).filter (previous ^ "j"));
  let host = send host (Paste `End) in
  assert (
    (not host.paste) && Option.is_none host.inspection_paste && not (view host).pasting);
  let host = send host (key Backspace) in
  assert (String.equal (view host).filter payload);
  let host = send host (key Enter) in
  assert ((not (view host).editing) && Option.is_none (view host).requested);
  assert (String.equal (view host).stage "signoff" && (view host).generation = 0);
  match route_inspection_filter_event host (key (ASCII 'r')) with
  | Filter_pass -> ()
  | _ -> assert false
;;

let%test_unit "inspection filter paste enforces 4096 UTF-8 bytes and consumes orphaned \
               paste until end"
  =
  let open Bonsai_term.Event in
  let registry =
    W.initial ~session_id:(W.Session_id.of_string "inspection-paste-boundary")
  in
  let tile = List.hd_exn registry.tiles in
  let view =
    { (Inspection_view.create ~run:Fs0_fixture.run_a ~domain:"timing" ~stage:"signoff" ()) with
      editing = true
    ; filter = String.make 4094 'a'
    }
  in
  let host = receive empty registry in
  let host =
    set_local
      { host with focus = Some tile.id }
      tile.id
      { default_local with inspection = Some view }
  in
  let send host event =
    match route_inspection_filter_event host event with
    | Filter_handled host -> host
    | _ -> assert false
  in
  let key key = Key_press { key; mods = [] } in
  let current host = Option.value_exn (local host tile.id).inspection in
  let host = send host (Paste `Start) in
  let host = send host (key (Uchar (Uchar.of_scalar_exn 0x754c))) in
  assert (String.length (current host).filter = 4094);
  assert (Option.is_some (current host).filter_notice);
  let host = send host (key (Uchar (Uchar.of_scalar_exn 0xe9))) in
  assert (String.length (current host).filter = 4096);
  assert (String.is_suffix (current host).filter ~suffix:"é");
  let host = send host (key (ASCII 'r')) in
  assert (String.length (current host).filter = 4096 && (current host).generation = 0);
  let host = send host (Paste `End) |> fun host -> send host (key Backspace) in
  assert (String.length (current host).filter = 4094);
  let appended = Inspection_view.append_filter_text (current host) "é界" in
  assert (
    String.length appended.filter = 4096 && String.is_suffix appended.filter ~suffix:"é");
  let rejected = Inspection_view.append_filter_text (current host) "\255" in
  assert (
    String.equal rejected.filter (current host).filter
    && Option.is_some rejected.filter_notice);
  let host = send host (Paste `Start) in
  let host = set_local host tile.id default_local in
  let host = send host (key (ASCII 'r')) in
  assert (
    host.paste
    && Option.is_none (local host tile.id).inspection
    && Option.is_none host.palette);
  let host = send host (Paste `End) in
  assert ((not host.paste) && Option.is_none host.inspection_paste)
;;

let input t event ~commands : t * effect =
  match event with
  | Paste_start -> { t with paste = true; prefix = 0 }, No_effect
  | Paste_end -> { t with paste = false }, No_effect
  | _ when t.paste ->
    if not (finalization_form t)
    then t, No_effect
    else (
      match event with
      | Character ch -> append_reference t (String.of_char ch)
      | Text text -> append_reference t text
      | _ -> reject_reference_text t)
  | Character ch when finalization_form t -> append_reference t (String.of_char ch)
  | Text text when finalization_form t -> append_reference t text
  | Backspace when finalization_form t ->
    ( { t with
        palette =
          Option.map t.palette ~f:(fun p ->
            { p with query = drop_last_codepoint p.query; index = 0 })
      }
    , No_effect )
  | _ when t.editing_filter ->
    (match event, t.focus with
     | (Escape | Enter), _ -> { t with editing_filter = false }, No_effect
     | Clear_filter, Some id ->
       let l = local t id in
       set_local t id { l with filter = ""; scroll = 0 }, No_effect
     | Character ch, Some id ->
       let l = local t id in
       ( set_local t id { l with filter = l.filter ^ String.of_char ch; scroll = 0 }
       , No_effect )
     | Backspace, Some id ->
       let l = local t id in
       ( set_local t id { l with filter = String.drop_suffix l.filter 1; scroll = 0 }
       , No_effect )
     | _ -> t, No_effect)
  | _ ->
    (match t.palette with
     | Some p ->
       (match event with
        | Clear_filter ->
          { t with palette = Some { p with query = ""; index = 0 } }, No_effect
        | Escape -> { t with palette = None; prefix = 0 }, No_effect
        | Character _
          when match p.argument with
               | Some (Finalization_attempt _ | Acceptance _ | Simulation_selection _) ->
                 String.length p.query >= 4096
               | None | Some (Plan_endpoint _) -> false ->
          { t with notice = "Finalization reference is limited to 4096 bytes" }, No_effect
        | Character ch ->
          ( { t with
              palette = Some { p with query = p.query ^ String.of_char ch; index = 0 }
            }
          , No_effect )
        | Backspace ->
          ( { t with
              palette = Some { p with query = String.drop_suffix p.query 1; index = 0 }
            }
          , No_effect )
        | Next ->
          ( { t with
              palette =
                Some
                  { p with
                    index = Int.min (Int.max 0 (List.length (matches p) - 1)) (p.index + 1)
                  }
            }
          , No_effect )
        | Previous ->
          { t with palette = Some { p with index = Int.max 0 (p.index - 1) } }, No_effect
        | Enter when Option.is_some p.argument ->
          if not (current t p.capture)
          then
            ( { t with palette = None; notice = "Command target changed; reopen palette" }
            , No_effect )
          else if finalization_form t && not (printable_utf8 p.query)
          then reject_reference_text t
          else if String.is_empty (String.strip p.query)
                  && not
                       (Option.exists p.argument ~f:(function
                         | Simulation_selection _ -> true
                         | _ -> false))
          then
            ( { t with
                notice = "An explicit endpoint or exact finalization attempt is required"
              }
            , No_effect )
          else if match p.argument with
                  | Some (Finalization_attempt _ | Acceptance _ | Simulation_selection _)
                    -> String.length p.query > reference_limit t
                  | None | Some (Plan_endpoint _) -> false
          then
            ( { t with notice = "Finalization reference is limited to 4096 bytes" }
            , No_effect )
          else (
            let operation =
              Or_error.try_with (fun () ->
                match Option.value_exn p.argument with
                | Finalization_attempt run ->
                  Asic (Asic.Operation.Inspect_finalization { run; attempt = p.query })
                | Acceptance (run, execution_file, key) ->
                  let acceptance = Asic.Acceptance.t_of_sexp (Sexp.of_string p.query) in
                  Asic
                    (Asic.Operation.Finalize
                       { key; run; execution_file; acceptance = Some acceptance })
                | Simulation_selection (tile, discovery_digest, submission_key, form) ->
                  (match Simulation_view.Form.accept form p.query |> Or_error.ok_exn with
                   | `Next form ->
                     Simulation_edit (tile, discovery_digest, submission_key, form)
                   | `Launch selection ->
                     Simulation
                       (tile, Launch { submission_key; discovery_digest; selection }))
                | Plan_endpoint (flow, profile) ->
                  let args =
                    String.split (String.strip p.query) ~on:' '
                    |> List.filter ~f:(Fn.non String.is_empty)
                  in
                  let endpoint = List.hd_exn args
                  and assignments = List.tl_exn args in
                  Asic (Asic.Operation.Plan { flow; profile; endpoint; assignments }))
            in
            match operation with
            | Ok operation -> { t with palette = None }, Execute (p.capture, operation)
            | Error error ->
              ( { t with notice = "Invalid typed input: " ^ Error.to_string_hum error }
              , No_effect ))
        | Enter ->
          (match List.nth (matches p) p.index with
           | None -> t, No_effect
           | Some _ when not (current t p.capture) ->
             ( { t with palette = None; notice = "Command target changed; reopen palette" }
             , No_effect )
           | Some { unavailable = Some reason; _ } ->
             { t with notice = reason }, No_effect
           | Some c -> { t with palette = None }, Execute (p.capture, c.action))
        | _ -> t, No_effect)
     | None ->
       (match event, t.prefix with
        | Clear_filter, _ ->
          let t =
            Option.value_map t.focus ~default:t ~f:(fun id ->
              let l = local t id in
              set_local t id { l with filter = ""; scroll = 0 })
          in
          { t with prefix = 0 }, No_effect
        | Character ' ', _ -> { t with prefix = 1 }, No_effect
        | Character 'c', 1 -> { t with prefix = 2 }, No_effect
        | Character 'c', 2 ->
          let palette =
            Option.map (capture t) ~f:(fun capture ->
              { capture; commands; query = ""; index = 0; argument = None })
          in
          { t with prefix = 0; palette }, No_effect
        | Character '/', _ ->
          ( { t with
              editing_filter = true
            ; prefix = 0
            ; notice = "Filter: type text; Enter/Esc returns to browsing"
            }
          , No_effect )
        | Focus, _ ->
          let visible = tiles t in
          let index =
            List.findi visible ~f:(fun _ tile ->
              Option.value_map t.focus ~default:false ~f:(W.Tile_id.equal tile.id))
            |> Option.value_map ~default:(-1) ~f:fst
          in
          let focus =
            if List.is_empty visible
            then None
            else
              Option.map
                (List.nth visible ((index + 1) mod List.length visible))
                ~f:(fun tile -> tile.id)
          in
          { t with focus; prefix = 0 }, No_effect
        | Enter, _ -> { t with prefix = 0 }, Activate
        | _, _ -> { t with prefix = 0 }, No_effect))
;;

let%test_unit "simulation palette paste captures cases without launching or losing \
               identity"
  =
  let host =
    receive empty (W.initial ~session_id:(W.Session_id.of_string "simulation-form"))
  in
  let capture = Option.value_exn (capture host) in
  let tile = (Option.value_exn (focused host)).id in
  let suite : Simulation.Suite.t =
    { id = "suite"
    ; label = "Suite"
    ; cases = [ { id = "a"; label = "A" } ]
    ; parameters = []
    ; default_seed = "42"
    }
  in
  let form = Simulation_view.Form.create suite in
  let host =
    { host with
      palette =
        Some
          { capture
          ; commands = []
          ; query = ""
          ; index = 0
          ; argument =
              Some (Simulation_selection (tile, "exact-digest", "exact-key", form))
          }
    }
  in
  let step host event =
    let host, effect = input host event ~commands:[] in
    (match effect with
     | No_effect -> ()
     | _ -> assert false);
    host
  in
  let host = List.fold [ Paste_start; Text "a"; Paste_end ] ~init:host ~f:step in
  let _, effect = input host Enter ~commands:[] in
  match effect with
  | Execute (_, Simulation_edit (actual_tile, digest, key, next)) ->
    assert (
      W.Tile_id.equal tile actual_tile
      && String.equal digest "exact-digest"
      && String.equal key "exact-key");
    assert (next.field = 1 && List.equal String.equal next.selection.cases [ "a" ])
  | _ -> assert false
;;

let select_run t run =
  match t.registry, active t with
  | Some s, Some w ->
    let c = W.context s w.context in
    Some
      (W.Mutation.Select_run
         { workspace = w.id
         ; context = c.id
         ; expected_selection_revision = c.selection_revision
         ; run
         })
  | _ -> None
;;

let%test_unit "finalization form dispatches only an explicit exact attempt and captured \
               run"
  =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "finalization-form") in
  let host = receive empty snapshot in
  let capture = Option.value_exn (capture host) in
  let run = Fs0_fixture.run_a in
  let form query =
    { host with
      palette =
        Some
          { capture
          ; commands = []
          ; query
          ; index = 0
          ; argument = Some (Finalization_attempt run)
          }
    }
  in
  let blank, effect = input (form "") Enter ~commands:[] in
  assert (Option.is_some blank.palette);
  (match effect with
   | No_effect -> ()
   | _ -> assert false);
  let bounded, effect =
    input (form (String.make 4096 'x')) (Character 'x') ~commands:[]
  in
  assert (String.length (Option.value_exn bounded.palette).query = 4096);
  (match effect with
   | No_effect -> ()
   | _ -> assert false);
  let _, effect = input (form (String.make 4097 'x')) Enter ~commands:[] in
  (match effect with
   | No_effect -> ()
   | _ -> assert false);
  let exact_attempt = "/private/returned operation attempt/operation.json" in
  let submitted, effect = input (form exact_attempt) Enter ~commands:[] in
  assert (Option.is_none submitted.palette);
  (match effect with
   | Execute (_, Asic (Inspect_finalization { run = actual; attempt })) ->
     assert (Run_ref.equal actual run);
     assert (String.equal attempt exact_attempt)
   | _ -> assert false);
  let stale =
    { (form "returned-operation-attempt") with
      registry = Some { snapshot with revision = snapshot.revision + 1 }
    }
  in
  let _, effect = input stale Enter ~commands:[] in
  (match effect with
   | No_effect -> ()
   | _ -> assert false);
  let escaped, effect = input (form "returned-operation-attempt") Escape ~commands:[] in
  assert (Option.is_none escaped.palette);
  match effect with
  | No_effect -> ()
  | _ -> assert false
;;

let%test_unit "acceptance form is typed bounded collateral captured with run and \
               execution"
  =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "acceptance-form") in
  let host = receive empty snapshot in
  let capture = Option.value_exn (capture host) in
  let run = Fs0_fixture.run_a in
  let execution_file = "/daemon/captured execution.json" in
  let acceptance : Asic.Acceptance.t =
    { support_tools = "/tools/界"
    ; precheck_python = "/python"
    ; testbench = "/explicit/tb with spaces.sv"
    ; testbench_top = "tb"
    ; replay_trace = "/explicit/trace"
    }
  in
  let query = Sexp.to_string_mach (Asic.Acceptance.sexp_of_t acceptance) in
  let form query =
    { host with
      palette =
        Some
          { capture
          ; commands = []
          ; query
          ; index = 0
          ; argument = Some (Acceptance (run, execution_file, "captured-key"))
          }
    }
  in
  let step t event = fst (input t event ~commands:[]) in
  let pasted = List.fold [ Paste_start; Text query; Paste_end ] ~init:(form "") ~f:step in
  assert (String.equal (Option.value_exn pasted.palette).query query);
  (match snd (input pasted Enter ~commands:[]) with
   | Execute
       ( _
       , Asic
           (Finalize
             { key
             ; run = actual
             ; execution_file = actual_file
             ; acceptance = Some actual_acceptance
             }) ) ->
     assert (String.equal key "captured-key" && Run_ref.equal run actual);
     assert (String.equal execution_file actual_file);
     assert (Asic.Acceptance.equal acceptance actual_acceptance)
   | _ -> assert false);
  List.iter
    [ ""; "((testbench /tb))"; String.make 4097 'x' ]
    ~f:(fun bad ->
      let after, effect = input (form bad) Enter ~commands:[] in
      assert (Option.is_some after.palette);
      match effect with
      | No_effect -> ()
      | _ -> assert false);
  let stale =
    { pasted with registry = Some { snapshot with revision = snapshot.revision + 1 } }
  in
  (match snd (input stale Enter ~commands:[]) with
   | No_effect -> ()
   | _ -> assert false);
  let first = List.hd_exn snapshot.tiles in
  let second = List.nth_exn snapshot.tiles 1 in
  let host =
    set_local
      host
      first.id
      { default_local with artifacts = Some (Artifact_view.create run) }
  in
  assert (Option.is_some (local host first.id).artifacts);
  assert (Option.is_none (local host second.id).artifacts)
;;

let%test_unit "finalization paths accept UTF-8 and bracketed paste without command \
               effects"
  =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "utf8-finalization") in
  let host = receive empty snapshot in
  let capture = Option.value_exn (capture host) in
  let form =
    { host with
      palette =
        Some
          { capture
          ; commands = []
          ; query = ""
          ; index = 0
          ; argument = Some (Finalization_attempt Fs0_fixture.run_a)
          }
    }
  in
  let commands = [ command "danger" "Build" "" Build ] in
  let step host event =
    let host, effect = input host event ~commands in
    (match effect with
     | No_effect -> ()
     | _ -> assert false);
    host
  in
  let query host = (Option.value_exn host.palette).query in
  let unicode =
    decode_event (Key_press { key = Uchar (Uchar.of_scalar_exn 0x754c); mods = [] })
    |> Option.value_exn
  in
  let typed = step (step form (Text "/tmp/")) unicode in
  assert (String.equal (query typed) "/tmp/界");
  let erased = step typed Backspace in
  assert (String.equal (query erased) "/tmp/");
  let typed = step (step erased unicode) (Text "/résultat.json") in
  let _, effect = input typed Enter ~commands in
  (match effect with
   | Execute (_, Asic (Inspect_finalization { attempt; _ })) ->
     assert (String.equal attempt "/tmp/界/résultat.json")
   | _ -> assert false);
  let pasted =
    List.fold
      [ Paste_start; Text "/tmp/界/"; Character 'b'; Text " c c/résultat.json" ]
      ~init:form
      ~f:step
  in
  assert pasted.paste;
  assert (Option.is_some pasted.palette);
  assert (is_interrupt (Key_press { key = ASCII 'c'; mods = [ Ctrl ] }));
  let rejected = step pasted Enter in
  assert (String.equal (query rejected) (query pasted));
  assert (String.is_substring rejected.notice ~substring:"newline/control");
  let pasted = step rejected Paste_end in
  assert (not pasted.paste);
  let _, effect = input pasted Enter ~commands in
  (match effect with
   | Execute (_, Asic (Inspect_finalization { attempt; _ })) ->
     assert (String.equal attempt "/tmp/界/b c c/résultat.json")
   | _ -> assert false);
  let ignored =
    List.fold
      [ Paste_start; Text "/tmp/界/"; Character 'b'; Enter; Paste_end ]
      ~init:host
      ~f:step
  in
  assert (Option.is_none ignored.palette);
  assert (ignored.prefix = 0)
;;

let%test_unit "finalization text rejects controls and truncates only at UTF-8 boundaries" =
  let host =
    receive empty (W.initial ~session_id:(W.Session_id.of_string "bounded-unicode"))
  in
  let capture = Option.value_exn (capture host) in
  let form query =
    { host with
      palette =
        Some
          { capture
          ; commands = []
          ; query
          ; index = 0
          ; argument = Some (Finalization_attempt Fs0_fixture.run_a)
          }
    }
  in
  let query host = (Option.value_exn host.palette).query in
  List.iter
    [ "bad\npath"; "bad\rpath"; "bad\tpath"; "bad\000path"; "\255" ]
    ~f:(fun text ->
      let after, effect = input (form "/safe/") (Text text) ~commands:[] in
      assert (String.equal (query after) "/safe/");
      assert (String.is_substring after.notice ~substring:"newline/control");
      match effect with
      | No_effect -> ()
      | _ -> assert false);
  let after, _ = input (form (String.make 4094 'x')) (Text "界") ~commands:[] in
  assert (String.length (query after) = 4094);
  assert (printable_utf8 (query after));
  let after, _ = input (form (String.make 4093 'x')) (Text "界é") ~commands:[] in
  assert (String.length (query after) = 4096);
  assert (String.is_suffix (query after) ~suffix:"界");
  assert (printable_utf8 (query after));
  assert (String.is_substring after.notice ~substring:"UTF-8 boundary");
  let erased, _ = input after Backspace ~commands:[] in
  assert (String.length (query erased) = 4093);
  let _, effect = input (form "/bad\npath") Enter ~commands:[] in
  match effect with
  | No_effect -> ()
  | _ -> assert false
;;

let%test_unit "metrics palette mode and scroll state belong to one synthesis tile" =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "metrics-local") in
  let snapshot =
    W.apply
      snapshot
      (Mutate
         { expected_revision = snapshot.revision
         ; mutation =
             Create_tile
               { workspace = (List.hd_exn snapshot.workspaces).id
               ; kind = "synthesis"
               ; geometry = { x = 0; y = 0; width = 64; height = 10 }
               }
         })
    |> Result.ok
    |> Option.value_exn
  in
  let host = receive empty snapshot in
  let synthesis =
    List.find_exn snapshot.tiles ~f:(fun tile -> String.equal tile.kind "synthesis")
  in
  let other =
    List.find_exn snapshot.tiles ~f:(fun tile ->
      not (W.Tile_id.equal tile.id synthesis.id))
  in
  let host = { host with focus = Some synthesis.id } in
  let commands = catalog host ~project:None ~jobs:[] in
  let command =
    List.find_exn commands ~f:(fun command -> String.equal command.id "synthesis.metrics")
  in
  (match command.action with
   | Synthesis_mode Metrics -> ()
   | _ -> assert false);
  let state = Synthesis_view.State.set_mode (local host synthesis.id).synthesis Metrics in
  let state = Synthesis_view.State.scroll state ~delta:7 ~max_offset:7 in
  let updated =
    set_local host synthesis.id { (local host synthesis.id) with synthesis = state }
  in
  assert (
    Synthesis_view.Mode.equal
      (Synthesis_view.State.mode (local updated synthesis.id).synthesis)
      Metrics);
  assert (
    Synthesis_view.Mode.equal
      (Synthesis_view.State.mode (local updated other.id).synthesis)
      Summary);
  assert (phys_equal host.registry updated.registry);
  let other_commands =
    catalog { host with focus = Some other.id } ~project:None ~jobs:[]
  in
  assert (
    not
      (List.exists other_commands ~f:(fun command ->
         String.equal command.id "synthesis.metrics")))
;;

let%test_unit "Ctrl-U clears focused filters without submitting or touching other tiles" =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "filter-recovery") in
  let host = receive empty snapshot in
  let first = List.hd_exn snapshot.tiles
  and other = List.last_exn snapshot.tiles in
  let host = set_local host first.id { default_local with filter = "no-match" } in
  let host = set_local host other.id { default_local with filter = "keep" } in
  let recover editing_filter =
    let before = { host with editing_filter } in
    let after, effect = input before Clear_filter ~commands:[] in
    assert (String.is_empty (local after first.id).filter);
    assert (String.equal (local after other.id).filter "keep");
    assert (phys_equal before.registry after.registry);
    assert (Bool.equal after.editing_filter editing_filter);
    match effect with
    | No_effect -> ()
    | _ -> assert false
  in
  recover true;
  recover false;
  match decode_event (Key_press { key = ASCII 'u'; mods = [ Ctrl ] }) with
  | Some Clear_filter -> ()
  | _ -> assert false
;;

type launch_target =
  { session_id : W.Session_id.t
  ; workspace_id : W.Workspace_id.t
  ; context_id : W.Context_id.t
  ; binding_revision : int
  ; selection_revision : int
  }

let launch_target t =
  match t.registry, active t with
  | Some s, Some w ->
    let c = W.context s w.context in
    Some
      { session_id = s.session_id
      ; workspace_id = w.id
      ; context_id = c.id
      ; binding_revision = w.binding_revision
      ; selection_revision = c.selection_revision
      }
  | _ -> None
;;

let selection_after_allocation (s : W.Snapshot.t) target run =
  let w =
    List.find s.workspaces ~f:(fun w -> W.Workspace_id.equal w.id target.workspace_id)
  in
  let c = List.find s.contexts ~f:(fun c -> W.Context_id.equal c.id target.context_id) in
  match w, c with
  | Some w, Some c
    when W.Session_id.equal s.session_id target.session_id
         && W.Context_id.equal w.context c.id
         && w.binding_revision = target.binding_revision
         && c.selection_revision = target.selection_revision ->
    Some
      (W.Mutation.Select_run
         { workspace = w.id
         ; context = c.id
         ; expected_selection_revision = c.selection_revision
         ; run = Some run
         })
  | _ -> None
;;

let%test_unit "focus with no visible tiles returns an option and a distinct no-effect" =
  let s = W.initial ~session_id:(W.Session_id.of_string "empty-focus") in
  let s = { s with tiles = [] } in
  let t = receive empty s in
  let t, effect = input t Focus ~commands:[] in
  let focus : W.Tile_id.t option = t.focus in
  assert (Option.is_none focus);
  assert (
    match effect with
    | No_effect -> true
    | _ -> false);
  let reference : W.Mutation.t option = select_run empty None in
  assert (Option.is_none reference)
;;

let%test_unit "actual catalog and palette can cancel an allocated owned launch but not \
               history"
  =
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"
    ; id = "allocated"
    ; build = None
    ; label = None
    }
  in
  let active : Asic.Pending.t =
    { key = "run:allocated"
    ; kind = "run"
    ; state = "executing"
    ; run = Some run
    ; error = None
    }
  in
  let snapshot : Asic.Snapshot.t =
    { configured = true
    ; flows = []
    ; description_json = None
    ; preview = None
    ; runs = []
    ; operations =
        [ active
        ; { active with key = "run:completed"; state = "completed" }
        ; { active with key = "run:detached"; state = "detached" }
        ; { active with
            key = "run:failed"
          ; state = "failed"
          ; error = Some "fixture failure"
          }
        ; { active with key = "run:queued"; state = "pending"; run = None }
        ]
    ; summaries = []
    ; cache_error = None
    ; finalizations = []
    ; artifacts = []
    ; artifact_pages = []
    ; artifact_byte_pages = []
    ; inspections = []
    ; inspection_details = []
    }
  in
  let commands = asic_cancel_commands snapshot in
  assert (List.length commands = 2);
  let t =
    receive
      empty
      (W.initial ~session_id:(W.Session_id.of_string "cancel-after-allocation"))
  in
  let press t key = input t key ~commands in
  let t, _ = press t (Character ' ') in
  let t, _ = press t (Character 'c') in
  let t, _ = press t (Character 'c') in
  let t =
    List.fold (String.to_list "run:allocated") ~init:t ~f:(fun t ch ->
      fst (press t (Character ch)))
  in
  let _, effect = press t Enter in
  assert (
    match effect with
    | Execute (_, Asic (Cancel key)) -> String.equal key active.key
    | _ -> false)
;;

let%test_unit "selectors and project-scoped tiles do not acquire ASIC evidence interest" =
  let s = W.initial ~session_id:(W.Session_id.of_string "evidence-interest") in
  let workspace = (List.hd_exn s.workspaces).id in
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id = "selected"; build = None; label = None }
  in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let s =
    apply
      s
      (Select_run
         { workspace
         ; context = s.main_context
         ; expected_selection_revision = 0
         ; run = Some run
         })
  in
  let geometry : W.Geometry.t = { x = 0; y = 0; width = 40; height = 8 } in
  let s = apply s (Create_tile { workspace; kind = "project-tests"; geometry }) in
  assert (List.is_empty (evidence_runs (receive empty s)));
  let s = apply s (Create_tile { workspace; kind = "timing"; geometry }) in
  let timing = List.last_exn s.tiles in
  assert (List.equal Run_ref.equal (evidence_runs (receive empty s)) [ run ]);
  let s = apply s (Set_tile_hidden { tile = timing.id; hidden = true }) in
  assert (List.is_empty (evidence_runs (receive empty s)))
;;

let%test_unit "palette captures text and revalidates registry target" =
  let s = W.initial ~session_id:(W.Session_id.of_string "test") in
  let t = receive empty s in
  let commands = [ command "test" "Run project tests" "" Test ] in
  let press t key = input t key ~commands in
  let t, _ = press t (Character ' ') in
  let t, _ = press t (Character 'c') in
  let t, _ = press t (Character 'c') in
  let t, effect = press t (Character 't') in
  assert (Option.is_some t.palette);
  assert (
    match effect with
    | No_effect -> true
    | _ -> false);
  let changed =
    W.apply
      s
      (Mutate
         { expected_revision = 0
         ; mutation = Make_independent (List.last_exn s.workspaces).id
         })
    |> Result.ok
    |> Option.value_exn
  in
  let t = receive t changed in
  let t, effect = press t Enter in
  assert (Option.is_none t.palette);
  assert (
    match effect with
    | No_effect -> true
    | _ -> false)
;;

let%test_unit "linked contexts and pins use registry semantics; local state survives" =
  let s = W.initial ~session_id:(W.Session_id.of_string "test") in
  let t = receive empty s in
  let tile = List.hd_exn s.tiles in
  let t = set_local t tile.id { default_local with scroll = 7; filter = "old" } in
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id = "A"; build = None; label = None }
  in
  let mutation = select_run t (Some run) |> Option.value_exn in
  let s =
    W.apply s (Mutate { expected_revision = s.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let t = receive t s in
  assert ((local t tile.id).scroll = 7);
  List.iter s.tiles ~f:(fun tile ->
    let r = W.resolve_tile s tile.id |> Result.ok |> Option.value_exn in
    assert (Option.equal Run_ref.equal r.run (Some run)))
;;

let%test_unit "frontend events capture modal shortcuts, bracketed paste and focus" =
  let s = W.initial ~session_id:(W.Session_id.of_string "events") in
  let commands = [ command "test" "Run project tests" "" Test ] in
  let send t event =
    match decode_event event with
    | None -> t, No_effect
    | Some event -> input t event ~commands
  in
  let key ch : Bonsai_term.Event.t = Key_press { key = ASCII ch; mods = [] } in
  let t = receive empty s in
  let t, _ = send t (key ' ') in
  let t, _ = send t (key 'c') in
  let t, _ = send t (key 'c') in
  let focus = t.focus in
  let t, effect = send t (key 'q') in
  assert (
    match effect with
    | No_effect -> true
    | _ -> false);
  assert (String.equal (Option.value_exn t.palette).query "q");
  let t, _ = send t (Paste `Start) in
  let t, _ = send t (key 't') in
  let t, _ = send t (Paste `End) in
  assert (String.equal (Option.value_exn t.palette).query "q");
  let t, _ = send t (Key_press { key = Escape; mods = [] }) in
  assert (Option.equal W.Tile_id.equal t.focus focus);
  assert (Option.is_none t.palette)
;;

let%test_unit "pin, unlink and relink fence delayed reads without sharing local \
               navigation"
  =
  let s = W.initial ~session_id:(W.Session_id.of_string "fences") in
  let overview = List.hd_exn s.workspaces
  and timing = List.last_exn s.workspaces in
  let a : Run_ref.t =
    { backend = Backend_id.of_string "asic"; id = "A"; build = None; label = None }
  in
  let b = { a with id = "B" } in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let choose s workspace run =
    let w = W.workspace s workspace in
    let c = W.context s w.context in
    apply
      s
      (Select_run
         { workspace
         ; context = c.id
         ; expected_selection_revision = c.selection_revision
         ; run = Some run
         })
  in
  let s = choose s overview.id a in
  let selector = List.last_exn s.tiles in
  let old = W.resolve_tile s selector.id |> Result.ok |> Option.value_exn in
  let s = apply s (Make_independent timing.id) in
  assert (not (W.view_is_current s old));
  let s = choose s overview.id b in
  let resolved = W.resolve_tile s selector.id |> Result.ok |> Option.value_exn in
  assert (Option.equal Run_ref.equal resolved.run (Some a));
  let s = apply s (Set_tile_binding { tile = selector.id; binding = Pin_run a }) in
  let s = apply s (Link_context { workspace = timing.id; context = s.main_context }) in
  let pinned = W.resolve_tile s selector.id |> Result.ok |> Option.value_exn in
  assert (Option.equal Run_ref.equal pinned.run (Some a));
  let s = apply s (Set_tile_binding { tile = selector.id; binding = Follow }) in
  let following = W.resolve_tile s selector.id |> Result.ok |> Option.value_exn in
  assert (Option.equal Run_ref.equal following.run (Some b));
  let t = receive empty s in
  let t = set_local t selector.id { default_local with filter = "A"; scroll = 9 } in
  let t = switch (switch t timing.id) overview.id in
  assert ((local t selector.id).scroll = 9);
  assert (String.equal (local t selector.id).filter "A");
  assert (not (W.view_is_current s pinned))
;;

let%test_unit "additive default preset exposes synthesis and preserves saved contexts, \
               hidden tiles and geometry"
  =
  let s = W.initial ~session_id:(W.Session_id.of_string "additive-layout") in
  let workspace = List.hd_exn s.workspaces in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let s = apply s (Make_independent workspace.id) in
  let context = W.context s (W.workspace s workspace.id).context in
  let s =
    apply
      s
      (Select_run
         { workspace = workspace.id
         ; context = context.id
         ; expected_selection_revision = context.selection_revision
         ; run = Some Fs0_fixture.run_b
         })
  in
  let selector = List.hd_exn s.tiles in
  let s = apply s (Set_tile_hidden { tile = selector.id; hidden = true }) in
  let original_contexts = s.contexts
  and original_workspaces = s.workspaces in
  let workspace = W.workspace s workspace.id in
  let pending = missing_default_tiles s workspace in
  assert (
    List.exists pending ~f:(function
      | Create_tile { kind = "synthesis"; _ } -> true
      | _ -> false));
  let s = List.fold pending ~init:s ~f:apply in
  assert (List.equal W.Context.equal original_contexts s.contexts);
  assert (List.equal W.Arrangement.equal original_workspaces s.workspaces);
  assert (W.Tile.equal (W.tile s selector.id) { selector with hidden = true });
  assert (List.is_empty (missing_default_tiles s workspace));
  let commands = catalog (receive empty s) ~project:None ~jobs:[] in
  assert (
    List.exists commands ~f:(fun command -> String.equal command.id "tile.add.synthesis"));
  assert (
    List.exists commands ~f:(fun command ->
      match command.action with
      | Apply_default_layout -> true
      | _ -> false))
;;

let%test_unit "allocation selects only an unchanged captured context" =
  let s = W.initial ~session_id:(W.Session_id.of_string "allocation") in
  let t = receive empty s in
  let target = launch_target t |> Option.value_exn in
  let run : Run_ref.t =
    { backend = Backend_id.of_string "asic"
    ; id = "allocated"
    ; build = None
    ; label = None
    }
  in
  assert (Option.is_some (selection_after_allocation s target run));
  let s =
    W.apply
      s
      (Mutate { expected_revision = 0; mutation = Make_independent target.workspace_id })
    |> Result.ok
    |> Option.value_exn
  in
  assert (Option.is_none (selection_after_allocation s target run));
  let s =
    W.apply
      s
      (Mutate
         { expected_revision = s.revision
         ; mutation =
             Link_context { workspace = target.workspace_id; context = target.context_id }
         })
    |> Result.ok
    |> Option.value_exn
  in
  assert (Option.is_none (selection_after_allocation s target run))
;;
