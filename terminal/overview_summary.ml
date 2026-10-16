open! Core
open Hardcaml_workbench_protocol
open Bonsai_term
module O = Overview_tiles

let supports = function
  | "synthesis" | "timing" | "placement" | "routing" | "checks" | "finalization" -> true
  | _ -> false
;;

let rows ?stage_id ~kind ~run ~summary ~stages () =
  let stage_id = Option.value stage_id ~default:kind in
  let summary =
    Option.filter summary ~f:(fun (s : Asic.Summary.t) -> Run_ref.equal s.run run)
  in
  let details =
    [ "Run: " ^ O.run_identity run; "Stage ID: " ^ stage_id ]
    @ Option.value_map summary ~default:[] ~f:(fun s ->
      [ "Source digest: " ^ s.source_digest
      ; "Producer: " ^ s.producer
      ; "Execution file: " ^ s.execution_file
      ; "Observed at: " ^ s.observed_at
      ]
      @ Option.value_map s.terminal ~default:[] ~f:(fun t ->
        [ "Finalization attempt: " ^ t.attempt
        ; "Results digest: " ^ t.results_digest
        ; "Results file: " ^ t.results_file
        ]))
  in
  let plain ?(role = O.Role.Muted) ?(extra = []) label value =
    O.row ~role ~details:(details @ extra) label value
  in
  let stage =
    match
      List.filter stages ~f:(fun (s : Asic.Stage.t) -> String.equal s.id stage_id)
    with
    | [ stage ] -> O.asic_stage_row ~run ~selected:false stage
    | stages ->
      plain
        "Stage"
        (if List.is_empty stages then "not reported" else "ambiguous duplicate stage IDs")
  in
  let freshness =
    match summary with
    | None -> plain "Evidence" "not loaded for this run"
    | Some s ->
      let value, role = O.freshness_label s.freshness in
      plain
        ~role
        ~extra:
          (match s.freshness with
           | Refresh_failed reason -> [ "Refresh error: " ^ reason ]
           | _ -> [])
        "Evidence"
        value
  in
  let metric (m : Asic.Metric.t) =
    plain
      ~extra:
        ([ "Metric key: " ^ m.key ]
         @ Option.to_list (Option.map m.source ~f:(fun s -> "Metric source: " ^ s)))
      ("Aggregate " ^ if String.is_empty m.label then m.key else m.label)
      (let value =
         match m.value with
         | Some value when not (Float.is_finite value) -> "invalid (non-finite)"
         | Some value when String.equal m.availability "available" ->
           sprintf
             "%g%s"
             value
             (Option.value_map m.unit_ ~default:" (unit not reported)" ~f:(fun u ->
                " " ^ u))
         | _ -> "unavailable"
       in
       value
       ^ " ["
       ^ (if String.is_empty m.availability
          then "availability not reported"
          else m.availability)
       ^ "]")
  in
  let fact field label value =
    plain
      ~role:(O.Fact.role field value)
      label
      (if String.is_empty value then "not reported" else value)
  in
  let evidence =
    match summary with
    | None -> []
    | Some s ->
      let terminal = s.terminal in
      let terminal_metrics keys =
        Option.value_map terminal ~default:[] ~f:(fun t ->
          List.filter_map t.metrics ~f:(fun m ->
            if List.mem keys m.Asic.Metric.key ~equal:String.equal
            then Some (metric m)
            else None))
      in
      (match kind with
       | "synthesis" ->
         [ plain
             "Reported cells (agg.)"
             (match Synthesis.Total.of_reported s.cell_count with
              | Unknown -> "not reported"
              | Zero -> "0"
              | Positive n -> Int.to_string n
              | Invalid n -> sprintf "invalid (%d)" n)
         ; plain
             "Cell breakdown"
             (if List.is_empty s.cells
              then "not reported"
              else sprintf "%d reported types" (List.length (Synthesis.project s).rows))
         ]
       | "timing" ->
         (match terminal_metrics [ "setup_slack"; "hold_slack" ] with
          | [] -> [ plain "Aggregate slack" "unavailable / not reported" ]
          | rows -> rows)
       | "placement" ->
         (match terminal_metrics [ "final_standard_cell_area"; "final_utilization" ] with
          | [] -> [ plain "Aggregate resources" "unavailable / not reported" ]
          | rows -> rows)
       | "routing" -> [ plain "Routing-stage metrics" "unsupported / not reported" ]
       | "checks" ->
         Option.value_map
           terminal
           ~default:[ plain "Checks" "terminal result not imported" ]
           ~f:(fun t ->
             if List.is_empty t.checks
             then [ plain "Checks" "not reported" ]
             else
               List.map t.checks ~f:(fun c ->
                 let r = fact Verdict ("Check " ^ c.name) c.status in
                 { r with
                   details =
                     r.details
                     @ Option.to_list (Option.map c.reason ~f:(fun s -> "Reason: " ^ s))
                     @ Option.to_list (Option.map c.source ~f:(fun s -> "Source: " ^ s))
                 }))
       | "finalization" ->
         Option.value_map
           terminal
           ~default:[ plain "Terminal result" "not imported" ]
           ~f:(fun t ->
             [ fact Verdict "Acceptance (agg.)" t.acceptance
             ; fact Physical_completion "Physical (agg.)" t.physical_completion
             ; fact Operation "Operation (agg.)" t.operation_status
             ; fact Verdict "Timing goal (agg.)" t.timing_goal
             ])
       | _ -> [ plain "Domain" "unsupported" ])
  in
  (* Keep freshness ahead of cached facts even in a very short panel. Stage request and
     outcomes remain independent of imported metrics and terminal acceptance. *)
  stage :: freshness :: evidence
