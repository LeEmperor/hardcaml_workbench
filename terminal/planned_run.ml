open! Core
open Hardcaml_workbench_protocol

type status =
  | Empty
  | Pending
  | Failed
  | Stale
  | Ready
[@@deriving equal, sexp]

type model =
  { status : status
  ; selection : Asic.Selection.t option
  ; preview : Asic.Preview.t option
  ; requested : Asic.Selection.t option
  ; operation_key : string option
  ; message : string
  }

type role =
  | Fact
  | Muted
  | Warning
  | Error
  | Success
[@@deriving equal, sexp]

type row =
  { role : role
  ; text : string
  }

type ticket =
  { scope : string
  ; generation : int
  }

type intent =
  { selection : Asic.Selection.t
  ; key : string
  ; acknowledged : bool
  ; floor : int
  ; error : string option
  }

type t =
  { scope : string
  ; generation : int
  ; revision : int
  ; intent : intent option
  ; snapshot : Asic.Snapshot.t option
  }

let empty = { scope = ""; generation = 0; revision = -1; intent = None; snapshot = None }

let reset t ~scope =
  if String.equal scope t.scope
  then t
  else { empty with scope; generation = t.generation + 1 }
;;

let key selection = List.hd_exn (Plain_rpc.keys (Plan selection) Fs0_fixture.snapshot)

let begin_plan t selection =
  let generation = t.generation + 1 in
  ( { t with
      generation
    ; intent =
        Some
          { selection
          ; key = key selection
          ; acknowledged = false
          ; floor = Int.max_value
          ; error = None
          }
    }
  , { scope = t.scope; generation } )
;;

let current_ticket t (ticket : ticket) =
  String.equal t.scope ticket.scope
  && t.generation = ticket.generation
  && Option.is_some t.intent
;;

let receipt t ticket ~floor result =
  if not (current_ticket t ticket)
  then t
  else
    { t with
      intent =
        Option.map t.intent ~f:(fun i ->
          { i with acknowledged = true; floor; error = Result.error result })
    }
;;

let receive t ~revision snapshot =
  if revision < t.revision
  then t
  else (
    let intent =
      Option.filter t.intent ~f:(fun i ->
        not
          (i.acknowledged
           && Option.is_none i.error
           && revision >= i.floor
           && Option.exists snapshot.Asic.Snapshot.preview ~f:(fun p ->
             Asic.Selection.equal p.selection i.selection)
           && List.exists snapshot.operations ~f:(fun op ->
             String.equal op.key i.key && String.equal op.state "completed")
           && not
                (List.exists snapshot.operations ~f:(fun op ->
                   String.equal op.kind "plan" && Plain_rpc.active op))))
    in
    { t with revision; snapshot = Some snapshot; intent })
;;

