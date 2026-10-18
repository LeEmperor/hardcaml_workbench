open! Core
open Hardcaml_workbench_protocol
open Hardcaml_workbench_workspaces

let kinds d = List.map d.Definition.tiles ~f:(fun t -> t.Common.kind)

let%test_unit "cooperative Testing is bounded, readable and project scoped" =
  let d = Testing.definition in
  assert (not (List.mem (kinds d) "run-selector" ~equal:String.equal));
  assert (not (List.mem (kinds d) "simulation" ~equal:String.equal));
  List.iter
    [ 120, 40; 180, 55; 80, 24 ]
    ~f:(fun (width, height) ->
      match Layout.compute d ~width ~height:(height - 2) ~kinds:(kinds d) with
      | Compact -> assert (width = 80)
      | Grid cells ->
        assert (List.length cells = List.length d.tiles);
        List.iteri cells ~f:(fun i a ->
          assert (a.Workspace.Geometry.x >= 0 && a.y >= 0);
          assert (a.width >= 24 && a.height >= 1);
          assert (a.x + a.width <= width && a.y + a.height <= height - 2);
          List.iter
            (List.drop cells (i + 1))
            ~f:(fun b ->
              assert (
                a.x + a.width <= b.x
                || b.x + b.width <= a.x
                || a.y + a.height <= b.y
                || b.y + b.height <= a.y)));
        if width >= 120
        then (
          let cell kind =
            List.nth_exn
              cells
              (List.findi_exn (kinds d) ~f:(fun _ k -> String.equal kind k) |> fst)
          in
          assert ((cell "live-status").width <= width / 4);
          List.iter [ "simulation-catalog"; "simulation-detail" ] ~f:(fun kind ->
            let g = cell kind in
            assert (g.width >= 48 && g.height >= 12));
          List.iter
            [ "simulation-attempts"
            ; "simulation-cases"
            ; "simulation-artifacts"
            ; "simulation-logs"
            ]
            ~f:(fun kind -> assert ((cell kind).height >= 7))))
;;

let%test_unit "Timing thirds preserve investigation geometry" =
  List.iter [ Timing.definition ] ~f:(fun d ->
    List.iter
      [ 80, 24; 120, 40; 180, 55 ]
      ~f:(fun (width, terminal_height) ->
        let height = terminal_height - 2 in
        match Layout.compute d ~width ~height ~kinds:(kinds d) with
        | Compact -> assert false
        | Grid cells ->
          assert (List.length cells = List.length d.tiles);
          List.iteri cells ~f:(fun i (a : Workspace.Geometry.t) ->
            assert (a.x >= 0 && a.y >= 0 && a.width >= 24 && a.height >= 1);
            assert (a.x + a.width <= width && a.y + a.height <= height);
            List.iter
              (List.drop cells (i + 1))
              ~f:(fun b ->
                assert (
                  a.x + a.width <= b.x
                  || b.x + b.width <= a.x
                  || a.y + a.height <= b.y
                  || b.y + b.height <= a.y)));
          let cell kind =
            List.nth_exn
              cells
              (List.findi_exn (kinds d) ~f:(fun _ k -> String.equal kind k) |> fst)
          in
          if width = 80
          then List.iter cells ~f:(fun g -> assert (g.height >= 6))
          else (
            let session = cell "live-status"
            and selector = cell "run-selector" in
            assert ((cell "workspace-tabs").height = 1);
            assert (session.x = 0 && session.y = 1 && session.width = width / 3);
            assert (session.height = 7 && selector.height = 7);
            assert (selector.x = session.width && selector.width = width - session.width);
            assert (selector.y = session.y);
            let paths = cell "timing-paths"
            and detail = cell "timing-detail"
            and context = cell "timing-context" in
            assert (paths.x = 0 && paths.y = session.y + session.height);
            assert (paths.width >= 32 && paths.height >= 10);
            assert (detail.x = paths.width && detail.y = paths.y);
            assert (detail.width >= 48 && detail.height >= 10);
            assert (context.x = detail.x && context.width = detail.width);
            assert (context.y = detail.y + detail.height && context.height >= 8);
            assert (paths.height = detail.height + context.height);
            assert (context.y + context.height = height))))
