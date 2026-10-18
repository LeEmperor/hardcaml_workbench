open! Core
open Hardcaml_workbench_protocol
open Bonsai_term
module H = Workspace_host
module W = Workspace
module T = Tile_presentation
module E = Evidence_style
module P = Hardcaml_workbench_workspaces

module Role = struct
  type t =
    | Background
    | Foreground
    | Surface
    | Muted
    | Border
    | Focus
    | Selection
    | Running
    | Success
    | Warning
    | Failure
    | Metric
    | Active_tab
    | Inactive_tab
    | Matched
    | Heading

  let rgb r g b = Attr.Color.rgb ~r ~g ~b

  type palette =
    { background : Attr.Color.t
    ; foreground : Attr.Color.t
    ; surface : Attr.Color.t
    ; card : Attr.Color.t
    ; muted : Attr.Color.t
    ; border : Attr.Color.t
    ; accent : Attr.Color.t
    ; selective : Attr.Color.t
    ; metric : Attr.Color.t
    ; success : Attr.Color.t
    ; warning : Attr.Color.t
    ; failure : Attr.Color.t
    }

  let palette (appearance : Appearance.t) =
    let make
      background
      foreground
      surface
      card
      muted
      border
      accent
      selective
      metric
      success
      warning
      failure
      =
      let c (r, g, b) = rgb r g b in
      { background = c background
      ; foreground = c foreground
      ; surface = c surface
      ; card = c card
      ; muted = c muted
      ; border = c border
      ; accent = c accent
      ; selective = c selective
      ; metric = c metric
      ; success = c success
      ; warning = c warning
      ; failure = c failure
      }
    in
    match appearance.scheme with
    | Carbon ->
      make
        (0, 0, 0)
        (216, 216, 220)
        (35, 35, 35)
        (17, 17, 17)
        (153, 153, 163)
        (91, 91, 104)
        (151, 177, 226)
        (151, 169, 198)
        (220, 196, 147)
        (151, 198, 151)
        (225, 185, 116)
        (235, 139, 151)
    | Slate ->
      make
        (28, 31, 36)
        (218, 221, 226)
        (49, 55, 64)
        (34, 38, 44)
        (157, 165, 177)
        (100, 112, 128)
        (153, 184, 213)
        (157, 178, 195)
        (214, 197, 157)
        (155, 197, 168)
        (224, 188, 130)
        (226, 144, 154)
    (* Adapted from read-only Ches ui/theme.ml Crimson: warm ground and rose accent. Lift
       muted/border/error luminance for small evidence text and status contrast. *)
    | Crimson ->
      make
        (12, 10, 10)
        (224, 210, 210)
        (53, 35, 40)
        (19, 16, 16)
        (167, 139, 145)
        (112, 83, 92)
        (232, 93, 117)
        (208, 140, 154)
        (255, 203, 107)
        (158, 206, 106)
        (255, 184, 108)
        (255, 112, 136)
    | Neon ->
      make
        (17, 22, 35)
        (224, 233, 249)
        (43, 55, 83)
        (25, 34, 53)
        (153, 173, 202)
        (132, 151, 236)
        (99, 218, 255)
        (117, 202, 221)
        (255, 207, 102)
        (115, 231, 167)
        (255, 202, 105)
        (255, 116, 144)
  ;;

  let backdrop (appearance : Appearance.t) role =
    let p = palette appearance in
    match role with
    | Selection | Active_tab ->
      (match appearance.scheme with
       | Carbon -> rgb 48 48 56
       | Slate -> rgb 64 75 88
       | Crimson -> rgb 76 39 49
       | Neon -> rgb 43 55 83)
    | Surface | Matched -> p.surface
    | Foreground ->
      (match appearance.preset with
       | Studio | Structured_studio -> p.card
       | _ -> p.background)
    | _ -> p.background
  ;;

  let foreground (appearance : Appearance.t) role =
    let p = palette appearance in
    let accent =
      match appearance.color with
      | Restrained -> p.foreground
      | Selective -> p.selective
      | Vivid -> p.accent
    in
    match role with
    | Muted | Inactive_tab -> p.muted
    | Border ->
      (match appearance.color with
       | Vivid -> p.border
       | _ -> p.muted)
    | Focus | Selection | Active_tab -> accent
    | Metric | Matched ->
      (match appearance.color with
       | Vivid -> p.metric
       | _ -> p.foreground)
    | Success -> p.success
    | Warning -> p.warning
    | Failure -> p.failure
    | Running -> accent
    | Heading -> rgb 255 255 255
    | _ -> p.foreground
  ;;

  let attrs (appearance : Appearance.t) role =
    let fg = foreground appearance role in
    let bg = backdrop appearance role in
    [ Attr.fg fg; Attr.bg bg ]
    @
    match role with
    | Matched -> [ Attr.underline; Attr.bold ]
    | Focus | Selection | Metric | Active_tab | Heading -> [ Attr.bold ]
    | _ -> []
  ;;
end

(** Clip the actual terminal image, not UTF-8 bytes. Notty/Bonsai measure display cells,
    including wide and combining characters, before clipping. *)
let box ~width ~height view =
  let width = Int.max 0 width
  and height = Int.max 0 height in
  let view =
    View.crop
      ~r:(Int.max 0 (View.width view - width))
      ~b:(Int.max 0 (View.height view - height))
      view
  in
  View.zcat [ view; View.rectangle ~width ~height () ]
;;

let colored appearance role view =
  let bg = Role.backdrop appearance role in
  View.with_colors ~fill_backdrop:true view ~fg:(Role.palette appearance).foreground ~bg
;;

let lines ?(appearance = Appearance.default) ?(role = Role.Foreground) ~width ~height rows
  =
  List.take rows (Int.max 0 height)
  |> List.map ~f:(View.text ~attrs:(Role.attrs appearance role))
  |> View.vcat
  |> box ~width ~height
  |> colored appearance role
;;

let framed = Panel.framed

let studio (appearance : Appearance.t) =
  match appearance.preset with
  | Studio | Structured_studio -> true
  | _ -> false
;;

let frame_tile ?(enabled = true) appearance ~focused ~width ~height content =
  let geometry =
    Panel.geometry
      ~framed:(enabled && framed appearance ~width ~height)
      ~width
      ~height
      ~horizontal_padding:0
      ~vertical_padding:0
  in
  Panel.render
    appearance
    ~attrs:(Role.attrs appearance (if focused then Focus else Border))
    ~title:View.none
    ~geometry
    ~width
    ~height
    content
;;

type data =
  { project : Project.t option
  ; jobs : Job.t list
  ; runs : (Run_ref.t * string) list
  ; log_lines : Job_id.t -> string list
  ; run_lines : Run_ref.t -> string -> string list
  ; run_context : Run_ref.t -> string list
  ; summary : Run_ref.t -> Asic.Summary.t option
  ; status : string
  ; environment : string
  ; asic_lines : string list
  ; asic : Asic.Snapshot.t option
  }

let run_label (run : Run_ref.t) = Backend_id.to_string run.backend ^ "/" ^ run.id

let display_run (run : Run_ref.t) =
  Backend_id.to_string run.backend ^ "/" ^ Overview_tiles.short_id run.id
;;

let cell_width text = View.width (View.text text)

let fit_label ~width text =
  let width = Int.max 0 width in
  if cell_width text <= width
  then text
  else if width < 5
  then E.text (E.clip ~width (E.plain text))
  else (
    let rec scalars offset acc =
      if offset >= String.length text
      then acc
      else (
        let decoded = Stdlib.String.get_utf_8_uchar text offset in
        let length = Stdlib.Uchar.utf_decode_length decoded in
        scalars (offset + length) (String.sub text ~pos:offset ~len:length :: acc))
    in
    let tail_width = (width - 1) / 2 in
    let _, tail =
      List.fold (scalars 0 []) ~init:(0, "") ~f:(fun (used, tail) scalar ->
        let size = cell_width scalar in
        if used + size > tail_width then tail_width, tail else used + size, scalar ^ tail)
    in
    E.text (E.clip ~width:(width - cell_width tail - 1) (E.plain text)) ^ "~" ^ tail)
;;

let run_selector_row ~width ~status_width ~cursor ~active run status =
  let marker = (if cursor then ">" else " ") ^ if active then "*" else " " in
  let status = E.text (E.clip ~width:status_width (E.plain status)) in
  let label_width = Int.max 0 (width - 3 - status_width - 1) in
  let label = fit_label ~width:label_width (run_label run) in
  marker
  ^ " "
  ^ label
  ^ String.make (Int.max 0 (label_width - cell_width label)) ' '
  ^ " "
  ^ status
;;

(** Lifecycle vocabulary only: an acceptance verdict or words inside an ID/report do not
    describe the execution lifecycle. Unknown provider values stay neutral. *)
let run_status_role = function
  | "completed" -> Role.Success
  | "failed" -> Failure
  | "running" | "starting" | "observing" -> Running
  | "pending" | "queued" | "cancelled" | "interrupted" | "skipped" -> Warning
  | _ -> Foreground
;;

(** Only lifecycle fields enter this mapping, never arbitrary report text. *)
let run_indicator : string -> Indicator.t = function
  | "running" | "starting" | "observing" -> Running
  | "pending" | "queued" -> Pending
  | "completed" -> Completed
  | "failed" -> Failed
  | "cancelled" | "interrupted" -> Cancelled
  | "skipped" -> Skipped
  | _ -> Unknown
;;

let indicator_view ?indicator_frames appearance role kind =
  let glyph = Indicator.view ?frames:indicator_frames appearance.Appearance.icons kind in
  if Appearance.Icons.equal appearance.icons None_
  then View.none
  else
    View.hcat [ box ~width:1 ~height:1 glyph; View.text " " ]
    |> View.with_colors' ~fg:(Role.foreground appearance role)
;;

let run_has_producer data run =
  Option.exists data.asic ~f:(fun snapshot ->
    List.exists snapshot.Asic.Snapshot.runs ~f:(fun execution ->
      Run_ref.equal execution.run run
      && List.mem
           [ "queued"; "pending"; "starting"; "running"; "observing" ]
           execution.status
           ~equal:String.equal)
    && List.exists snapshot.operations ~f:(fun operation ->
      String.equal operation.kind "run"
      && (Plain_rpc.active operation || String.equal operation.state "reserving")
      && Option.exists operation.run ~f:(Run_ref.equal run)))
;;

let run_selector_view
  ?indicator_frames
  appearance
  ~width
  ~status_width
  ~cursor
  ~active
  run
  status
  =
  let status_role = run_status_role status in
  let icon =
    indicator_view ?indicator_frames appearance status_role (run_indicator status)
  in
  let text_width = Int.max 0 (width - View.width icon) in
  let row = run_selector_row ~width:text_width ~status_width ~cursor ~active run status in
  let identity_width = Int.max 0 (text_width - status_width) in
  let identity = E.text (E.clip ~width:identity_width (E.plain row)) in
  let status = E.text (E.clip ~width:status_width (E.plain status)) in
  let attrs role =
    Role.attrs appearance role
    @ if cursor then [ Attr.bg (Role.backdrop appearance Selection) ] else []
  in
  View.hcat
    [ View.text ~attrs:(attrs (if cursor then Selection else Foreground)) identity
    ; icon
      |> View.with_colors'
           ?bg:(if cursor then Some (Role.backdrop appearance Selection) else None)
    ; View.text ~attrs:(attrs status_role) status
    ]
  |> box ~width ~height:1
;;

let request_scope (execution : Asic.Run.t) =
  match execution.selection with
  | None -> "Request scope: unknown (selection unavailable)"
  | Some selection -> "Request endpoint: " ^ selection.endpoint
;;

let request_context snapshot run =
  Option.bind snapshot ~f:(fun (snapshot : Asic.Snapshot.t) ->
    List.find snapshot.runs ~f:(fun execution -> Run_ref.equal execution.run run))
  |> Option.value_map
       ~default:[ "Request scope: unknown (execution unavailable)" ]
       ~f:(fun execution -> [ request_scope execution ])
;;

let stage_lines (execution : Asic.Run.t) kind =
  let scope = request_scope execution in
  match kind with
  | "placement" | "cts" | "routing" | "checks" | "finalization" | "timing" ->
    [ "No terminal result imported; inspect exact finalization reference"
    ; scope
    ; "Stage completion / verification not inferred from cached synthesis metrics"
    ]
  | _ -> [ "Unsupported evidence kind: " ^ kind; scope ]
;;

let finalization_lines (f : Asic.Finalization.t) =
  [ "Finalization: " ^ f.key
  ; sprintf "State: %s · owned=%b" f.state f.owned
  ; "Phase: " ^ Option.value f.phase ~default:"unreported"
  ; "Reported operation: " ^ Option.value f.operation_status ~default:"unreported"
  ; "Acceptance: "
    ^ Option.value
        f.acceptance
        ~default:
          (if f.acceptance_requested then "requested / unreported" else "not requested")
  ]
  @ Option.to_list (Option.map f.error ~f:(fun e -> "ERROR: " ^ e))
  @ [ "Run: " ^ run_label f.run; "Palette: Reconnect finalization (read-only) " ^ f.key ]
;;

let run_lines snapshot run kind =
  match (snapshot : Asic.Snapshot.t option) with
  | None -> [ "ASIC provider not loaded" ]
  | Some asic ->
    if String.equal kind "finalization-status"
    then
      List.filter asic.finalizations ~f:(fun f -> Run_ref.equal f.run run)
      |> List.concat_map ~f:finalization_lines
    else (
      match List.find asic.runs ~f:(fun r -> Run_ref.equal r.run run) with
      | None -> [ "Saved run unavailable; no replacement selected" ]
      | Some execution ->
        (match List.find asic.summaries ~f:(fun s -> Run_ref.equal s.run run) with
         | None ->
           (if String.equal kind "synthesis" then [] else stage_lines execution kind)
           @ [ "Loading summary for " ^ run_label run
             ; "Observed execution: " ^ execution.status
             ]
           @ Option.to_list execution.error
         | Some summary
           when Terminal_result_view.supports kind && Option.is_some summary.terminal ->
           Terminal_result_view.lines
             (Option.value_exn summary.terminal)
             ~kind
             ~detail:false
           @ [ "Freshness: "
               ^ Sexp.to_string_hum (Asic.Summary.Freshness.sexp_of_t summary.freshness)
             ; "Observed execution: " ^ execution.status
             ; request_scope execution
             ]
           @ Option.to_list execution.error
         | Some summary ->
           let metrics =
             if String.equal kind "timing"
             then
               if List.is_empty summary.timing
               then stage_lines execution kind
               else
                 List.map summary.timing ~f:(fun (name, value, unit_) ->
                   sprintf "%s: %g %s" name value unit_)
             else if String.equal kind "synthesis"
             then
               [ "Cell count: "
                 ^ Option.value_map
                     summary.cell_count
                     ~default:"unavailable"
                     ~f:Int.to_string
               ]
             else if String.equal kind "checks"
             then stage_lines execution kind @ Synthesis_view.checks_lines summary
             else stage_lines execution kind
           in
           let breakdown =
             if not (String.equal kind "synthesis")
             then []
             else
               [ ("Cells: "
                  ^
                  if List.is_empty summary.cells
                  then "breakdown unavailable"
                  else
                    List.map summary.cells ~f:(fun (name, count) ->
                      sprintf "%s=%d" name count)
                    |> String.concat ~sep:", ")
               ]
           in
           metrics
           @ [ "Freshness: "
               ^ Sexp.to_string_hum (Asic.Summary.Freshness.sexp_of_t summary.freshness)
             ]
           @ breakdown
           @ [ "Evidence: "
               ^ Filename.basename summary.execution_file
               ^ " #"
               ^ String.prefix summary.source_digest 12
             ; "Run completion: "
               ^ summary.completion
               ^ " | acceptance: "
               ^ summary.acceptance
             ; "Observed execution: " ^ execution.status
             ; "Producer: provider checkpoint (inspect synthesis evidence)"
             ; "Source: "
               ^ Filename.basename summary.execution_file
               ^ " (inspect for full path)"
             ]
           @ Option.to_list execution.error
           @
           if (not (String.equal kind "synthesis")) || List.is_empty summary.cells
           then []
           else
             "CELL BREAKDOWN"
             :: List.map summary.cells ~f:(fun (name, count) ->
               sprintf "  %s: %d" name count)))
;;

let wrap_cells ~width text =
  let width = Int.max 1 width in
  let rec loop start offset cells output =
    if offset >= String.length text
    then List.rev (String.sub text ~pos:start ~len:(offset - start) :: output)
    else (
      let decoded = Stdlib.String.get_utf_8_uchar text offset in
      let length = Stdlib.Uchar.utf_decode_length decoded in
      let cell_width =
        View.uchar_tty_width (Stdlib.Uchar.utf_decode_uchar decoded) |> Int.max 0
      in
      if cells + cell_width > width && offset > start
      then
        loop offset offset 0 (String.sub text ~pos:start ~len:(offset - start) :: output)
      else loop start (offset + length) (cells + cell_width) output)
  in
  loop 0 0 0 []
;;

let artifact_inspector host tile =
  Option.bind (H.local host tile.W.Tile.id).artifacts ~f:(fun view ->
    Option.bind host.H.registry ~f:(fun registry ->
      W.resolve_tile registry tile.id
      |> Result.ok
      |> Option.bind ~f:(fun reference ->
        Artifact_view.reconcile_scope view ~scope:reference.run)))
;;

(* Previews are project-scoped plans for NEW runs, not evidence belonging to the observed
   run. Only advertise a matching selection beside a checklist action. *)
let checklist_selection host data run stage =
  Stage_action.resolve
    ~stage
    ~remembered:host.H.remembered_selection
    ~observed:
      (Option.bind data.asic ~f:(fun snapshot ->
         List.find snapshot.runs ~f:(fun execution -> Run_ref.equal execution.run run)
         |> Option.bind ~f:(fun execution -> execution.selection)))
    ~snapshot:data.asic
;;

let checklist_preview host data tile =
  Option.bind host.H.registry ~f:(fun registry ->
    W.resolve_tile registry tile.W.Tile.id
    |> Result.ok
    |> Option.bind ~f:(fun reference -> reference.run)
    |> Option.bind ~f:(fun run ->
      let stages = Overview_tiles.observed_stages ~asic:data.asic ~run in
      Option.bind
        (H.stage_cursor (H.local host tile.id) ~run ~stages)
        ~f:(fun stage ->
          match
            ( checklist_selection host data run stage
            , Option.bind data.asic ~f:(fun asic -> asic.preview) )
          with
          | Ok selection, Some preview
            when Asic.Selection.equal selection preview.selection
                 && Option.is_none host.stage_preparation
                 && Planned_run.launchable host.planned_run preview -> Some preview
          | _ -> None)))
;;

let checklist_hints host data tile =
  if not (H.policy host tile).hints
  then []
  else (
    match checklist_preview host data tile with
    | None -> [ "r prepare NEW run"; "j/k browse | Enter inspect" ]
    | Some preview ->
      [ "Space c c: Launch"
      ; "or Launch and view"
      ; "r prepare NEW run"
      ; "j/k browse | Enter inspect"
      ; "Matching plan: " ^ preview.selection.endpoint
      ])
;;

let utility_rows host data tile =
  let policy = H.policy host tile in
  Option.bind host.H.registry ~f:(fun registry ->
    let selected_run =
      W.resolve_tile registry tile.W.Tile.id
      |> Result.ok
      |> Option.bind ~f:(fun reference -> reference.run)
    in
    match tile.kind with
    | "live-status" when H.compact_summary host tile ->
      Some
        [ Overview_tiles.row "Connection" data.status
        ; Overview_tiles.row
            "Project"
            (Option.value_map data.project ~default:"none" ~f:(fun p -> p.Project.name))
        ; Overview_tiles.row "Scope" "Project tests"
        ]
    | "live-status" ->
      Some
        (Overview_tiles.status_rows
           ~snapshot:registry
           ~active_workspace:host.active
           ~project:data.project
           ~selected_run
           ~connection:data.status)
    | "workspace-tabs" ->
      Some
        (Overview_tiles.navigation_rows ~snapshot:registry ~active_workspace:host.active
         |> List.filter ~f:(fun row ->
           Option.exists row.Overview_tiles.workspace ~f:(fun id ->
             List.exists (H.workspace_choices host tile.id) ~f:(fun w ->
               W.Workspace_id.equal id w.id)))
         |> List.map ~f:(fun row ->
           let browsing =
             Option.equal
               W.Workspace_id.equal
               row.workspace
               (Option.map (H.workspace_cursor host tile.id) ~f:(fun w -> w.id))
           in
           { row with
             value =
               (if row.active then "active" else if browsing then "Enter to open" else "")
           ; role = (if browsing then Active else row.role)
           }))
    | "stage-checklist" ->
      let local = H.local host tile.id in
      let observed =
        Option.value_map selected_run ~default:[] ~f:(fun run ->
          Overview_tiles.observed_stages ~asic:data.asic ~run)
      in
      let selected =
        Option.bind selected_run ~f:(fun run ->
          H.stage_cursor local ~run ~stages:observed)
      in
      let stages =
        match selected_run, observed with
        | Some run, (_ :: _ as stages) ->
          (if local.utility_detail then Option.to_list selected else stages)
          |> List.map ~f:(fun stage ->
            Overview_tiles.asic_stage_row
              ~run
              ~selected:(Option.exists selected ~f:(fun s -> String.equal s.id stage.id))
              stage)
        | _ ->
          Overview_tiles.stage_rows ~selected_run ~asic:data.asic ~observation:None ()
      in
      let facts =
        Option.bind selected_run ~f:data.summary
        |> Option.value_map ~default:[] ~f:(fun summary ->
          Overview_tiles.summary_rows ~freshness:policy.freshness summary)
      in
      let interaction =
        if (not local.utility_detail) || not policy.hints
        then []
        else
          [ Overview_tiles.row
              ~role:Muted
              "Interaction"
              "Esc overview; r prepares a NEW run through advertised endpoint"
          ]
          @ (match selected_run, selected with
             | Some run, Some stage ->
               [ (match checklist_selection host data run stage with
                  | Error reason -> Overview_tiles.row ~role:Warning "New run" reason
                  | Ok selection ->
                    Overview_tiles.row
                      ~role:Muted
                      "New run inputs"
                      (selection.flow
                       ^ "/"
                       ^ selection.profile
                       ^ " → "
                       ^ selection.endpoint
                       ^ " | assignments: "
                       ^ String.concat ~sep:"; " selection.assignments))
               ]
             | _ -> [])
          @ Option.value_map host.stage_preparation ~default:[] ~f:(fun reason ->
            [ Overview_tiles.row ~role:Warning "Preparation" reason ])
          @ (checklist_preview host data tile
             |> Option.value_map ~default:[] ~f:(fun preview ->
               [ Overview_tiles.row
                   ~role:Running
                   "Matching project preview"
                   (preview.plan_identity ^ " — Space c c: Launch / Launch and view")
               ]))
      in
      Some
        ((if policy.run_reference
          then
            [ Overview_tiles.row
                ~role:Muted
                "Run"
                (Option.value_map selected_run ~default:"none selected" ~f:run_label)
            ]
          else [])
         @ (if H.compact_summary host tile && not local.utility_detail
            then Overview_tiles.checklist_rows ~compact:true ~stages ~aggregate:facts ()
            else stages @ facts)
         @ interaction)
    | _ -> None)
;;

let utility_attrs appearance : Overview_tiles.Role.t -> Attr.t list = function
  | Heading -> Role.attrs appearance Heading
  | Foreground -> Role.attrs appearance Foreground
  | Muted -> Role.attrs appearance Muted
  | Active -> Role.attrs appearance Selection
  | Running -> Role.attrs appearance Running
  | Success -> Role.attrs appearance Success
  | Warning -> Role.attrs appearance Warning
  | Failure -> Role.attrs appearance Failure
;;

let inspection_explorer host tile =
  Option.bind (H.local host tile.W.Tile.id).inspection ~f:(fun view ->
    Option.bind host.H.registry ~f:(fun registry ->
      W.resolve_tile registry tile.id
      |> Result.ok
      |> Option.bind ~f:(fun reference ->
        Inspection_view.reconcile_scope view ~scope:reference.run)))
;;

let evidence_attrs appearance : E.Role.t -> Attr.t list = function
  | Plain -> Role.attrs appearance Foreground
  | Muted -> Role.attrs appearance Muted
  | Validated -> Role.attrs appearance Success
  | Passed -> Role.attrs appearance Success
  | Failed -> Role.attrs appearance Failure
  | Pending | Stale -> Role.attrs appearance Warning
  | Running -> Role.attrs appearance Running
;;

let tile_run host tile =
  if Testing_workspace.is_pane tile.W.Tile.kind
  then None
  else
    Option.bind host.H.registry ~f:(fun registry ->
      W.resolve_tile registry tile.W.Tile.id
      |> Result.ok
      |> Option.bind ~f:(fun reference -> reference.run))
