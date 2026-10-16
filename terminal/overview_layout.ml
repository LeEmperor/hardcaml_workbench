open! Core
open Hardcaml_workbench_protocol
module G = Workspace.Geometry

(** Fit-only geometry. [Grid] has exactly one rectangle per input kind, in the same order
    (including duplicates and unfamiliar kinds). [Compact] asks the host to show its
    focused-tile fallback. No requested geometry is read/written. All cells have at least
    24 columns and 6 rows, except the explicit full-width workspace navigation band, which
    uses 3 rows. Gutters occupy one cell. *)
type t =
  | Grid of G.t list
  | Compact

let tracks ~total ~count =
  let usable = total - count + 1 in
  List.init count ~f:(fun i ->
    let size = (usable / count) + if i < usable % count then 1 else 0 in
    let offset = (i * ((usable / count) + 1)) + Int.min i (usable % count) in
    offset, size)
;;

let grid ~x ~y ~width ~height count =
  if count = 0
  then Some []
  else (
    let preferred = Int.min count (Int.min 4 (Int.max 1 ((width + 1) / 40))) in
    let columns =
      List.range 1 (Int.min 4 count + 1)
      |> List.filter ~f:(fun columns ->
        let rows = (count + columns - 1) / columns in
        width >= (columns * 24) + columns - 1 && height >= (rows * 6) + rows - 1)
      |> List.sort ~compare:(fun a b ->
        Int.compare (Int.abs (a - preferred)) (Int.abs (b - preferred)))
      |> List.hd
    in
    Option.map columns ~f:(fun columns ->
      let rows = (count + columns - 1) / columns in
      let xs = tracks ~total:width ~count:columns in
      let ys = tracks ~total:height ~count:rows in
      List.init count ~f:(fun i ->
        let dx, width = List.nth_exn xs (i % columns) in
        let dy, height = List.nth_exn ys (i / columns) in
        { G.x = x + dx; y = y + dy; width; height })))
;;

let sidebar_rank = function
  | "live-status" -> Some 0
  | "workspace-tabs" -> Some 1
  | "run-selector" -> Some 2
  | "stage-checklist" -> Some 3
  | _ -> None
;;

let overview ~width ~height kinds =
  let indexed = List.mapi kinds ~f:(fun i kind -> i, kind) in
  let sidebar, panels =
    List.partition_tf indexed ~f:(fun (_, k) -> Option.is_some (sidebar_rank k))
  in
  let sidebar =
    List.stable_sort sidebar ~compare:(fun (_, a) (_, b) ->
      Option.compare Int.compare (sidebar_rank a) (sidebar_rank b))
  in
  if List.is_empty sidebar || List.is_empty panels || width < 73
  then None
  else (
    let side_width = Int.max 24 (Int.min 32 (width / 4)) in
    let minima =
      List.map sidebar ~f:(fun (_, k) ->
        match k with
        | "live-status" -> 7
        | "stage-checklist" -> 9
        | "run-selector" -> 8
        | _ -> 6)
    in
    let needed = List.sum (module Int) minima ~f:Fn.id + List.length sidebar - 1 in
    if height < needed
    then None
    else (
      (* Reserve readable stage/status rows first. Spare height brings the first status
         surface toward ten rows before expanding the browsing surfaces. *)
      let status_index =
        List.findi sidebar ~f:(fun _ (_, k) -> String.equal k "live-status")
        |> Option.map ~f:fst
      in
      let status_extra =
        if Option.is_some status_index then Int.min 3 (height - needed) else 0
      in
      let remaining = height - needed - status_extra in
      let weights =
        List.map sidebar ~f:(fun (_, k) ->
          if String.equal k "run-selector" || String.equal k "stage-checklist"
          then 2
          else 0)
      in
      let total_weight = List.sum (module Int) weights ~f:Fn.id in
      let _, side_cells =
        List.foldi sidebar ~init:(0, []) ~f:(fun i (y, cells) (index, _) ->
          let extra =
            if total_weight = 0
            then remaining / List.length sidebar
            else remaining * List.nth_exn weights i / total_weight
          in
          let extra =
            extra
            + if Option.equal Int.equal status_index (Some i) then status_extra else 0
          in
          let h =
            if i = List.length sidebar - 1
            then height - y
            else List.nth_exn minima i + extra
          in
          y + h + 1, (index, { G.x = 0; y; width = side_width; height = h }) :: cells)
      in
      let x = side_width + 1 in
      let panel_width = width - x in
      (* A leading summary gets a full-width inspection surface when the remaining panels
         still meet their minima. Otherwise use all available main tracks. *)
      let main =
        let primary = List.find panels ~f:(fun (_, k) -> String.equal k "synthesis") in
        Option.bind primary ~f:(fun (primary_index, _) ->
          let rest = List.filter panels ~f:(fun (i, _) -> i <> primary_index) in
          if List.is_empty rest
          then None
          else (
            let h = Int.max 8 (height / 3) in
            Option.map
              (grid
                 ~x
                 ~y:(h + 1)
                 ~width:panel_width
                 ~height:(height - h - 1)
                 (List.length rest))
              ~f:(fun cells ->
                (primary_index, { G.x; y = 0; width = panel_width; height = h })
                :: List.map2_exn rest cells ~f:(fun (i, _) g -> i, g))))
        |> fun primary ->
        match primary with
        | Some _ -> primary
        | None ->
          Option.map
            (grid ~x ~y:0 ~width:panel_width ~height (List.length panels))
            ~f:(fun cells -> List.map2_exn panels cells ~f:(fun (i, _) g -> i, g))
      in
      Option.map main ~f:(fun main ->
        List.sort (side_cells @ main) ~compare:(fun (a, _) (b, _) -> Int.compare a b)
        |> List.map ~f:snd)))
