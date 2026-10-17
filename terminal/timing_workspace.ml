open! Core
open Hardcaml_workbench_protocol

type pane =
  | Paths
  | Detail
  | Context
[@@deriving equal]

type t = Inspection_view.t

type selection =
  { run : Run_ref.t
  ; domain : string
  ; stage : string
  ; source_digest : string
  ; row_id : string
  }

type path_item =
  { row : Asic_inspection.Row.t
  ; selected : bool
  ; label : string
  }

let path_items (t : t) =
  Inspection_view.visible t
  |> List.map ~f:(fun row ->
    let selected =
      Option.equal String.equal t.selected (Some row.Asic_inspection.Row.id)
    in
    let endpoint key = List.Assoc.find row.fields key ~equal:String.equal in
    let endpoints =
      match endpoint "startpoint", endpoint "endpoint" with
      | Some a, Some b -> " · " ^ a ^ " → " ^ b
      | _, Some b -> " · endpoint=" ^ b
      | Some a, _ -> " · startpoint=" ^ a
      | _ -> ""
    in
    { row
    ; selected
    ; label =
        Artifact_view.safe
          (sprintf
             "%s %s %s · %s%s · %s"
             (if selected then ">" else " ")
             (Option.value_map row.value ~default:"—" ~f:(sprintf "%.6g"))
             (Option.value row.unit_ ~default:"")
             row.status
             endpoints
             row.name)
    })
;;

let pane = function
  | "timing-paths" -> Some Paths
  | "timing-detail" -> Some Detail
  | "timing-context" -> Some Context
  | _ -> None
;;

let create ~generation ~run ~stage =
  Inspection_view.create ~scope:run ~generation ~run ~domain:"timing" ~stage ()
;;

let selection (t : t) =
  Option.bind t.index ~f:(fun index ->
    Option.map t.selected ~f:(fun row_id ->
      { run = t.run
      ; domain = t.domain
      ; stage = t.stage
      ; source_digest = index.source_digest
      ; row_id
      }))
;;

type line_role =
  | Selected
  | Metric
  | Metadata
  | Pending
  | Failure

let selected_row (t : t) =
  List.find (Inspection_view.visible t) ~f:(fun row ->
    Option.equal String.equal t.selected (Some row.Asic_inspection.Row.id))
;;

(** The compact prefix is width-bounded; complete values live in Context. Provider payload
    is deliberately outside this prefix and is never semantically styled. *)
let semantic_prefix ~pane ~width (t : t) =
  let field label value = Metadata, label ^ ": " ^ value in
  match pane with
  | Paths -> []
  | Detail ->
    (match selected_row t with
     | None -> [ Pending, "No selected path · select a loaded path in Paths" ]
     | Some row ->
       let endpoint key =
         List.Assoc.find row.fields key ~equal:String.equal |> Option.value ~default:"—"
       in
       [ Selected, "Path: " ^ row.name
       ; ( Metric
         , "Slack: "
           ^ Option.value_map row.value ~default:"unreported" ~f:(sprintf "%.9g")
           ^ " "
           ^ Option.value row.unit_ ~default:"(unit unreported)"
           ^ " · "
           ^ row.status )
       ; ( Metadata
         , "Corner: "
           ^ Option.value row.corner ~default:"—"
           ^ " · Group: "
           ^ Option.value row.group ~default:"—" )
       ; Metadata, "Endpoints: " ^ endpoint "startpoint" ^ " → " ^ endpoint "endpoint"
       ])
    |> List.map ~f:(fun (role, line) ->
      let lines =
        Artifact_view.wrap ~width:(Int.max 1 (width - 1)) (Artifact_view.safe line)
      in
      ( role
      , if width <= 0
        then ""
        else (
          match lines with
          | [] -> ""
          | [ line ] -> line
          | line :: _ -> if width = 1 then "…" else line ^ "…") ))
  | Context ->
    let observation =
      match t.index with
      | None -> [ Pending, "No loaded observation; explicit Inspect/refresh required" ]
      | Some i ->
        [ (if i.cached_unverified
           then Pending, "CACHED UNVERIFIED"
           else Metadata, "Verified cached observation")
        ; (if i.truncated then Pending, "TRUNCATED index" else Metadata, "Complete index")
        ; field "Source digest" i.source_digest
        ; field "Execution" i.execution_file
        ; field "Execution SHA256" i.execution_sha256
        ]
        @ List.map i.diagnostics ~f:(fun diagnostic -> field "Diagnostic" diagnostic)
    in
    [ field "Run" t.run.id; field "Domain" (t.domain ^ " · Stage: " ^ t.stage) ]
    @ observation
    @
      (match selected_row t with
      | None -> [ Pending, "No selected path provenance" ]
      | Some row ->
        [ field "Row" row.id
        ; field "Path" row.name
        ; field "Producer" row.producer
        ; field "Category / status" (row.category ^ " / " ^ row.status)
        ; field
            "Value"
            (Option.value_map row.value ~default:"unreported" ~f:(sprintf "%.17g")
             ^ " "
             ^ Option.value row.unit_ ~default:"(unit unreported)")
        ; field "Corner" (Option.value row.corner ~default:"(none)")
        ; field "Group" (Option.value row.group ~default:"(none)")
        ; field "Source" row.source
        ]
        @ List.map row.fields ~f:(fun (key, value) -> field key value))