;;

(* Chrome is removed at typed construction locations, before wrapping/paging. Never search
   provider text: full evidence, raw reports and fallback payloads retain every source row
   even when their text resembles chrome. *)
let terminal_content host data tile ~run =
  let local = H.local host tile.W.Tile.id
  and policy = H.policy host tile in
  let summary = data.summary run in
  let exact_terminal =
    Option.exists summary ~f:(fun s ->
      Run_ref.equal s.Asic.Summary.run run && Option.is_some s.terminal)
  in
  let content =
    Terminal_result_view.semantic_rows
      ~fallback:(data.run_lines run tile.kind)
      ~request_context:(data.run_context run)
      { local.terminal_result with offset = 0 }
      ~run
      ~summary
      ~kind:tile.kind
      ~width:Int.max_value
      ~height:Int.max_value
  in
  let hint_index =
    Option.bind summary ~f:(fun s ->
      Option.map s.Asic.Summary.terminal ~f:(fun terminal ->
        2
        + List.length (data.run_context run)
        + List.length
            (Terminal_result_view.semantic_lines terminal ~kind:tile.kind ~detail:false)
        - 1))
  in
  let content =
    if not exact_terminal
    then content
    else
      List.filteri content ~f:(fun i _ ->
        i <> 0 (* run reference belongs to host chrome *)
        && (policy.freshness || i <> 1)
        && (policy.hints || not (Option.equal Int.equal (Some i) hint_index)))
  in
  (if String.equal tile.kind "finalization"
   then List.map (data.run_lines run "finalization-status") ~f:E.plain
   else [])
  @ content
;;

let synthesis_metrics_content host data tile ~run =
  let local = H.local host tile.W.Tile.id
  and policy = H.policy host tile in
  let summary = data.summary run in
  let state =
    Synthesis_view.State.scroll local.synthesis ~delta:Int.min_value ~max_offset:0
  in
  let rows =
    Synthesis_view.semantic_rows
      state
      ~summary
      ~filter:local.filter
      ~width:Int.max_value
      ~height:Int.max_value
  in
  let freshness_index =
    Option.map summary ~f:(fun s -> 2 + Int.max 1 (List.length s.Asic.Summary.metrics))
  in
  List.filter_mapi rows ~f:(fun i row ->
    if (not policy.freshness) && Option.equal Int.equal (Some i) freshness_index
    then None
    else if i = 0 && not policy.hints
    then Some (E.plain "Synthesis metrics")
    else Some row)
;;

let metrics_scope data run =
  Option.map (data.summary run) ~f:(fun s -> run, s.Asic.Summary.source_digest)
;;

let metrics_offset local data run =
  if Option.equal
       (fun (r, d) (s, e) -> Run_ref.equal r s && String.equal d e)
       local.H.metrics_scope
       (metrics_scope data run)
  then local.scroll
  else 0
;;

let compact_summary_enabled host tile =
  let local = H.local host tile.W.Tile.id in
  H.compact_summary host tile
  && Overview_summary.supports tile.kind
  && Option.is_none local.inspection
  && Option.is_none local.artifacts
  && (not local.terminal_result.detail)
  && ((not (String.equal tile.kind "synthesis"))
      || Synthesis_view.Mode.equal (Synthesis_view.State.mode local.synthesis) Summary)
;;

let compact_rows host data tile =
  if not (compact_summary_enabled host tile)
  then None
  else
    Option.map (tile_run host tile) ~f:(fun run ->
      Overview_summary.rows
        ~compact:(H.compact_summary host tile)
        ~freshness:(H.policy host tile).freshness
        ~kind:tile.W.Tile.kind
        ~run
        ~summary:(data.summary run)
        ~stages:(Overview_tiles.observed_stages ~asic:data.asic ~run)
        ())
;;

let semantic_rows host data tile ~width ~height =
  let local = H.local host tile.W.Tile.id
  and policy = H.policy host tile in
  if Option.is_some local.inspection || Option.is_some local.artifacts
  then None
  else
    Option.bind (tile_run host tile) ~f:(fun run ->
      if String.equal tile.kind "synthesis"
      then (
        let mode = Synthesis_view.State.mode local.synthesis in
        let rows =
          match mode with
          | Metrics ->
            E.page
              ~width
              ~height
              ~offset:(metrics_offset local data run)
              (synthesis_metrics_content host data tile ~run)
          | Summary | Cells ->
            let base_height =
              height
              +
              if (not policy.freshness) && Synthesis_view.Mode.equal mode Summary
              then 1
              else 0
            in
            let source_height =
              base_height
              +
              if (not policy.hints)
                 && ((Synthesis_view.Mode.equal mode Summary && base_height >= 8)
                     || (Synthesis_view.Mode.equal mode Cells && base_height >= 5))
              then 1
              else 0
            in
            let rows =
              Synthesis_view.semantic_rows
                local.synthesis
                ~summary:(data.summary run)
                ~filter:local.filter
                ~width
                ~height:source_height
            in
            let count = List.length rows in
            List.filteri rows ~f:(fun i _ ->
              (policy.freshness
               || not
                    (Synthesis_view.Mode.equal mode Summary
                     && i = 1
                     && Option.is_some (data.summary run)))
              && (policy.hints
                  || not
                       (Option.is_some (data.summary run)
                        && i = count - 1
                        && ((Synthesis_view.Mode.equal mode Summary && source_height >= 8)
                            || (Synthesis_view.Mode.equal mode Cells && source_height >= 5)
                           ))))
            |> Fn.flip List.take height
          | Details | Evidence ->
            Synthesis_view.semantic_rows
              local.synthesis
              ~summary:(data.summary run)
              ~filter:local.filter
              ~width
              ~height
        in
        Some rows)
      else if Terminal_result_view.supports tile.kind
      then (
        let state =
          Terminal_result_view.State.reconcile
            local.terminal_result
            ~run
            ~summary:(data.summary run)
        in
        Some
          (E.page
             ~width
             ~height
             ~offset:state.offset
             (terminal_content host data tile ~run)))
      else None)
;;

(* A shallow plan panel must show state and endpoint before verbose explanatory metadata.
   Summary facts each occupy one display-cell-clipped line; Enter retains the complete
   wrapped typed model, including exact identity and JSON. *)
let planned_source_rows host tile =
  let detail = (H.local host tile.W.Tile.id).utility_detail in
  let model = Planned_run.model host.H.planned_run in
  let rows = Planned_run.rows model ~detail in
  match host.H.stage_preparation with
  | Some reason ->
    [ { Planned_run.role = Warning; text = reason }
    ; { Planned_run.role = Muted; text = "Launch disabled; press r to retry preparation" }
    ]
  | None ->
    if detail
    then rows
    else (
      let selection =
        Option.value_map model.selection ~default:[] ~f:(fun selection ->
          [ { Planned_run.role = Fact
            ; text = "endpoint: " ^ selection.Asic.Selection.endpoint
            }
          ; { role = Fact
            ; text = "flow: " ^ selection.flow ^ " / profile: " ^ selection.profile
            }
          ; { role = Fact
            ; text =
                ("assignments: "
                 ^
                 if List.is_empty selection.assignments
                 then "(none)"
                 else String.concat ~sep:"; " selection.assignments)
            }
          ])
      in
      let state =
        String.lowercase (Sexp.to_string (Planned_run.sexp_of_status model.status))
      in
      let launch =
        String.lowercase
          (Sexp.to_string (Planned_run.sexp_of_launch_status model.launch.state))
      in
      let headline =
        List.map (List.take rows 1) ~f:(fun row ->
          { row with
            Planned_run.text =
              state
              ^ ": plan / "
              ^ (if Option.is_none model.preview
                 then "separate launch: "
                 else if Planned_run.equal_status model.status Ready
                 then "last launch: "
                 else "retained preview launch: ")
              ^ launch
          })
      in
      headline
      @ List.take selection 1
      @ [ { Planned_run.role = Fact
          ; text = Planned_run.launch_label model ^ ": " ^ model.launch.message
          }
        ]
      @ Option.value_map model.launch.run_id ~default:[] ~f:(fun id ->
        [ { Planned_run.role = Fact; text = "exact allocated run: " ^ id } ])
      @ Option.value_map model.launch.key ~default:[] ~f:(fun key ->
        [ { Planned_run.role = Fact; text = "submission key: " ^ key } ])
      @ List.drop selection 1)
;;

let planned_rows host tile ~width =
  let detail = (H.local host tile.W.Tile.id).utility_detail in
  planned_source_rows host tile
  |> List.concat_map ~f:(fun row ->
    let text = Artifact_view.safe row.Planned_run.text in
    (if detail then wrap_cells ~width text else [ E.text (E.clip ~width (E.plain text)) ])
    |> List.map ~f:(fun text -> { row with text }))
;;

let plan_indicator : Planned_run.status -> Indicator.t = function
  | Empty -> Not_requested
  | Pending -> Running
  | Failed -> Failed
  | Stale -> Stale
  | Ready -> Ready
;;

let producer_indicator : Planned_run.launch_status -> Indicator.t = function
  | Submitting | Allocated | Running -> Running
  | Completed -> Completed
  | Launch_failed -> Failed
  | Cancelled -> Cancelled
  | Detached | Unavailable -> Unknown
;;

let planned_role : Planned_run.role -> Role.t = function
  | Fact -> Foreground
  | Muted -> Muted
  | Warning -> Warning
  | Error -> Failure
  | Success -> Success
;;

let planned_view_rows ?indicator_frames host tile ~width =
  let model = Planned_run.model host.H.planned_run in
  let detail = (H.local host tile.W.Tile.id).utility_detail in
  planned_source_rows host tile
  |> List.concat_mapi ~f:(fun i row ->
    let kind =
      if Option.is_some host.stage_preparation
      then None
      else if i = 0
      then Some (plan_indicator model.status)
      else if i = if detail then 1 else 2
      then Some (producer_indicator model.launch.state)
      else None
    in
    let role = planned_role row.Planned_run.role in
    let icon_role =
      match kind with
      | Some Running -> Role.Running
      | Some Completed | Some Ready -> Success
      | Some Failed -> Failure
      | Some Stale | Some Cancelled -> Warning
      | _ -> Muted
    in
    let icon =
      Option.value_map
        kind
        ~default:View.none
        ~f:(indicator_view ?indicator_frames host.appearance icon_role)
    in
    let text_width = Int.max 0 (width - View.width icon) in
    let text = Artifact_view.safe row.text in
    let texts = if detail then wrap_cells ~width:text_width text else [ text ] in
    List.mapi texts ~f:(fun j text ->
      View.hcat
        [ (if j = 0 then icon else View.rectangle ~width:(View.width icon) ~height:1 ())
        ; View.text ~attrs:(Role.attrs host.appearance role) text
        ]
      |> box ~width ~height:1))
;;

let job_indicator : Job.State.t -> Indicator.t = function
  | Queued -> Pending
  | Starting | Running -> Running
  | Complete -> Completed
  | Failed -> Failed
  | Cancelled -> Cancelled
;;

let indicator_role : Indicator.t -> Role.t = function
  | Running -> Running
  | Completed -> Success
  | Failed -> Failure
  | Pending | Cancelled | Skipped | Stale -> Warning
  | Ready -> Success
  | Not_requested | Unknown | Pin | Artifact | Log | Seed | Report | Trace | Info -> Muted
;;

let simulation_annotations host data tile =
  match Testing_workspace.pane tile.W.Tile.kind with
  | Some pane ->
    (match pane with
     | Catalog ->
       [ Simulation_view.row "d discover | n/p suite | j/k case | x toggle"
       ; Simulation_view.row "a all | / filter | Enter launch | u accept"
       ]
     | Artifacts ->
       let view = H.simulation host tile.id in
       List.map
         (Option.to_list view.error @ Option.to_list view.notice)
         ~f:Simulation_view.row
     | _ -> [])
    @ Testing_workspace.rows (H.testing_state host tile.id) pane ~log_lines:data.log_lines
  | None ->
    Simulation_view.annotated_rows (H.simulation host tile.id) ~log_lines:data.log_lines
;;

let simulation_view_rows_with_selection ?indicator_frames host data tile ~width =
  simulation_annotations host data tile
  |> List.filter ~f:(fun row ->
    (not row.Simulation_view.hint) || (H.policy host tile).hints)
  |> List.concat_map
       ~f:(fun { Simulation_view.text; indicator = kind; value_start; selected; _ } ->
         let role = Option.value_map kind ~default:Role.Foreground ~f:indicator_role in
         let icon =
           Option.value_map
             kind
             ~default:View.none
             ~f:(indicator_view ?indicator_frames host.H.appearance role)
         in
         let used = ref 0 in
         wrap_cells ~width:(width - View.width icon) text
         |> List.mapi ~f:(fun i text ->
           let neutral_cells =
             Option.value_map value_start ~default:(cell_width text) ~f:(fun start ->
               Int.clamp_exn (start - !used) ~min:0 ~max:(cell_width text))
           in
           used := !used + cell_width text;
           let neutral = E.text (E.clip ~width:neutral_cells (E.plain text)) in
           let view =
             View.hcat
               [ (if i = 0
                  then icon
                  else View.rectangle ~width:(View.width icon) ~height:1 ())
               ; View.text ~attrs:(Role.attrs host.appearance Foreground) neutral
               ; View.text ~attrs:(Role.attrs host.appearance role) text
                 |> View.crop ~l:neutral_cells
               ]
             |> box ~width ~height:1
           in
           selected && i = 0, view))
;;

let simulation_view_rows ?indicator_frames host data tile ~width =
  simulation_view_rows_with_selection ?indicator_frames host data tile ~width
  |> List.map ~f:snd
;;

let simulation_cursor_pane kind =
  match Testing_workspace.pane kind with
  | Some (Catalog | Attempts | Cases | Artifacts) -> true
  | Some (Detail | Logs) | None -> false
;;

(** Display-cell wrapping precedes viewport selection. Only typed cursor metadata
    participates; provider text and checkbox membership cannot move the viewport. *)
let ensure_visible ~start ~height ~length ~selected =
  let maximum = Int.max 0 (length - Int.max 1 height) in
  let start = Int.clamp_exn start ~min:0 ~max:maximum in
  match selected with
  | Some cursor when height > 0 ->
    Int.clamp_exn
      (if cursor < start
       then cursor
       else if cursor >= start + height
       then cursor - height + 1
       else start)
      ~min:0
      ~max:maximum
  | _ -> start
;;

let%test_unit "cursor viewport keeps its origin until the cursor crosses a boundary" =
  let follow start cursor =
    ensure_visible ~start ~height:6 ~length:100 ~selected:(Some cursor)
  in
  assert (follow 20 20 = 20);
  assert (follow 20 25 = 20);
  assert (follow 20 19 = 19);
  assert (follow 20 26 = 21);
  assert (ensure_visible ~start:200 ~height:6 ~length:100 ~selected:None = 94);
  assert (ensure_visible ~start:0 ~height:0 ~length:0 ~selected:None = 0)
;;

let simulation_viewport_start host tile ~height rows =
  let local = H.local host tile.W.Tile.id in
  let selected =
    if simulation_cursor_pane tile.kind && local.follow
    then List.findi rows ~f:(fun _ (selected, _) -> selected) |> Option.map ~f:fst
    else None
  in
  ensure_visible ~start:local.scroll ~height ~length:(List.length rows) ~selected
;;

let rows host data tile ~width ~height =
  let local = H.local host tile.W.Tile.id in
  let scope =
    match host.H.registry with
    | None -> None
    | Some s -> W.resolve_tile s tile.id |> Result.ok |> Option.bind ~f:(fun r -> r.run)
  in
  let run_rows () =
    let candidates =
      List.filter data.runs ~f:(fun (r, label) ->
        String.is_substring
          (String.lowercase (run_label r ^ " " ^ label))
          ~substring:(String.lowercase local.filter))
    in
    let available = Int.min height (H.policy host tile).run_selector_rows in
    let selected = Option.first_some local.cursor (Option.map scope ~f:run_label) in
    let selected_index =
      List.findi candidates ~f:(fun _ (run, _) ->
        Option.equal String.equal selected (Some (run_label run)))
      |> Option.value_map ~default:0 ~f:fst
    in
    let start =
      Int.clamp_exn
        local.scroll
        ~min:(Int.max 0 (selected_index - Int.max 1 available + 1))
        ~max:selected_index
    in
    let status_width =
      Int.min
        (Int.max 0 (width / 3))
        (List.fold candidates ~init:0 ~f:(fun n (_, status) ->
           Int.max n (cell_width status)))
    in
    List.drop candidates start
    |> Fn.flip List.take (Int.max 0 available)
    |> List.map ~f:(fun (run, label) ->
      run_selector_row
        ~width
        ~status_width
        ~cursor:(Option.equal String.equal selected (Some (run_label run)))
        ~active:(Option.equal Run_ref.equal scope (Some run))
        run
        label)
  in
  let jobs =
    if String.equal tile.kind "project-tests"
    then
      List.filter data.jobs ~f:(fun job ->
        String.equal job.kind.namespace "dune" && String.equal job.kind.name "test")
    else data.jobs
  in
  let selected =
    Option.bind local.cursor ~f:(fun id ->
      List.find jobs ~f:(fun job -> String.equal (Job_id.to_string job.id) id))
  in
  let job_rows =
    List.map jobs ~f:(fun job ->
      sprintf
        "%s %s  %s  %s"
        (if Option.value_map selected ~default:false ~f:(fun selected ->
              Job_id.equal selected.id job.id)
         then ">"
         else " ")
        (Job_id.to_string job.id)
        (Job.State.to_string job.state)
        (Job.Kind.to_string job.kind))
  in
  let rows =
    match inspection_explorer host tile, artifact_inspector host tile with
    | Some view, _ -> Inspection_view.rows view ~width ~height
    | None, Some view -> Artifact_view.rows view ~width ~height
    | None, None ->
      (match tile.kind with
       | "planned-run" ->
         planned_rows host tile ~width |> List.map ~f:(fun row -> row.Planned_run.text)
       | "run-selector" -> run_rows ()
       | kind when Option.is_some (Timing_workspace.pane kind) ->
         (match Timing_workspace.pane kind, H.timing host tile with
          | Some pane, Some view ->
            Timing_workspace.rows ~pane ~scroll:local.scroll ~width ~height view
          | _ ->
            [ "No matching Timing investigation"
            ; "Use Inspect timing paths for this exact run"
            ])
       | kind when H.simulation_kind kind ->
         simulation_annotations host data tile
         |> List.filter ~f:(fun row ->
           (not row.Simulation_view.hint) || (H.policy host tile).hints)
         |> List.map ~f:(fun row -> row.Simulation_view.text)
         |> List.concat_map ~f:(wrap_cells ~width)
       | "execution" | "project-tests" ->
         (if H.compact_summary host tile
          then
            [ (if String.equal tile.kind "project-tests"
               then "Generic project tests"
               else "Execution attempts")
            ; "Process results only"
            ; "b build | t test"
            ]
          else
            [ (if String.equal tile.kind "project-tests"
               then "Project tests (not ASIC-run scoped)"
               else "Project execution attempts")
            ; "Environment: " ^ data.environment
            ; "Case details / progress: unavailable (generic command runner)"
            ])
         @ Option.value_map selected ~default:[] ~f:(fun job ->
           Presentation.job_outcome_lines job
           @
           if String.equal tile.kind "project-tests"
           then "ATTEMPT OUTPUT" :: List.take (data.log_lines job.id) 4
           else [])
         @ job_rows
       | "logs" ->
         [ "Project job output: "
           ^ Option.value local.cursor ~default:"select attempt with j/k"
         ; (if local.follow then "FOLLOW" else "PAUSED — palette: Resume log follow")
         ]
         @ Option.value_map selected ~default:[ "No attempt selected" ] ~f:(fun job ->
           data.log_lines job.id)
       | "project" ->
         Option.value_map data.project ~default:[ "No project open" ] ~f:(fun project ->
           [ project.name
           ; Project_root.to_absolute_path project.root
           ; "Environment: " ^ data.environment
           ])
       | "navigation" ->
         [ "Space c c: searchable commands"
         ; "Tab / Shift-Tab: next / previous tile"
         ; "1-9: workspaces; j/k browse; Enter select"
         ; "[ / ]: scroll; palette: resume log follow"
         ; "Timing/checks/physical/finalization: Enter/e evidence; Esc overview"
         ; "Palette: add/hide/restore/move/resize/zoom; unlink/relink; pin/follow"
         ; data.status
         ]
       | "asic" -> List.concat_map data.asic_lines ~f:(wrap_cells ~width)
       | "synthesis" ->
         (match scope with
          | None -> [ "No run selected — use a run selector" ]
          | Some run ->
            ignore (run : Run_ref.t);
            semantic_rows host data tile ~width ~height
            |> Option.value ~default:[]
            |> List.map ~f:E.text)
       | kind when Terminal_result_view.supports kind ->
         (match scope with
          | None -> [ "No run selected — use a run selector" ]
          | Some run ->
            ignore (run : Run_ref.t);
            semantic_rows host data tile ~width ~height
            |> Option.value ~default:[]
            |> List.map ~f:E.text)
       | kind ->
         (match scope with
          | None -> [ "No run selected — use a run selector" ]
          | Some run -> ("Run: " ^ run_label run) :: data.run_lines run kind))
  in
  if Option.is_some local.artifacts
     || Option.is_some local.inspection
     || String.equal tile.kind "synthesis"
     || Terminal_result_view.supports tile.kind
     || Option.is_some (Timing_workspace.pane tile.kind)
     || (String.equal tile.kind "logs" && local.follow)
  then rows
  else if String.equal tile.kind "run-selector"
  then rows
  else if H.simulation_kind tile.kind
  then List.drop rows (Int.min local.scroll (Int.max 0 (List.length rows - height)))
  else List.drop rows local.scroll
;;

let panel_geometry host tile ~width ~height =
  let policy = H.policy host tile in
  let appearance = host.H.appearance in
  Panel.geometry
    ~framed:(policy.frame && framed appearance ~width ~height)
    ~width
    ~height
    ~horizontal_padding:policy.padding
    ~vertical_padding:0
;;

let body_geometry host tile ~width ~height =
  let policy = H.policy host tile in
  let g = panel_geometry host tile ~width ~height in
  let body_height =
    Int.max
      0
      (g.content_height
       - (if g.border = 0
             && (T.show_title policy || T.show_badge policy (H.binding_kind tile))
          then 1
          else 0)
       - if policy.run_reference then 1 else 0)
  in
  g.inner_width, g.inner_height, g.horizontal_padding, g.content_width, body_height
;;

let timing_status_role (row : Asic_inspection.Row.t) =
  match String.lowercase row.status with
  | "violated" | "fail" | "failed" -> Role.Failure
  | "met" | "ok" | "pass" | "passed" -> Success
  | "pending" | "unknown" | "unavailable" -> Warning
  | _ -> Foreground
;;

(* C owns prefix content and width budgeting. Apply the same final sanitation/wrapping as
   [Timing_workspace.rows], carrying only its explicit roles across wrapped lines. *)
let timing_line_role : Timing_workspace.line_role -> Role.t = function
  | Selected -> Selection
  | Metric -> Metric
  | Metadata -> Muted
  | Pending -> Warning
  | Failure -> Failure
;;

let timing_semantic_prefix ~pane ~width view =
  Timing_workspace.semantic_prefix ~pane ~width view
  |> List.concat_map ~f:(fun (role, line) ->
    Artifact_view.wrap ~width (Artifact_view.safe line)
    |> List.map ~f:(fun line -> timing_line_role role, line))
;;