let model t =
  let preview = Option.bind t.snapshot ~f:(fun s -> s.preview) in
  let plans =
    Option.value_map t.snapshot ~default:[] ~f:(fun s ->
      List.filter s.operations ~f:(fun op -> String.equal op.kind "plan"))
  in
  let operation key = List.find plans ~f:(fun op -> String.equal op.key key) in
  let active = List.exists plans ~f:Plain_rpc.active in
  let make ?selection ?requested ?operation_key status message =
    { status; selection; requested; operation_key; preview; message }
  in
  let shared () =
    match preview with
    | Some p ->
      let operation_key = key p.selection in
      let status, message =
        if active
        then Pending, "Shared plan operation pending; retained preview is not ready"
        else (
          match operation operation_key with
          | Some op when String.equal op.state "completed" ->
            Ready, "Plan ready; launch explicitly (no job allocated)"
          | Some op when String.equal op.state "failed" ->
            Failed, Option.value op.error ~default:"Plan failed"
          | _ -> Stale, "Preview retained; exact completed plan operation unavailable")
      in
      make ~selection:p.selection ~operation_key status message
    | None ->
      if active
      then make Pending "Shared plan pending; selection not published by daemon yet"
      else (
        match List.find plans ~f:(fun op -> String.equal op.state "failed") with
        | Some op ->
          make
            ~operation_key:op.key
            Failed
            ("Shared preview unavailable; observed plan failure (selection/order \
              unpublished): "
             ^ Option.value op.error ~default:"plan operation failed")
        | None ->
          if List.is_empty plans
          then make Empty "No plan preview; stage r or palette Plan prepares a plan"
          else
            make
              Stale
              "Plan operation retained but current preview absent; prepare explicitly \
               again")
  in
  match t.intent with
  | None -> shared ()
  | Some i ->
    let local status message =
      make
        ~selection:i.selection
        ~requested:i.selection
        ~operation_key:i.key
        status
        message
    in
    (match i.error with
     | Some error -> local Failed ("Plan request failed/unconfirmed: " ^ error)
     | None when (not i.acknowledged) || t.revision < i.floor ->
       local Pending "Plan requested; waiting for matching request receipt/observation"
     | None ->
       (match operation i.key with
        | Some op when Plain_rpc.active op ->
          local Pending "Requested plan pending; previous preview is not ready"
        | Some op when String.equal op.state "failed" ->
          local Failed (Option.value op.error ~default:"Requested plan failed")
        | Some op when String.equal op.state "completed" ->
          (match preview with
           | Some p when Asic.Selection.equal p.selection i.selection -> shared ()
           | _ ->
             let m = shared () in
             { m with
               status = Stale
             ; requested = Some i.selection
             ; message =
                 "Requested plan completed but preview is absent/superseded; inspect \
                  current shared selection: "
                 ^ m.message
             })
        | _ ->
          local
            Stale
            "Requested plan operation expired or unavailable; prepare explicitly again"))
;;

let launchable t preview =
  let m = model t in
  equal_status m.status Ready && Option.equal Asic.Preview.equal m.preview (Some preview)
;;

let rows m ~detail =
  let role =
    match m.status with
    | Ready -> Success
    | Failed -> Error
    | Pending | Stale -> Warning
    | Empty -> Muted
  in
  let state = String.lowercase (Sexp.to_string (sexp_of_status m.status)) in
  let facts selection =
    [ { role = Fact
      ; text =
          "flow: "
          ^ selection.Asic.Selection.flow
          ^ " / profile: "
          ^ selection.profile
          ^ " / endpoint: "
          ^ selection.endpoint
      }
    ; { role = Fact
      ; text =
          ("assignments: "
           ^
           if List.is_empty selection.assignments
           then "(none)"
           else String.concat ~sep:"; " selection.assignments)
      }
    ]
  in
  [ { role; text = state ^ ": " ^ m.message } ]
  @ Option.value_map m.selection ~default:[] ~f:facts
  @
  if not detail
  then []
  else
    Option.value_map m.operation_key ~default:[] ~f:(fun key ->
      [ { role = Muted; text = "plan operation: " ^ key } ])
    @ Option.value_map m.requested ~default:[] ~f:(fun selection ->
      { role = Muted; text = "local requested selection (not a producer association):" }
      :: facts selection)
    @ Option.value_map m.preview ~default:[] ~f:(fun p ->
      (if equal_status m.status Ready
       then []
       else
         [ { role = Warning
           ; text =
               "Retained/unconfirmed shared preview below; not ready for current intent."
           }
         ])
      @ [ { role = Fact; text = "exact plan identity: " ^ p.plan_identity }
        ; { role = Muted; text = "shared preview selection:" }
        ]
      @ facts p.selection
      @ [ { role = Muted; text = "exact plan metadata (JSON):" } ]
      @ List.map (String.split_lines p.plan_json) ~f:(fun text -> { role = Fact; text }))
    @ [ { role = Muted
        ; text =
            "Plan only; no queued job, allocated run or historical producer association."
        }
      ]
;;

let max_scroll m ~detail = Int.max 0 (List.length (rows m ~detail) - 1)

