open! Core
open Hardcaml_workbench_protocol
open Bonsai_term
module H = Workspace_host
module W = Workspace

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

  let rgb r g b = Attr.Color.rgb ~r ~g ~b
  let background = rgb 20 25 34
  let foreground = rgb 218 225 234
  let surface = rgb 35 44 58
  let card = rgb 27 34 46
  let muted = rgb 154 168 187

  let backdrop (appearance : Appearance.t) = function
    | Surface | Selection | Active_tab -> surface
    | Foreground ->
      (match appearance.preset with
       | Studio | Structured_studio -> card
       | _ -> background)
    | _ -> background
  ;;

  let attrs (appearance : Appearance.t) role =
    let accent =
      match appearance.color with
      | Restrained -> foreground
      | Selective | Vivid -> rgb 117 202 221
    in
    let fg =
      match role with
      | Muted | Inactive_tab -> muted
      | Border ->
        (match appearance.color with
         | Vivid -> rgb 104 153 189
         | _ -> muted)
      | Focus | Selection | Active_tab -> accent
      | Metric ->
        (match appearance.color with
         | Vivid -> rgb 227 192 126
         | _ -> foreground)
      | Success ->
        (match appearance.color with
         | Restrained -> foreground
         | _ -> rgb 142 203 150)
      | Warning ->
        (match appearance.color with
         | Restrained -> foreground
         | _ -> rgb 227 192 126)
      | Failure ->
        (match appearance.color with
         | Restrained -> foreground
         | _ -> rgb 236 139 147)
      | Running -> accent
      | _ -> foreground
    in
    let bg = backdrop appearance role in
    [ Attr.fg fg; Attr.bg bg ]
    @
    match role with
    | Focus | Selection | Metric | Active_tab -> [ Attr.bold ]
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
  View.with_colors ~fill_backdrop:true view ~fg:Role.foreground ~bg
;;

let lines ?(appearance = Appearance.default) ?(role = Role.Foreground) ~width ~height rows
  =
  List.take rows (Int.max 0 height)
  |> List.map ~f:(View.text ~attrs:(Role.attrs appearance role))
  |> View.vcat
  |> box ~width ~height
  |> colored appearance role
;;

(* Only the outer frame owns borders. Small surfaces reclaim every evidence row. *)
let framed (appearance : Appearance.t) ~width ~height =
  width >= 20
  && height > 8
  &&
  match appearance.preset with
  | Instrument | Structured | Structured_studio -> true
  | Minimal | Studio -> false
;;

let studio (appearance : Appearance.t) =
  match appearance.preset with
  | Studio | Structured_studio -> true
  | _ -> false
;;

let focus_marker (appearance : Appearance.t) focused =
  match appearance.icons with
  | None_ -> ""
  | Ascii -> if focused then "> " else "- "
  | Unicode -> if focused then "◆ " else "· "
;;

let frame_tile appearance ~focused ~width ~height content =
  if not (framed appearance ~width ~height)
  then box ~width ~height content
  else (
    let tl, tr, bl, br, horizontal, vertical =
      match appearance.Appearance.icons, appearance.preset with
      | Unicode, Instrument -> "╭", "╮", "╰", "╯", "─", "│"
      | Unicode, _ -> "┌", "┐", "└", "┘", "─", "│"
      | (None_ | Ascii), _ -> "+", "+", "+", "+", "-", "|"
    in
    let attrs = Role.attrs appearance (if focused then Focus else Border) in
    let text = View.text ~attrs in
    let edge left right =
      text (left ^ String.concat (List.init (width - 2) ~f:(fun _ -> horizontal)) ^ right)
    in
    let side = View.vcat (List.init (height - 2) ~f:(fun _ -> text vertical)) in
    View.vcat
      [ edge tl tr
      ; View.hcat [ side; box ~width:(width - 2) ~height:(height - 2) content; side ]
      ; edge bl br
      ])
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
  }