(* Use typed fields and selection, never keywords found in producer report text. Paths
   retains C's four-row viewport budget; tiny panes give selection priority. *)
let timing_body appearance ~pane ~scroll ~width ~height (view : Timing_workspace.t) =
  let source = Timing_workspace.rows ~pane ~scroll ~width ~height view in
  let text role value =
    View.text ~attrs:(Role.attrs appearance role) (Artifact_view.safe value)
  in
  match pane with
  | Timing_workspace.Paths ->
    let visible = Inspection_view.visible view in
    let position =
      List.findi visible ~f:(fun _ row ->
        Option.equal String.equal view.selected (Some row.Asic_inspection.Row.id))
      |> Option.value_map ~default:0 ~f:fst
    in
    let capacity = Int.max 1 (height - 4) in
    let page =
      List.drop visible (position / capacity * capacity) |> Fn.flip List.take capacity
    in
    let all = Option.value ~default:"ALL" in
    let sort =
      match view.sort with
      | Numeric_ascending -> "value ↑"
      | Numeric_descending -> "value ↓"
      | Name -> "name"
    in
    let count =
      sprintf
        "%d paths · %s%s"
        (List.length visible)
        sort
        (if view.near then " · ≤1ns" else "")
    in
    let observation, observation_role =
      match view.index with
      | None -> "Explicit Inspect / refresh required", Role.Warning
      | Some i ->
        ( ((if i.cached_unverified then "Cached unverified" else "Verified observation")
           ^ if i.truncated then " · TRUNCATED" else "")
        , if i.cached_unverified || i.truncated then Role.Warning else Muted )
    in
    let header =
      [ text
          (if view.pasting then Warning else Focus)
          (if view.editing || view.pasting
           then (if view.pasting then "Paste filter: " else "/ ") ^ view.filter ^ "|"
           else "Filter: " ^ if String.is_empty view.filter then "ALL" else view.filter)
      ; text
          (if Option.is_some view.filter_notice then Warning else Muted)
          (Option.value
             view.filter_notice
             ~default:
               (sprintf
                  "Corner %s · Group %s · Producer %s"
                  (all view.corner)
                  (all view.group)
                  (all view.producer)))
      ; View.hcat [ text Metric (count ^ " · "); text observation_role observation ]
      ; text Muted "Path / endpoint                         Value · reported status"
      ]
    in
    let header = List.take header (Int.max 0 (height - 1) |> Int.min 4) in
    let path row =
      let selected =
        Option.equal String.equal view.selected (Some row.Asic_inspection.Row.id)
      in
      let numeric =
        Option.value_map row.value ~default:"—" ~f:(fun value ->
          if Float.is_finite value then sprintf "%.6g" value else "invalid")
        ^ Option.value_map row.unit_ ~default:"" ~f:(fun unit_ -> " " ^ unit_)
      in
      let suffix = numeric ^ " · " ^ row.status in
      let suffix_width = Int.min (Int.max 0 (width / 2)) (cell_width suffix) in
      let name_width = Int.max 0 (width - suffix_width - 3) in
      let endpoint key = List.Assoc.find row.fields key ~equal:String.equal in
      let label =
        match endpoint "startpoint", endpoint "endpoint" with
        | Some start, Some finish -> start ^ " → " ^ finish ^ " · " ^ row.name
        | _, Some finish -> row.name ^ " · endpoint=" ^ finish
        | Some start, _ -> row.name ^ " · startpoint=" ^ start
        | _ -> row.name
      in
      let name = fit_label ~width:name_width (Artifact_view.safe label) in
      View.hcat
        [ text (if selected then Selection else Muted) (if selected then "> " else "  ")
        ; text
            (if selected then Selection else Foreground)
            (name ^ String.make (Int.max 0 (name_width - cell_width name)) ' ' ^ " ")
        ; text (timing_status_role row) (fit_label ~width:suffix_width suffix)
        ]
    in
    let body =
      if List.is_empty page
      then
        [ text
            Warning
            (if Option.is_none view.index
             then observation
             else "No paths match the current filters")
        ]
      else List.map page ~f:path
    in
    let error = Option.first_some view.error view.pending_error in
    let header =
      match error, header with
      | Some error, _ :: rest -> text Failure error :: rest
      | _ -> header
    in
    View.vcat (header @ body) |> box ~width ~height |> colored appearance Foreground
  | Detail | Context ->
    (* Scroll offsets are those of C's actual wrapped output. Only the canonical semantic
       prefix receives role styling; provider payload is always neutral. *)
    let full = Timing_workspace.rows ~pane ~scroll:0 ~width ~height:Int.max_value view in
    let start = Int.min scroll (Int.max 0 (List.length full - height)) in
    let prefix = timing_semantic_prefix ~pane ~width view |> Array.of_list in
    List.mapi source ~f:(fun i line ->
      let offset = start + i in
      if offset < Array.length prefix && String.equal (snd prefix.(offset)) line
      then text (fst prefix.(offset)) line
      else text Foreground line)
    |> View.vcat
    |> box ~width ~height
    |> colored appearance Foreground
;;

let tile_view ?indicator_frames host data tile ~width ~height =
  let appearance = host.H.appearance in
  let local = H.local host tile.W.Tile.id in
  let indicator_frames =
    if List.mem [ "stage-checklist"; "synthesis" ] tile.kind ~equal:String.equal
       && not (Option.exists (tile_run host tile) ~f:(run_has_producer data))
    then None
    else indicator_frames
  in
  let policy = H.policy host tile in
  let show_title = T.show_title policy in
  let show_badge = T.show_badge policy (H.binding_kind tile) in
  let focused =
    Option.value_map host.H.focus ~default:false ~f:(W.Tile_id.equal tile.id)
  in
  let binding =
    if Testing_workspace.is_pane tile.kind
    then "project"
    else (
      match tile.binding with
      | Pin_run run ->
        let glyph = Indicator.text appearance.icons Pin in
        (if String.is_empty glyph then "" else glyph ^ " ") ^ "PIN " ^ run_label run
      | Follow -> if H.project_scoped_kind tile.kind then "project" else "follow")
  in
  let _, _, _, body_width, body_height = body_geometry host tile ~width ~height in
  let geometry = panel_geometry host tile ~width ~height in
  let compact = compact_rows host data tile in
  let semantic =
    if Option.is_some compact
    then None
    else semantic_rows host data tile ~width:body_width ~height:body_height
  in
  let rows =
    match compact, semantic with
    | Some rows, _ ->
      List.map rows ~f:(fun row -> row.Overview_tiles.label ^ ": " ^ row.value)
    | None, Some rows -> List.map rows ~f:E.text
    | None, None -> rows host data tile ~width:body_width ~height:body_height
  in
  let rows =
    if String.equal tile.kind "logs" && local.follow
    then
      List.take rows 2
      @ (List.drop rows 2
         |> List.rev
         |> Fn.flip List.take (Int.max 0 (body_height - 2))
         |> List.rev)
    else rows
  in
  let header =
    if show_title || show_badge
    then (
      let title =
        if Terminal_result_view.supports tile.kind && local.terminal_result.detail
        then tile.kind ^ "/evidence"
        else if not (String.equal tile.kind "synthesis")
        then (
          match tile.kind with
          | "live-status" -> "session"
          | "workspace-tabs" -> "workspaces"
          | "stage-checklist" -> "stage checklist"
          | "timing-paths" -> "timing · paths"
          | "timing-detail" -> "timing · selected path"
          | "timing-context" -> "timing · provenance"
          | "run-selector" ->
            let total =
              List.count data.runs ~f:(fun (run, status) ->
                String.is_substring
                  (String.lowercase (run_label run ^ " " ^ status))
                  ~substring:(String.lowercase local.filter))
            in
            sprintf
              "runs %d/%d (cap %d)"
              (Int.min total (Int.min body_height policy.run_selector_rows))
              total
              policy.run_selector_rows
          | kind -> kind)
        else (
          match Synthesis_view.State.mode local.synthesis with
          | Summary -> "synthesis"
          | Cells -> "synthesis/cells"
          | Details -> "synthesis/detail"
          | Metrics -> "synthesis/metrics"
          | Evidence -> "synthesis/evidence")
      in
      (* Host-generated titles stay lowercase; binding badges retain exact run IDs. Focus
         belongs to border styling, never a decorative title prefix. *)
      let title =
        if not show_title
        then ""
        else if studio appearance
        then "[ " ^ title ^ " ]"
        else title
      in
      let room =
        if geometry.border > 0 then Int.max 0 (geometry.inner_width - 2) else body_width
      in
      let badge =
        if not show_badge then "" else if show_title then "[" ^ binding ^ "]" else binding
      in
      let badge = fit_label ~width:room badge in
      let title =
        fit_label
          ~width:
            (Int.max 0 (room - cell_width badge - if String.is_empty badge then 0 else 1))
          title
      in
      let heading =
        title
        ^ (if String.is_empty title || String.is_empty badge then "" else " ")
        ^ badge
      in
      let filter =
        if String.is_empty local.filter then "" else " filter=" ^ local.filter
      in
      let heading =
        heading
        ^ E.text (E.clip ~width:(Int.max 0 (room - cell_width heading)) (E.plain filter))
      in
      [ View.text ~attrs:(Role.attrs appearance Heading) heading ])
    else []
  in
  let border_title = if geometry.border > 0 then View.vcat header else View.none in
  let header =
    (if geometry.border > 0 then [] else header)
    @
    if policy.run_reference
    then
      [ lines
          ~appearance
          ~role:Muted
          ~width:body_width
          ~height:1
          [ "Run: "
            ^ Option.value_map (tile_run host tile) ~default:"none selected" ~f:run_label
          ]
      ]
    else []
  in
  let body =
    List.take rows body_height
    |> List.map ~f:(fun row ->
      let role = if focused && not show_title then Role.Focus else Role.Foreground in
      lines ~appearance ~role ~width:body_width ~height:1 [ row ])
    |> View.vcat
    |> box ~width:body_width ~height:body_height
  in
  let body =
    match compact with
    | Some rows ->
      Overview_tiles.render
        ?indicator_frames
        ~indicator_fg:(Role.foreground appearance Running)
        ~selected_bg:(Role.backdrop appearance Selection)
        ~appearance
        ~attrs:(utility_attrs appearance)
        ~width:body_width
        ~height:body_height
        rows
    | None ->
      (match utility_rows host data tile with
       | None ->
         (match semantic with
          | None
            when String.equal tile.kind "run-selector"
                 && Option.is_none local.inspection
                 && Option.is_none local.artifacts ->
            let candidates =
              List.filter data.runs ~f:(fun (run, status) ->
                String.is_substring
                  (String.lowercase (run_label run ^ " " ^ status))
                  ~substring:(String.lowercase local.filter))
            in
            let status_width =
              Int.min
                (Int.max 0 (body_width / 3))
                (List.fold candidates ~init:0 ~f:(fun n (_, status) ->
                   Int.max n (cell_width status)))
            in
            (* [rows] already applies the selector's cursor paging. Resolve each row
               against the same typed candidate and keep status styling out of IDs. *)
            let selected =
              Option.first_some
                local.cursor
                (Option.map (tile_run host tile) ~f:run_label)
            in
            let selected_index =
              List.findi candidates ~f:(fun _ (run, _) ->
                Option.equal String.equal selected (Some (run_label run)))
              |> Option.value_map ~default:0 ~f:fst
            in
            let available = Int.min body_height policy.run_selector_rows in
            let start =
              Int.clamp_exn
                local.scroll
                ~min:(Int.max 0 (selected_index - Int.max 1 available + 1))
                ~max:selected_index
            in
            List.drop candidates start
            |> Fn.flip List.take (Int.max 0 available)
            |> List.map ~f:(fun (run, status) ->
              run_selector_view
                ?indicator_frames:
                  (if run_has_producer data run then indicator_frames else None)
                appearance
                ~width:body_width
                ~status_width
                ~cursor:(Option.equal String.equal selected (Some (run_label run)))
                ~active:(Option.equal Run_ref.equal (tile_run host tile) (Some run))
                run
                status)
            |> View.vcat
            |> box ~width:body_width ~height:body_height
          | None -> body
          | Some rows ->
            E.render ~attrs:(evidence_attrs appearance) rows
            |> box ~width:body_width ~height:body_height
            |> colored appearance Foreground)
       | Some rows when local.utility_detail ->
         Overview_tiles.inspection_lines rows
         |> List.concat_map ~f:(wrap_cells ~width:body_width)
         |> Fn.flip List.drop local.scroll
         |> lines ~appearance ~width:body_width ~height:body_height
       | Some rows
         when String.equal tile.kind "stage-checklist"
              && H.horizontal_stages host tile
              && Option.is_some (tile_run host tile) ->
         let run = Option.value_exn (tile_run host tile) in
         let stages = Overview_tiles.observed_stages ~asic:data.asic ~run in
         if List.is_empty stages
         then
           Overview_tiles.render
             ?indicator_frames
             ~indicator_fg:(Role.foreground appearance Running)
             ~selected_bg:(Role.backdrop appearance Selection)
             ~appearance
             ~attrs:(utility_attrs appearance)
             ~width:body_width
             ~height:body_height
             rows
         else (
           let selected_id =
             H.stage_cursor local ~run ~stages
             |> Option.map ~f:(fun stage -> stage.Asic.Stage.id)
           in
           let model =
             Overview_tiles.Stage_strip.model
               ~appearance
               ~width:body_width
               ~run
               ~selected_id
               stages
           in
           let model =
             match model.selected with
             | None -> model
             | Some item ->
               let selected = model.selected_line in
               let overhead =
                 cell_width (Overview_tiles.marker appearance selected)
                 + (if selected.active then 2 else 0)
                 + (match appearance.density with
                   | Comfortable when body_width >= 30 -> 1
                   | _ -> 0)
                 + cell_width ("Selected: " ^ ": " ^ selected.value)
               in
               { model with
                 selected_line =
                   { selected with
                     label =
                       "Selected: "
                       ^ fit_label
                           ~width:(Int.max 0 (body_width - overhead))
                           item.stage.id
                   }
               }
           in
           let hints = checklist_hints host data tile in
           let hint_height = Int.min (List.length hints) (Int.max 0 (body_height - 2)) in
           let strip =
             Overview_tiles.Stage_strip.render
               ?indicator_frames
               ~indicator_fg:(Role.foreground appearance Running)
               ~selected_bg:(Role.backdrop appearance Selection)
               ~appearance
               ~attrs:(utility_attrs appearance)
               ~width:body_width
               ~height:(body_height - hint_height)
               model
           in
           View.vcat
             [ strip
             ; lines ~appearance ~role:Muted ~width:body_width ~height:hint_height hints
             ]
           |> box ~width:body_width ~height:body_height)
       | Some rows when String.equal tile.kind "stage-checklist" ->
         let hints = checklist_hints host data tile in
         (* Short Overview tiles must spend their scarce rows on stage evidence. At least
            one row remains even at the smallest viewport; roomier tiles retain three
            evidence rows before spending space on additional hints. *)
         let evidence_height = Int.min 3 (Int.max 1 (body_height - 1)) in
         let hint_height =
           Int.min (List.length hints) (Int.max 0 (body_height - evidence_height))
         in
         let available = Int.max 0 (body_height - hint_height) in
         let selected_index =
           List.findi rows ~f:(fun _ row -> row.Overview_tiles.active)
           |> Option.value_map ~default:0 ~f:fst
         in
         let start =
           Int.clamp_exn
             local.scroll
             ~min:(Int.max 0 (selected_index - Int.max 1 available + 1))
             ~max:selected_index
         in
         View.vcat
           [ lines ~appearance ~role:Muted ~width:body_width ~height:hint_height hints
           ; Overview_tiles.render
               ?indicator_frames
               ~indicator_fg:(Role.foreground appearance Running)
               ~selected_bg:(Role.backdrop appearance Selection)
               ~appearance
               ~attrs:(utility_attrs appearance)
               ~width:body_width
               ~height:available
               (List.drop rows start)
           ]
         |> box ~width:body_width ~height:body_height
       | Some rows when String.equal tile.kind "workspace-tabs" ->
         let tabs =
           List.mapi rows ~f:(fun i row ->
             let i =
               Option.bind host.registry ~f:(fun registry ->
                 List.findi registry.workspaces ~f:(fun _ w ->
                   Option.equal
                     W.Workspace_id.equal
                     row.Overview_tiles.workspace
                     (Some w.id)))
               |> Option.value_map ~default:i ~f:fst
             in
             let role =
               if row.Overview_tiles.active
               then Role.Active_tab
               else if Overview_tiles.Role.equal row.role Active
               then Selection
               else Inactive_tab
             in
             View.text
               ~attrs:(Role.attrs appearance role)
               (sprintf
                  " %s%d %s%s "
                  (if row.active then "[" else " ")
                  (i + 1)
                  row.label
                  (if row.active then "]" else " ")))
         in
         let tabline = View.hcat tabs in
         let navigation =
           if View.width tabline <= body_width
           then tabline
           else
             Overview_tiles.render
               ?indicator_frames
               ~indicator_fg:(Role.foreground appearance Running)
               ~selected_bg:(Role.backdrop appearance Selection)
               ~appearance
               ~attrs:(utility_attrs appearance)
               ~width:body_width
               ~height:(Int.max 1 (body_height - 1))
               (let index =
                  List.findi rows ~f:(fun _ row ->
                    Option.equal
                      W.Workspace_id.equal
                      row.Overview_tiles.workspace
                      (Option.map (H.workspace_cursor host tile.id) ~f:(fun w -> w.id)))
                  |> Option.value_map ~default:0 ~f:fst
                in
                List.drop rows (Int.max 0 (index - body_height + 2)))
         in
         View.vcat
           [ navigation
           ; (if not policy.hints
              then View.none
              else
                lines
                  ~appearance
                  ~role:Muted
                  ~width:body_width
                  ~height:1
                  [ "j/k browse | Enter open | 1-9 jump" ])
           ]
         |> box ~width:body_width ~height:body_height
       | Some rows ->
         Overview_tiles.render
           ?indicator_frames
           ~indicator_fg:(Role.foreground appearance Running)
           ~selected_bg:(Role.backdrop appearance Selection)
           ~appearance
           ~attrs:(utility_attrs appearance)
           ~width:body_width
           ~height:body_height
           (List.drop rows local.scroll))
  in
  let body =
    if String.equal tile.kind "planned-run"
    then
      planned_view_rows ?indicator_frames host tile ~width:body_width
      |> Fn.flip List.drop local.scroll
      |> Fn.flip List.take body_height
      |> View.vcat
      |> box ~width:body_width ~height:body_height
      |> colored appearance Foreground
    else if Option.is_some local.inspection || Option.is_some local.artifacts
    then body
    else if H.simulation_kind tile.kind
    then (
      let views =
        simulation_view_rows_with_selection
          ?indicator_frames
          host
          data
          tile
          ~width:body_width
      in
      List.drop views (simulation_viewport_start host tile ~height:body_height views)
      |> Fn.flip List.take body_height
      |> List.map ~f:snd
      |> View.vcat
      |> box ~width:body_width ~height:body_height)
    else if List.mem [ "execution"; "project-tests" ] tile.kind ~equal:String.equal
    then (
      let jobs =
        List.filter data.jobs ~f:(fun job ->
          (not (String.equal tile.kind "project-tests"))
          || (String.equal job.kind.namespace "dune" && String.equal job.kind.name "test"))
      in
      List.mapi rows ~f:(fun i text ->
        let index = i - (List.length rows - List.length jobs) in
        match if index < 0 then None else List.nth jobs index with
        | None -> lines ~appearance ~width:body_width ~height:1 [ text ]
        | Some job ->
          let kind = job_indicator job.state in
          let role = indicator_role kind in
          View.hcat
            [ View.text
                ~attrs:(Role.attrs appearance Foreground)
                ((if Option.equal
                       String.equal
                       local.cursor
                       (Some (Job_id.to_string job.id))
                  then ">"
                  else " ")
                 ^ " "
                 ^ Job_id.to_string job.id
                 ^ "  ")
            ; indicator_view ?indicator_frames appearance role kind
            ; View.text
                ~attrs:(Role.attrs appearance role)
                (Job.State.to_string job.state)
            ; View.text
                ~attrs:(Role.attrs appearance Foreground)
                ("  " ^ Job.Kind.to_string job.kind)
            ]
          |> box ~width:body_width ~height:1)
      |> Fn.flip List.take body_height
      |> View.vcat
      |> box ~width:body_width ~height:body_height)
    else (
      match Timing_workspace.pane tile.kind, H.timing host tile with
      | Some pane, Some view ->
        timing_body
          appearance
          ~pane
          ~scroll:local.scroll
          ~width:body_width
          ~height:body_height
          view
      | _ -> body)
  in
  let content = View.vcat (header @ [ body ]) in
  Panel.render
    appearance
    ~attrs:(Role.attrs appearance (if focused then Focus else Border))
    ~title:border_title
    ~geometry
    ~width
    ~height
    content
  |> colored appearance Foreground
  |> box ~width ~height
;;

module Fit_layout = struct
  type t =
    | Grid of W.Geometry.t list
    | Compact

  (* Gaps are terminal cells. Remainders go to the leading tracks so every available cell
     belongs to a track or a gap, including an incomplete last row. *)
  let tracks total count =
    let usable = total - (count - 1) in
    List.init count ~f:(fun i ->
      let size = (usable / count) + if i < usable % count then 1 else 0 in
      let offset = (i * ((usable / count) + 1)) + Int.min i (usable % count) in
      offset, size)
  ;;

  let compute ~width ~height ~count =
    if count <= 0
    then Grid []
    else (
      let columns = Int.min count (Int.min 4 (Int.max 1 ((width + 1) / 40))) in
      let rows = (count + columns - 1) / columns in
      if width - columns + 1 < columns * 24 || height - rows + 1 < rows * 6
      then Compact
      else (
        let xs = tracks width columns in
        let ys = tracks height rows in
        Grid
          (List.init count ~f:(fun i ->
             let x, width = List.nth_exn xs (i % columns) in
             let y, height = List.nth_exn ys (i / columns) in
             { W.Geometry.x; y; width; height }))))
  ;;
end

let show_global_header host =
  host.H.chrome
  && not
       (List.exists (H.tiles host) ~f:(fun tile ->
          String.equal tile.W.Tile.kind "live-status"))
;;

(** The same outer and inner geometry is used by rendering and page navigation. *)
let tile_layout host ({ Dimensions.width; height } : Dimensions.t) =
  let width = Int.max 1 width
  and height = Int.max 1 height in
  let available =
    Int.max
      1
      (height
       - (if show_global_header host then 1 else 0)
       - if host.chrome || host.editing_filter || host.paste then 1 else 0)
  in
  let tiles = H.tiles host in
  let zoomed =
    Option.value_map (H.active host) ~default:false ~f:(fun w ->
      Option.is_some w.zoomed_tile)
  in
  let definition = Option.bind (H.active host) ~f:H.definition in
  let layout_mode = host.layout_mode in
  let fit =
    match definition with
    | Some definition ->
      let kinds = List.map tiles ~f:(fun tile -> tile.W.Tile.kind) in
      let tree = P.Layout.resolve definition.layout kinds in
      let spare =
        Option.value_map tree ~default:0 ~f:(fun tree ->
          Int.max 0 (available - snd (P.Layout.min_size tree)))
      in
      let selector_count =
        Int.max 1 (List.count kinds ~f:(String.equal "run-selector"))
      in
      let rec minimum i = function
        | P.Layout.Cell (index, _, height, _) -> if i = index then height else 0
        | Narrow tree -> minimum i tree
        | Weighted_columns children ->
          List.fold children ~init:0 ~f:(fun height (_, tree) ->
            Int.max height (minimum i tree))
        | Stack children | Columns children ->
          List.fold children ~init:0 ~f:(fun height tree ->
            Int.max height (minimum i tree))
      in
      (match
         P.Layout.compute
           ~min_height_for_index:(fun i ->
             Option.bind (List.nth tiles i) ~f:(fun tile ->
               if not (String.equal tile.W.Tile.kind "run-selector")
               then None
               else (
                 let policy = H.policy host tile in
                 let frame =
                   policy.frame && framed host.appearance ~width ~height:available
                 in
                 let requested =
                   Int.min available policy.run_selector_rows
                   + (if frame
                      then 2
                      else if T.show_title policy
                              || T.show_badge policy (H.binding_kind tile)
                      then 1
                      else 0)
                   + if policy.run_reference then 1 else 0
                 in
                 let budget =
                   Option.value_map tree ~default:available ~f:(fun tree ->
                     minimum i tree + (spare / selector_count))
                 in
                 Some (Int.min requested budget))))
           definition
           ~width
           ~height:available
           ~kinds:(List.map tiles ~f:(fun tile -> tile.W.Tile.kind))
       with
       | Grid cells -> Fit_layout.Grid cells
       | Compact -> Fit_layout.Compact)
    | None -> Fit_layout.compute ~width ~height:available ~count:(List.length tiles)
  in
  let compact =
    (not zoomed)
    &&
    match layout_mode, fit with
    | H.Fit, Fit_layout.Compact -> true
    | _ -> false
  in
  let focused () =
    let tile =
      Option.filter (H.focused host) ~f:(fun tile ->
        List.exists tiles ~f:(fun t -> W.Tile_id.equal t.id tile.id))
      |> fun focused -> Option.first_some focused (List.hd tiles)
    in
    Option.to_list tile
    |> List.map ~f:(fun tile ->
      tile, { W.Geometry.x = 0; y = 0; width; height = available })
  in
  let layout =
    if zoomed || compact
    then focused ()
    else (
      match layout_mode, fit with
      | H.Fit, Fit_layout.Grid cells -> List.zip_exn tiles cells
      | H.Fit, Fit_layout.Compact -> focused ()
      | H.Preferred, _ ->
        let rec pack pending x y row_height acc =
          match pending with
          | [] -> List.rev acc, y + row_height
          | tile :: rest ->
            let g = tile.W.Tile.requested_geometry in
            let tw = Int.min width (Int.max 8 g.width) in
            let th = Int.min available (Int.max 3 g.height) in
            let gap = if x = 0 then 0 else 1 in
            if x + gap + tw > width && x > 0
            then pack pending 0 (y + row_height) 0 acc
            else
              pack
                rest
                (x + gap + tw)
                y
                (Int.max row_height th)
                ((tile, { W.Geometry.x = x + gap; y; width = tw; height = th }) :: acc)
        in
        let packed, total_height = pack tiles 0 0 0 [] in
        if total_height > available && Option.is_some (H.focused host)
        then focused ()
        else packed)
  in
  available, compact, layout
;;

let reconcile_simulation_viewports host data dimensions =
  let _, _, layout = tile_layout host dimensions in
  List.fold layout ~init:host ~f:(fun host (tile, g) ->
    if not (simulation_cursor_pane tile.W.Tile.kind)
    then host
    else (
      let _, _, _, width, height =
        body_geometry host tile ~width:g.W.Geometry.width ~height:g.height
      in
      let rows = simulation_view_rows_with_selection host data tile ~width in
      let local = H.local host tile.id in
      let scroll = simulation_viewport_start host tile ~height rows in
      if scroll = local.scroll
      then host
      else H.set_local host tile.id { local with scroll }))
;;

let scroll_run_focused host data dimensions ~delta =
  let _, _, layout = tile_layout host dimensions in
  match H.focused host, host.H.registry with
  | Some tile, Some registry ->
    (match
       ( List.find layout ~f:(fun (visible, _) -> W.Tile_id.equal visible.id tile.id)
       , W.resolve_tile registry tile.id
         |> Result.ok
         |> Option.bind ~f:(fun reference -> reference.run) )
     with
     | Some (_, g), _ when H.simulation_kind tile.kind ->
       let _, _, _, width, height =
         body_geometry host tile ~width:g.width ~height:g.height
       in
       let local = H.local host tile.id in
       let full = simulation_view_rows_with_selection host data tile ~width in
       let maximum = Int.max 0 (List.length full - height) in
       let scroll = simulation_viewport_start host tile ~height full in
       let scroll =
         if delta >= 0
         then scroll + Int.min delta (maximum - scroll)
         else
           scroll
           - Int.min scroll (if delta = Int.min_value then Int.max_value else -delta)
       in
       H.set_local
         host
         tile.id
         { local with
           scroll
         ; follow = (if simulation_cursor_pane tile.kind then false else local.follow)
         }
     | Some (_, g), Some run ->
       let _, _, _, width, height =
         body_geometry host tile ~width:g.width ~height:g.height
       in
       let local = H.local host tile.id in
       let local =
         if String.equal tile.kind "synthesis"
            && Synthesis_view.Mode.equal
                 (Synthesis_view.State.mode local.synthesis)
                 Metrics
         then (
           let count =
             synthesis_metrics_content host data tile ~run
             |> List.concat_map ~f:(E.wrap ~width)
             |> List.length
           in
           let maximum = Int.max 0 (count - height) in
           let current = metrics_offset local data run in
           let scroll =
             Int64.(
               max
                 zero
                 (min (of_int maximum) (of_int (Int.min current maximum) + of_int delta)))
             |> Int64.to_int_exn
           in
           { local with scroll; metrics_scope = metrics_scope data run })
         else if String.equal tile.kind "synthesis"
         then
           { local with
             synthesis =
               Synthesis_view.scroll
                 local.synthesis
                 ~summary:(data.summary run)
                 ~filter:local.filter
                 ~width
                 ~height
                 ~delta
           }
         else if Terminal_result_view.supports tile.kind
         then (
           let count =
             terminal_content host data tile ~run
             |> List.concat_map ~f:(E.wrap ~width)
             |> List.length
           in
           { local with
             terminal_result =
               Terminal_result_view.State.scroll
                 (Terminal_result_view.State.reconcile
                    local.terminal_result
                    ~run
                    ~summary:(data.summary run))
                 ~delta
                 ~max_offset:(Int.max 0 (count - height))
           })
         else local
       in
       H.set_local host tile.id local
     | _ -> host)
  | _ -> host
;;

let scroll_focused host data dimensions ~delta =
  match H.focused host with
  | Some tile
    when List.mem [ "live-status"; "stage-checklist" ] tile.kind ~equal:String.equal ->
    let _, _, layout = tile_layout host dimensions in
    (match
       ( List.find layout ~f:(fun (t, _) -> W.Tile_id.equal t.id tile.id)
       , utility_rows host data tile )
     with
     | Some (_, g), Some rows ->
       let _, _, _, width, height =
         body_geometry host tile ~width:g.width ~height:g.height
       in
       let local = H.local host tile.id in
       let count =
         if local.utility_detail
         then
           Overview_tiles.inspection_lines rows
           |> List.concat_map ~f:(wrap_cells ~width)
           |> List.length
         else List.length rows
       in
       let bound = Int.max 0 (count - height) in
       let current = Int.min local.scroll bound in
       let scroll =
         Int64.(max zero (min (of_int bound) (of_int current + of_int delta)))
         |> Int64.to_int_exn
       in
       H.set_local host tile.id { local with scroll }
     | _ -> host)
  | _ -> scroll_run_focused host data dimensions ~delta
;;

(** Fit uses responsive tracks; Preferred preserves saved shelf dimensions. *)
let inspection_viewport (dimensions : Dimensions.t) =
  Int.max 1 dimensions.width, Int.max 1 dimensions.height
;;

let render_workspace
  ?indicator_frames
  host
  data
  ({ Dimensions.width; height } as dimensions)
  =
  let appearance = host.H.appearance in
  let width = Int.max 1 width
  and height = Int.max 1 height in
  let header =
    if not (show_global_header host)
    then []
    else
      [ lines
          ~appearance
          ~role:Active_tab
          ~width
          ~height:1
          [ (match host.registry, H.active host with
             | Some s, Some w ->
               let c = W.context s w.context in
               sprintf
                 "%s | run %s | %s: %s | %s | %s"
                 w.name
                 (Option.value_map c.selected_run ~default:"none" ~f:display_run)
                 (if W.Context_id.equal c.id s.main_context
                  then "Linked"
                  else "Independent")
                 c.name
                 (Option.value_map data.project ~default:"Workbench" ~f:(fun p -> p.name))
                 data.status
             | _ -> "Workbench | " ^ host.notice)
          ]
      ]
  in
  let available, compact, layout = tile_layout host dimensions in
  let content =
    if Option.is_none host.registry
    then lines ~appearance ~width ~height:available [ "Loading workspace..." ]
    else if List.is_empty layout
    then
      lines
        ~appearance
        ~width
        ~height:available
        [ "No visible tiles in this workspace."
        ; "Space c c: Apply default layout to recover"
        ]
    else
      List.map layout ~f:(fun (tile, (g : W.Geometry.t)) ->
        tile_view ?indicator_frames host data tile ~width:g.width ~height:g.height
        |> View.pad ~l:g.x ~t:g.y)
      |> View.zcat
  in
  let footer =
    if host.paste
    then
      [ lines
          ~appearance
          ~role:Warning
          ~width
          ~height:1
          [ (if H.finalization_form host
             then
               "FINALIZATION PASTE | printable path captured; Enter after paste imports \
                | Ctrl-C exits"
             else "PASTE CAPTURE | content ignored until end marker | Ctrl-C exits client")
          ]
      ]
    else if host.editing_filter
    then (
      let filter =
        Option.value_map host.focus ~default:"" ~f:(fun id -> (H.local host id).filter)
      in
      [ lines
          ~appearance
          ~role:Focus
          ~width
          ~height:1
          [ "FILTER INPUT | Enter/Esc finish | Ctrl-U clear | query: " ^ filter ]
      ])
    else if not host.chrome
    then []
    else
      [ lines
          ~appearance
          ~role:Muted
          ~width
          ~height:1
          [ (if not (String.is_empty host.notice)
             then host.notice
             else if compact
             then
               "Compact: focused tile only | Tab: next tile | enlarge terminal for grid"
             else
               "Space c c commands | Tab/Shift-Tab focus | j/k browse | Enter inspect | \
                q exit")
          ]
      ]
  in
  let frame =
    View.vcat (header @ [ box ~width ~height:available content ] @ footer)
    |> box ~width ~height
    |> colored appearance Background
  in
  match Option.bind (H.focused host) ~f:(artifact_inspector host) with
  | None -> frame
  | Some view ->
    lines
      ~appearance
      ~role:Surface
      ~width
      ~height
      (Artifact_view.rows view ~width ~height)
    |> colored appearance Surface
    |> box ~width:dimensions.width ~height:dimensions.height
;;

let render_palette host dimensions background =
  match host.H.palette with
  | None -> background
  | Some p ->
    let appearance = host.appearance in
    let bounds =
      Palette_view.bounds ~width:dimensions.Dimensions.width ~height:dimensions.height
    in
    let geometry =
      Panel.geometry
        ~framed:(bounds.height >= 6 && bounds.width >= 6)
        ~width:bounds.width
        ~height:bounds.height
        ~horizontal_padding:(if bounds.width >= 8 then 1 else 0)
        ~vertical_padding:0
    in
    let width = geometry.content_width in
    let height = geometry.content_height in
    let footer_height = if height >= 3 then 1 else 0 in
    let footer_gap = if height >= 5 then 1 else 0 in
    let heading_height = if geometry.border = 0 && height >= 4 then 1 else 0 in
    let prompt_rows =
      Int.max 1 (Int.min 3 (height - footer_height - footer_gap - heading_height))
    in
    let text ?(role = Role.Surface) text =
      lines ~appearance ~role ~width ~height:1 [ text ]
    in
    let heading =
      match p.argument with
      | Some (H.Plan_endpoint _) ->
        "PLAN ENDPOINT - exact provider endpoint; Enter previews; Esc closes"
      | Some (H.Finalization_attempt run) ->
        "INSPECT FINALIZATION for "
        ^ run_label run
        ^ " - exact returned attempt; Enter imports; Esc closes"
      | Some (H.Acceptance (run, _, _)) ->
        "FINALIZE AND ACCEPT " ^ run_label run ^ " — Enter submits; Esc closes"
      | Some (H.Simulation_selection _) ->
        "SIMULATION LAUNCH FORM — explicit inputs; Enter accepts each field"
      | None -> "COMMAND PALETTE · captured target"
    in
    let query =
      match p.argument with
      | Some (H.Simulation_selection _ | H.Acceptance _) ->
        let input =
          "> "
          ^ p.query
          ^
          match appearance.icons with
          | Unicode -> "▏"
          | Ascii | None_ -> "|"
        in
        (* Anchor overflowing forms at the tail, so a useful path component does not split
           just because the frame/padding consumes a different number of cells. *)
        let input =
          if width > 0 && cell_width input > width * prompt_rows
          then String.make ((width - (cell_width input % width)) % width) ' ' ^ input
          else input
        in
        wrap_cells ~width input |> List.rev |> Fn.flip List.take prompt_rows |> List.rev
      | _ -> []
    in
    let help =
      match p.argument with
      | Some (H.Simulation_selection (_, _, _, form)) ->
        Simulation_view.Form.help form |> List.concat_map ~f:(wrap_cells ~width)
      | Some (H.Acceptance _) ->
        [ "Acceptance S-expression (≤4096 UTF-8 bytes; quote paths with spaces):"
        ; "((support_tools /tools) (precheck_python /python)"
        ; " (testbench /tb.sv) (testbench_top tb) (replay_trace /trace))"
        ; "All five values are explicit strings; no shell expansion."
        ]
      | _ -> []
    in
    let prompt =
      if List.is_empty query
      then
        [ Palette_view.query
            ~attrs:(Role.attrs appearance Surface)
            ~prompt_attrs:(Role.attrs appearance Focus)
            ~caret:
              (match appearance.icons with
               | Unicode -> "▏"
               | Ascii | None_ -> "|")
            ~caret_attrs:(Role.attrs appearance Focus)
            ~width
            p.query
        ]
      else List.map query ~f:(text ~role:Focus)
    in
    let header =
      (if heading_height > 0 then [ text heading ] else [])
      @ prompt
      @ List.map help ~f:text
    in
    let shown = Int.max 0 (height - List.length header - footer_height - footer_gap) in
    let ranked = if Option.is_some p.argument then [] else H.ranked_matches p in
    let start = Int.max 0 (p.index - shown + 1) in
    let commands =
      List.drop ranked start
      |> Fn.flip List.take shown
      |> List.mapi ~f:(fun i result ->
        let selected = start + i = p.index in
        let role = if selected then Role.Selection else Surface in
        let attrs = Role.attrs appearance role in
        (* Selection owns the row backdrop; matching owns underline and a warm foreground.
           The two remain distinct even on the selected command. *)
        let match_attrs =
          Role.attrs appearance Matched @ [ Attr.bg (Role.backdrop appearance role) ]
        in
        Palette_view.result_row
          ~attrs
          ~match_attrs
          ~marker_attrs:(Role.attrs appearance role)
          ~width
          ~selected
          result
        |> colored appearance role)
    in
    let commands =
      if Option.is_none p.argument && List.is_empty ranked && shown > 0
      then [ text ~role:Muted "No matching commands" ]
      else commands
    in
    let footer =
      if not (String.is_empty host.notice)
      then host.notice
      else if Option.is_some p.argument
      then "Enter accepts input · Esc return · Ctrl-C exits"
      else
        sprintf
          "%d/%d · Tab/Shift-Tab ↑/↓ · Enter run · Esc return"
          (if List.is_empty ranked then 0 else p.index + 1)
          (List.length ranked)
    in
    let body =
      View.vcat (header @ commands)
      |> box ~width ~height:(Int.max 0 (height - footer_height - footer_gap))
    in
    let panel =
      View.vcat
        ([ body ]
         @ (if footer_gap > 0 then [ text "" ] else [])
         @ if footer_height > 0 then [ text ~role:Muted footer ] else [])
      |> box ~width ~height
      |> Panel.render
           appearance
           ~attrs:(Role.attrs appearance Focus)
           ~title:(View.text ~attrs:(Role.attrs appearance Focus) heading)
           ~geometry
           ~width:bounds.width
           ~height:bounds.height
      |> box ~width:bounds.width ~height:bounds.height
      |> colored appearance Surface
    in
    Palette_view.overlay ~background ~panel bounds
    |> box ~width:dimensions.width ~height:dimensions.height
;;

(* A focused explorer covers the workspace. Do not construct the obscured tile images:
   those have different widths and would wrap the same large source a second time. *)
let render ?indicator_frames host data dimensions =
  let inspection_tile =
    match host.H.inspection_paste with
    | None -> H.focused host
    | Some id ->
      Option.bind host.registry ~f:(fun registry ->
        List.find registry.tiles ~f:(fun tile -> W.Tile_id.equal tile.id id))
  in
  let background =
    match Option.bind inspection_tile ~f:(inspection_explorer host) with
    | Some view ->
      let width, height = inspection_viewport dimensions in
      lines
        ~appearance:host.appearance
        ~role:Surface
        ~width
        ~height
        (Inspection_view.rows view ~width ~height)
      |> colored host.appearance Surface
      |> box ~width ~height
    | None -> render_workspace ?indicator_frames host data dimensions
  in
  render_palette host dimensions background
;;

let appearance_cases =
  List.concat_map Appearance.Preset.all ~f:(fun preset ->
    List.concat_map Appearance.Color.all ~f:(fun color ->
      List.concat_map Appearance.Icons.all ~f:(fun icons ->
        List.map Appearance.Density.all ~f:(fun density ->
          { Appearance.preset; color; scheme = Slate; icons; density }))))
;;

let plain_text view =
  let buffer = Buffer.create (View.width view * View.height view) in
  Notty.Render.to_buffer
    buffer
    Notty.Cap.dumb
    (0, 0)
    (View.width view, View.height view)
    (View.Private.notty_image view);
  Buffer.contents buffer
;;

let refinement_fixture (definition : P.Definition.t) =
  let initial = W.initial ~session_id:(W.Session_id.of_string "refinement-render") in
  let workspace = List.hd_exn initial.workspaces in
  let apply registry mutation =
    W.apply
      registry
      (Mutate { expected_revision = registry.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let registry = apply initial (P.Definition.apply definition ~workspace:workspace.id) in
  let registry =
    apply
      registry
      (Select_run
         { workspace = workspace.id
         ; context = workspace.context
         ; expected_selection_revision = 0
         ; run = Some Fs0_fixture.run_a
         })
  in
  let stages =
    List.map
      [ "synthesis"; "floorplan"; "placement"; "cts"; "routing"; "signoff" ]
      ~f:(fun id ->
        { Asic.Stage.id
        ; name = id
        ; status = Completed
        ; requested = true
        ; reason = None
        ; action = None
        })
  in
  let snapshot =
    { Fs0_fixture.snapshot with
      runs = List.map Fs0_fixture.snapshot.runs ~f:(fun run -> { run with stages })
    }
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = List.map snapshot.runs ~f:(fun run -> run.Asic.Run.run, run.status)
    ; log_lines = (fun _ -> [])
    ; run_lines = run_lines (Some snapshot)
    ; run_context = request_context (Some snapshot)
    ; summary =
        (fun run -> List.find snapshot.summaries ~f:(fun s -> Run_ref.equal s.run run))
    ; status = "connected"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = Some snapshot
    }
  in
  let host = H.receive H.empty registry in
  let find kind =
    List.find_exn (H.tiles host) ~f:(fun tile -> String.equal tile.W.Tile.kind kind)
  in
  host, data, find
;;

let%test_unit "lifecycle icons do not turn readiness, ownership or completion into case \
               pass"
  =
  let glyph = Indicator.text Unicode in
  let check actual expected = assert (String.equal (glyph actual) (glyph expected)) in
  List.iter
    [ Planned_run.Submitting, Indicator.Running
    ; Allocated, Running
    ; Running, Running
    ; Completed, Completed
    ; Launch_failed, Failed
    ; Cancelled, Cancelled
    ; Detached, Unknown
    ; Unavailable, Unknown
    ]
    ~f:(fun (state, expected) -> check (producer_indicator state) expected);
  List.iter
    [ Planned_run.Empty, Indicator.Not_requested
    ; Pending, Running
    ; Failed, Failed
    ; Stale, Stale
    ; Ready, Ready
    ]
    ~f:(fun (state, expected) -> check (plan_indicator state) expected);
  assert (not (String.equal (glyph (plan_indicator Ready)) (glyph Completed)));
  List.iter
    [ Job.State.Queued, Indicator.Pending
    ; Starting, Running
    ; Running, Running
    ; Complete, Completed
    ; Failed, Failed
    ; Cancelled, Cancelled
    ]
    ~f:(fun (state, expected) -> check (job_indicator state) expected);
  List.iter
    [ Simulation.Lifecycle.Finished; Cancelled; Interrupted; Queued ]
    ~f:(fun lifecycle ->
      check (Simulation_view.case_indicator ~lifecycle Running) Unknown);
  check (Simulation_view.case_indicator ~lifecycle:Running Running) Running;
  check (Simulation_view.case_indicator ~lifecycle:Finished Incomplete) Unknown;
  check (Simulation_view.case_indicator ~lifecycle:Finished Passed) Completed;
  check (Simulation_view.attempt_indicator Finished Unknown) Unknown;
  check (Simulation_view.attempt_indicator Finished Incomplete) Unknown;
  check (Simulation_view.attempt_indicator Finished Failed) Failed;
  check (Simulation_view.attempt_indicator Finished Passed) Completed;
  List.iter
    [ "pass"; "detached"; "unknown"; "unavailable"; "running in report" ]
    ~f:(fun status -> check (run_indicator status) Unknown)
;;

let%test_unit "cooperative Testing renderer keeps project scope and bounded panes" =
  let host, data, find = refinement_fixture P.Testing.definition in
  let catalog = find "simulation-catalog" in
  assert (
    T.Binding.equal
      (H.binding_kind { catalog with binding = Pin_run Fs0_fixture.run_a })
      Project);
  let host = H.set_filter host catalog.id "directed" in
  assert (
    String.equal
      (Simulation_catalog.filter
         (Testing_workspace.catalog (H.testing_state host catalog.id)))
      "directed");
  List.iter
    [ 120, 40; 180, 55; 40, 12 ]
    ~f:(fun (width, height) ->
      let view = render host data { Dimensions.width; height } in
      assert (View.width view = width && View.height view = height));
  let frame text : Indicator.frames = { dot = View.text text; line = View.text text } in
  List.iter
    [ "simulation-catalog"
    ; "simulation-attempts"
    ; "simulation-cases"
    ; "simulation-detail"
    ; "simulation-artifacts"
    ; "simulation-logs"
    ]
    ~f:(fun kind ->
      let tile = find kind in
      let host = { host with appearance = { host.appearance with icons = None_ } } in
      let a =
        tile_view ~indicator_frames:(frame "A") host data tile ~width:48 ~height:12
      in
      let b =
        tile_view ~indicator_frames:(frame "B") host data tile ~width:48 ~height:12
      in
      assert (String.equal (plain_text a) (plain_text b));
      assert (
        not (String.is_substring (plain_text a) ~substring:(run_label Fs0_fixture.run_a))));
  let text =
    tile_view host data (find "project-tests") ~width:24 ~height:8 |> plain_text
  in
  assert (String.is_substring text ~substring:"Generic project tests");
  assert (String.is_substring text ~substring:"Process results only")
;;

let%test_unit "long cooperative lists follow typed wrapped cursors and respect manual \
               scroll"
  =
  let host, data, find = refinement_fixture P.Testing.definition in
  let cases =
    List.init 40 ~f:(fun i ->
      { Simulation.Case.id = sprintf "case-%02d" i
      ; label = "Long case label wrapping across narrow display cells"
      })
  in
  let suite : Simulation.Suite.t =
    { id = "suite-00"
    ; label = "Selected suite"
    ; cases
    ; default_seed = "42"
    ; parameters =
        List.init 20 ~f:(fun i ->
          { Simulation.Parameter.key = sprintf "p%d" i
          ; label = "Parameter"
          ; default = "0"
          ; choices = []
          })
    }
  in
  let selection = Simulation_view.selection suite in
  let attempt : Simulation.Attempt.t =
    { id = "attempt-24"
    ; job = Job_id.of_string "exact-long-list-job"
    ; project_root = "/fixture"
    ; created_at = "now"
    ; parent = None
    ; captured =
        { selection
        ; discovery_digest = String.make 64 'd'
        ; provider_executable = "/provider"
        ; provider_args = []
        ; environment = Inherit_daemon
        }
    ; lifecycle = Finished
    ; outcome = Failed
    ; exit_code = Some 0
    ; diagnostic = None
    ; progress = None
    ; cases =
        List.map cases ~f:(fun c ->
          { Simulation.Case_result.case_id = c.id
          ; status = Failed
          ; message = None
          ; progress = None
          })
    ; artifacts =
        List.mapi cases ~f:(fun i c ->
          { Simulation.Artifact.id = sprintf "artifact-%02d" i
          ; attempt_id = "attempt-24"
          ; case_id = Some c.id
          ; label = sprintf "Artifact-%02d long wrapping artifact label" i
          ; kind = "report"
          ; media_type = "text/plain"
          ; size = Some 42
          ; sha256 = Some (String.make 64 'a')
          ; availability = Available
          })
    ; next_sequence = 0
    ; recent_events = []
    }
  in
  let snapshot : Simulation.Snapshot.t =
    { configured = true
    ; discovery =
        Some
          { protocol_version = 1
          ; suites = List.init 30 ~f:(fun i -> { suite with id = sprintf "suite-%02d" i })
          }
    ; discovery_digest = Some (String.make 64 'd')
    ; discovery_job = None
    ; discovery_error = None
    ; history_error = None
    ; next_before = None
    ; detail = Some attempt
    ; byte_page = None
    ; attempts =
        List.init 25 ~f:(fun i ->
          { Simulation.Summary.id = sprintf "attempt-%02d" i
          ; job = attempt.job
          ; suite = suite.id
          ; seed = "42"
          ; created_at = "now"
          ; parent = None
          ; lifecycle = Finished
          ; outcome = Failed
          })
    }
  in
  let view =
    { Simulation_view.empty with snapshot = Some snapshot; attempt = Some attempt.id }
  in
  let host = H.set_simulation host (find "simulation-catalog").id view in
  let overview = simulation_annotations host data (find "simulation-catalog") in
  let first_case =
    List.findi_exn overview ~f:(fun _ row -> row.Simulation_view.selected) |> fst
  in
  assert (first_case < 10);
  let prefix =
    List.take overview (first_case + 1)
    |> List.map ~f:(fun row -> row.Simulation_view.text)
    |> String.concat ~sep:"\n"
  in
  assert (not (String.is_substring prefix ~substring:(String.make 64 'd')));
  assert (not (String.is_substring prefix ~substring:"Parameter p"));
  assert (String.is_substring prefix ~substring:"Ready for explicit launch");
  List.iter
    [ 120, 40; 40, 12; 24, 8 ]
    ~f:(fun (width, height) ->
      let dimensions : Dimensions.t = { width; height } in
      List.iter
        [ "simulation-catalog", 39
        ; "simulation-attempts", 25
        ; "simulation-cases", 40
        ; "simulation-artifacts", 40
        ]
        ~f:(fun (kind, moves) ->
          let tile = find kind in
          let host = { host with focus = Some tile.id } in
          let host =
            if String.equal kind "simulation-attempts"
            then H.set_simulation host tile.id { view with attempt = None }
            else host
          in
          let reconcile host = reconcile_simulation_viewports host data dimensions in
          let selected_visible host =
            let _, _, layout = tile_layout host dimensions in
            let _, g =
              List.find_exn layout ~f:(fun (t, _) -> W.Tile_id.equal t.id tile.id)
            in
            let _, _, _, body_width, body_height =
              body_geometry host tile ~width:g.width ~height:g.height
            in
            let rows =
              simulation_view_rows_with_selection host data tile ~width:body_width
            in
            let index = List.findi_exn rows ~f:(fun _ (selected, _) -> selected) |> fst in
            assert (List.count rows ~f:fst = 1);
            let start = (H.local host tile.id).scroll in
            assert (start <= index && index < start + body_height);
            let image = tile_view host data tile ~width:g.width ~height:g.height in
            assert (View.width image = g.width && View.height image = g.height)
          in
          let press host key =
            let host, _ = H.input host (Character key) ~commands:[] in
            let host = reconcile host in
            selected_visible host;
            host
          in
          let host =
            List.init moves ~f:Fn.id
            |> List.fold ~init:host ~f:(fun host _ -> press host 'j')
          in
          let state = H.testing_state host tile.id in
          (match kind with
           | "simulation-catalog" ->
             assert (
               Option.equal
                 String.equal
                 (Simulation_catalog.case_id (Testing_workspace.catalog state))
                 (Some "case-39"))
           | "simulation-attempts" ->
             assert (
               Option.equal
                 String.equal
                 (Testing_workspace.view state).attempt
                 (Some "attempt-24"))
           | "simulation-cases" ->
             assert (
               Option.equal
                 String.equal
                 (Testing_workspace.view state).case_id
                 (Some "case-39"))
           | "simulation-artifacts" ->
             assert (
               Option.equal
                 String.equal
                 (Testing_workspace.selected_artifact state)
                 (Some "artifact-39"))
           | _ -> assert false);
          assert ((H.local host tile.id).scroll > 0);
          let host = scroll_run_focused host data dimensions ~delta:Int.min_value in
          assert ((not (H.local host tile.id).follow) && (H.local host tile.id).scroll = 0);
          let host = reconcile host in
          assert ((H.local host tile.id).scroll = 0);
          let host = press host 'k' in
          assert ((H.local host tile.id).follow && (H.local host tile.id).scroll > 0);
          ignore
            (List.init moves ~f:Fn.id
             |> List.fold ~init:host ~f:(fun host _ -> press host 'k')
             : H.t)));
  List.iter [ "simulation-detail"; "simulation-logs" ] ~f:(fun kind ->
    let tile = find kind in
    let host =
      H.set_local host tile.id { (H.local host tile.id) with scroll = 17; follow = true }
    in
    let host =
      reconcile_simulation_viewports host data { Dimensions.width = 120; height = 40 }
    in
    assert ((H.local host tile.id).scroll = 17))
;;

let%test_unit "simulation annotations preserve typed rows, logs and terminal case fences" =
  let definition =
    { P.Testing.definition with
      tiles = P.Testing.definition.tiles @ [ P.Common.tile "simulation" ]
    }
  in
  let host, data, find = refinement_fixture definition in
  let tile = find "simulation" in
  let attempt : Simulation.Attempt.t =
    { id = "exact-running-ID"
    ; job = Job_id.of_string "exact-job"
    ; project_root = "/fixture"
    ; created_at = "now"
    ; parent = None
    ; captured =
        { selection =
            { suite = "suite"
            ; cases = [ "case" ]
            ; seed = "17"
            ; parameters = []
            ; asic_inputs = []
            }
        ; discovery_digest = "digest"
        ; provider_executable = "/fixture/provider"
        ; provider_args = []
        ; environment = V1.Environment_selection.Inherit_daemon
        }
    ; lifecycle = Running
    ; outcome = Unknown
    ; exit_code = None
    ; diagnostic = Some "completed failed running\nraw diagnostic"
    ; progress = None
    ; cases =
        [ { case_id = "case"
          ; status = Running
          ; message = Some "passed\nraw message"
          ; progress = None
          }
        ]
    ; artifacts = []
    ; next_sequence = 0
    ; recent_events = []
    }
  in
  let snapshot : Simulation.Snapshot.t =
    { configured = true
    ; discovery = None
    ; discovery_digest = None
    ; discovery_job = None
    ; discovery_error = None
    ; history_error = Some "running\nraw history error"
    ; attempts = []
    ; next_before = None
    ; detail = Some attempt
    ; byte_page = None
    }
  in
  let logs =
    [ "running failed completed"
    ; "Attempt: exact-running-ID"
    ; "case: Running"
    ; "raw\nlog"
    ]
  in
  let data = { data with log_lines = (fun _ -> logs) } in
  let frames glyph : Indicator.frames =
    { dot = View.text glyph; line = View.text glyph }
  in
  List.iter Appearance.Icons.all ~f:(fun icons ->
    List.iter [ Simulation.Lifecycle.Running; Finished; Interrupted ] ~f:(fun lifecycle ->
      let simulation =
        { Simulation_view.empty with
          snapshot = Some { snapshot with detail = Some { attempt with lifecycle } }
        ; attempt = Some attempt.id
        ; logs = true
        ; case_id = Some "case"
        }
      in
      let host =
        H.set_local
          { host with appearance = { host.appearance with icons } }
          tile.id
          { H.default_local with simulation }
      in
      let source = Simulation_view.rows simulation ~log_lines:data.log_lines in
      let projected =
        Simulation_view.annotated_rows simulation ~log_lines:data.log_lines
      in
      assert (
        List.equal
          String.equal
          source
          (List.map projected ~f:(fun row -> row.Simulation_view.text)));
      let log_count = List.concat_map logs ~f:String.split_lines |> List.length in
      let log_start = List.length source - 1 - log_count in
      List.iteri projected ~f:(fun i { Simulation_view.text; indicator = kind; _ } ->
        if (i >= log_start && i < log_start + log_count)
           || List.mem
                [ "raw diagnostic"
                ; "completed failed running"
                ; "  passed"
                ; "  raw message"
                ; "running"
                ]
                text
                ~equal:String.equal
        then assert (Option.is_none kind));
      let views frames width =
        simulation_view_rows ~indicator_frames:frames host data tile ~width
      in
      let a = views (frames "A") 120 |> View.vcat |> plain_text in
      let b = views (frames "B") 120 |> View.vcat |> plain_text in
      let animated =
        Simulation.Lifecycle.equal lifecycle Running
        && not (Appearance.Icons.equal icons None_)
      in
      assert (Bool.equal (not (String.equal a b)) animated);
      List.iter logs ~f:(fun log ->
        String.split_lines log
        |> List.iter ~f:(fun line -> assert (String.is_substring a ~substring:line)));
      if Appearance.Icons.equal icons None_
      then
        assert (
          String.equal
            a
            (List.map source ~f:(fun text -> View.text text |> box ~width:120 ~height:1)
             |> View.vcat
             |> plain_text));
      List.iter [ 0; 1; 7; 32; 120 ] ~f:(fun width ->
        let a = views (frames "A") width
        and b = views (frames "B") width in
        assert (List.length a = List.length b);
        List.iter a ~f:(fun view ->
          assert (View.width view = width && View.height view = 1)))))
;;

let%test_unit "shared host frames follow exact producers and leave tile layout unchanged" =
  let host, data, find = refinement_fixture P.Overview.definition in
  let stage_tile = find "stage-checklist" in
  let plan_tile = find "planned-run" in
  let snapshot = Option.value_exn data.asic in
  let operation : Asic.Pending.t =
    { key = "run:exact"
    ; kind = "run"
    ; state = "executing"
    ; run = Some Fs0_fixture.run_a
    ; error = None
    }
  in
  let snapshot =
    { snapshot with
      operations = [ operation ]
    ; runs =
        List.map snapshot.runs ~f:(fun execution ->
          { execution with
            status = "observing"
          ; stages =
              List.map execution.stages ~f:(fun stage -> { stage with status = Running })
          })
    }
  in
  let data =
    { data with asic = Some snapshot; runs = [ Fs0_fixture.run_a, "observing" ] }
  in
  assert (run_has_producer data Fs0_fixture.run_a);
  assert (not (run_has_producer data Fs0_fixture.run_b));
  let frames glyph : Indicator.frames =
    { dot = View.text glyph; line = View.text glyph }
  in
  List.iter Appearance.Icons.all ~f:(fun icons ->
    let host = { host with appearance = { host.appearance with icons } } in
    let render data tile frame width height =
      tile_view ~indicator_frames:(frames frame) host data tile ~width ~height
    in
    let a = render data stage_tile "A" 100 16 |> plain_text in
    let b = render data stage_tile "B" 100 16 |> plain_text in
    assert (Bool.equal (not (String.equal a b)) (not (Appearance.Icons.equal icons None_)));
    List.iter
      [ []
      ; [ { operation with run = Some Fs0_fixture.run_b } ]
      ; [ { operation with state = "detached" } ]
      ]
      ~f:(fun operations ->
        let data = { data with asic = Some { snapshot with operations } } in
        assert (not (run_has_producer data Fs0_fixture.run_a));
        assert (
          String.equal
            (render data stage_tile "A" 100 16 |> plain_text)
            (render data stage_tile "B" 100 16 |> plain_text)));
    List.iter
      [ "completed"; "failed"; "detached"; "unknown"; "unavailable" ]
      ~f:(fun status ->
        let data =
          { data with
            asic =
              Some
                { snapshot with
                  runs = List.map snapshot.runs ~f:(fun run -> { run with status })
                }
          }
        in
        assert (not (run_has_producer data Fs0_fixture.run_a)));
    let selection : Asic.Selection.t =
      { flow = "flow"
      ; profile = "profile"
      ; endpoint = "exact-endpoint"
      ; assignments = []
      }
    in
    let planned_run, _ = Planned_run.begin_plan Planned_run.empty selection in
    let pending_host = { host with planned_run } in
    let plan frame =
      planned_view_rows ~indicator_frames:(frames frame) pending_host plan_tile ~width:100
      |> View.vcat
      |> plain_text
    in
    assert (
      Bool.equal
        (not (String.equal (plan "A") (plan "B")))
        (not (Appearance.Icons.equal icons None_)));
    assert (String.is_substring (plan "A") ~substring:"exact-endpoint");
    List.iter
      [ 0, 0; 1, 1; 32, 8; 100, 16 ]
      ~f:(fun (width, height) ->
        List.iter [ stage_tile; plan_tile ] ~f:(fun tile ->
          let a = render data tile "A" width height
          and b = render data tile "B" width height in
          assert (View.width a = width && View.height a = height);
          assert (View.width b = width && View.height b = height))))
;;

let%test_unit "generic job icons retain exact identity and completion vocabulary" =
  let definition =
    { P.Testing.definition with
      id = "generic-job-icon-regression"
    ; tiles =
        List.map P.Testing.definition.tiles ~f:(fun tile ->
          { tile with
            presentation = { tile.presentation with compact_summary = Some false }
          })
    }
  in
  let host, data, find = refinement_fixture definition in
  let tile = find "project-tests" in
  let base = List.hd_exn Baseline_fixture.jobs in
  let frames glyph : Indicator.frames =
    { dot = View.text glyph; line = View.text glyph }
  in
  List.iter Appearance.Icons.all ~f:(fun icons ->
    let host = { host with appearance = { host.appearance with icons } } in
    List.iter Job.State.all ~f:(fun state ->
      let job = { base with kind = { namespace = "dune"; name = "test" }; state } in
      let data = { data with jobs = [ job ] } in
      let render frame =
        tile_view ~indicator_frames:(frames frame) host data tile ~width:140 ~height:16
      in
      let a = render "A" |> plain_text
      and b = render "B" |> plain_text in
      let animated =
        List.mem [ Job.State.Starting; Running ] state ~equal:Job.State.equal
        && not (Appearance.Icons.equal icons None_)
      in
      assert (Bool.equal (not (String.equal a b)) animated);
      assert (String.is_substring a ~substring:(Job_id.to_string job.id));
      assert (String.is_substring a ~substring:(Job.State.to_string state));
      assert (String.is_substring a ~substring:"Case details / progress: unavailable");
      assert (not (String.is_substring a ~substring:"Passed"));
      List.iter
        [ 0, 0; 1, 1; 32, 8 ]
        ~f:(fun (width, height) ->
          let view =
            tile_view ~indicator_frames:(frames "A") host data tile ~width ~height
          in
          assert (View.width view = width && View.height view = height))))
;;

let%test_unit "Overview renders four primary domains with shallow frames and bounded \
               selector growth"
  =
  let host, data, find = refinement_fixture P.Overview.definition in
  let dimensions = { Dimensions.width = 120; height = 40 } in
  let _, compact, layout = tile_layout host dimensions in
  assert (not compact);
  let cell tile =
    List.find_exn layout ~f:(fun (t, _) -> W.Tile_id.equal t.id tile.W.Tile.id) |> snd
  in
  let navigation = cell (find "workspace-tabs") in
  assert (navigation.height = 1);
  assert ((cell (find "live-status")).y = navigation.y + 1);
  List.iter [ "live-status"; "run-selector" ] ~f:(fun kind ->
    let tile = find kind in
    let g = cell tile in
    let panel = panel_geometry host tile ~width:g.width ~height:g.height in
    assert (panel.border = 1 && panel.vertical_padding = 0);
    let image = tile_view host data tile ~width:g.width ~height:g.height in
    assert (String.is_prefix (plain_text image) ~prefix:"╭");
    let _, _, _, _, rows = body_geometry host tile ~width:g.width ~height:g.height in
    assert (rows = g.height - 2));
  let image = render_workspace host data dimensions |> plain_text in
  List.iter [ "synthesis"; "timing"; "placement"; "routing" ] ~f:(fun kind ->
    assert (String.is_substring image ~substring:kind);
    let tile = find kind in
    let g = cell tile in
    let panel = tile_view host data tile ~width:g.width ~height:g.height in
    let first = View.crop ~b:(g.height - 1) panel |> plain_text in
    assert (String.is_substring first ~substring:kind);
    let body =
      View.crop ~l:1 ~t:1 panel |> box ~width:(g.width - 2) ~height:1 |> plain_text
    in
    assert (
      String.is_substring
        body
        ~substring:
          (match kind with
           | "synthesis" -> "Reported cells (agg.): 50"
           | "timing" -> "Aggregate slack: unavailable"
           | "placement" -> "Aggregate resources: unavailable"
           | _ -> "Routing-stage metrics: unsupported"));
    assert (not (String.is_substring body ~substring:(String.uppercase kind))));
  assert (String.is_substring image ~substring:"Reported cells (agg.): 50");
  let selector = find "run-selector" in
  let large =
    H.set_local
      host
      selector.id
      { H.default_local with
        presentation = { T.inherit_ with run_selector_rows = Some 1_000_000 }
      }
  in
  let _, compact, expanded = tile_layout large dimensions in
  assert (not compact);
  let grown =
    List.find_exn expanded ~f:(fun (t, _) -> W.Tile_id.equal t.id selector.id) |> snd
  in
  assert (grown.height > (cell selector).height && grown.height < dimensions.height);
  let _, _, _, _, capacity =
    body_geometry large selector ~width:grown.width ~height:grown.height
  in
  assert (capacity < 1_000_000);
  List.iter
    [ 1, 1; 12, 4; 80, 24 ]
    ~f:(fun (width, height) ->
      let view = render_workspace large data { Dimensions.width; height } in
      assert (View.width view = width && View.height view = height));
  let synthesis = find "synthesis" in
  let explicit =
    H.set_local
      host
      synthesis.id
      { H.default_local with
        synthesis = Synthesis_view.State.set_mode Synthesis_view.State.empty Cells
      }
  in
  assert (Option.is_none (compact_rows explicit data synthesis));
  assert (Option.is_some (semantic_rows explicit data synthesis ~width:60 ~height:12))
;;

let%test_unit "two-row compact facts retain stages and stale warnings with freshness off" =
  let host, data, find = refinement_fixture P.Overview.definition in
  let synthesis = find "synthesis" in
  let data =
    { data with
      summary =
        (fun run ->
          Option.map (data.summary run) ~f:(fun s ->
            { s with freshness = Cached_unverified }))
    }
  in
  let before = compact_rows host data synthesis |> Option.value_exn in
  let quiet =
    H.set_local
      host
      synthesis.id
      { H.default_local with presentation = { T.inherit_ with freshness = Some false } }
  in
  let after = compact_rows quiet data synthesis |> Option.value_exn in
  assert (Poly.equal (List.take before 2) (List.take after 2));
  (* Warning freshness survives chrome suppression; ordinary validated freshness is
     optional, without hiding either the metric or the independent stage. *)
  assert (List.length after = List.length before);
  let validated =
    { data with
      summary =
        (fun run ->
          Option.map (data.summary run) ~f:(fun s -> { s with freshness = Validated }))
    }
  in
  let before_validated = compact_rows host validated synthesis |> Option.value_exn in
  let after_validated = compact_rows quiet validated synthesis |> Option.value_exn in
  assert (List.length after_validated = List.length before_validated - 1);
  assert (Poly.equal (List.take before_validated 2) (List.take after_validated 2));
  let text = tile_view quiet data synthesis ~width:100 ~height:4 |> plain_text in
  List.iter
    [ "Reported cells (agg.): 50"; "cached/unverified"; "synthesis: completed" ]
    ~f:(fun substring -> assert (String.is_substring text ~substring));
  let checklist = find "stage-checklist" in
  let normal = utility_rows host data checklist |> Option.value_exn in
  assert (List.length normal = 6);
  assert (List.for_all normal ~f:(fun row -> Option.is_some row.Overview_tiles.status));
  let detailed =
    H.set_local host checklist.id { H.default_local with utility_detail = true }
  in
  let details =
    utility_rows detailed data checklist
    |> Option.value_exn
    |> Overview_tiles.inspection_lines
    |> String.concat ~sep:"\n"
  in
  List.iter
    [ "Stage ID: synthesis"; "Source digest:"; "Accept (agg.)" ]
    ~f:(fun substring -> assert (String.is_substring details ~substring))
;;

let%test_unit "shallow plan always shows readiness and endpoint; detail retains metadata" =
  let host, data, find = refinement_fixture P.Overview.definition in
  let tile = find "planned-run" in
  let snapshot = Option.value_exn data.asic in
  let selection : Asic.Selection.t =
    { flow = String.concat (List.init 100 ~f:(fun _ -> "界"))
    ; profile = "Exact-Profile"
    ; endpoint = "signoff"
    ; assignments = [ String.make 100 'A' ]
    }
  in
  let preview : Asic.Preview.t =
    { selection
    ; plan_identity = "Exact-Identity-AbC"
    ; plan_json = "{\"exact\":\"Metadata-AbC\"}"
    }
  in
  let key = List.hd_exn (Plain_rpc.keys (Plan selection) snapshot) in
  let snapshot =
    { snapshot with
      preview = Some preview
    ; operations =
        [ { key; kind = "plan"; state = "completed"; run = None; error = None } ]
    }
  in
  let host =
    { host with planned_run = Planned_run.receive host.planned_run ~revision:1 snapshot }
  in
  let preparing =
    { host with stage_preparation = Some "Preparing NEW run through routing" }
  in
  let preparation_text =
    planned_rows preparing tile ~width:80
    |> List.map ~f:(fun row -> row.Planned_run.text)
    |> String.concat ~sep:"\n"
  in
  assert (
    String.is_substring preparation_text ~substring:"Preparing NEW run through routing");
  assert (String.is_substring preparation_text ~substring:"Launch disabled");
  assert (not (String.is_substring preparation_text ~substring:"ready:"));
  List.iter [ 4; 5 ] ~f:(fun height ->
    let image = tile_view host data tile ~width:60 ~height in
    assert (View.width image = 60 && View.height image = height);
    let text = plain_text image in
    assert (String.is_substring text ~substring:"ready:");
    assert (String.is_substring text ~substring:"endpoint: signoff"));
  let detail = H.set_local host tile.id { H.default_local with utility_detail = true } in
  let full =
    planned_rows detail tile ~width:30
    |> List.map ~f:(fun row -> row.Planned_run.text)
    |> String.concat
  in
  List.iter
    [ "Exact-Identity-AbC"
    ; "Metadata-AbC"
    ; selection.flow
    ; List.hd_exn selection.assignments
    ]
    ~f:(fun substring -> assert (String.is_substring full ~substring));
  let launched_snapshot =
    { snapshot with
      launches =
        [ { key = "rendered-launch"; preview; run_id = Some Fs0_fixture.run_b.id } ]
    ; runs = [ Fs0_fixture.run Fs0_fixture.run_b ]
    }
  in
  let launched_host =
    { host with
      planned_run = Planned_run.receive host.planned_run ~revision:2 launched_snapshot
    }
  in
  let launched_text =
    tile_view
      launched_host
      { data with asic = Some launched_snapshot }
      tile
      ~width:80
      ~height:10
    |> plain_text
  in
  List.iter
    [ "last launch: completed"; "exact allocated run: fixture-B"; "rendered-launch" ]
    ~f:(fun substring -> assert (String.is_substring launched_text ~substring))
;;

let%test_unit "live schemes change semantic paint without geometry registry or queries" =
  let host, data, find = refinement_fixture P.Overview.definition in
  let dimensions = { Dimensions.width = 120; height = 40 } in
  let layout host =
    tile_layout host dimensions
    |> fun (_, _, cells) ->
    List.map cells ~f:(fun (tile, geometry) -> tile.W.Tile.id, geometry)
  in
  let original = layout host in
  let plain = render host data dimensions |> plain_text in
  List.iter Appearance.Scheme.all ~f:(fun scheme ->
    let appearance = { host.H.appearance with scheme } in
    let command =
      List.find_exn (H.appearance_commands host) ~f:(fun c ->
        String.equal c.H.id ("appearance.scheme." ^ Appearance.Scheme.key scheme))
    in
    (* A local Set_appearance action carries no request/query payload. *)
    let changed =
      match command.action with
      | Set_appearance selected -> H.set_appearance host selected
      | _ -> failwith "scheme action must be client-local"
    in
    assert (phys_equal changed.registry host.registry);
    assert (phys_equal changed.locals host.locals);
    assert (phys_equal changed.focus host.focus);
    assert (Poly.equal original (layout changed));
    assert (String.equal plain (render changed data dimensions |> plain_text));
    let title =
      tile_view changed data (find "live-status") ~width:40 ~height:5 |> plain_text
    in
    assert (String.is_prefix title ~prefix:"╭ session ─");
    List.iter Appearance.Color.all ~f:(fun color ->
      let appearance = { appearance with color } in
      let attrs = Role.attrs appearance in
      assert (not (Poly.equal (attrs Success) (attrs Failure)));
      assert (not (Poly.equal (attrs Warning) (attrs Foreground)));
      assert (
        not
          (Poly.equal
             (Role.backdrop appearance Selection)
             (Role.backdrop appearance Foreground))));
    List.iter Appearance.Scheme.all ~f:(fun other ->
      if not (Appearance.Scheme.equal scheme other)
      then (
        let other = { appearance with scheme = other } in
        assert (
          not
            (Poly.equal
               (Role.backdrop appearance Background)
               (Role.backdrop other Background)));
        assert (not (Poly.equal (Role.attrs appearance Focus) (Role.attrs other Focus))))))
;;

let%test_unit "host vertical stages preserve exact selected identity and detail" =
  let host, data, find = refinement_fixture P.Overview.definition in
  let tile = find "stage-checklist" in
  let host =
    H.set_local
      host
      tile.id
      { H.default_local with cursor = Some "signoff"; stage_run = Some Fs0_fixture.run_a }
  in
  List.iter
    [ 120, 5; 40, 10; 12, 4 ]
    ~f:(fun (width, height) ->
      let image = tile_view host data tile ~width ~height in
      assert (View.width image = width && View.height image = height));
  let text = tile_view host data tile ~width:120 ~height:5 |> plain_text in
  assert (String.is_substring text ~substring:"signoff: completed");
  let detail =
    H.set_local host tile.id { (H.local host tile.id) with utility_detail = true }
  in
  assert (
    String.is_substring
      (tile_view detail data tile ~width:100 ~height:20 |> plain_text)
      ~substring:"Stage ID: signoff")
;;

let%test_unit "Timing panes render typed selection and exact scoped detail with normal \
               panel chrome"
  =
  let host, data, find = refinement_fixture P.Timing.definition in
  let paths = find "timing-paths"
  and detail = find "timing-detail"
  and context = find "timing-context" in
  let _, compact, layout = tile_layout host { Dimensions.width = 120; height = 40 } in
  assert (not compact);
  assert (
    not
      (List.exists (H.tiles host) ~f:(fun tile ->
         String.equal tile.W.Tile.kind "stage-checklist")));
  let cell tile =
    List.find_exn layout ~f:(fun (t, _) -> W.Tile_id.equal t.id tile.W.Tile.id) |> snd
  in
  let pg = cell paths
  and dg = cell detail
  and cg = cell context in
  assert (pg.x < dg.x && dg.x = cg.x && dg.y < cg.y);
  assert (dg.width > pg.width && dg.height > cg.height);
  List.iter [ paths; detail; context ] ~f:(fun tile ->
    let g = cell tile in
    let panel = panel_geometry host tile ~width:g.width ~height:g.height in
    assert (panel.border = 1 && panel.vertical_padding = 0));
  let rows =
    List.init 30 ~f:(fun i ->
      { Asic_inspection.Row.id = Int.to_string i
      ; name = sprintf "path-%02d/endpoint/Q" i
      ; category = "path"
      ; producer = "sta"
      ; corner = Some "slow"
      ; group = Some "clk"
      ; value = Some (Float.of_int i -. 1.)
      ; unit_ = Some "ns"
      ; status = "violated"
      ; source = "/exact/report"
      ; fields = [ "startpoint", "input/D" ]
      })
  in
  let index : Asic_inspection.Index.t =
    { run = Fs0_fixture.run_a
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "exact-source-digest"
    ; execution_file = "/exact/execution"
    ; execution_sha256 = "exact-sha"
    ; rows
    ; diagnostics = []
    ; truncated = false
    ; cached_unverified = true
    }
  in
  let snapshot = { (Option.value_exn data.asic) with inspections = [ index ] } in
  let state =
    Inspection_view.reconcile
      (Timing_workspace.create ~generation:1 ~run:Fs0_fixture.run_a ~stage:"signoff")
      snapshot
  in
  let state = { state with selected = Some "29" } in
  let host = H.set_timing host paths state in
  let data = { data with asic = Some snapshot } in
  List.iter [ paths; detail; context ] ~f:(fun tile ->
    let image = tile_view host data tile ~width:70 ~height:14 in
    assert (String.is_prefix (plain_text image) ~prefix:"╭");
    assert (String.is_substring (plain_text image) ~substring:"timing"));
  let path_image = tile_view host data paths ~width:70 ~height:14 |> plain_text in
  assert (String.is_substring path_image ~substring:"path-29/endpoint/Q");
  assert (String.is_substring path_image ~substring:"violated");
  assert (String.is_substring path_image ~substring:"Cached unverified");
  assert (
    String.is_substring
      (tile_view host data detail ~width:70 ~height:14 |> plain_text)
      ~substring:"Path: path-29/endpoint/Q");
  assert (
    String.is_substring
      (tile_view host data detail ~width:70 ~height:14 |> plain_text)
      ~substring:"Slack: 28 ns · violated");
  assert (
    String.is_substring
      (tile_view host data context ~width:70 ~height:14 |> plain_text)
      ~substring:"Row: 29");
  let selection = Timing_workspace.selection state |> Option.value_exn in
  assert (
    String.equal selection.row_id "29"
    && String.equal selection.source_digest "exact-source-digest");
  assert (
    String.is_substring
      (tile_view host data context ~width:70 ~height:14 |> plain_text)
      ~substring:"exact-source-digest");
  List.iter [ Timing_workspace.Detail; Context ] ~f:(fun pane ->
    List.iter
      [ 12, 3; 40, 7; 70, 14 ]
      ~f:(fun (width, height) ->
        List.iter [ 0; 2; Int.max_value ] ~f:(fun scroll ->
          let actual =
            timing_body host.appearance ~pane ~scroll ~width ~height state |> plain_text
          in
          let expected =
            Timing_workspace.rows ~pane ~scroll ~width ~height state
            |> lines ~width ~height
            |> plain_text
          in
          assert (String.equal actual expected))));
  let prefix = timing_semantic_prefix ~pane:Detail ~width:70 state in
  assert (
    List.exists prefix ~f:(fun (role, text) ->
      match role with
      | Metric -> String.equal text "Slack: 28 ns · violated"
      | _ -> false));
  let prefix = timing_semantic_prefix ~pane:Context ~width:70 state in
  assert (
    List.exists prefix ~f:(fun (role, text) ->
      match role with
      | Warning -> String.equal text "CACHED UNVERIFIED"
      | _ -> false));
  List.iter [ Timing_workspace.Detail; Context ] ~f:(fun pane ->
    let typed = timing_semantic_prefix ~pane ~width:70 state |> List.map ~f:snd in
    let actual =
      Timing_workspace.rows ~pane ~scroll:0 ~width:70 ~height:Int.max_value state
    in
    assert (List.equal String.equal typed (List.take actual (List.length typed))));
  let long_source = String.make 2048 'j'
  and long_field = String.make 3072 'f' in
  let long_row =
    { (List.last_exn rows) with
      name = String.make 3000 'n'
    ; source = long_source
    ; fields =
        [ "startpoint", "exact/start/D"
        ; "endpoint", "exact/end/Q"
        ; "payload", long_field
        ]
    }
  in
  let payload = "failed pending selected raw\nprovider second line" in
  let provider_detail : Asic_inspection.Detail.t =
    { run = state.run
    ; domain = state.domain
    ; stage = state.stage
    ; source_digest = index.source_digest
    ; row_id = long_row.id
    ; text = payload
    ; error = None
    }
  in
  let loaded =
    { state with
      index = Some { index with rows = [ long_row ] }
    ; cache = None
    ; requested = Some (index.source_digest, long_row.id)
    ; detail = Some provider_detail
    }
  in
  let prefix = timing_semantic_prefix ~pane:Detail ~width:40 loaded in
  assert (List.length prefix = 4);
  let rendered =
    timing_body host.appearance ~pane:Detail ~scroll:0 ~width:40 ~height:6 loaded
  in
  let body = View.crop ~t:4 rendered |> box ~width:40 ~height:2 in
  let expected =
    String.split_lines payload |> lines ~appearance:host.appearance ~width:40 ~height:2
  in
  let ansi view =
    let buffer = Buffer.create 200 in
    Notty.Render.to_buffer
      buffer
      Notty.Cap.ansi
      (0, 0)
      (40, 2)
      (View.Private.notty_image view);
    Buffer.contents buffer
  in
  assert (String.equal (ansi body) (ansi expected));
  let scrolled =
    timing_body host.appearance ~pane:Detail ~scroll:4 ~width:40 ~height:2 loaded
  in
  assert (String.equal (ansi scrolled) (ansi expected));
  let full_context =
    timing_semantic_prefix ~pane:Context ~width:40 loaded
    |> List.map ~f:snd
    |> String.concat
  in
  List.iter
    [ "Row: 29"
    ; long_source
    ; long_field
    ; index.source_digest
    ; "exact/start/D"
    ; "exact/end/Q"
    ]
    ~f:(fun value -> assert (String.is_substring full_context ~substring:value));
  let pasting =
    { state with
      pasting = true
    ; filter = "literal"
    ; filter_notice = Some "Rejected control text"
    }
  in
  let paste_image =
    timing_body host.appearance ~pane:Paths ~scroll:0 ~width:70 ~height:12 pasting
    |> plain_text
  in
  assert (String.is_substring paste_image ~substring:"Paste filter: literal|");
  assert (String.is_substring paste_image ~substring:"Rejected control text");
  let tiny = tile_view host data paths ~width:40 ~height:3 |> plain_text in
  assert (String.is_substring tiny ~substring:"path-29");
  let registry = Option.value_exn host.registry in
  let registry =
    { registry with
      tiles =
        List.map registry.tiles ~f:(fun t ->
          if W.Tile_id.equal t.id paths.id
          then { t with binding = Pin_run Fs0_fixture.run_b }
          else t)
    }
  in
  let mismatched = { host with registry = Some registry } in
  let stale =
    tile_view mismatched data (W.tile registry paths.id) ~width:70 ~height:14
    |> plain_text
  in
  assert (not (String.is_substring stale ~substring:"path-29"));
  assert (String.is_substring stale ~substring:"No matching Timing investigation")
;;

let%test_unit "actual palette reserves a blank footer separator within its styled frame" =
  let host, data, _ = refinement_fixture P.Overview.definition in
  let palette : H.palette =
    { capture = Option.value_exn (H.capture host)
    ; commands = []
    ; query = "palette-query"
    ; index = 0
    ; argument = None
    }
  in
  let host = { host with palette = Some palette } in
  let dimensions = { Dimensions.width = 120; height = 40 } in
  let image = render host data dimensions in
  let bounds = Palette_view.bounds ~width:dimensions.width ~height:dimensions.height in
  let blank =
    View.crop ~l:(bounds.x + 1) ~t:(bounds.y + bounds.height - 3) image
    |> box ~width:(bounds.width - 2) ~height:1
    |> plain_text
  in
  assert (String.for_all blank ~f:(Char.equal ' '));
  let panel =
    View.crop ~l:bounds.x ~t:bounds.y image
    |> box ~width:bounds.width ~height:bounds.height
    |> plain_text
  in
  assert (String.is_prefix panel ~prefix:"╭");
  assert (String.is_substring panel ~substring:"> palette-query▏");
  assert (String.is_substring panel ~substring:"Esc return");
  assert (String.is_substring panel ~substring:"╰─")
;;

let%test_unit "selector width budget preserves useful IDs and aligns compact status" =
  let run =
    { Fs0_fixture.run_a with id = "long-distinguishable-selected-run-abcdefghijklmnop" }
  in
  let wide =
    run_selector_row ~width:90 ~status_width:9 ~cursor:true ~active:true run "completed"
  in
  assert (String.is_substring wide ~substring:(run_label run));
  assert (String.is_prefix wide ~prefix:">* ");
  assert (cell_width wide = 90);
  let narrow =
    run_selector_row ~width:36 ~status_width:9 ~cursor:true ~active:false run "completed"
  in
  assert (cell_width narrow = 36);
  assert (String.is_suffix narrow ~suffix:" completed");
  assert (String.is_substring narrow ~substring:"~");
  List.iter [ 0; 1; 2; 3; 5; 10; 20 ] ~f:(fun width ->
    let label = fit_label ~width "界é selected run identity 界é" in
    assert (cell_width label <= width))
;;

let%test_unit "actual utility and selector token images carry independent attributes" =
  let appearance = { Appearance.default with density = Compact; icons = None_ } in
  let ansi view =
    let buffer = Buffer.create 200 in
    Notty.Render.to_buffer
      buffer
      Notty.Cap.ansi
      (0, 0)
      (View.width view, View.height view)
      (View.Private.notty_image view);
    Buffer.contents buffer
  in
  let slice view ~x ~width = View.crop ~l:x view |> box ~width ~height:1 |> ansi in
  let token role text = View.text ~attrs:(Role.attrs appearance role) text |> ansi in
  let utility =
    Overview_tiles.render
      ~appearance
      ~attrs:(utility_attrs appearance)
      ~width:40
      ~height:1
      [ Overview_tiles.row ~role:Success "Evidence" "validated" ]
  in
  assert (String.equal (slice utility ~x:0 ~width:10) (token Foreground "Evidence: "));
  assert (String.equal (slice utility ~x:10 ~width:9) (token Success "validated"));
  assert (not (String.equal (token Foreground "validated") (token Success "validated")));
  List.iter Appearance.Scheme.all ~f:(fun scheme ->
    let appearance = { appearance with scheme } in
    let bg = Role.backdrop appearance Selection in
    let expected role text =
      View.text ~attrs:(Role.attrs appearance role @ [ Attr.bg bg ]) text |> ansi
    in
    List.iter
      [ "validated", Overview_tiles.Role.Success, Role.Success
      ; "cached/unverified", Warning, Warning
      ; "pending", Warning, Warning
      ; "running", Running, Running
      ; "cancelled", Warning, Warning
      ; "future-value", Foreground, Foreground
      ]
      ~f:(fun (value, utility_role, value_role) ->
        let image =
          Overview_tiles.render
            ~selected_bg:bg
            ~appearance
            ~attrs:(utility_attrs appearance)
            ~width:40
            ~height:1
            [ Overview_tiles.row ~active:true ~role:utility_role "Evidence" value ]
        in
        assert (
          String.equal (slice image ~x:0 ~width:10) (expected Foreground "Evidence: "));
        assert (
          String.equal
            (slice image ~x:10 ~width:(cell_width value))
            (expected value_role value))));
  let stage_appearance = { appearance with icons = Ascii } in
  let stage_bg = Role.backdrop stage_appearance Selection in
  let stage : Asic.Stage.t =
    { id = "synthesis"
    ; name = "Synthesis"
    ; status = Completed
    ; requested = true
    ; reason = None
    ; action = None
    }
  in
  let strip =
    Overview_tiles.Stage_strip.model
      ~appearance:stage_appearance
      ~width:80
      ~run:Fs0_fixture.run_a
      ~selected_id:(Some stage.id)
      [ stage ]
  in
  let image =
    Overview_tiles.Stage_strip.render
      ~selected_bg:stage_bg
      ~appearance:stage_appearance
      ~attrs:(utility_attrs stage_appearance)
      ~width:80
      ~height:2
      strip
  in
  let expected role text =
    View.text ~attrs:(Role.attrs stage_appearance role @ [ Attr.bg stage_bg ]) text
    |> ansi
  in
  let prefix = "> " ^ Indicator.text Ascii Completed ^ " " in
  let prefix_width = cell_width prefix in
  assert (String.equal (slice image ~x:0 ~width:prefix_width) (expected Selection prefix));
  assert (
    String.equal
      (slice image ~x:prefix_width ~width:11)
      (expected Foreground "Synthesis: "));
  assert (
    String.equal
      (slice image ~x:(prefix_width + 11) ~width:9)
      (expected Success "completed"));
  let detail = View.crop ~t:1 image in
  let label = strip.selected_line.label ^ ": " in
  assert (
    String.equal
      (slice detail ~x:prefix_width ~width:(cell_width label))
      (expected Foreground label));
  assert (
    String.equal
      (slice detail ~x:(prefix_width + cell_width label) ~width:9)
      (expected Success "completed"));
  let run = { Fs0_fixture.run_a with id = "failed-running-identity" } in
  List.iter
    [ "completed", Role.Success
    ; "failed", Failure
    ; "running", Running
    ; "starting", Running
    ; "pending", Warning
    ; "queued", Warning
    ; "cancelled", Warning
    ; "interrupted", Warning
    ; "skipped", Warning
    ; "pass", Foreground
    ; "future-status", Foreground
    ]
    ~f:(fun (status, role) ->
      List.iter [ false; true ] ~f:(fun cursor ->
        let width = 65
        and status_width = cell_width status in
        let image =
          run_selector_view
            appearance
            ~width
            ~status_width
            ~cursor
            ~active:true
            run
            status
        in
        let expected role text =
          View.text
            ~attrs:
              (Role.attrs appearance role
               @ if cursor then [ Attr.bg (Role.backdrop appearance Selection) ] else [])
            text
          |> ansi
        in
        let identity = if cursor then ">* " else " * " in
        assert (
          String.equal
            (slice image ~x:0 ~width:3)
            (expected (if cursor then Selection else Foreground) identity));
        assert (
          String.equal
            (slice image ~x:3 ~width:(cell_width (run_label run)))
            (expected (if cursor then Selection else Foreground) (run_label run)));
        assert (
          String.equal
            (slice image ~x:(width - status_width) ~width:status_width)
            (expected role status))));
  let clipped =
    run_selector_view
      appearance
      ~width:20
      ~status_width:3
      ~cursor:false
      ~active:false
      run
      "completed"
  in
  assert (String.equal (slice clipped ~x:17 ~width:3) (token Success "com"))
;;

let%test_unit "default Carbon ground is black and actual tile headers are neutral white" =
  assert (Appearance.Scheme.equal Appearance.default.scheme Carbon);
  let host, data, find = refinement_fixture P.Overview.definition in
  let ansi view =
    let buffer = Buffer.create 200 in
    Notty.Render.to_buffer
      buffer
      Notty.Cap.ansi
      (0, 0)
      (View.width view, View.height view)
      (View.Private.notty_image view);
    Buffer.contents buffer
  in
  let expected =
    View.text
      ~attrs:[ Attr.fg (Role.rgb 255 255 255); Attr.bg (Role.rgb 0 0 0); Attr.bold ]
      "session"
  in
  let tile = find "live-status" in
  List.iter Appearance.Preset.all ~f:(fun preset ->
    List.iter [ false; true ] ~f:(fun focused ->
      let appearance = { Appearance.default with preset } in
      let host =
        { host with H.appearance; focus = (if focused then Some tile.id else None) }
      in
      let image = tile_view host data tile ~width:60 ~height:8 in
      let y, line =
        plain_text image
        |> String.split_lines
        |> List.findi_exn ~f:(fun _ line -> String.is_substring line ~substring:"session")
      in
      let prefix =
        String.substr_index_exn line ~pattern:"session" |> String.prefix line
      in
      let header =
        View.crop ~l:(cell_width prefix) ~t:y image |> box ~width:7 ~height:1
      in
      assert (String.equal (ansi header) (ansi expected));
      let geometry = panel_geometry host tile ~width:60 ~height:8 in
      if geometry.border > 0
      then (
        let corner = if Appearance.Preset.equal preset Instrument then "╭" else "┌" in
        let expected =
          View.text
            ~attrs:(Role.attrs appearance (if focused then Focus else Border))
            corner
        in
        assert (String.equal (ansi (box ~width:1 ~height:1 image)) (ansi expected)))))
;;

let%test_unit "palette prompt caret and fuzzy spans have independent typed attributes" =
  let appearance = { Appearance.default with color = Vivid } in
  let ansi view =
    let buffer = Buffer.create 200 in
    Notty.Render.to_buffer
      buffer
      Notty.Cap.ansi
      (0, 0)
      (View.width view, View.height view)
      (View.Private.notty_image view);
    Buffer.contents buffer
  in
  let normal = ansi (View.text ~attrs:(Role.attrs appearance Surface) "x")
  and selected = ansi (View.text ~attrs:(Role.attrs appearance Selection) "x")
  and matched = ansi (View.text ~attrs:(Role.attrs appearance Matched) "x") in
  assert (not (String.equal normal selected));
  assert (not (String.equal selected matched));
  let query =
    Palette_view.query
      ~attrs:(Role.attrs appearance Surface)
      ~prompt_attrs:(Role.attrs appearance Focus)
      ~width:20
      "search"
  in
  assert (String.is_substring (plain_text query) ~substring:"> search▏");
  assert (String.is_substring (ansi query) ~substring:"search")
;;

let%test_unit "palette scroll keeps selected result visible at normal and tiny sizes" =
  let registry = W.initial ~session_id:(W.Session_id.of_string "palette-scrolling") in
  let host = H.receive H.empty registry in
  let commands =
    List.init 40 ~f:(fun i ->
      { H.id = Int.to_string i
      ; title = sprintf "Similar command %02d" i
      ; aliases = ""
      ; action = Toggle_chrome
      ; unavailable = None
      })
  in
  let host =
    List.fold [ ' '; 'c'; 'c' ] ~init:host ~f:(fun host c ->
      fst (H.input host (Character c) ~commands))
  in
  let host =
    List.fold (List.init 39 ~f:Fn.id) ~init:host ~f:(fun host _ ->
      fst (H.input host Focus ~commands))
  in
  List.iter
    [ 80, 24; 120, 40; 40, 4 ]
    ~f:(fun (width, height) ->
      let dimensions = { Dimensions.width; height } in
      let background = lines ~width ~height [ "WORKSPACE BACKGROUND" ] in
      let frame = render_palette host dimensions background in
      let text = plain_text frame in
      assert (View.width frame = width && View.height frame = height);
      assert (String.is_substring text ~substring:"Similar command 39");
      assert (not (String.is_substring text ~substring:"Similar command 00")));
  List.iter
    [ 1, 1; 3, 2; 12, 3 ]
    ~f:(fun (width, height) ->
      let frame =
        render_palette
          host
          { Dimensions.width; height }
          (View.rectangle ~width ~height ())
      in
      assert (View.width frame = width && View.height frame = height))
;;

let%test_unit "form overlay keeps query tail visible without changing captured form state"
  =
  let registry = W.initial ~session_id:(W.Session_id.of_string "form-overlay-tail") in
  let host = H.receive H.empty registry in
  let query = String.make 290 'x' ^ "QUERY-TAIL" in
  let palette : H.palette =
    { capture = Option.value_exn (H.capture host)
    ; commands = []
    ; query
    ; index = 0
    ; argument = Some (Acceptance (Fs0_fixture.run_a, "/exact/execution", "captured-key"))
    }
  in
  let host = { host with palette = Some palette } in
  List.iter
    [ 40, 4; 80, 24 ]
    ~f:(fun (width, height) ->
      let frame =
        render_palette
          host
          { Dimensions.width; height }
          (View.rectangle ~width ~height ())
      in
      if not (String.is_substring (plain_text frame) ~substring:"QUERY-TAIL")
      then failwithf "form %dx%d: %s" width height (plain_text frame) ();
      assert (phys_equal (Option.value_exn host.palette) palette));
  let returned, effect = H.input host Escape ~commands:[] in
  assert (Option.is_none returned.palette);
  match effect with
  | No_effect -> ()
  | _ -> assert false
;;

let%test_unit "density changes rendered padding while explicit overrides retain geometry" =
  let registry = W.initial ~session_id:(W.Session_id.of_string "density-rendering") in
  let original = List.hd_exn registry.tiles in
  let tile = { original with kind = "project" } in
  let registry = { registry with tiles = tile :: List.tl_exn registry.tiles } in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> assert false)
    ; run_lines = (fun _ _ -> assert false)
    ; run_context = (fun _ -> assert false)
    ; summary = (fun _ -> assert false)
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let host = H.receive H.empty registry in
  let host =
    H.set_local
      { host with focus = None }
      tile.id
      { H.default_local with presentation = { T.inherit_ with header = Some false } }
  in
  let host = { host with appearance = { host.appearance with preset = Minimal } } in
  let density host density = H.set_appearance host { host.H.appearance with density } in
  let geometry host = body_geometry host tile ~width:40 ~height:12 in
  let image host = tile_view host data tile ~width:40 ~height:12 in
  let compact = density host Compact
  and comfortable = density host Comfortable in
  let equal_geometry = [%equal: int * int * int * int * int] in
  assert (equal_geometry (geometry compact) (40, 12, 0, 40, 12));
  assert (equal_geometry (geometry comfortable) (40, 12, 1, 38, 12));
  assert (String.is_prefix (plain_text (image compact)) ~prefix:"No project open");
  let comfortable_body = image comfortable |> View.crop ~l:1 in
  assert (String.is_prefix (plain_text comfortable_body) ~prefix:"No project open");
  assert (not (String.equal (plain_text (image compact)) (plain_text (image comfortable))));
  List.iter [ 0; 2 ] ~f:(fun padding ->
    let explicit =
      H.set_local
        host
        tile.id
        { (H.local host tile.id) with
          presentation = { T.inherit_ with header = Some false; padding = Some padding }
        }
    in
    let a = density explicit Compact
    and b = density explicit Comfortable in
    assert ((H.policy a tile).padding = padding && (H.policy b tile).padding = padding);
    assert (equal_geometry (geometry a) (geometry b));
    assert (String.equal (plain_text (image a)) (plain_text (image b))));
  let app = { host with presentation = { T.inherit_ with padding = Some 0 } } in
  assert ((H.policy (density app Comfortable) tile).padding = 0);
  let workspace =
    { app with
      workspace_presentation =
        [ W.Workspace_id.to_string tile.workspace, { T.inherit_ with padding = Some 2 } ]
    }
  in
  assert ((H.policy (density workspace Compact) tile).padding = 2);
  let navigation = { tile with kind = "workspace-tabs" } in
  assert (
    (H.policy compact navigation).padding = 0
    && (H.policy comfortable navigation).padding = 0);
  assert (
    let _, _, padding, _, _ = body_geometry comfortable tile ~width:3 ~height:2 in
    padding = 0);
  List.iter [ compact; comfortable; app; workspace ] ~f:(fun host ->
    assert (phys_equal (Option.value_exn host.H.registry) registry);
    assert (W.Tile.equal (W.tile (Option.value_exn host.registry) tile.id) tile))
;;

let%test_unit "actual preset host resolves quiet chrome, headerless pins and selector cap"
  =
  let initial = W.initial ~session_id:(W.Session_id.of_string "composed-host") in
  let workspace = List.hd_exn initial.workspaces in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let registry =
    apply initial (P.Definition.apply P.Overview.definition ~workspace:workspace.id)
  in
  let context = W.context registry workspace.context in
  let registry =
    apply
      registry
      (Select_run
         { workspace = workspace.id
         ; context = context.id
         ; expected_selection_revision = context.selection_revision
         ; run = Some Fs0_fixture.run_a
         })
  in
  let find kind =
    List.find_exn registry.tiles ~f:(fun t ->
      W.Workspace_id.equal t.W.Tile.workspace workspace.id && String.equal t.kind kind)
  in
  let synthesis = find "synthesis"
  and selector = find "run-selector"
  and navigation = find "workspace-tabs" in
  let data =
    { project = None
    ; jobs = []
    ; runs =
        List.init 12 ~f:(fun i ->
          { Fs0_fixture.run_a with id = sprintf "run-%02d" i }, sprintf "candidate-%02d" i)
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary =
        (fun run ->
          List.find Fs0_fixture.snapshot.summaries ~f:(fun s -> Run_ref.equal s.run run))
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = Some Fs0_fixture.snapshot
    }
  in
  let host = H.receive H.empty registry in
  let image host tile = tile_view host data tile ~width:100 ~height:16 |> plain_text in
  let normal = image host synthesis in
  assert (not (String.is_substring normal ~substring:"follow"));
  assert (
    not (String.is_substring normal ~substring:("Run: " ^ run_label Fs0_fixture.run_a)));
  assert (String.is_substring normal ~substring:"Evidence: cached/unverified");
  let pin_registry =
    apply
      registry
      (Set_tile_binding { tile = synthesis.id; binding = Pin_run Fs0_fixture.run_a })
  in
  let pinned = W.tile pin_registry synthesis.id in
  let pin_host = H.receive host pin_registry in
  let pin_host =
    H.set_local
      pin_host
      pinned.id
      { H.default_local with
        presentation = { T.inherit_ with header = Some false; freshness = Some false }
      }
  in
  let pinned_text = image pin_host pinned in
  assert (String.is_substring pinned_text ~substring:("PIN " ^ run_label Fs0_fixture.run_a));
  let titled_pin =
    H.set_local
      pin_host
      pinned.id
      { H.default_local with presentation = { T.inherit_ with header = Some true } }
  in
  let narrow_pin = tile_view titled_pin data pinned ~width:32 ~height:6 |> plain_text in
  assert (String.is_substring narrow_pin ~substring:("PIN " ^ run_label Fs0_fixture.run_a));
  assert (String.is_substring pinned_text ~substring:"Evidence: cached/unverified");
  assert (String.is_substring pinned_text ~substring:"Reported cells (agg.): 50");
  let hidden =
    H.set_local
      pin_host
      pinned.id
      { (H.local pin_host pinned.id) with
        presentation = { T.inherit_ with header = Some false; badge = Some Hidden }
      }
  in
  assert (not (String.is_substring (image hidden pinned) ~substring:"PIN "));
  assert (W.Snapshot.equal (Option.value_exn hidden.registry) pin_registry);
  let nav_policy = H.policy host navigation in
  assert (
    (not (T.show_title nav_policy))
    && (not nav_policy.hints)
    && (not nav_policy.frame)
    && nav_policy.padding = 0);
  let nav = image host navigation in
  assert (
    (not (String.is_substring nav ~substring:"project"))
    && not (String.is_substring nav ~substring:"j/k browse"));
  let selector_host =
    H.set_local host selector.id { H.default_local with cursor = Some "asic/run-11" }
  in
  let candidates = rows selector_host data selector ~width:100 ~height:12 in
  assert (List.length candidates = 4);
  assert (
    List.exists candidates ~f:(fun row ->
      String.is_substring row ~substring:"candidate-11"));
  let global_rows =
    { selector_host with presentation = { T.inherit_ with run_selector_rows = Some 7 } }
  in
  assert (List.length (rows global_rows data selector ~width:100 ~height:12) = 7);
  let more =
    H.set_local
      selector_host
      selector.id
      { (H.local selector_host selector.id) with
        presentation = { T.inherit_ with run_selector_rows = Some 6 }
      }
  in
  assert (List.length (rows more data selector ~width:100 ~height:12) = 6);
  let dimensions = { Dimensions.width = 120; height = 40 } in
  let _, compact, layout = tile_layout host dimensions in
  assert (not compact);
  let cell tile =
    List.find_exn layout ~f:(fun (t, _) -> W.Tile_id.equal t.id tile.W.Tile.id) |> snd
  in
  let select_cell = cell selector
  and synthesis_cell = cell synthesis in
  assert (
    select_cell.width = (cell (find "live-status")).width
    && select_cell.x < synthesis_cell.x
    && select_cell.y > synthesis_cell.y);
  let renamed =
    { registry with
      workspaces =
        List.map registry.workspaces ~f:(fun w ->
          if W.Workspace_id.equal w.id workspace.id
          then { w with name = "Custom title" }
          else w)
    }
  in
  let _, _, renamed_layout = tile_layout (H.receive host renamed) dimensions in
  assert (
    List.equal
      (fun (a, g) (b, h) ->
        W.Tile_id.equal a.W.Tile.id b.W.Tile.id && W.Geometry.equal g h)
      layout
      renamed_layout)
;;

let%test_unit "host semantic terminal rows preserve failure and raw evidence when chrome \
               hidden"
  =
  let initial = W.initial ~session_id:(W.Session_id.of_string "semantic-host") in
  let workspace = List.hd_exn initial.workspaces in
  let registry =
    W.apply
      initial
      (Mutate
         { expected_revision = initial.revision
         ; mutation = P.Definition.apply P.Overview.definition ~workspace:workspace.id
         })
    |> Result.ok
    |> Option.value_exn
  in
  let timing =
    List.find_exn registry.tiles ~f:(fun t -> String.equal t.W.Tile.kind "timing")
  in
  let timing = { timing with binding = Pin_run Fs0_fixture.run_a } in
  let registry =
    { registry with
      tiles =
        List.map registry.tiles ~f:(fun t ->
          if W.Tile_id.equal t.id timing.id then timing else t)
    }
  in
  let terminal : Asic.Terminal_result.t =
    { attempt = "exact"
    ; results_file = "/results"
    ; results_digest = "digest"
    ; operation_status = "completed"
    ; physical_completion = "partial"
    ; acceptance = "fail"
    ; timing_goal = "unknown"
    ; metrics = []
    ; checks =
        [ { name = "drc"
          ; status = "fail"
          ; reason = Some "validated passed is provider prose"
          ; source = None
          }
        ]
    ; evidence =
        "Freshness: provider source\nRun: original raw identity\nfailed pending validated"
    }
  in
  let summary =
    { (List.hd_exn Fs0_fixture.snapshot.summaries) with
      run = Fs0_fixture.run_a
    ; freshness = Validated
    ; terminal = Some terminal
    }
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> Some summary)
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let host = H.receive H.empty registry in
  let local =
    { H.default_local with
      terminal_result =
        Terminal_result_view.State.inspect
          (Terminal_result_view.State.reconcile
             Terminal_result_view.State.empty
             ~run:Fs0_fixture.run_a
             ~summary:(Some summary))
    }
  in
  let host = H.set_local host timing.id local in
  let typed = semantic_rows host data timing ~width:120 ~height:200 |> Option.value_exn in
  assert (
    List.exists typed ~f:(List.exists ~f:(fun span -> E.Role.equal span.E.role Validated)));
  assert (
    List.exists typed ~f:(List.exists ~f:(fun span -> E.Role.equal span.E.role Failed)));
  let hidden =
    H.set_local
      host
      timing.id
      { local with
        presentation =
          { T.inherit_ with
            freshness = Some false
          ; run_reference = Some false
          ; hints = Some false
          }
      }
  in
  let hidden_rows =
    semantic_rows hidden data timing ~width:120 ~height:200 |> Option.value_exn
  in
  let text = String.concat ~sep:"\n" (List.map hidden_rows ~f:E.text) in
  assert (String.is_substring text ~substring:"Freshness: provider source");
  assert (String.is_substring text ~substring:"Run: original raw identity");
  assert (
    not
      (List.exists
         hidden_rows
         ~f:(List.exists ~f:(fun span -> E.Role.equal span.E.role Validated))));
  assert (
    List.exists
      hidden_rows
      ~f:
        (List.exists ~f:(fun span ->
           E.Role.equal span.E.role Plain
           && String.is_substring
                span.text
                ~substring:"validated passed is provider prose")));
  assert (W.Snapshot.equal registry (Option.value_exn hidden.registry));
  let hidden = { hidden with focus = Some timing.id } in
  List.iter
    [ 32, 8; 80, 24 ]
    ~f:(fun (width, height) ->
      let dimensions = { Dimensions.width; height } in
      let bottom = scroll_focused hidden data dimensions ~delta:Int.max_value in
      let stopped = scroll_focused bottom data dimensions ~delta:1 in
      assert (
        (H.local stopped timing.id).terminal_result.offset
        = (H.local bottom timing.id).terminal_result.offset);
      let reverse = scroll_focused stopped data dimensions ~delta:(-1) in
      if (H.local bottom timing.id).terminal_result.offset > 0
      then
        assert (
          not
            (String.equal
               (render bottom data dimensions |> plain_text)
               (render reverse data dimensions |> plain_text))))