let%test_unit "old ready to local pending, transport failure, retry and new ready" =
  let a : Asic.Selection.t =
    { flow = "flow"; profile = "profile"; endpoint = "a"; assignments = [ "x=1" ] }
  in
  let b = { a with endpoint = "b" } in
  let preview selection identity : Asic.Preview.t =
    { selection; plan_identity = identity; plan_json = "{}" }
  in
  let pa = preview a "exact-a"
  and pb = preview b "exact-b" in
  let op selection state : Asic.Pending.t =
    { key = key selection; kind = "plan"; state; run = None; error = None }
  in
  let snap p ops = { Fs0_fixture.snapshot with preview = p; operations = ops } in
  let ready =
    receive
      (reset empty ~scope:"daemon/project")
      ~revision:1
      (snap (Some pa) [ op a "completed" ])
  in
  assert (launchable ready pa);
  let pending, ticket = begin_plan ready b in
  assert (equal_status (model pending).status Pending && not (launchable pending pa));
  let failed = receipt pending ticket ~floor:2 (Error "transport") in
  let failed = receive failed ~revision:3 (snap (Some pa) [ op a "completed" ]) in
  assert (equal_status (model failed).status Failed && not (launchable failed pa));
  let retry, current = begin_plan failed b in
  let retry = receipt retry ticket ~floor:3 (Error "late old failure") in
  assert (equal_status (model retry).status Pending);
  let retry = receipt retry current ~floor:5 (Ok ()) in
  let retry = receive retry ~revision:4 (snap (Some pb) [ op b "completed" ]) in
  assert (equal_status (model retry).status Pending);
  let retry = receive retry ~revision:5 (snap (Some pb) [ op b "failed" ]) in
  assert (equal_status (model retry).status Failed);
  let retry = receive retry ~revision:6 (snap (Some pb) [ op b "completed" ]) in
  assert (launchable retry pb);
  let delayed = receive retry ~revision:2 (snap (Some pa) [ op a "completed" ]) in
  assert (launchable delayed pb);
  let foreign =
    receive retry ~revision:7 (snap (Some pa) [ op a "completed"; op b "completed" ])
  in
  assert (launchable foreign pa);
  let pending, ticket = begin_plan retry b in
  assert (not (launchable pending pb));
  let pending = receipt pending ticket ~floor:7 (Ok ()) in
  let superseded =
    receive pending ~revision:7 (snap (Some pa) [ op a "completed"; op b "completed" ])
  in
  assert (equal_status (model superseded).status Stale && not (launchable superseded pa));
  let other =
    receive ready ~revision:8 (snap (Some pa) [ op b "executing"; op a "completed" ])
  in
  assert (equal_status (model other).status Pending && not (launchable other pa));
  let reset = reset retry ~scope:"replacement/project" in
  assert (equal_status (model reset).status Empty);
  let reset = receipt reset current ~floor:10 (Error "late replaced daemon") in
  assert (equal_status (model reset).status Empty)
;;

let%test_unit "same-selection retry waits past every pre-receipt poll then ordinary \
               reads stay ready"
  =
  let selection : Asic.Selection.t =
    { flow = "flow"; profile = "profile"; endpoint = "endpoint"; assignments = [] }
  in
  let preview : Asic.Preview.t =
    { selection; plan_identity = "exact-identity"; plan_json = "opaque metadata" }
  in
  let operation state : Asic.Pending.t =
    { key = key selection; kind = "plan"; state; run = None; error = None }
  in
  let completed =
    { Fs0_fixture.snapshot with
      preview = Some preview
    ; operations = [ operation "completed" ]
    }
  in
  let ready = receive (reset empty ~scope:"same-owner") ~revision:1 completed in
  let retry, ticket = begin_plan ready selection in
  assert (current_ticket retry ticket && not (launchable retry preview));
  (* IDs 2..8 may have been issued before the Plan receipt; their snapshots can still
     contain the old completed task, despite arriving after the receipt. *)
  let retry = receipt retry ticket ~floor:9 (Ok ()) in
  let retry = receive retry ~revision:8 completed in
  assert (equal_status (model retry).status Pending && not (launchable retry preview));
  let pending =
    { completed with preview = None; operations = [ operation "executing" ] }
  in
  let retry = receive retry ~revision:9 pending in
  assert (equal_status (model retry).status Pending);
  let ready = receive retry ~revision:10 completed in
  assert (launchable ready preview && not (current_ticket ready ticket));
  let ready = receive ready ~revision:11 { completed with runs = [] } in
  assert (launchable ready preview);
  (* Late dispatcher rejection or duplicate receipt cannot reopen a completed intent. *)
  let ready = receipt ready ticket ~floor:12 (Error "late rejected dispatcher") in
  assert (launchable ready preview);
  let failed =
    receive ready ~revision:12 { completed with operations = [ operation "failed" ] }
  in
  assert (equal_status (model failed).status Failed && not (launchable failed preview));
  let expired = receive ready ~revision:12 { completed with operations = [] } in
  assert (equal_status (model expired).status Stale && not (launchable expired preview));
  let absent = receive ready ~revision:12 { completed with preview = None } in
  assert (equal_status (model absent).status Stale && not (launchable absent preview))