;;

let%test_unit "Timing sparse membership retains duplicate and custom extras" =
  List.iter [ Timing.definition ] ~f:(fun d ->
    let ks =
      ("custom-provider"
       :: List.rev
            (List.filter (kinds d) ~f:(fun k ->
               not (List.mem [ "live-status"; "project-tests" ] k ~equal:String.equal))))
      @ [ "run-selector" ]
    in
    match Layout.compute d ~width:180 ~height:100 ~kinds:ks with
    | Compact -> assert false
    | Grid cells ->
      assert (List.length cells = List.length ks);
      let selector_index =
        List.findi_exn ks ~f:(fun _ k -> String.equal k "run-selector") |> fst
      in
      let selector = List.nth_exn cells selector_index
      and duplicate = List.last_exn cells
      and custom = List.hd_exn cells in
      assert (selector.height = 7 && selector.width = 180);
      assert (custom.width = 180 && duplicate.width = 180);
      assert (custom.y >= selector.y + selector.height);
      assert (duplicate.y >= custom.y + custom.height))
;;

let%test_unit "weighted widths and configurable gutters are full-rectangle partitions" =
  List.iter [ 0; 1 ] ~f:(fun gutter ->
    List.iter
      [ 120, 55; 180, 55 ]
      ~f:(fun (width, height) ->
        match
          Layout.compute
            ~gutter
            Overview.definition
            ~width
            ~height
            ~kinds:(kinds Overview.definition)
        with
        | Compact -> assert false
        | Grid cells ->
          let session = List.nth_exn cells 1 in
          let synthesis = List.nth_exn cells 4 in
          assert (Int.abs (session.width - ((width - gutter) / 3)) <= 1);
          assert (synthesis.x = session.width + gutter);
          assert (synthesis.x + synthesis.width = width)));
  let d = Overview.definition in
  let ks = kinds d in
  let selector required =
    match
      Layout.compute d ~width:120 ~height:38 ~kinds:ks ~min_height_for_index:(fun i ->
        if i = 2 then Some required else None)
    with
    | Compact -> assert false
    | Grid cells -> List.nth_exn cells 2
  in
  assert ((selector 12).height > (selector 7).height)
;;

let%test_unit "runtime minima change real selector geometry, including duplicate fallback"
  =
  let d = Overview.definition in
  let ks = kinds d in
  let selector_index =
    List.findi_exn ks ~f:(fun _ k -> String.equal k "run-selector") |> fst
  in
  let compute required =
    Layout.compute
      ~min_height_for_index:(fun i -> if i = selector_index then Some required else None)
      d
      ~width:120
      ~height:60
      ~kinds:ks
  in
  (match compute 14 with
   | Compact -> assert false
   | Grid cells -> assert ((List.nth_exn cells selector_index).height = 14));
  (match compute 80 with
   | Compact -> ()
   | Grid _ -> assert false);
  let ks = [ "custom"; "run-selector"; "run-selector" ] in
  match
    Layout.compute
      ~min_height_for_index:(fun i -> if i = 2 then Some 17 else None)
      d
      ~width:80
      ~height:60
      ~kinds:ks
  with
  | Compact -> assert false
  | Grid cells -> assert ((List.nth_exn cells 2).height >= 17)
;;

let%test_unit "actual terminal content bounds at80x24,120x40,large" =
  let d = Overview.definition in
  List.iter
    [ 80, 24; 120, 40; 240, 80 ]
    ~f:(fun (width, terminal_height) ->
      let height = terminal_height - 2 in
      match Layout.compute d ~width ~height ~kinds:(kinds d) with
      | Compact -> assert (width = 80)
      | Grid cells ->
        assert (List.length cells = 11);
        List.iteri cells ~f:(fun i (a : Workspace.Geometry.t) ->
          assert (a.x >= 0 && a.y >= 0 && a.width > 0 && a.height > 0);
          assert (a.x + a.width <= width && a.y + a.height <= height);
          List.iter
            (List.drop cells (i + 1))
            ~f:(fun b ->
              assert (
                a.x + a.width <= b.x
                || b.x + b.width <= a.x
                || a.y + a.height <= b.y
                || b.y + b.height <= a.y))))