;;

let%test_unit "utility navigation filters match input and inspection scroll is bounded" =
  let registry = W.initial ~session_id:(W.Session_id.of_string "utility-rendering") in
  let workspace = List.hd_exn registry.workspaces in
  let registry =
    W.apply
      registry
      (Mutate
         { expected_revision = registry.revision
         ; mutation =
             Create_tile
               { workspace = workspace.id
               ; kind = "workspace-tabs"
               ; geometry = { x = 0; y = 0; width = 32; height = 8 }
               }
         })
    |> Result.ok
    |> Option.value_exn
  in
  let tile = List.last_exn registry.tiles in
  let host = H.receive H.empty registry in
  let host =
    H.set_local
      { host with focus = Some tile.id }
      tile.id
      { H.default_local with filter = "Timing" }
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> None)
    ; status = "connected"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let rows = utility_rows host data tile |> Option.value_exn in
  assert (
    List.equal
      String.equal
      (List.map rows ~f:(fun row -> row.Overview_tiles.label))
      [ "Timing" ]);
  let host = H.browse_workspaces host tile.id ~delta:1 in
  assert (String.equal (Option.value_exn (H.workspace_cursor host tile.id)).name "Timing");
  let registry =
    { registry with
      tiles =
        List.map registry.tiles ~f:(fun t ->
          if W.Tile_id.equal t.id tile.id then { t with kind = "live-status" } else t)
    }
  in
  let host = H.receive host registry in
  let host = H.set_local host tile.id { H.default_local with utility_detail = true } in
  let dimensions = { Dimensions.width = 32; height = 8 } in
  let bottom = scroll_focused host data dimensions ~delta:Int.max_value in
  assert ((H.local bottom tile.id).scroll > 0);
  let stopped = scroll_focused bottom data dimensions ~delta:1 in
  assert ((H.local stopped tile.id).scroll = (H.local bottom tile.id).scroll);
  let reverse = scroll_focused stopped data dimensions ~delta:(-1) in
  assert ((H.local reverse tile.id).scroll = (H.local stopped tile.id).scroll - 1)
