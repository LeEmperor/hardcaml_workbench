open! Core
open Hardcaml_workbench_protocol
open Hardcaml_workbench_workspaces

let kinds d = List.map d.Definition.tiles ~f:(fun t -> t.Common.kind)

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
        assert (List.length cells = 10);
        List.iteri cells ~f:(fun i (a : Workspace.Geometry.t) ->
          assert (a.x >= 0 && a.y >= 0 && a.width > 0 && a.height > 0);
          assert (a.x + a.width <= width && a.y + a.height <= height);
          List.iter
            (List.drop cells (i + 1))
            ~f:(fun b ->
              assert (
                a.x + a.width < b.x
                || b.x + b.width < a.x
                || a.y + a.height < b.y
                || b.y + b.height < a.y))))
;;

let%test_unit "wide shallow selector and six compact evidence panels cover Overview" =
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
    assert (session.width = 24 && session.height = 7);
    assert (selector.x > session.x && selector.y = session.y && selector.height = 7);
    assert (selector.width > 3 * session.width);
    assert ((cell "stage-checklist").y > session.y);
    assert ((cell "synthesis").y > selector.y);
    assert ((cell "timing").y = (cell "synthesis").y);
    assert ((cell "timing").x > (cell "synthesis").x);
    assert ((cell "placement").y > (cell "timing").y);
    assert ((cell "checks").y > (cell "placement").y);
    List.iter
      [ "synthesis"; "timing"; "placement"; "routing"; "checks"; "finalization" ]
      ~f:(fun kind ->
        let g = cell kind in
        assert (g.width >= 59 && g.height >= 6));
    assert ((cell "workspace-tabs").height = 1)
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
    assert (selector.y = session.y && selector.x > 0 && selector.height = 7);
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
                    a.x + a.width < b.x
                    || b.x + b.width < a.x
                    || a.y + a.height < b.y
                    || b.y + b.height < a.y))))));
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
                    a.x + a.width < b.x
                    || b.x + b.width < a.x
                    || a.y + a.height < b.y
                    || b.y + b.height < a.y)))))
;;