;;

let%test_unit "typed metrics preserve zero, units, missing and nonfinite without a \
               verdict"
  =
  let run = Fs0_fixture.run_a in
  let metric value availability : Asic.Metric.t =
    { key = "setup_slack"
    ; label = "pass is a provider label"
    ; value
    ; availability
    ; unit_ = Some "ns"
    ; source = Some "exact metric source"
    }
  in
  let terminal metrics : Asic.Terminal_result.t =
    { attempt = "attempt"
    ; results_file = "results"
    ; results_digest = "results-digest"
    ; operation_status = "completed"
    ; physical_completion = "incomplete"
    ; acceptance = "not_evaluated"
    ; timing_goal = "unknown"
    ; metrics
    ; checks = []
    ; evidence = "{}"
    }
  in
  let summary metrics : Asic.Summary.t =
    { run
    ; source_digest = "digest"
    ; execution_file = "execution"
    ; plan_identity = None
    ; cell_count = None
    ; cells = []
    ; metrics = []
    ; terminal = Some (terminal metrics)
    ; timing = []
    ; completion = "completed"
    ; acceptance = "pass"
    ; producer = "provider"
    ; observed_at = "now"
    ; freshness = Refresh_failed "offline"
    }
  in
  List.iter
    [ Some 0., "available", "0 ns [available]"
    ; None, "available", "unavailable [available]"
    ; Some 12., "not_requested", "unavailable [not_requested]"
    ; Some Float.nan, "available", "invalid (non-finite) [available]"
    ]
    ~f:(fun (value, availability, expected) ->
      let rs =
        rows
          ~kind:"timing"
          ~run
          ~summary:(Some (summary [ metric value availability ]))
          ~stages:[]
          ()
      in
      let r = List.nth_exn rs 2 in
      [%test_result: string] r.value ~expect:expected;
      [%test_result: O.Role.t] r.role ~expect:Muted;
      assert (Option.is_none r.status);
      List.iter
        [ "Metric source: exact metric source"
        ; "Source digest: digest"
        ; "Results digest: results-digest"
        ]
        ~f:(fun text -> assert (List.mem r.details text ~equal:String.equal)));
  let rs = rows ~kind:"finalization" ~run ~summary:(Some (summary [])) ~stages:[] () in
  let acceptance = List.nth_exn rs 2 in
  [%test_result: string] acceptance.value ~expect:"not_evaluated";
  [%test_result: O.Role.t] acceptance.role ~expect:Warning
;;

let%test_unit "typed compact facts fence run, availability and acceptance" =
  let run = Fs0_fixture.run_a in
  let summary : Asic.Summary.t =
    { run
    ; source_digest = "digest"
    ; execution_file = "execution"
    ; plan_identity = None
    ; cell_count = Some 0
    ; cells = []
    ; metrics = []
    ; terminal = None
    ; timing = []
    ; completion = "completed"
    ; acceptance = "pass"
    ; producer = "provider"
    ; observed_at = "now"
    ; freshness = Cached_unverified
    }
  in
  let get kind summary = rows ~kind ~run ~summary ~stages:[] () in
  let rs = get "synthesis" (Some summary) in
  assert (String.equal (List.nth_exn rs 2).value "0");
  assert (String.equal (List.nth_exn rs 1).value "cached/unverified");
  assert (List.for_all rs ~f:(fun r -> Option.is_none r.status));
  let other = { summary with run = { run with id = "foreign" } } in
  assert (List.length (get "synthesis" (Some other)) = 2);
  let finalization = get "finalization" (Some summary) in
  assert (String.equal (List.nth_exn finalization 2).value "not imported");
  assert (List.for_all finalization ~f:(fun r -> not (String.equal r.value "pass")))
;;

let%test_unit "compact evidence uses actual panel content bounds at accepted terminal \
               sizes"
  =
  let module W = Hardcaml_workbench_workspaces in
  let d = W.Overview.definition in
  let kinds = List.map d.tiles ~f:(fun t -> t.W.Common.kind) in
  let appearance = Appearance.default in
  List.iter
    [ 80, 24; 120, 40; 240, 80 ]
    ~f:(fun (width, terminal_height) ->
      let height = terminal_height - 2 in
      let cells =
        match W.Layout.compute d ~width ~height ~kinds with
        | Compact ->
          assert (width = 80);
          [ "synthesis", { Workspace.Geometry.x = 0; y = 0; width; height } ]
        | Grid cells -> List.zip_exn kinds cells
      in
      let evidence = List.filter cells ~f:(fun (kind, _) -> supports kind) in
      assert (List.length evidence = if width = 80 then 1 else 6);
      List.iter evidence ~f:(fun (kind, g) ->
        let geometry =
          Panel.geometry
            ~framed:true
            ~width:g.width
            ~height:g.height
            ~horizontal_padding:1
            ~vertical_padding:0
        in
        assert (geometry.content_height >= 4);
        let content =
          O.render
            ~appearance
            ~attrs:(fun _ -> [])
            ~width:geometry.content_width
            ~height:geometry.content_height
            (rows ~kind ~run:Fs0_fixture.run_a ~summary:None ~stages:[] ())
        in
        let view =
          Panel.render
            appearance
            ~attrs:[]
            ~title:(View.text kind)
            ~geometry
            ~width:g.width
            ~height:g.height
            content
        in
        assert (View.width view = g.width && View.height view = g.height)))
;;