;;

let compute ~width ~height ~kinds =
  let fit ~height kinds =
    match overview ~width ~height kinds with
    | Some cells -> Some cells
    | None -> grid ~x:0 ~y:0 ~width ~height (List.length kinds)
  in
  (* Only the first navigation tile owns the horizontal top band. Carry original indices
     through removal/reinsertion so duplicate/custom tiles remain visible and the host's
     tile-to-rectangle association never changes. *)
  let navigation =
    List.findi kinds ~f:(fun _ kind -> String.equal kind "workspace-tabs")
  in
  let with_navigation =
    Option.bind navigation ~f:(fun (index, _) ->
      if width < 24 || height < 3
      then None
      else (
        let remaining = List.filteri kinds ~f:(fun i _ -> i <> index) in
        Option.map
          (fit ~height:(height - 4) remaining)
          ~f:(fun cells ->
            let cells = List.map cells ~f:(fun g -> { g with G.y = g.y + 4 }) in
            List.take cells index
            @ [ { G.x = 0; y = 0; width; height = 3 } ]
            @ List.drop cells index)))
  in
  match with_navigation with
  | Some cells -> Grid cells
  | None ->
    (* A short viewport can fit every tile in ordinary tracks even when reserving a
       navigation band cannot. Never drop tiles to force the overview shape. *)
    let cells =
      match navigation with
      | Some _ -> grid ~x:0 ~y:0 ~width ~height (List.length kinds)
      | None -> fit ~height kinds
    in
    (match cells with
     | Some cells -> Grid cells
     | None -> Compact)
;;

let%test_unit "overview preserves arbitrary ordered tiles and gives summary more space" =
  let kinds =
    [ "timing"
    ; "stage-checklist"
    ; "live-status"
    ; "synthesis"
    ; "workspace-tabs"
    ; "run-selector"
    ; "checks"
    ; "logs"
    ; "unknown"
    ; "synthesis"
    ]
  in
  match compute ~width:120 ~height:40 ~kinds with
  | Compact -> assert false
  | Grid cells ->
    assert (List.length cells = List.length kinds);
    let status = List.nth_exn cells 2
    and summary = List.nth_exn cells 3 in
    assert (status.x = 0 && status.y = 4 && status.height = 10);
    assert (summary.width > status.width && summary.height > status.height);
    let navigation = List.nth_exn cells 4 in
    assert (
      navigation.x = 0
      && navigation.y = 0
      && navigation.width = 120
      && navigation.height = 3);
    assert ((List.nth_exn cells 1).height >= 9);
    assert ((List.nth_exn cells 5).height >= 8);
    assert ((List.nth_exn cells 5).y < (List.nth_exn cells 1).y);
    List.iteri cells ~f:(fun i g -> if i <> 4 then assert (g.y >= 4))