let run_label (run : Run_ref.t) = Backend_id.to_string run.backend ^ "/" ^ run.id

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

let rows host data tile ~width ~height =
  let local = H.local host tile.W.Tile.id in
  let scope =
    match host.H.registry with
    | None -> None
    | Some s -> W.resolve_tile s tile.id |> Result.ok |> Option.bind ~f:(fun r -> r.run)
  in
  let run_rows () =
    ("Context selection: " ^ Option.value_map scope ~default:"none" ~f:run_label)
    :: (List.filter data.runs ~f:(fun (r, label) ->
          String.is_substring
            (String.lowercase (run_label r ^ " " ^ label))
            ~substring:(String.lowercase local.filter))
        |> List.map ~f:(fun (run, label) ->
          sprintf
            "%s%s %s  %s"
            (if Option.equal String.equal local.cursor (Some (run_label run))
             then ">"
             else " ")
            (if Option.equal Run_ref.equal scope (Some run) then "*" else " ")
            (run_label run)
            label))
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
    match artifact_inspector host tile with
    | Some view -> Artifact_view.rows view ~width ~height
    | None ->
      (match tile.kind with
       | "run-selector" -> run_rows ()
       | "execution" | "project-tests" ->
         [ (if String.equal tile.kind "project-tests"
            then "Project tests (not ASIC-run scoped)"
            else "Project execution attempts")
         ; "Environment: " ^ data.environment
         ; "Case details / progress: unavailable (generic command runner)"
         ]
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
         ; "Tab: focus tile; j/k: browse; Enter: select run"
         ; "1/2: Overview / Timing; /: filter focused selector"
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
            ("Run: " ^ run_label run)
            :: Synthesis_view.rows
                 local.synthesis
                 ~summary:(data.summary run)
                 ~filter:local.filter
                 ~width
                 ~height:(Int.max 0 (height - 1)))
       | kind when Terminal_result_view.supports kind ->
         (match scope with
          | None -> [ "No run selected — use a run selector" ]
          | Some run ->
            (if String.equal tile.kind "finalization"
             then data.run_lines run "finalization-status"
             else [])
            @ Terminal_result_view.rows
                ~fallback:(("Run: " ^ run_label run) :: data.run_lines run kind)
                ~request_context:(data.run_context run)
                local.terminal_result
                ~run
                ~summary:(data.summary run)
                ~kind
                ~width
                ~height)
       | kind ->
         (match scope with
          | None -> [ "No run selected — use a run selector" ]
          | Some run -> ("Run: " ^ run_label run) :: data.run_lines run kind))
  in
  if Option.is_some local.artifacts
     || String.equal tile.kind "synthesis"
     || Terminal_result_view.supports tile.kind
     || (String.equal tile.kind "logs" && local.follow)
  then rows
  else if String.equal tile.kind "run-selector"
  then (
    match rows with
    | [] -> []
    | scope :: rest -> scope :: List.drop rest local.scroll)
  else List.drop rows local.scroll
;;

let body_geometry host tile ~width ~height =
  let local = H.local host tile.W.Tile.id in
  let appearance = host.H.appearance in
  let border = if framed appearance ~width ~height then 1 else 0 in
  let inner_width = Int.max 0 (width - (2 * border)) in
  let inner_height = Int.max 0 (height - (2 * border)) in
  let padding =
    if width >= 40
       && height > 8
       && Appearance.Density.equal appearance.density Comfortable
    then 1
    else 0
  in
  let body_width = Int.max 0 (inner_width - (2 * padding)) in
  let body_height =
    Int.max 0 (inner_height - (2 * padding) - if local.headers then 1 else 0)
  in
  inner_width, inner_height, padding, body_width, body_height
;;

