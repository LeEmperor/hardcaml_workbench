open! Core
open Hardcaml_workbench_protocol
open Bonsai_term
module V = Host_view

let measured n = Execution_timing.make ~measured_seconds:n ~running:false ()

let%test_unit "Overview actual five-row tiles show exact selected and pinned execution \
               scopes"
  =
  let host, data, find =
    V.refinement_fixture Hardcaml_workbench_workspaces.Overview.definition
  in
  let now = Time_ns.epoch in
  let snapshot = Option.value_exn data.asic in
  let snapshot =
    { snapshot with
      runs =
        List.map snapshot.runs ~f:(fun r ->
          let seconds = if Run_ref.equal r.run Fs0_fixture.run_a then 127. else 14. in
          { r with
            execution_timing = measured seconds
          ; stages =
              List.map r.stages ~f:(fun s ->
                let seconds =
                  if not (Run_ref.equal r.run Fs0_fixture.run_a)
                  then 29.
                  else (
                    match s.id with
                    | "synthesis" -> 127.
                    | "placement" -> 14.
                    | "routing" -> 61.
                    | _ -> 9.)
                in
                { s with execution_timing = measured seconds })
          })
    ; finalizations =
        [ { Asic.Finalization.key = "receipt"
          ; run = Fs0_fixture.run_a
          ; execution_file = "execution"
          ; acceptance_requested = false
          ; attempt = Some "final"
          ; state = "completed"
          ; phase = None
          ; operation_status = Some "completed"
          ; acceptance = None
          ; error = None
          ; owned = false
          ; execution_timing = measured 3723.
          }
        ]
    }
  in
  let data = { data with asic = Some snapshot } in
  let text ?(host = host) ?(height = 5) ?(width = 60) tile =
    V.tile_view ~now host data tile ~width ~height |> V.plain_text
  in
  let pin_host (tile : Workspace.Tile.t) =
    { host with
      registry =
        Option.map host.registry ~f:(fun r ->
          { r with
            tiles =
              List.map r.tiles ~f:(fun t ->
                if Workspace.Tile_id.equal t.id tile.id then tile else t)
          })
    }
  in
  List.iter
    [ "synthesis", "2m 07s"; "placement", "14s"; "routing", "1m 01s" ]
    ~f:(fun (kind, expected) ->
      let tile = find kind in
      assert (String.is_substring (text tile) ~substring:("Time: " ^ expected));
      let pin = { tile with binding = Pin_run Fs0_fixture.run_b } in
      let pinned = text ~host:(pin_host pin) pin in
      assert (String.is_substring pinned ~substring:"Time: 29s");
      assert (not (String.is_substring pinned ~substring:("Time: " ^ expected))));
  List.iter [ "timing"; "checks" ] ~f:(fun kind ->
    let rendered = text (find kind) in
    assert (String.is_substring rendered ~substring:("Time: unknown (stage " ^ kind ^ ")"));
    assert (not (String.is_substring rendered ~substring:"2m 07s")));
  assert (String.is_substring (text (find "finalization")) ~substring:"Time: 1h 02m 03s");
  assert (
    String.is_substring (text ~height:10 (find "run-selector")) ~substring:"Time: 2m 07s");
  let checklist = find "stage-checklist" in
  assert (String.is_substring (text ~height:10 checklist) ~substring:"Time: 2m 07s");
  let pinned = { checklist with binding = Pin_run Fs0_fixture.run_b } in
  assert (
    String.is_substring
      (text ~host:(pin_host pinned) ~height:10 pinned)
      ~substring:"Time: 29s");
  let stages = Overview_tiles.observed_stages ~asic:data.asic ~run:Fs0_fixture.run_a in
  let model =
    Overview_tiles.Stage_strip.model
      ~now
      ~appearance:host.appearance
      ~width:60
      ~run:Fs0_fixture.run_a
      ~selected_id:(Some "placement")
      stages
  in
  assert (String.equal (Option.value_exn model.selected).stage.id "placement");
  assert (
    Option.equal
      String.equal
      (Option.value_exn model.selected).row.time
      (Some "Time: 14s"));
  let view =
    Overview_tiles.Stage_strip.render
      ~appearance:host.appearance
      ~attrs:(fun _ -> [])
      ~width:60
      ~height:5
      model
  in
  assert (String.is_substring (V.plain_text view) ~substring:"Time: 2m 07s");
  List.iter [ 0; 1; 8; 22; 40; 60 ] ~f:(fun width ->
    let view = V.tile_view ~now host data checklist ~width ~height:5 in
    assert (View.width view = width && View.height view = 5));
  List.iter
    [ 120, 40; 240, 80 ]
    ~f:(fun (width, height) ->
      let _, _, layout = V.tile_layout host { Dimensions.width; height } in
      List.iter layout ~f:(fun (tile, g) ->
        if Overview_summary.supports tile.kind
           || String.equal tile.kind "run-selector"
           || String.equal tile.kind "stage-checklist"
        then (
          let rendered = text ~width:g.width ~height:g.height tile in
          assert (String.is_substring rendered ~substring:"Time: "))))
;;