;;

let detail_body (t : t) =
  match selected_row t with
  | None -> []
  | Some _ ->
    (match Option.first_some t.error t.pending_error with
     | Some error -> [ "ERROR: " ^ error ]
     | None ->
       (match t.requested, t.detail with
        | None, _ -> [ "Enter to load selected path detail (read-only)" ]
        | Some _, None ->
          [ "Pending: waiting for exact selected path detail · Enter retries" ]
        | Some _, Some detail ->
          (match detail.error with
           | Some error -> [ "ERROR: " ^ error ]
           | None ->
             if String.is_empty detail.text
             then [ "Provider returned no detail text" ]
             else String.split_lines detail.text)))
;;

let rows ~pane ~scroll ~width ~height (t : t) =
  match pane with
  | Paths ->
    let items = path_items t in
    let status =
      match t.index with
      | None -> "No loaded index · explicit Inspect/refresh required"
      | Some index ->
        sprintf
          "%d paths · %s%s%s"
          (List.length items)
          t.stage
          (if index.cached_unverified then " · CACHED UNVERIFIED" else " · observed cache")
          (if index.truncated then " · TRUNCATED" else "")
    in
    let status =
      Option.value_map
        (Option.first_some t.error t.pending_error)
        ~default:status
        ~f:(fun error -> "ERROR: " ^ error ^ " · " ^ status)
    in
    let query =
      if t.editing || t.pasting
      then
        (if t.pasting then "PASTE " else "FILTER ")
        ^ t.filter
        ^ "▏ · "
        ^ Option.value t.filter_notice ~default:"Enter/Esc finish · Ctrl-U clear"
      else
        sprintf
          "filter=%s · %s · corner=%s group=%s producer=%s near=%b"
          t.filter
          (match t.sort with
           | Numeric_ascending -> "value ↑"
           | Numeric_descending -> "value ↓"
           | Name -> "name")
          (Option.value t.corner ~default:"ALL")
          (Option.value t.group ~default:"ALL")
          (Option.value t.producer ~default:"ALL")
          t.near
    in
    (* The styled host path table reserves four header rows; on tiny panes both
       representations retain one actual path row. Keep keyboard paging identical. *)
    let header_height = Int.min 4 (Int.max 0 (height - 1)) in
    let viewport = Int.max 1 (height - header_height) in
    let position =
      List.findi items ~f:(fun _ item -> item.selected)
      |> Option.value_map ~default:0 ~f:fst
    in
    List.take
      (List.map
         (List.take
            [ status
            ; query
            ; "Enter detail · / filter · s sort · c/g/p axes · v near · t stage · r \
               refresh"
            ; "Value / unit · reported status · reported endpoints / path"
            ]
            header_height)
         ~f:Artifact_view.safe
       @ (List.drop items (position / viewport * viewport)
          |> Fn.flip List.take viewport
          |> List.map ~f:(fun item -> item.label)))
      (Int.max 0 height)
  | Detail | Context ->
    let lines =
      List.map (semantic_prefix ~pane ~width t) ~f:snd
      @ if equal_pane pane Detail then detail_body t else []
    in
    let lines =
      List.concat_map lines ~f:(fun line ->
        Artifact_view.wrap ~width (Artifact_view.safe line))
    in
    List.take
      (List.drop lines (Int.min scroll (Int.max 0 (List.length lines - height))))
      height