let tile_view host data tile ~width ~height =
  let appearance = host.H.appearance in
  let local = H.local host tile.W.Tile.id in
  let focused =
    Option.value_map host.H.focus ~default:false ~f:(W.Tile_id.equal tile.id)
  in
  let binding =
    if H.project_scoped_kind tile.kind
    then "PROJECT"
    else (
      match tile.binding with
      | Follow -> "FOLLOW"
      | Pin_run run -> "PIN " ^ run_label run)
  in
  let inner_width, inner_height, padding, body_width, body_height =
    body_geometry host tile ~width ~height
  in
  let rows = rows host data tile ~width:body_width ~height:body_height in
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
  let rows =
    if focused && not local.headers
    then (
      match rows with
      | [] -> [ "> focused tile" ]
      | first :: rest -> (focus_marker appearance true ^ first) :: rest)
    else rows
  in
  let header =
    if local.headers
    then (
      let title =
        if Terminal_result_view.supports tile.kind && local.terminal_result.detail
        then tile.kind ^ "/evidence"
        else if not (String.equal tile.kind "synthesis")
        then tile.kind
        else (
          match Synthesis_view.State.mode local.synthesis with
          | Summary -> "synthesis"
          | Cells -> "synthesis/cells"
          | Details -> "synthesis/detail"
          | Metrics -> "synthesis/metrics"
          | Evidence -> "synthesis/evidence")
      in
      (* A tile-title badge indicates real tile focus, not a navigation tab. *)
      [ lines
          ~appearance
          ~role:
            (if studio appearance
             then if focused then Selection else Surface
             else if focused
             then Focus
             else Border)
          ~width:body_width
          ~height:1
          [ sprintf
              "%s%s [%s] %s%s"
              (focus_marker appearance focused)
              (if studio appearance
               then "[ " ^ title ^ " ]"
               else if Appearance.Preset.equal appearance.preset Instrument
               then String.uppercase title
               else title)
              binding
              (W.Tile_id.to_string tile.id)
              (if String.is_empty local.filter then "" else " filter=" ^ local.filter)
          ]
      ])
    else []
  in
  let body =
    List.take rows body_height
    |> List.map ~f:(fun row ->
      (* This is a known metric emitted by the synthesis summary above, never a
         severity/acceptance classification inferred from arbitrary provider text. *)
      let role =
        if Appearance.Preset.equal appearance.preset Instrument
           && String.equal tile.kind "synthesis"
           && String.is_prefix row ~prefix:"Cell count: "
        then Role.Metric
        else if H.job_attempt_kind tile.kind
                && (not (String.equal tile.kind "logs"))
                && String.is_prefix row ~prefix:"STATUS: Failed"
        then Failure
        else if H.job_attempt_kind tile.kind
                && (not (String.equal tile.kind "logs"))
                && String.is_prefix row ~prefix:"STATUS: Complete"
        then Success
        else if H.job_attempt_kind tile.kind
                && (not (String.equal tile.kind "logs"))
                && String.is_prefix row ~prefix:"STATUS: Running"
        then Running
        else if focused && not local.headers
        then Focus
        else Foreground
      in
      lines ~appearance ~role ~width:body_width ~height:1 [ row ])
    |> View.vcat
    |> box ~width:body_width ~height:body_height
  in
  let content =
    View.vcat (header @ [ body ])
    |> View.pad ~l:padding ~r:padding ~t:padding ~b:padding
    |> box ~width:inner_width ~height:inner_height
  in
  frame_tile appearance ~focused ~width ~height content
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

(** The same outer and inner geometry is used by rendering and page navigation. *)
let tile_layout host ({ Dimensions.width; height } : Dimensions.t) =
  let width = Int.max 1 width
  and height = Int.max 1 height in
  let available =
    Int.max
      1
      (height
       - (if host.H.chrome then 1 else 0)
       - if host.chrome || host.editing_filter || host.paste then 1 else 0)
  in
  let tiles = H.tiles host in
  let zoomed =
    Option.value_map (H.active host) ~default:false ~f:(fun w ->
      Option.is_some w.zoomed_tile)
  in
  let fit = Fit_layout.compute ~width ~height:available ~count:(List.length tiles) in
  let compact =
    (not zoomed)
    &&
    match host.layout_mode, fit with
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
      match host.layout_mode, fit with
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