;;

let%test_unit "one-third sidebar splits stages and plan above six full-width domains" =
  let d = Overview.definition in
  (* Reserve two rows for the host's global header/footer at 120x40. *)
  match Layout.compute d ~width:120 ~height:38 ~kinds:(kinds d) with
  | Compact -> assert false
  | Grid cells ->
    let cell kind =
      List.nth_exn
        cells
        (List.findi_exn (kinds d) ~f:(fun _ k -> String.equal kind k) |> fst)
    in
    let session = cell "live-status"
    and selector = cell "run-selector" in
    assert (session.width = 40 && session.height = Overview.session_height);
    assert (selector.x = session.x && selector.y = session.y + session.height);
    assert (selector.width = session.width && selector.height = Overview.selector_height);
    assert ((cell "stage-checklist").y = selector.y + selector.height);
    let stages = cell "stage-checklist"
    and plan = cell "planned-run" in
    assert (stages.x = 0 && stages.width = session.width);
    assert (plan.x = 0 && plan.width = session.width);
    assert (plan.y = stages.y + stages.height);
    assert (plan.y + plan.height = 38);
    assert (stages.height >= Overview.checklist_height);
    assert (plan.height >= Overview.planned_run_height);
    assert (Int.abs (stages.height - plan.height) <= 1);
    let bottom = ref session.y in
    List.iter
      [ "synthesis"; "timing"; "placement"; "routing"; "checks"; "finalization" ]
      ~f:(fun kind ->
        let g = cell kind in
        assert (g.x = 40 && g.width = 80 && g.height >= 5 && g.y = !bottom);
        bottom := g.y + g.height);
    assert (!bottom = 38);
    assert ((cell "workspace-tabs").height = 1)
;;

let%test_unit "six-row selector preserves readable stages and balanced plan at120x40" =
  let d = Overview.definition in
  List.iter [ 7; 9 ] ~f:(fun selector_height ->
    match
      Layout.compute
        d
        ~width:120
        ~height:38
        ~kinds:(kinds d)
        ~min_height_for_index:(fun i -> if i = 2 then Some selector_height else None)
    with
    | Compact -> assert false
    | Grid cells ->
      let selector = List.nth_exn cells 2
      and stages = List.nth_exn cells 3
      and plan = List.nth_exn cells 10 in
      assert (selector.height = selector_height);
      assert (stages.height >= 10 && plan.height >= 10);
      assert (Int.abs (stages.height - plan.height) <= 1);
      assert (stages.y = selector.y + selector.height);
      assert (plan.y = stages.y + stages.height && plan.y + plan.height = 38))
;;

let%test_unit "shuffled membership keeps tile-to-cell association and duplicate extras" =
  let kinds =
    [ "timing"
    ; "workspace-tabs"
    ; "synthesis"
    ; "live-status"
    ; "run-selector"
    ; "stage-checklist"
    ; "checks"
    ; "run-selector"
    ; "custom"
    ]
  in
  match Layout.compute Overview.definition ~width:180 ~height:80 ~kinds with
  | Compact -> assert false
  | Grid cells ->
    assert (List.length cells = List.length kinds);
    let nav = List.nth_exn cells 1
    and session = List.nth_exn cells 3
    and selector = List.nth_exn cells 4
    and duplicate = List.nth_exn cells 7 in
    assert (nav.y = 0 && nav.height = 1);
    assert (session.x = 0 && session.height = 7);
    assert (
      selector.y = session.y + session.height && selector.x = 0 && selector.height = 7);
    assert (duplicate.y > (List.nth_exn cells 6).y)
;;

let%test_unit "all presets preserve extras and duplicates with bounded disjoint cells" =
  List.iter Presets.all ~f:(fun d ->
    List.iter
      [ 1, 1; 24, 3; 32, 8; 80, 24; 120, 40; 180, 60; 240, 100 ]
      ~f:(fun (width, height) ->
        List.iter (List.range 0 20) ~f:(fun count ->
          let ks =
            kinds d
            @ List.init count ~f:(fun i ->
              if i % 2 = 0 then "run-selector" else "custom-provider")
          in
          match Layout.compute d ~width ~height ~kinds:ks with
          | Compact -> ()
          | Grid cells ->
            assert (List.length cells = List.length ks);
            List.iteri cells ~f:(fun i (a : Workspace.Geometry.t) ->
              assert (a.width >= 24 && a.height >= 1 && a.x >= 0 && a.y >= 0);
              assert (a.x + a.width <= width && a.y + a.height <= height);
              List.iter
                (List.drop cells (i + 1))
                ~f:(fun b ->
                  assert (
                    a.x + a.width <= b.x
                    || b.x + b.width <= a.x
                    || a.y + a.height <= b.y
                    || b.y + b.height <= a.y))))));
  assert (
    match
      Layout.compute
        Overview.definition
        ~width:32
        ~height:8
        ~kinds:(kinds Overview.definition)
    with
    | Compact -> true
    | _ -> false)
;;

let%test_unit "stable identity selects definitions after rename" =
  let s = Workspace.initial ~session_id:(Workspace.Session_id.of_string "presets") in
  let w = List.hd_exn s.workspaces in
  let renamed = { w with name = "My debugging desk" } in
  assert (String.equal (Option.value_exn (Presets.for_arrangement renamed)).id "overview");
  let custom = { w with preset = None; name = "Timing" } in
  assert (Option.is_none (Presets.for_arrangement custom))
;;

let%test_unit "portable current starters come directly from the shared definitions" =
  List.iter Presets.all ~f:(fun d ->
    let template = Definition.template d in
    Workspace_template.validate template |> Or_error.ok_exn;
    assert (Option.equal String.equal template.preset (Some d.id));
    assert (
      List.equal String.equal (List.map template.views ~f:(fun v -> v.kind)) (kinds d));
    List.iter2_exn template.views d.tiles ~f:(fun view tile ->
      let g = view.geometry
      and h = tile.Common.geometry in
      assert (g.x = h.x && g.y = h.y && g.width = h.width && g.height = h.height)))
;;

let%test_unit "shared bootstrap completes after import and protects explicit user edits" =
  let ok = function
    | Ok s -> s
    | Error e -> raise_s [%sexp (e : V1.Error.t)]
  in
  let s = Workspace.initial ~session_id:(Workspace.Session_id.of_string "bootstrap") in
  let mutate (s : Workspace.Snapshot.t) mutation =
    Workspace.apply s (Mutate { expected_revision = s.revision; mutation }) |> ok
  in
  let first = List.hd_exn s.tiles in
  let geometry : Workspace.Geometry.t = { x = 3; y = 5; width = 33; height = 11 } in
  let s = mutate s (Resize_tile { tile = first.id; geometry }) in
  let s = mutate s (Set_tile_hidden { tile = first.id; hidden = true }) in
  let template =
    { (Definition.template Overview.definition) with
      name = "Sparse imported overview"
    ; views = []
    }
  in
  let s =
    mutate s (Instantiate_template { window = (List.hd_exn s.windows).id; template })
  in
  let imported = List.last_exn s.workspaces in
  let next = Workspace.apply s Presets.bootstrap |> ok in
  assert next.defaults_initialized;
  assert (Workspace.Tile.equal (Workspace.tile s first.id) (Workspace.tile next first.id));
  assert (
    Workspace_template.equal template (Workspace.export_template next imported.id |> ok));
  List.iter (List.take next.workspaces 2) ~f:(fun w ->
    let d = Presets.for_arrangement w |> Option.value_exn in
    let tiles =
      List.filter next.tiles ~f:(fun t -> Workspace.Workspace_id.equal t.workspace w.id)
    in
    assert (List.length tiles = List.length d.tiles);
    List.iter d.tiles ~f:(fun expected ->
      let tile =
        List.find_exn tiles ~f:(fun t -> String.equal t.kind expected.Common.kind)
      in
      if not (Workspace.Tile_id.equal tile.id first.id)
      then assert (Workspace.Geometry.equal tile.requested_geometry expected.geometry)));
  assert (Workspace.Snapshot.equal next (Workspace.apply next Presets.bootstrap |> ok))
;;

let%test_unit "unknown preset IDs never select a known definition by display name" =
  let s = Workspace.initial ~session_id:(Workspace.Session_id.of_string "unknown") in
  let w =
    { (List.hd_exn s.workspaces) with
      preset = Some "future-workspace"
    ; name = "Overview"
    }
  in
  assert (Option.is_none (Presets.for_arrangement w))
;;

let%test_unit "shared restore API repairs every preset in the captured renamed workspace" =
  let ok = function
    | Ok s -> s
    | Error e -> raise_s [%sexp (e : V1.Error.t)]
  in
  List.iter Presets.all ~f:(fun d ->
    let s =
      Workspace.initial ~session_id:(Workspace.Session_id.of_string "restore-api")
    in
    let w = List.hd_exn s.workspaces in
    let mutate (s : Workspace.Snapshot.t) mutation =
      Workspace.apply s (Mutate { expected_revision = s.revision; mutation }) |> ok
    in
    let first = List.hd_exn s.tiles in
    let s =
      mutate s (Rename_workspace { workspace = w.id; name = "Captured custom desk" })
    in
    let s = mutate s (Set_tile_hidden { tile = first.id; hidden = true }) in
    let s =
      mutate
        s
        (Create_tile
           { workspace = w.id
           ; kind = "custom-extra"
           ; geometry = first.requested_geometry
           })
    in
    let extra = List.last_exn s.tiles in
    let s = mutate s (Set_zoom { workspace = w.id; tile = Some extra.id }) in
    let mutation = Definition.restore d ~workspace:w.id in
    assert (
      Workspace.Mutation.equal
        mutation
        (Restore_default_layout
           { workspace = w.id; preset = d.id; tiles = Definition.specs d }));
    let next = mutate s mutation in
    assert (next.revision = s.revision + 1);
    assert (String.equal (Workspace.workspace next w.id).name "Captured custom desk");
    assert (Option.equal String.equal (Workspace.workspace next w.id).preset (Some d.id));
    assert (Option.is_none (Workspace.workspace next w.id).zoomed_tile);
    assert (List.equal Workspace.Context.equal s.contexts next.contexts);
    assert (
      Workspace.Tile.equal (Workspace.tile next extra.id) { extra with hidden = true });
    List.iter d.tiles ~f:(fun expected ->
      let actual =
        List.find_exn next.tiles ~f:(fun t ->
          Workspace.Workspace_id.equal t.workspace w.id
          && String.equal t.kind expected.Common.kind)
      in
      assert (not actual.hidden);
      assert (Workspace.Geometry.equal actual.requested_geometry expected.geometry));
    let visible =
      List.filter next.tiles ~f:(fun t ->
        Workspace.Workspace_id.equal t.workspace w.id && not t.hidden)
    in
    assert (List.length visible = List.length d.tiles);
    let repeated = mutate next mutation in
    assert (Workspace.Snapshot.equal { next with revision = repeated.revision } repeated))
;;

let%test_unit "sparse membership and resize thresholds never overflow or overlap" =
  let all = kinds Overview.definition in
  List.iter
    (List.range 0 (1 lsl List.length all))
    ~f:(fun mask ->
      let kinds = List.filteri all ~f:(fun i _ -> mask land (1 lsl i) <> 0) in
      List.iter
        [ 0, 0; 23, 5; 24, 6; 48, 16; 49, 16; 74, 23; 80, 22; 120, 31; 120, 32; 120, 38 ]
        ~f:(fun (width, height) ->
          match Layout.compute Overview.definition ~width ~height ~kinds with
          | Compact -> ()
          | Grid cells ->
            assert (List.length cells = List.length kinds);
            List.iteri cells ~f:(fun i (a : Workspace.Geometry.t) ->
              assert (a.width >= 24 && a.height > 0 && a.x >= 0 && a.y >= 0);
              assert (a.x + a.width <= width && a.y + a.height <= height);
              List.iter
                (List.drop cells (i + 1))
                ~f:(fun b ->
                  assert (
                    a.x + a.width <= b.x
                    || b.x + b.width <= a.x
                    || a.y + a.height <= b.y
                    || b.y + b.height <= a.y)))))
;;