;;

let%test_unit "checklist follows exact run and pin with selected-stage detail and \
               aggregate checks"
  =
  let initial = W.initial ~session_id:(W.Session_id.of_string "stage-frames") in
  let workspace = (List.hd_exn initial.workspaces).id in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let registry =
    apply
      initial
      (Create_tile
         { workspace
         ; kind = "stage-checklist"
         ; geometry = { x = 0; y = 0; width = 64; height = 20 }
         })
  in
  let following = List.last_exn registry.tiles in
  let registry =
    apply
      registry
      (Create_tile
         { workspace
         ; kind = "stage-checklist"
         ; geometry = { x = 0; y = 0; width = 64; height = 20 }
         })
  in
  let pinned = List.last_exn registry.tiles in
  let registry =
    apply
      registry
      (Set_tile_binding { tile = pinned.id; binding = Pin_run Fs0_fixture.run_a })
  in
  let stage id status reason : Asic.Stage.t =
    { id; name = id; status; requested = true; reason; action = None }
  in
  let terminal : Asic.Terminal_result.t =
    { attempt = "attempt"
    ; results_file = "results"
    ; results_digest = "digest"
    ; operation_status = "completed"
    ; physical_completion = "partial"
    ; acceptance = "unknown"
    ; timing_goal = "unknown"
    ; metrics = []
    ; checks =
        [ { name = "drc"
          ; status = "fail"
          ; reason = Some "aggregate reason"
          ; source = Some "report"
          }
        ]
    ; evidence = "{}"
    }
  in
  let snapshot =
    { Fs0_fixture.snapshot with
      summaries =
        List.map Fs0_fixture.snapshot.summaries ~f:(fun s ->
          { s with terminal = Some terminal })
    ; preview =
        Some
          { selection =
              { flow = "ordinary"
              ; profile = "default"
              ; endpoint = "placement"
              ; assignments = []
              }
          ; plan_identity = "ready-plan"
          ; plan_json = "{}"
          }
    ; runs =
        [ { (Fs0_fixture.run Fs0_fixture.run_a) with
            stages =
              [ stage "placement" Completed None
              ; stage "routing" Failed (Some "route reason")
              ]
          }
        ; { (Fs0_fixture.run Fs0_fixture.run_b) with
            stages = [ stage "placement" Running None ]
          }
        ]
    }
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = run_lines (Some snapshot)
    ; run_context = request_context (Some snapshot)
    ; summary =
        (fun run -> List.find snapshot.summaries ~f:(fun s -> Run_ref.equal s.run run))
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = Some snapshot
    }
  in
  let select host run =
    let mutation = H.select_run host (Some run) |> Option.value_exn in
    H.receive host (apply (Option.value_exn host.H.registry) mutation)
  in
  let host = select (H.receive H.empty registry) Fs0_fixture.run_a in
  let stages = Overview_tiles.observed_stages ~asic:data.asic ~run:Fs0_fixture.run_a in
  let host = H.browse_stages host following.id ~run:Fs0_fixture.run_a ~stages ~delta:1 in
  let host =
    H.set_local
      host
      following.id
      { (H.local host following.id) with utility_detail = true }
  in
  let detail =
    utility_rows host data following
    |> Option.value_exn
    |> Overview_tiles.inspection_lines
    |> String.concat ~sep:"\n"
  in
  List.iter
    [ "routing: failed"
    ; "Stage ID: routing"
    ; "route reason"
    ; "Action: unavailable"
    ; "Accept (agg.)"
    ; "Check drc (aggregate): fail"
    ; "aggregate reason"
    ; "Source: report"
    ]
    ~f:(fun text -> assert (String.is_substring detail ~substring:text));
  assert (not (String.is_substring detail ~substring:"Matching project preview"));
  assert (not (String.is_substring detail ~substring:"placement: completed"));
  let host = select host Fs0_fixture.run_b in
  let projected tile =
    utility_rows host data tile
    |> Option.value_exn
    |> List.filter_map ~f:(fun row ->
      Option.map row.Overview_tiles.status ~f:(fun _ -> row.value))
  in
  assert (List.equal String.equal (projected following) [ "running" ]);
  assert (List.equal String.equal (projected pinned) [ "completed"; "failed" ]);
  let compact_host =
    H.set_local
      host
      following.id
      { H.default_local with
        presentation = { T.inherit_ with header = Some false; hints = Some true }
      }
  in
  let compact =
    tile_view compact_host data following ~width:40 ~height:10 |> plain_text
  in
  List.iter [ "placement: running" ] ~f:(fun text ->
    assert (String.is_substring compact ~substring:text));
  let missing = { data with asic = None } in
  let fallback = utility_rows host missing following |> Option.value_exn in
  assert (
    List.for_all fallback ~f:(fun row ->
      Option.value_map
        row.Overview_tiles.status
        ~default:true
        ~f:(Overview_tiles.Status.equal Unknown)));
  (* Six stages plus run identity, summaries and hints exceed an ordinary Overview
     viewport. Selection must survive both browsing and a stale manual scroll. *)
  let selection = (Option.value_exn snapshot.preview).selection in
  let stages =
    List.init 6 ~f:(fun i ->
      { (stage (sprintf "stage-%d" i) Pending None) with action = Some selection })
  in
  let snapshot =
    { snapshot with
      runs =
        List.map snapshot.runs ~f:(fun run ->
          if Run_ref.equal run.run Fs0_fixture.run_b then { run with stages } else run)
    }
  in
  let data = { data with asic = Some snapshot } in
  let host =
    H.browse_stages compact_host following.id ~run:Fs0_fixture.run_b ~stages ~delta:5
  in
  let key = List.hd_exn (Plain_rpc.keys (Plan selection) snapshot) in
  let snapshot =
    { snapshot with
      operations =
        [ { key; kind = "plan"; state = "completed"; run = None; error = None } ]
    }
  in
  let host =
    { host with planned_run = Planned_run.receive host.planned_run ~revision:1 snapshot }
  in
  assert (Option.is_some (checklist_preview host data following));
  List.iter [ 8; 9; 10; 12; 14 ] ~f:(fun height ->
    List.iter [ 0; 99 ] ~f:(fun scroll ->
      let host =
        H.set_local
          host
          following.id
          { (H.local host following.id) with presentation = T.inherit_; scroll }
      in
      let text = tile_view host data following ~width:40 ~height |> plain_text in
      assert (String.is_substring text ~substring:"stage-5: pending")));
  let top =
    H.browse_stages host following.id ~run:Fs0_fixture.run_b ~stages ~delta:(-5)
  in
  let top =
    H.set_local top following.id { (H.local top following.id) with scroll = 99 }
  in
  assert (
    String.is_substring
      (tile_view top data following ~width:40 ~height:10 |> plain_text)
      ~substring:"stage-0: pending");
  let ready = tile_view host data following ~width:40 ~height:14 |> plain_text in
  assert (String.is_substring ready ~substring:"Space c c: Launch");
  assert (String.is_substring ready ~substring:"or Launch and view");
  assert (Option.is_none (checklist_preview host data pinned));
  List.iter
    [ { selection with endpoint = "unrelated" }
    ; { selection with flow = "other-flow" }
    ; { selection with profile = "other-profile" }
    ; { selection with assignments = [ "different=value" ] }
    ]
    ~f:(fun selection ->
      let unrelated =
        { data with
          asic =
            Some
              { snapshot with
                preview =
                  Option.map snapshot.preview ~f:(fun preview ->
                    { preview with selection })
              }
        }
      in
      assert (Option.is_none (checklist_preview host unrelated following));
      let text = tile_view host unrelated following ~width:40 ~height:14 |> plain_text in
      assert (not (String.is_substring text ~substring:"Space c c: Launch")))