let scroll_focused host data dimensions ~delta =
  let _, _, layout = tile_layout host dimensions in
  match H.focused host, host.H.registry with
  | Some tile, Some registry ->
    (match
       ( List.find layout ~f:(fun (visible, _) -> W.Tile_id.equal visible.id tile.id)
       , W.resolve_tile registry tile.id
         |> Result.ok
         |> Option.bind ~f:(fun reference -> reference.run) )
     with
     | Some (_, g), Some run ->
       let _, _, _, width, height =
         body_geometry host tile ~width:g.width ~height:g.height
       in
       let local = H.local host tile.id in
       let local =
         if String.equal tile.kind "synthesis"
         then
           { local with
             synthesis =
               Synthesis_view.scroll
                 local.synthesis
                 ~summary:(data.summary run)
                 ~filter:local.filter
                 ~width
                 ~height:(Int.max 0 (height - 1))
                 ~delta
           }
         else if Terminal_result_view.supports tile.kind
         then
           { local with
             terminal_result =
               Terminal_result_view.scroll
                 ~fallback:(("Run: " ^ run_label run) :: data.run_lines run tile.kind)
                 ~request_context:(data.run_context run)
                 local.terminal_result
                 ~run
                 ~summary:(data.summary run)
                 ~kind:tile.kind
                 ~width
                 ~height
                 ~delta
           }
         else local
       in
       H.set_local host tile.id local
     | _ -> host)
  | _ -> host
;;

(** Fit uses responsive tracks; Preferred preserves saved shelf dimensions. *)
let render host data ({ Dimensions.width; height } as dimensions) =
  let appearance = host.H.appearance in
  let width = Int.max 1 width
  and height = Int.max 1 height in
  let header =
    if not host.H.chrome
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
                 (Option.value_map c.selected_run ~default:"none" ~f:run_label)
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
        tile_view host data tile ~width:g.width ~height:g.height |> View.pad ~l:g.x ~t:g.y)
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
          [ (if compact
             then
               "Compact: focused tile only | Tab: next tile | enlarge terminal for grid"
             else if String.is_empty host.notice
             then "Space c c commands | Tab focus | j/k browse | Enter select | q exit"
             else host.notice)
          ]
      ]
  in
  let frame =
    View.vcat (header @ [ box ~width ~height:available content ] @ footer)
    |> box ~width ~height
    |> colored appearance Background
  in
  match host.palette with
  | None ->
    (match Option.bind (H.focused host) ~f:(artifact_inspector host) with
     | None -> frame
     | Some view ->
       lines
         ~appearance
         ~role:Surface
         ~width
         ~height
         (Artifact_view.rows view ~width ~height)
       |> colored appearance Surface
       |> box ~width:dimensions.width ~height:dimensions.height)
  | Some p ->
    let matches = H.matches p in
    let shown = Int.max 1 (height - 4) in
    let start = Int.max 0 (p.index - shown + 1) in
    let commands =
      List.drop matches start
      |> Fn.flip List.take shown
      |> List.mapi ~f:(fun i c ->
        sprintf
          "%s %s%s"
          (if i + start = p.index then ">" else " ")
          c.H.title
          (Option.value_map c.unavailable ~default:"" ~f:(fun reason ->
             " [" ^ reason ^ "]")))
    in
    let overlay =
      lines
        ~appearance
        ~role:Surface
        ~width
        ~height
        ([ (match p.argument with
            | Some (H.Plan_endpoint _) ->
              "PLAN ENDPOINT - exact provider endpoint; Enter previews; Esc closes"
            | Some (H.Finalization_attempt run) ->
              "INSPECT FINALIZATION for "
              ^ run_label run
              ^ " - exact returned attempt; Enter imports; Esc closes"
            | Some (H.Acceptance (run, _, _)) ->
              "FINALIZE AND ACCEPT " ^ run_label run ^ " — Enter submits; Esc closes"
            | None -> "COMMAND PALETTE - Esc closes; Enter executes captured target")
         ]
         @ (match p.argument with
            | Some (H.Acceptance _) ->
              wrap_cells ~width ("> " ^ p.query)
              |> List.rev
              |> Fn.flip List.take 3
              |> List.rev
            | _ -> [ "> " ^ p.query ])
         @ (match p.argument with
            | Some (H.Acceptance _) ->
              [ "Acceptance S-expression (≤4096 UTF-8 bytes; quote paths with spaces):"
              ; "((support_tools /tools) (precheck_python /python)"
              ; " (testbench /tb.sv) (testbench_top tb) (replay_trace /trace))"
              ; "All five values are explicit strings; no shell expansion."
              ]
            | _ -> [])
         @ commands
         @ [ host.notice ])
      |> colored appearance Surface
    in
    View.zcat [ overlay; frame ] |> box ~width:dimensions.width ~height:dimensions.height