let%test_unit "live Overview duration uses supplied clock; terminal run freezes; \
               statuses retain semantics"
  =
  let host, data, find =
    V.refinement_fixture Hardcaml_workbench_workspaces.Overview.definition
  in
  let snapshot = Option.value_exn data.asic in
  let live =
    Execution_timing.make
      ~started_at:(Timestamp.of_time_ns Time_ns.epoch)
      ~running:true
      ()
  in
  let snapshot =
    { snapshot with
      runs =
        List.map snapshot.runs ~f:(fun r ->
          { r with
            status = "running"
          ; execution_timing = live
          ; stages =
              List.map r.stages ~f:(fun s ->
                { s with execution_timing = live; status = Running })
          })
    }
  in
  let data =
    { data with
      asic = Some snapshot
    ; runs = List.map data.runs ~f:(fun (r, _) -> r, "running")
    }
  in
  let tile = find "synthesis" in
  let image now = V.tile_view ~now host data tile ~width:60 ~height:5 |> V.plain_text in
  assert (String.is_substring (image Time_ns.epoch) ~substring:"Time: 0s elapsed");
  assert (
    String.is_substring
      (image (Time_ns.add Time_ns.epoch (Time_ns.Span.of_sec 127.)))
      ~substring:"Time: 2m 07s elapsed");
  let _, _, layout = V.tile_layout host { Dimensions.width = 120; height = 40 } in
  let checklist, checklist_geometry =
    List.find_exn layout ~f:(fun (t, _) -> String.equal t.kind "stage-checklist")
  in
  let checklist_text =
    V.tile_view
      ~now:(Time_ns.add Time_ns.epoch (Time_ns.Span.of_sec 127.))
      host
      data
      checklist
      ~width:checklist_geometry.width
      ~height:checklist_geometry.height
    |> V.plain_text
  in
  assert (String.is_substring checklist_text ~substring:"Elapsed: 2m 07s");
  let selector, geometry =
    List.find_exn layout ~f:(fun (t, _) -> String.equal t.kind "run-selector")
  in
  List.iter
    [ 127., "Elapsed: 2m 07s"; 3723., "Elapsed: 1h 02m 03s" ]
    ~f:(fun (seconds, substring) ->
      let now = Time_ns.add Time_ns.epoch (Time_ns.Span.of_sec seconds) in
      let text =
        V.tile_view ~now host data selector ~width:geometry.width ~height:geometry.height
        |> V.plain_text
      in
      assert (String.is_substring text ~substring));
  assert (Poly.equal (V.run_indicator "running") Indicator.Running);
  let row =
    V.run_selector_view
      ~time:"Time: 2m 07s elapsed"
      host.appearance
      ~width:60
      ~status_width:7
      ~cursor:false
      ~active:false
      Fs0_fixture.run_a
      "running"
  in
  assert (
    String.is_substring (V.plain_text row) ~substring:"running | Time: 2m 07s elapsed")
;;

let%test_unit "Testing attempts paint duration on the list and advance with the render \
               clock"
  =
  let host, data, find =
    V.refinement_fixture Hardcaml_workbench_workspaces.Testing.definition
  in
  let tile = find "simulation-attempts" in
  let now = Time_ns.epoch in
  let attempt : Simulation.Summary.t =
    { id = "exact-attempt"
    ; job = Job_id.of_string "exact-job"
    ; suite = "suite"
    ; seed = "7"
    ; created_at = "unrelated evidence time"
    ; parent = None
    ; lifecycle = Running
    ; outcome = Unknown
    ; execution_timing =
        Execution_timing.make ~started_at:(Timestamp.of_time_ns now) ~running:true ()
    }
  in
  let snapshot : Simulation.Snapshot.t =
    { configured = true
    ; discovery = None
    ; discovery_digest = None
    ; discovery_job = None
    ; discovery_error = None
    ; attempts = [ attempt ]
    ; next_before = None
    ; detail = None
    ; byte_page = None
    ; history_error = None
    }
  in
  let host =
    Workspace_host.set_simulation
      host
      tile.id
      { Simulation_view.empty with snapshot = Some snapshot; attempt = Some attempt.id }
  in
  let paint now width = V.tile_view ~now host data tile ~width ~height:8 in
  let before = paint now 60 |> V.plain_text in
  let later = Time_ns.add now (Time_ns.Span.of_sec 127.) in
  let after = paint later 60 |> V.plain_text in
  assert (String.is_substring before ~substring:"Time: 0s elapsed");
  assert (String.is_substring after ~substring:"Time: 2m 07s elapsed");
  List.iter [ 8; 22; 40; 60 ] ~f:(fun width ->
    let view = paint later width in
    assert (View.width view = width && View.height view = 8));
  let frozen = { attempt with lifecycle = Finished; execution_timing = measured 0. } in
  let host =
    Workspace_host.set_simulation
      host
      tile.id
      { Simulation_view.empty with
        snapshot = Some { snapshot with attempts = [ frozen ] }
      }
  in
  let paint now = V.tile_view ~now host data tile ~width:60 ~height:8 |> V.plain_text in
  assert (String.equal (paint now) (paint later));
  assert (String.is_substring (paint later) ~substring:"Time: 0s")
;;