;;

let%test_unit "simulation tile renders project scope and independent selection at real \
               cell bounds"
  =
  let s = W.initial ~session_id:(W.Session_id.of_string "simulation-render") in
  let s =
    W.apply
      s
      (Mutate
         { expected_revision = s.revision
         ; mutation =
             Create_tile
               { workspace = (List.hd_exn s.workspaces).id
               ; kind = "simulation"
               ; geometry = { x = 0; y = 0; width = 80; height = 20 }
               }
         })
    |> Result.ok
    |> Option.value_exn
  in
  let tile = List.last_exn s.tiles in
  let host = H.receive H.empty s in
  let host =
    H.set_local
      host
      tile.id
      { H.default_local with
        simulation =
          { Simulation_view.empty with
            notice = Some "Verified simulation bytes retained: /host/trace.vcd"
          }
      }
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> None)
    ; asic = None
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    }
  in
  List.iter
    [ 80, 24; 120, 40; 32, 8; 1, 1 ]
    ~f:(fun (width, height) ->
      let view = tile_view host data tile ~width ~height in
      assert (View.width view = width && View.height view = height));
  let text = tile_view host data tile ~width:120 ~height:24 |> plain_text in
  assert (String.is_substring text ~substring:"Structured simulation");
  assert (not (String.is_substring text ~substring:"[project]"));
  let explicit =
    H.set_local
      host
      tile.id
      { (H.local host tile.id) with
        presentation = { T.inherit_ with badge = Some Always }
      }
  in
  assert (
    String.is_substring
      (tile_view explicit data tile ~width:120 ~height:24 |> plain_text)
      ~substring:"[project]");
  assert (String.is_substring text ~substring:"/host/trace.vcd");
  assert (not (String.is_substring text ~substring:"No run selected"));
  let local = H.local host tile.id in
  let host =
    H.set_local
      { host with focus = Some tile.id }
      tile.id
      { local with
        simulation =
          { local.simulation with notice = Some (String.make 512 'x' ^ "HORIZONTAL-END") }
      }
  in
  let dimensions : Dimensions.t = { width = 32; height = 8 } in
  let bottom = scroll_focused host data dimensions ~delta:Int.max_value in
  assert ((H.local bottom tile.id).scroll > 0);
  assert (
    String.is_substring
      (render bottom data dimensions |> plain_text)
      ~substring:"HORIZONTAL-END");
  let stopped = scroll_focused bottom data dimensions ~delta:1 in
  assert ((H.local stopped tile.id).scroll = (H.local bottom tile.id).scroll);
  let back = scroll_focused stopped data dimensions ~delta:(-1) in
  assert ((H.local back tile.id).scroll = (H.local stopped tile.id).scroll - 1);
  let top = scroll_focused bottom data dimensions ~delta:Int.min_value in
  assert ((H.local top tile.id).scroll = 0)