;;

let input ~pane ~scroll ~width ~height (t : t) action =
  match pane, action with
  | _, Inspection_view.Back ->
    ( { t with
        requested = None
      ; detail = None
      ; info = false
      ; generation = t.generation + 1
      ; operation_key = None
      ; error = None
      ; pending_error = None
      }
    , scroll
    , None )
  | (Detail | Context), (Inspection_view.Up | Down | Page_up | Page_down) ->
    let delta =
      match action with
      | Up -> -1
      | Down -> 1
      | Page_up -> -Int.max 1 height
      | _ -> Int.max 1 height
    in
    let length = List.length (rows ~pane ~scroll:0 ~width ~height:Int.max_value t) in
    let last = Int.max 0 (length - height) in
    t, Int.clamp_exn (Int.min scroll last + delta) ~min:0 ~max:last, None
  | _ ->
    (* A selected detail never steals the list's navigation mode. *)
    let browsing = { t with requested = None; detail = None; info = false; scroll = 0 } in
    let next, operation = Inspection_view.input ~width ~height browsing action in
    let next = Option.value next ~default:browsing in
    let changed = not (Option.equal String.equal next.selected t.selected) in
    let next =
      if changed || Option.is_some operation
      then next
      else
        { next with
          requested = t.requested
        ; detail = t.detail
        ; operation_key = t.operation_key
        }
    in
    next, scroll, operation
;;

let%test_unit "ten-row selected detail leads with provider text and retains full \
               provenance in Context"
  =
  let run = Fs0_fixture.run_a in
  let source =
    "{\"path\":\"/report/" ^ String.make 2048 's' ^ "\",\"row_id\":\"selected\"}"
  in
  let payload = String.make 3000 'x' in
  let row : Asic_inspection.Row.t =
    { id = "selected"
    ; name = "setup path " ^ String.make 200 'n'
    ; category = "path"
    ; producer = "sta"
    ; corner = Some "slow"
    ; group = Some "clk"
    ; value = Some (-0.125)
    ; unit_ = Some "ns"
    ; status = "violated"
    ; source
    ; fields = [ "startpoint", "in/Q"; "endpoint", "out/D"; "raw_payload", payload ]
    }
  in
  let index : Asic_inspection.Index.t =
    { run
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "source-digest"
    ; execution_file = "/execution.json"
    ; execution_sha256 = "execution-sha"
    ; rows = [ row ]
    ; diagnostics = [ "provider diagnostic" ]
    ; truncated = false
    ; cached_unverified = false
    }
  in
  let snapshot = { Fs0_fixture.snapshot with inspections = [ index ] } in
  let t =
    Inspection_view.reconcile (create ~generation:1 ~run ~stage:"signoff") snapshot
  in
  let t, _, _ = input ~pane:Paths ~scroll:0 ~width:68 ~height:10 t Open in
  let pending = rows ~pane:Detail ~scroll:0 ~width:68 ~height:10 t in
  assert (List.exists pending ~f:(fun line -> String.is_prefix line ~prefix:"Pending:"));
  let detail : Asic_inspection.Detail.t =
    { run
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "source-digest"
    ; row_id = "selected"
    ; text = "ACTUAL PROVIDER DETAIL\ncell/A 0.1 ns\ncell/B 0.2 ns"
    ; error = None
    }
  in
  let t = Inspection_view.reconcile t { snapshot with inspection_details = [ detail ] } in
  let visible = rows ~pane:Detail ~scroll:0 ~width:68 ~height:10 t in
  assert (String.equal (List.nth_exn visible 4) "ACTUAL PROVIDER DETAIL");
  assert (
    List.exists visible ~f:(fun line -> String.is_substring line ~substring:"-0.125 ns"));
  assert (
    List.exists visible ~f:(fun line ->
      String.is_substring line ~substring:"in/Q → out/D"));
  assert (
    not
      (List.exists visible ~f:(fun line ->
         String.is_substring line ~substring:"Source:"
         || String.is_substring line ~substring:"raw_payload")));
  let context =
    rows ~pane:Context ~scroll:0 ~width:68 ~height:Int.max_value t
    |> String.concat ~sep:""
  in
  List.iter
    [ source; payload; "source-digest"; "execution-sha"; row.name; "provider diagnostic" ]
    ~f:(fun value -> assert (String.is_substring context ~substring:value));
  let failed =
    Inspection_view.reconcile
      t
      { snapshot with
        inspection_details = [ { detail with error = Some "detail unavailable" } ]
      }
  in
  assert (
    List.mem
      (rows ~pane:Detail ~scroll:0 ~width:68 ~height:10 failed)
      "ERROR: detail unavailable"
      ~equal:String.equal)
;;

let%test_unit "Timing investigation layout fits 120x40 without a default vertical \
               checklist"
  =
  let module P = Hardcaml_workbench_workspaces in
  let definition = P.Timing.definition in
  let kinds = List.map definition.tiles ~f:(fun tile -> tile.P.Common.kind) in
  assert (not (List.mem kinds "stage-checklist" ~equal:String.equal));
  match P.Layout.compute definition ~width:120 ~height:38 ~kinds with
  | Compact -> assert false
  | Grid cells ->
    let geometry kind =
      List.nth_exn
        cells
        (List.findi_exn kinds ~f:(fun _ value -> String.equal value kind) |> fst)
    in
    let nav = geometry "workspace-tabs"
    and session = geometry "live-status"
    and selector = geometry "run-selector"
    and paths = geometry "timing-paths"
    and detail = geometry "timing-detail"
    and context = geometry "timing-context" in
    assert (nav.height = 1);
    assert (session.y = selector.y && session.width = 40 && selector.width = 80);
    assert (paths.y >= session.y + session.height);
    assert (paths.width >= 44 && paths.width <= 50 && detail.width >= 68);
    assert (
      detail.x = context.x && detail.y = paths.y && context.y >= detail.y + detail.height);
    assert (detail.height >= 10 && context.height >= 8);
    List.iter cells ~f:(fun cell ->
      assert (cell.x + cell.width <= 120 && cell.y + cell.height <= 38))
;;

let%test_unit "cooperating panes select actual paths; browsing is local and details exact"
  =
  let run = Fs0_fixture.run_a in
  let row id value : Asic_inspection.Row.t =
    { id
    ; category = "path"
    ; producer = "sta"
    ; corner = Some "slow"
    ; group = Some "clk"
    ; name = id
    ; value = Some value
    ; unit_ = Some "ns"
    ; status = "violated"
    ; source = "/report"
    ; fields = [ "endpoint", id ^ "/Q" ]
    }
  in
  let index : Asic_inspection.Index.t =
    { run
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "digest"
    ; execution_file = "/execution"
    ; execution_sha256 = "sha"
    ; rows = [ row "a" (-1.); row "b" 0. ]
    ; diagnostics = []
    ; truncated = false
    ; cached_unverified = false
    }
  in
  let snapshot = { Fs0_fixture.snapshot with inspections = [ index ] } in
  let original =
    Inspection_view.reconcile (create ~generation:1 ~run ~stage:"signoff") snapshot
  in
  let moved, _, op = input ~pane:Paths ~scroll:0 ~width:60 ~height:12 original Down in
  assert (Option.is_none op);
  assert (String.equal (Option.value_exn (selection moved)).row_id "b");
  assert (String.equal (Option.value_exn (selection original)).row_id "a");
  assert (
    List.exists (rows ~pane:Detail ~scroll:0 ~width:80 ~height:30 moved) ~f:(fun line ->
      String.is_substring line ~substring:"b/Q"));
  let opened, _, operation =
    input ~pane:Paths ~scroll:0 ~width:60 ~height:12 moved Open
  in
  let opened = { opened with workspace_epoch = Some "workspace-A:selection-epoch" } in
  let ticket = Inspection_view.capture opened (Option.value_exn operation) in
  (match operation with
   | Some (Inspect_detail { row_id; source_digest; _ }) ->
     assert (String.equal row_id "b" && String.equal source_digest "digest")
   | _ -> assert false);
  let moved, _, op = input ~pane:Paths ~scroll:0 ~width:60 ~height:12 opened Up in
  assert (Option.is_none op && Option.is_none moved.requested);
  assert (
    Option.is_none (Inspection_view.apply_response moved ticket (Error "late")).error);
  let independent, scroll, op =
    input ~pane:Detail ~scroll:0 ~width:60 ~height:3 opened Down
  in
  assert (scroll = 1 && Option.is_none op);
  assert (Option.equal String.equal independent.selected opened.selected);
  assert (
    Option.is_none
      (Inspection_view.apply_response
         { opened with workspace_epoch = Some "workspace-B:selection-epoch" }
         ticket
         (Error "moved tile receipt"))
        .error);
  let closed, _, operation =
    input ~pane:Detail ~scroll:4 ~width:60 ~height:3 opened Back
  in
  assert (Option.is_none operation && Option.is_none closed.requested);
  assert (Option.is_some closed.index);
  let detail : Asic_inspection.Detail.t =
    { run
    ; domain = "timing"
    ; stage = "signoff"
    ; source_digest = "digest"
    ; row_id = "b"
    ; text = "cached selected detail"
    ; error = None
    }
  in
  let late =
    Inspection_view.reconcile closed { snapshot with inspection_details = [ detail ] }
  in
  assert (Option.is_none late.detail);
  assert (
    Option.is_none
      (Inspection_view.apply_response late ticket (Error "closed reader receipt")).error);
  let changed_row = { (List.last_exn index.rows) with source = "/replacement-report" } in
  let replaced =
    Inspection_view.reconcile
      opened
      { snapshot with
        inspections = [ { index with rows = [ List.hd_exn index.rows; changed_row ] } ]
      ; inspection_details = [ detail ]
      }
  in
  assert (Option.is_none replaced.requested && Option.is_none replaced.detail);
  assert (
    Option.is_none
      (Inspection_view.apply_response replaced ticket (Error "old same-id row receipt"))
        .error);
  let loaded =
    Inspection_view.reconcile
      opened
      { snapshot with
        inspection_details =
          [ { detail with
              text = String.concat ~sep:"\n" (List.init 100 ~f:(fun i -> Int.to_string i))
            }
          ]
      }
  in
  let bottom, scroll =
    List.fold (List.init 1000 ~f:Fn.id) ~init:(loaded, 0) ~f:(fun (t, scroll) _ ->
      let t, scroll, operation = input ~pane:Detail ~scroll ~width:60 ~height:3 t Down in
      assert (Option.is_none operation);
      t, scroll)
  in
  let _, up, _ = input ~pane:Detail ~scroll ~width:60 ~height:3 bottom Up in
  assert (up = scroll - 1);
  assert (Option.equal String.equal bottom.selected opened.selected);
  let refreshing, _, operation =
    input ~pane:Paths ~scroll:0 ~width:60 ~height:12 opened Refresh
  in
  let refresh_ticket = Inspection_view.capture refreshing (Option.value_exn operation) in
  let stale =
    Inspection_view.reconcile
      opened
      { snapshot with inspections = [ { index with source_digest = "new" } ] }
  in
  assert (Option.is_none stale.detail && Option.is_none stale.requested);
  assert (
    Option.is_none
      (Inspection_view.apply_response stale ticket (Error "old digest")).error);
  let refreshed =
    Inspection_view.reconcile
      refreshing
      { snapshot with inspections = [ { index with source_digest = "new" } ] }
  in
  assert (
    Option.is_none
      (Inspection_view.apply_response
         refreshed
         refresh_ticket
         (Error "old index receipt"))
        .error)
;;