;;

let appearance_cases =
  List.concat_map Appearance.Preset.all ~f:(fun preset ->
    List.concat_map Appearance.Color.all ~f:(fun color ->
      List.concat_map Appearance.Icons.all ~f:(fun icons ->
        List.map Appearance.Density.all ~f:(fun density ->
          { Appearance.preset; color; icons; density }))))
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
    let without_headers = H.set_local host test_tile.id { local with headers = false } in
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
    }
  in
  let frame host = render host data { width = 100; height = 30 } |> plain_text in
  assert (String.is_substring (frame host) ~substring:page.text);
  (* Deliberately retain old local state: the renderer independently checks binding. *)
  let changed = { host with registry = Some (bind snapshot Fs0_fixture.run_b) } in
  assert (Option.is_none (artifact_inspector changed tile));
  assert (not (String.is_substring (frame changed) ~substring:page.text))
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
  let before = frame host 32 8 in
  assert (has before "Cell count: 50");
  assert (has before "Freshness: Cached_unverified");
  assert (has before "Count  Cell type");
  assert (has before "35  NAND2");
  assert (not (has before "/explicit/synthetic"));
  let host = select host Fs0_fixture.run_b in
  let registry_before = Option.value_exn host.registry |> W.Snapshot.sexp_of_t in
  List.iter appearance_cases ~f:(fun appearance ->
    let host = { host with appearance } in
    let both = frame host 128 24 in
    assert (has both "Cell count: 73" && has both "Cell count: 50");
    assert (has both "run asic/fixture-B" && has both "PIN asic/fixture-A");
    let small = frame host 32 8 in
    assert (has small "Cell count: 73");
    assert (has small "Freshness: Cached_unverified");
    assert (has small "Count  Cell type");
    assert (has small "50  NAND2");
    assert (not (has small "/explicit/synthetic"));
    let pinned_frame = frame { host with focus = Some pinned } 32 8 in
    assert (has pinned_frame "Cell count: 50");
    assert (not (has pinned_frame "Cell count: 73"));
    assert (
      Sexp.equal registry_before (Option.value_exn host.registry |> W.Snapshot.sexp_of_t)));
  let both = frame host 128 24 in
  assert (has both "Cell count: 73" && has both "Cell count: 50");
  assert (has both "run asic/fixture-B" && has both "PIN asic/fixture-A");
  let compact_following = frame host 32 8 in
  assert (has compact_following "Cell count: 73");
  assert (not (has compact_following "Cell count: 50"));
  let compact_pinned = frame { host with focus = Some pinned } 32 8 in
  assert (has compact_pinned "Cell count: 50");
  assert (not (has compact_pinned "Cell count: 73"));
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
  assert (has (frame host 32 8) "Cell count: 50")
;;