;;

let%test_unit "fit geometry fills tracks, keeps thirteen tiles visible, and falls back" =
  let grid ~width ~height ~count =
    match Fit_layout.compute ~width ~height ~count with
    | Compact -> assert false
    | Grid cells ->
      assert (List.length cells = count);
      List.iteri cells ~f:(fun i (a : W.Geometry.t) ->
        assert (a.x >= 0 && a.y >= 0 && a.width >= 24 && a.height >= 6);
        assert (a.x + a.width <= width && a.y + a.height <= height);
        List.iter
          (List.drop cells (i + 1))
          ~f:(fun (b : W.Geometry.t) ->
            assert (
              a.x + a.width < b.x
              || b.x + b.width < a.x
              || a.y + a.height < b.y
              || b.y + b.height < a.y)));
      assert (List.exists cells ~f:(fun g -> g.x + g.width = width));
      assert (List.exists cells ~f:(fun g -> g.y + g.height = height));
      cells
  in
  let two = grid ~width:120 ~height:40 ~count:2 in
  assert (List.sum (module Int) two ~f:(fun g -> g.width) = 119);
  assert (List.for_all two ~f:(fun g -> g.y = 0 && g.height = 40));
  ignore (grid ~width:120 ~height:40 ~count:13 : W.Geometry.t list);
  List.iter
    [ 24, 6; 32, 6; 1, 1; 120, 5 ]
    ~f:(fun (width, height) ->
      match Fit_layout.compute ~width ~height ~count:2 with
      | Compact -> ()
      | Grid _ -> assert false)
;;

let%test_unit "stage evidence is scoped honestly and never borrows synthesis counts" =
  let known =
    { Fs0_fixture.snapshot with
      runs =
        List.map Fs0_fixture.snapshot.runs ~f:(fun execution ->
          { execution with
            selection =
              Some
                { Asic.Selection.flow = "fixture"
                ; profile = "fixture"
                ; endpoint = "synthesis"
                ; assignments = []
                }
          })
    }
  in
  let text snapshot kind =
    run_lines (Some snapshot) Fs0_fixture.run_a kind |> String.concat ~sep:"\n"
  in
  List.iter [ "placement"; "cts"; "routing" ] ~f:(fun kind ->
    let requested = text known kind in
    assert (
      String.is_substring
        requested
        ~substring:"No terminal result imported; inspect exact finalization reference");
    assert (String.is_substring requested ~substring:"Request endpoint: synthesis");
    let unknown = text Fs0_fixture.snapshot kind in
    assert (String.is_substring unknown ~substring:"Request scope: unknown");
    assert (String.is_substring unknown ~substring:"No terminal result imported"));
  let physical =
    { known with
      runs =
        List.map known.runs ~f:(fun execution ->
          { execution with
            selection =
              Option.map execution.selection ~f:(fun selection ->
                { selection with endpoint = "physical" })
          })
    }
  in
  List.iter [ "placement"; "cts"; "routing"; "finalization"; "timing" ] ~f:(fun kind ->
    let output = text physical kind in
    assert (String.is_substring output ~substring:"Request endpoint: physical");
    assert (String.is_substring output ~substring:"No terminal result imported");
    assert (not (String.is_substring output ~substring:"not requested")));
  List.iter
    [ "placement"; "cts"; "routing"; "checks"; "finalization"; "timing"; "unknown" ]
    ~f:(fun kind ->
      let output = text known kind in
      assert (not (String.is_substring output ~substring:"Cell count"));
      assert (not (String.is_substring output ~substring:"NAND2"));
      assert (not (String.is_substring output ~substring:"PASS"));
      assert (String.is_substring output ~substring:"acceptance: not evaluated"));
  assert (
    String.is_substring
      (text known "checks")
      ~substring:"Synthesis diagnostics unavailable; explicit Refresh needed");
  let with_metrics =
    { known with
      summaries =
        List.map known.summaries ~f:(fun summary ->
          { summary with
            metrics =
              [ { Asic.Metric.key = "synthesis__check_error__count"
                ; label = "Synthesis check errors"
                ; value = Some 0.
                ; unit_ = Some "count"
                ; availability = "available"
                ; source = Some "/private/checkpoint/check.json#errors"
                }
              ]
          })
    }
  in
  let checks = text with_metrics "checks" in
  assert (
    String.is_substring checks ~substring:"Synthesis check errors: 0 count [available]");
  assert (String.is_substring checks ~substring:"not DRC/LVS");
  assert (
    String.is_substring checks ~substring:"Zero diagnostic counts do not imply signoff");
  assert (String.is_substring checks ~substring:"Acceptance (reported): not evaluated");
  assert (not (String.is_substring checks ~substring:"/private/checkpoint"));
  List.iter [ "placement"; "cts"; "routing"; "finalization" ] ~f:(fun kind ->
    assert (
      not
        (String.is_substring (text with_metrics kind) ~substring:"Synthesis check errors")));
  assert (
    String.is_substring
      (text known "finalization")
      ~substring:"No terminal result imported");
  assert (
    String.is_substring (text known "timing") ~substring:"No terminal result imported");
  assert (String.is_substring (text known "synthesis") ~substring:"Cell count: 50")