;;

let%test_unit "scope round trips and newer command acceptance invalidate old dispatch \
               and receipt"
  =
  let selection : Asic.Selection.t =
    { flow = "flow"; profile = "profile"; endpoint = "endpoint"; assignments = [] }
  in
  let owner = reset empty ~scope:"daemon/project" in
  let first, old_ticket = begin_plan owner selection in
  let second, ticket = begin_plan first { selection with endpoint = "new-endpoint" } in
  assert ((not (current_ticket second old_ticket)) && current_ticket second ticket);
  let rejected =
    receipt second ticket ~floor:Int.max_value (Error "target changed before dispatch")
  in
  assert (equal_status (model rejected).status Failed);
  let reconnected = reset (reset second ~scope:"") ~scope:"daemon/project" in
  let reconnected, replacement = begin_plan reconnected selection in
  assert (not (current_ticket reconnected old_ticket));
  assert (not (current_ticket reconnected ticket));
  assert (current_ticket reconnected replacement);
  let reconnected = receipt reconnected ticket ~floor:1 (Error "old transport") in
  assert (equal_status (model reconnected).status Pending);
  List.iter [ "other-daemon/project"; "daemon/other-project" ] ~f:(fun scope ->
    let changed = reset reconnected ~scope in
    assert (equal_status (model changed).status Empty);
    assert (not (current_ticket changed replacement)))
;;

let%test_unit "exact raw selection identity and metadata survive display projection \
               without normalization"
  =
  let selection : Asic.Selection.t =
    { flow = "Flow;\027[31m"
    ; profile = "Profile With Spaces"
    ; endpoint = "Endpoint/Case"
    ; assignments = [ "z=1"; "a=2"; "z=1" ]
    }
  in
  let preview : Asic.Preview.t =
    { selection
    ; plan_identity = "raw\027identity"
    ; plan_json = "{malformed opaque\000JSON}\nsecond line"
    }
  in
  let op : Asic.Pending.t =
    { key = key selection; kind = "plan"; state = "completed"; run = None; error = None }
  in
  let snapshot =
    { Fs0_fixture.snapshot with preview = Some preview; operations = [ op ] }
  in
  let ready = receive empty ~revision:1 snapshot in
  assert (launchable ready preview);
  assert (not (launchable ready { preview with plan_json = "different raw metadata" }));
  assert (not (launchable ready { preview with plan_identity = "different" }));
  assert (
    not
      (String.equal
         (key selection)
         (key { selection with assignments = [ "a=2"; "z=1"; "z=1" ] })));
  assert (
    not
      (String.equal
         (key selection)
         (key { selection with assignments = [ "z=1"; "a=2" ] })));
  let before = model ready in
  let detail = rows before ~detail:true in
  assert (
    List.exists detail ~f:(fun row ->
      String.equal row.text "exact plan identity: raw\027identity"));
  assert (
    List.exists detail ~f:(fun row -> String.equal row.text "{malformed opaque\000JSON}"));
  assert (Asic.Preview.equal (Option.value_exn (model ready).preview) preview)
;;