;;

let%test_unit "top navigation preserves duplicates and falls back without losing tiles" =
  let kinds =
    [ "custom"
    ; "workspace-tabs"
    ; "workspace-tabs"
    ; "live-status"
    ; "stage-checklist"
    ; "run-selector"
    ; "synthesis"
    ]
  in
  (match compute ~width:120 ~height:48 ~kinds with
   | Compact -> assert false
   | Grid cells ->
     assert (List.length cells = List.length kinds);
     let first = List.nth_exn cells 1
     and duplicate = List.nth_exn cells 2 in
     assert (first.y = 0 && first.width = 120 && first.height = 3);
     assert (duplicate.y >= 4 && duplicate.width < 120 && duplicate.height >= 6);
     assert ((List.nth_exn cells 3).x = 0 && (List.nth_exn cells 3).y = 4);
     assert ((List.nth_exn cells 4).height >= 9));
  (* At six rows both tiles fit side by side, but the three-row band plus a gutter would
     leave fewer than six rows for the ordinary status tile. *)
  (match compute ~width:80 ~height:6 ~kinds:[ "live-status"; "workspace-tabs" ] with
   | Compact -> assert false
   | Grid cells ->
     assert (List.length cells = 2);
     assert (List.for_all cells ~f:(fun g -> g.y = 0 && g.height = 6)));
  (* The smallest useful sidebar honors content minima even before spare rows. *)
  (match
     compute
       ~width:120
       ~height:30
       ~kinds:
         [ "workspace-tabs"
         ; "live-status"
         ; "run-selector"
         ; "stage-checklist"
         ; "synthesis"
         ]
   with
   | Compact -> assert false
   | Grid cells ->
     assert ((List.nth_exn cells 1).height = 7);
     assert ((List.nth_exn cells 2).height = 8);
     assert ((List.nth_exn cells 3).height = 9));
  match compute ~width:24 ~height:3 ~kinds:[ "workspace-tabs" ] with
  | Compact -> assert false
  | Grid [ navigation ] ->
    assert (navigation.width = 24 && navigation.height = 3 && navigation.y = 0)
  | Grid _ -> assert false
;;

let%test_unit "all fit rectangles obey minima, bounds, gutters, and cardinality" =
  List.iter
    [ 1, 1; 24, 3; 80, 6; 80, 10; 32, 8; 68, 20; 80, 24; 120, 40; 180, 60 ]
    ~f:(fun (width, height) ->
      List.iter (List.range 0 25) ~f:(fun count ->
        let kinds =
          List.init count ~f:(fun i ->
            List.nth_exn
              [ "live-status"
              ; "workspace-tabs"
              ; "run-selector"
              ; "stage-checklist"
              ; "synthesis"
              ; "custom"
              ]
              (i % 6))
        in
        match compute ~width ~height ~kinds with
        | Compact -> ()
        | Grid cells ->
          assert (List.length cells = count);
          List.iteri cells ~f:(fun i a ->
            let navigation_band =
              String.equal (List.nth_exn kinds i) "workspace-tabs"
              && (not (List.mem (List.take kinds i) "workspace-tabs" ~equal:String.equal))
              && a.x = 0
              && a.y = 0
              && a.width = width
              && a.height = 3
            in
            assert (
              a.width >= 24 && (a.height >= 6 || navigation_band) && a.x >= 0 && a.y >= 0);
            assert (a.x + a.width <= width && a.y + a.height <= height);
            List.iter
              (List.drop cells (i + 1))
              ~f:(fun b ->
                assert (
                  a.x + a.width < b.x
                  || b.x + b.width < a.x
                  || a.y + a.height < b.y
                  || b.y + b.height < a.y)))));
  match compute ~width:32 ~height:8 ~kinds:[ "live-status"; "workspace-tabs" ] with
  | Compact -> ()
  | Grid _ -> assert false
;;