;;

let%test_unit "imported clock configuration retains explicit known or unknown request \
               scope"
  =
  let clock : Asic.Metric.t =
    { key = "declared_clock_period"
    ; label = "Declared clock clk_i period"
    ; value = Some 10.
    ; unit_ = Some "ns"
    ; availability = "available"
    ; source = Some "/private/recorded/config.json#clock"
    }
  in
  let terminal : Asic.Terminal_result.t =
    { attempt = "/private/returned-operation"
    ; results_file = "/private/results.json"
    ; results_digest = "exact-results-digest"
    ; operation_status = "completed"
    ; physical_completion = "unknown"
    ; acceptance = "unknown"
    ; timing_goal = "unknown"
    ; metrics = [ clock ]
    ; checks = []
    ; evidence = "original terminal evidence"
    }
  in
  let snapshot =
    { Fs0_fixture.snapshot with
      summaries =
        List.map Fs0_fixture.snapshot.summaries ~f:(fun summary ->
          { summary with terminal = Some terminal })
    }
  in
  let output = run_lines (Some snapshot) Fs0_fixture.run_a "cts" in
  assert (
    List.mem output "Declared clock clk_i period: 10 ns [available]" ~equal:String.equal);
  assert (
    List.mem output "Request scope: unknown (selection unavailable)" ~equal:String.equal);
  let snapshot =
    { snapshot with
      runs =
        List.map snapshot.runs ~f:(fun execution ->
          { execution with
            selection =
              Some
                { Asic.Selection.flow = "fixture"
                ; profile = "fixture"
                ; endpoint = "physical"
                ; assignments = []
                }
          })
    }
  in
  assert (
    List.mem
      (run_lines (Some snapshot) Fs0_fixture.run_a "cts")
      "Request endpoint: physical"
      ~equal:String.equal);
  let summary = List.hd_exn snapshot.summaries in
  let output =
    Terminal_result_view.rows
      ~request_context:(request_context (Some snapshot) summary.run)
      Terminal_result_view.State.empty
      ~run:summary.run
      ~summary:(Some summary)
      ~kind:"cts"
      ~width:100
      ~height:100
  in
  assert (List.mem output "Request endpoint: physical" ~equal:String.equal);
  assert (
    List.mem
      output
      "Recorded methodology configuration, not measured CTS"
      ~equal:String.equal)
;;

let%test_unit "fit renders all thirteen tiles across skins and distinguishes loading \
               from empty"
  =
  let initial = W.initial ~session_id:(W.Session_id.of_string "fit-frames") in
  let workspace = (List.hd_exn initial.workspaces).id in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let empty =
    List.fold initial.tiles ~init:initial ~f:(fun s tile ->
      apply s (Set_tile_hidden { tile = tile.id; hidden = true }))
  in
  let kinds = List.init 13 ~f:(fun i -> sprintf "fixture%02d" i) in
  let loaded =
    List.fold kinds ~init:empty ~f:(fun s kind ->
      apply
        s
        (Create_tile
           { workspace; kind; geometry = { x = 0; y = 0; width = 40; height = 6 } }))
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> None)
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let frame host = render host data { width = 120; height = 40 } |> plain_text in
  assert (String.is_substring (frame H.empty) ~substring:"Loading workspace...");
  let empty_text = frame (H.receive H.empty empty) in
  assert (String.is_substring empty_text ~substring:"Apply default layout");
  assert (not (String.is_substring empty_text ~substring:"Loading workspace"));
  List.iter appearance_cases ~f:(fun appearance ->
    let host = { (H.receive H.empty loaded) with appearance; layout_mode = H.Fit } in
    let text = frame host |> String.lowercase in
    List.iter kinds ~f:(fun kind -> assert (String.is_substring text ~substring:kind));
    let compact = render host data { width = 32; height = 8 } |> plain_text in
    assert (String.is_substring compact ~substring:"Compact: focused tile only"))
;;

let%test_unit "actual renderer clips cell geometry and distinguishes run and project \
               scope"
  =
  let s = W.initial ~session_id:(W.Session_id.of_string "render-test") in
  let workspace = (List.hd_exn s.workspaces).id in
  let s =
    W.apply
      s
      (Mutate
         { expected_revision = s.revision
         ; mutation =
             Create_tile
               { workspace
               ; kind = "project-tests"
               ; geometry = { x = 0; y = 0; width = 64; height = 8 }
               }
         })
    |> Result.ok
    |> Option.value_exn
  in
  let host = H.receive H.empty s in
  let test_tile = List.last_exn s.tiles in
  let host = { host with focus = Some test_tile.id } in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [ "No measurement" ])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> None)
    ; status = "fixture"
    ; environment = "test"
    ; asic_lines = [ "Explicit synthetic rendering fixture" ]
    ; asic = None
    }
  in
  List.iter appearance_cases ~f:(fun appearance ->
    let host = { host with appearance } in
    List.iter
      [ 80, 24; 120, 40; 32, 8; 1, 1 ]
      ~f:(fun (width, height) ->
        let view = render host data { width; height } in
        assert (View.width view = width);
        assert (View.height view = height));
    let tile = tile_view host data test_tile ~width:64 ~height:12 in
    let text = plain_text tile in
    assert (View.width tile = 64 && View.height tile = 12);
    assert (String.is_substring text ~substring:"Project tests (not ASIC-run scoped)");
    (match appearance.icons with
     | None_ | Ascii -> assert (String.for_all text ~f:(fun ch -> Char.to_int ch < 128))
     | Unicode -> ());
    let local = H.local host test_tile.id in
    let without_headers =
      H.set_local
        host
        test_tile.id
        { local with presentation = { local.presentation with header = Some false } }
    in
    let text =
      tile_view without_headers data test_tile ~width:64 ~height:12 |> plain_text
    in
    assert (String.is_substring text ~substring:"Project tests (not ASIC-run scoped)"));
  let skins =
    List.map Appearance.Preset.all ~f:(fun preset ->
      let appearance = { Appearance.default with preset; icons = Unicode } in
      tile_view { host with appearance } data test_tile ~width:64 ~height:12 |> plain_text)
  in
  assert (List.length (List.dedup_and_sort skins ~compare:String.compare) = 5);
  let view = render host data { width = 80; height = 24 } in
  let buffer = Buffer.create 2048 in
  Notty.Render.to_buffer
    buffer
    Notty.Cap.dumb
    (0, 0)
    (80, 24)
    (View.Private.notty_image view);
  assert (
    String.is_substring
      (Buffer.contents buffer)
      ~substring:"Project tests (not ASIC-run scoped)");
  let unicode = box ~width:3 ~height:1 (View.text "界界é") in
  assert (View.width unicode = 3);
  assert (View.height unicode = 1);
  let wrapped = wrap_cells ~width:3 "界界é" in
  assert (String.equal (String.concat wrapped) "界界é");
  List.iter wrapped ~f:(fun line -> assert (View.width (View.text line) <= 3))
;;

let%test_unit "artifact overlay cannot render retained page after tile binding changes" =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "artifact-scope") in
  let tile = List.hd_exn snapshot.tiles in
  let bind snapshot run =
    W.apply
      snapshot
      (Mutate
         { expected_revision = snapshot.W.Snapshot.revision
         ; mutation = Set_tile_binding { tile = tile.id; binding = Pin_run run }
         })
    |> Result.ok
    |> Option.value_exn
  in
  let snapshot = bind snapshot Fs0_fixture.run_a in
  let reference : Asic_artifact.Reference.t =
    { id = "report"
    ; run = Fs0_fixture.run_a
    ; terminal_attempt = "attempt-a"
    ; label = "Report"
    ; path = "/daemon/report"
    ; sha256 = "hash-a"
    ; size = 24
    ; kind = "text"
    }
  in
  let page : Asic_artifact.Page.t =
    { artifact_id = reference.id
    ; run = reference.run
    ; terminal_attempt = reference.terminal_attempt
    ; sha256 = reference.sha256
    ; offset = 0
    ; limit = Artifact_view.limit
    ; next_offset = 24
    ; eof = true
    ; text = "PRIVATE-RUN-A-PAGE"
    ; error = None
    }
  in
  let inspector =
    { (Artifact_view.create ~scope:reference.run reference.run) with
      catalog = [ reference ]
    ; reading = Some { artifact = reference; offset = 0; previous = []; page = Some page }
    }
  in
  let host = H.receive H.empty snapshot in
  let host =
    H.set_local
      { host with focus = Some tile.id }
      tile.id
      { H.default_local with artifacts = Some inspector }
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> None)
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let frame host = render host data { width = 100; height = 30 } |> plain_text in
  assert (String.is_substring (frame host) ~substring:page.text);
  (* Deliberately retain old local state: the renderer independently checks binding. *)
  let changed = { host with registry = Some (bind snapshot Fs0_fixture.run_b) } in
  assert (Option.is_none (artifact_inspector changed tile));
  assert (not (String.is_substring (frame changed) ~substring:page.text))
;;

let%test_unit "inspection overlay and input share full viewport and visibly reverse from \
               bottom"
  =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "inspection-viewport") in
  let tile = List.hd_exn snapshot.tiles in
  let run = Fs0_fixture.run_a in
  let bind snapshot run =
    W.apply
      snapshot
      (Mutate
         { expected_revision = snapshot.W.Snapshot.revision
         ; mutation = Set_tile_binding { tile = tile.id; binding = Pin_run run }
         })
    |> Result.ok
    |> Option.value_exn
  in
  let snapshot = bind snapshot run in
  let row : Asic_inspection.Row.t =
    { id = "row"
    ; category = "path"
    ; producer = "sta"
    ; corner = None
    ; group = None
    ; name = "path"
    ; value = Some 0.
    ; unit_ = Some "ns"
    ; status = "ok"
    ; source = "/report"
    ; fields = []
    }
  in
  let index : Asic_inspection.Index.t =
    { run
    ; execution_file = "/execution"
    ; execution_sha256 = "sha"
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "digest"
    ; rows = [ row ]
    ; diagnostics = []
    ; truncated = false
    ; cached_unverified = false
    }
  in
  let detail : Asic_inspection.Detail.t =
    { run
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "digest"
    ; row_id = "row"
    ; text =
        String.concat
          ~sep:"\n"
          (List.init 120 ~f:(fun i -> sprintf "detail-%03d %s" i (String.make 130 'x')))
    ; error = None
    }
  in
  let inspector =
    { (Inspection_view.create ~scope:run ~run ~domain:"timing" ~stage:"signoff" ()) with
      index = Some index
    ; selected = Some "row"
    ; requested = Some ("digest", "row")
    ; detail = Some detail
    }
  in
  let host = H.receive H.empty snapshot in
  let host = { host with focus = Some tile.id } in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> assert false)
    ; run_lines = (fun _ _ -> assert false)
    ; run_context = (fun _ -> assert false)
    ; summary = (fun _ -> assert false)
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  List.iter
    [ { Dimensions.width = 120; height = 40 }; { width = 112; height = 40 } ]
    ~f:(fun dimensions ->
      let width, height = inspection_viewport dimensions in
      assert (width = dimensions.width && height = dimensions.height);
      let step state action =
        let state, operation = Inspection_view.input ~width ~height state action in
        assert (Option.is_none operation);
        Option.value_exn state
      in
      let bottom =
        List.fold (List.init 1000 ~f:Fn.id) ~init:inspector ~f:(fun state _ ->
          step state Down)
      in
      let up = step bottom Up in
      assert (up.scroll = bottom.scroll - 1);
      let host_for inspection =
        H.set_local host tile.id { H.default_local with inspection = Some inspection }
      in
      let frame state = render (host_for state) data dimensions in
      assert (View.width (frame bottom) = width && View.height (frame bottom) = height);
      assert (not (String.equal (plain_text (frame bottom)) (plain_text (frame up))));
      (* Opening the palette must preserve this actual inspector, not rebuild a different
         workspace underneath. Data callbacks above deliberately fail if the workspace
         renderer is accidentally entered. *)
      let source = host_for bottom in
      let opened =
        List.fold [ ' '; 'c'; 'c' ] ~init:source ~f:(fun host ch ->
          fst (H.input host (Character ch) ~commands:[]))
      in
      let overlay = render opened data dimensions in
      let b = Palette_view.bounds ~width ~height in
      let top image = View.crop ~b:(height - b.y) image |> plain_text in
      assert (b.y > 0 && String.equal (top overlay) (top (frame bottom)));
      let returned = fst (H.input opened Escape ~commands:[]) in
      assert (
        String.equal
          (plain_text (render returned data dimensions))
          (plain_text (frame bottom)));
      let stale =
        { (host_for bottom) with registry = Some (bind snapshot Fs0_fixture.run_b) }
      in
      assert (Option.is_none (inspection_explorer stale tile)))
;;

let%test_unit "unterminated inspection paste keeps query and rejection visible without \
               chrome after polling"
  =
  let open Bonsai_term.Event in
  let registry =
    W.initial ~session_id:(W.Session_id.of_string "inspection-paste-visible")
  in
  let tile = List.hd_exn registry.tiles in
  let inspector =
    { (Inspection_view.create ~run:Fs0_fixture.run_a ~domain:"timing" ~stage:"signoff" ()) with
      editing = true
    }
  in
  let host = H.receive H.empty registry in
  let host =
    H.set_local
      { host with focus = Some tile.id; chrome = false }
      tile.id
      { H.default_local with inspection = Some inspector }
  in
  let send host event =
    match H.route_inspection_filter_event host event with
    | H.Filter_handled host -> host
    | _ -> assert false
  in
  let host = send host (Paste `Start) in
  let host =
    String.fold "endpoint/Q jtr" ~init:host ~f:(fun host c ->
      send host (Key_press { key = ASCII c; mods = [] }))
  in
  let host = send host (Key_press { key = Enter; mods = [] }) in
  let host = H.receive host registry in
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> assert false)
    ; run_lines = (fun _ _ -> assert false)
    ; run_context = (fun _ -> assert false)
    ; summary = (fun _ -> assert false)
    ; status = "fixture"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let frame host = render host data { width = 120; height = 40 } |> plain_text in
  List.iter
    [ host; { host with focus = None } ]
    ~f:(fun host ->
      let text = frame host in
      assert (String.is_substring text ~substring:"FILTER PASTE ACTIVE");
      assert (String.is_substring text ~substring:"filter=endpoint/Q jtr");
      assert (String.is_substring text ~substring:"rejects controls"));
  let host = send host (Paste `End) in
  assert (not (String.is_substring (frame host) ~substring:"FILTER PASTE ACTIVE"))
;;

let%test_unit "filter input remains visible after polling and with chrome hidden" =
  let snapshot = W.initial ~session_id:(W.Session_id.of_string "filter-visible") in
  let tile = List.hd_exn snapshot.tiles in
  let host = H.receive H.empty snapshot in
  let host = H.set_local host tile.id { H.default_local with filter = "no-match" } in
  let host = H.receive { host with editing_filter = true; chrome = false } snapshot in
  assert (String.is_empty host.notice);
  let data =
    { project = None
    ; jobs = []
    ; runs = []
    ; log_lines = (fun _ -> [])
    ; run_lines = (fun _ _ -> [])
    ; run_context = (fun _ -> [])
    ; summary = (fun _ -> None)
    ; status = "connected"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = None
    }
  in
  let text = render host data { width = 120; height = 40 } |> plain_text in
  List.iter
    [ "FILTER INPUT"; "Enter/Esc finish"; "Ctrl-U clear"; "no-match" ]
    ~f:(fun label -> assert (String.is_substring text ~substring:label))
;;

let%test_unit "warm synthesis run switch renders 73 while pinned reference retains 50, \
               including compact frames"
  =
  let s = W.initial ~session_id:(W.Session_id.of_string "synthesis-frames") in
  let workspace = (List.hd_exn s.workspaces).id in
  let apply s mutation =
    W.apply s (Mutate { expected_revision = s.W.Snapshot.revision; mutation })
    |> Result.ok
    |> Option.value_exn
  in
  let s = apply s (Set_tile_hidden { tile = (List.hd_exn s.tiles).id; hidden = true }) in
  let geometry : W.Geometry.t = { x = 0; y = 0; width = 64; height = 10 } in
  let s = apply s (Create_tile { workspace; kind = "synthesis"; geometry }) in
  let following = (List.last_exn s.tiles).id in
  let s = apply s (Create_tile { workspace; kind = "synthesis"; geometry }) in
  let pinned = (List.last_exn s.tiles).id in
  let s =
    apply s (Set_tile_binding { tile = pinned; binding = Pin_run Fs0_fixture.run_a })
  in
  let select host run =
    let s = Option.value_exn host.H.registry in
    let mutation = H.select_run host (Some run) |> Option.value_exn in
    H.receive host (apply s mutation)
  in
  let data =
    { project = None
    ; jobs = []
    ; runs = List.map Fs0_fixture.snapshot.runs ~f:(fun run -> run.run, run.status)
    ; log_lines = (fun _ -> [])
    ; run_lines = run_lines (Some Fs0_fixture.snapshot)
    ; run_context = request_context (Some Fs0_fixture.snapshot)
    ; summary =
        (fun run ->
          List.find Fs0_fixture.snapshot.summaries ~f:(fun s -> Run_ref.equal s.run run))
    ; status = "SYNTHETIC FIXTURE"
    ; environment = "fixture"
    ; asic_lines = []
    ; asic = Some Fs0_fixture.snapshot
    }
  in
  let frame host width height =
    let view = render host data { width; height } in
    let buffer = Buffer.create (width * height) in
    Notty.Render.to_buffer
      buffer
      Notty.Cap.dumb
      (0, 0)
      (width, height)
      (View.Private.notty_image view);
    Buffer.contents buffer
  in
  let has frame text = String.is_substring frame ~substring:text in
  let host = select (H.receive H.empty s) Fs0_fixture.run_a in
  let host = { host with focus = Some following } in
  (* Overview is compact by default. Counts and provenance survive a run switch; cell
     tables remain an explicit Cells mode instead of consuming summary rows. *)
  let before = frame host 32 10 in
  assert (has before "Reported cells (agg.): 50");
  assert (has before "Evidence: cached/unverified");
  assert (has before "Cell breakdown: 2 reported");
  assert (not (has before "/explicit/synthetic"));
  let host = select host Fs0_fixture.run_b in
  let registry_before = Option.value_exn host.registry |> W.Snapshot.sexp_of_t in
  List.iter appearance_cases ~f:(fun appearance ->
    let host = { host with appearance } in
    let both = frame host 128 24 in
    assert (has both "Reported cells (agg.): 73" && has both "Reported cells (agg.): 50");
    assert (has both "run asic/fixture-B" && has both "PIN asic/fixture-A");
    let small = frame host 32 10 in
    assert (has small "Reported cells (agg.): 73");
    assert (has small "Evidence: cached/unverified");
    assert (has small "Cell breakdown: 2 reported");
    assert (not (has small "/explicit/synthetic"));
    let pinned_frame = frame { host with focus = Some pinned } 32 8 in
    assert (has pinned_frame "Reported cells (agg.): 50");
    assert (not (has pinned_frame "Reported cells (agg.): 73"));
    assert (
      Sexp.equal registry_before (Option.value_exn host.registry |> W.Snapshot.sexp_of_t)));
  let both = frame host 128 24 in
  assert (has both "Reported cells (agg.): 73" && has both "Reported cells (agg.): 50");
  assert (has both "run asic/fixture-B" && has both "PIN asic/fixture-A");
  let compact_following = frame host 32 8 in
  assert (has compact_following "Reported cells (agg.): 73");
  assert (not (has compact_following "Reported cells (agg.): 50"));
  let compact_pinned = frame { host with focus = Some pinned } 32 8 in
  assert (has compact_pinned "Reported cells (agg.): 50");
  assert (not (has compact_pinned "Reported cells (agg.): 73"));
  let _, intents =
    Asic_intents.plan
      Asic_intents.empty
      ~now:Time_ns.epoch
      Fs0_fixture.snapshot
      ~visible:(H.evidence_runs host)
  in
  assert (List.is_empty intents);
  let detail =
    H.set_local
      host
      following
      { (H.local host following) with
        synthesis =
          Synthesis_view.State.set_mode (H.local host following).synthesis Evidence
      }
  in
  List.iter [ H.Fit; H.Preferred ] ~f:(fun layout_mode ->
    let detail = { detail with layout_mode } in
    let small = { Dimensions.width = 32; height = 8 } in
    let large = { Dimensions.width = 128; height = 24 } in
    let bottom = scroll_focused detail data small ~delta:Int.max_value in
    let stopped =
      List.fold (List.init 100 ~f:Fn.id) ~init:bottom ~f:(fun host _ ->
        scroll_focused host data small ~delta:1)
    in
    let reverse = scroll_focused stopped data small ~delta:(-1) in
    assert (not (String.equal (frame bottom 32 8) (frame reverse 32 8)));
    let resized = scroll_focused stopped data large ~delta:(-1) in
    let expected =
      scroll_focused detail data large ~delta:Int.max_value
      |> fun host -> scroll_focused host data large ~delta:(-1)
    in
    assert (String.equal (frame resized 128 24) (frame expected 128 24));
    assert (
      Synthesis_view.Mode.equal
        (Synthesis_view.State.mode (H.local resized pinned).synthesis)
        Summary));
  let host = select host Fs0_fixture.run_a in
  assert (has (frame host 32 8) "Reported cells (agg.): 50")
;;

let%test_unit "custom and unknown presets honor generic Fit without rewriting geometry" =
  let ok = function
    | Ok value -> value
    | Error error -> raise_s [%sexp (error : V1.Error.t)]
  in
  List.iter [ None; Some "future-preset" ] ~f:(fun preset ->
    let initial = W.initial ~session_id:(W.Session_id.of_string "custom-fit") in
    let template =
      { Workspace_template.generic with
        preset
      ; views =
          List.mapi Workspace_template.generic.views ~f:(fun i view ->
            { view with
              hidden = i = 1
            ; geometry = { x = i * 100; y = 300; width = 400; height = 200 }
            })
      }
    in
    let registry =
      W.apply
        initial
        (Mutate
           { expected_revision = initial.revision
           ; mutation =
               Instantiate_template
                 { window = (List.hd_exn initial.windows).id; template }
           })
      |> ok
    in
    let workspace = List.last_exn registry.workspaces in
    let host = H.switch (H.receive H.empty registry) workspace.id in
    let host = { host with layout_mode = H.Fit; chrome = false } in
    assert (Option.is_none (H.definition workspace));
    List.iter
      [ 90, 28; 120, 40; 25, 6; 1, 1 ]
      ~f:(fun (width, height) ->
        let _, compact, cells = tile_layout host { Dimensions.width; height } in
        assert (List.length cells = if compact then 1 else 3);
        assert (Bool.equal compact (width = 1 || width = 25));
        List.iteri cells ~f:(fun i (tile, (g : W.Geometry.t)) ->
          assert (not tile.W.Tile.hidden);
          assert (g.x >= 0 && g.y >= 0 && g.width > 0 && g.height > 0);
          assert (g.x + g.width <= width && g.y + g.height <= height);
          List.iter
            (List.drop cells (i + 1))
            ~f:(fun (_, (other : W.Geometry.t)) ->
              assert (
                g.x + g.width <= other.x
                || other.x + other.width <= g.x
                || g.y + g.height <= other.y
                || other.y + other.height <= g.y))));
    assert (W.Snapshot.equal registry (Option.value_exn host.registry));
    assert (
      Workspace_template.equal template (W.export_template registry workspace.id |> ok)))
;;
