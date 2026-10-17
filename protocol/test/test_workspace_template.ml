open! Core
open Hardcaml_workbench_protocol
module W = Workspace
module T = Workspace_template

let ok = function
  | Ok value -> value
  | Error (error : V1.Error.t) -> raise_s [%sexp (error : V1.Error.t)]
;;

let mutate (s : W.Snapshot.t) mutation =
  W.apply s (Mutate { expected_revision = s.revision; mutation }) |> ok
;;

let error kind = function
  | Ok _ -> failwith "Expected registry error"
  | Error (e : V1.Error.t) -> assert (V1.Error.Kind.equal kind e.kind)
;;

let initial () = W.initial ~session_id:(W.Session_id.of_string "private-session")

let%test_unit "generic starter is project-scoped; ASIC starter includes supported \
               evidence views"
  =
  let kinds template = List.map template.T.views ~f:(fun view -> view.T.View.kind) in
  let generic = kinds T.generic in
  let asic = kinds T.asic in
  assert (
    List.equal String.equal generic [ "project"; "execution"; "project-tests"; "logs" ]);
  let asic_kinds =
    [ "run-selector"
    ; "asic"
    ; "synthesis"
    ; "placement"
    ; "cts"
    ; "routing"
    ; "timing"
    ; "checks"
    ; "finalization"
    ]
  in
  List.iter asic_kinds ~f:(fun kind ->
    assert (not (List.mem generic kind ~equal:String.equal)));
  assert (List.mem asic "synthesis" ~equal:String.equal);
  assert (List.equal String.equal asic asic_kinds);
  List.iter [ T.generic; T.asic ] ~f:(fun template ->
    T.validate template |> Or_error.ok_exn;
    assert (
      T.equal
        template
        (T.encode template |> Or_error.ok_exn |> T.decode |> Or_error.ok_exn)))
;;

let%test_unit "template mutation uses the existing workspace wire envelope" =
  let s = initial () in
  let request : W.Request.t =
    { instance_id = "instance"
    ; project = Project_id.of_string "project"
    ; operation =
        Mutate
          { expected_revision = s.revision
          ; mutation =
              Instantiate_template
                { window = (List.hd_exn s.windows).id; template = T.asic }
          }
    }
  in
  let encoded = V1.Codec.encode W.Request.sexp_of_t request in
  let decoded = V1.Codec.decode W.Request.t_of_sexp encoded |> ok in
  assert (W.Request.equal request decoded);
  W.apply s decoded.operation |> ok |> W.validate |> ok
;;

let%test_unit "export strips live state; repeated import allocates fresh Main-linked \
               views"
  =
  let s = initial () in
  let source = List.hd_exn s.workspaces in
  let first = List.hd_exn s.tiles in
  let run : Run_ref.t =
    { backend = Backend_id.of_string "private-provider"
    ; id = "private-run"
    ; build = None
    ; label = None
    }
  in
  let s = mutate s (Make_independent source.id) in
  let independent = (W.workspace s source.id).context in
  let s =
    mutate
      s
      (Select_run
         { workspace = source.id
         ; context = independent
         ; expected_selection_revision = 0
         ; run = Some run
         })
  in
  let s = mutate s (Set_tile_binding { tile = first.id; binding = Pin_run run }) in
  let s = mutate s (Set_zoom { workspace = source.id; tile = Some first.id }) in
  let s =
    mutate
      s
      (Create_tile
         { workspace = source.id
         ; kind = "future-extension"
         ; geometry = { x = 5; y = 7; width = 11; height = 13 }
         })
  in
  let last = List.last_exn s.tiles in
  let s = mutate s (Set_tile_hidden { tile = last.id; hidden = true }) in
  let template = W.export_template s source.id |> ok in
  let encoded = T.encode template |> Or_error.ok_exn in
  List.iter
    [ "private-session"
    ; "private-provider"
    ; "private-run"
    ; W.Context_id.to_string independent
    ; W.Tile_id.to_string first.id
    ; W.Workspace_id.to_string source.id
    ]
    ~f:(fun secret -> assert (not (String.is_substring encoded ~substring:secret)));
  assert (T.equal template (T.decode encoded |> Or_error.ok_exn));
  let import s = mutate s (Instantiate_template { window = source.window; template }) in
  let next = import s in
  assert (next.revision = s.revision + 1);
  assert (List.equal W.Context.equal s.contexts next.contexts);
  assert (W.Arrangement.equal (W.workspace s source.id) (W.workspace next source.id));
  let created = List.last_exn next.workspaces in
  assert (W.Context_id.equal created.context s.main_context);
  assert (Option.is_none created.zoomed_tile);
  assert (T.equal template (W.export_template next created.id |> ok));
  let new_tiles =
    List.filter next.tiles ~f:(fun t -> W.Workspace_id.equal t.workspace created.id)
  in
  assert (List.length new_tiles = 2);
  List.iter new_tiles ~f:(fun t ->
    assert (W.Binding.equal t.binding Follow);
    assert (Option.is_none (W.resolve_tile next t.id |> ok).run);
    assert (not (List.exists s.tiles ~f:(fun old -> W.Tile_id.equal old.id t.id))));
  let again = import next in
  let second = List.last_exn again.workspaces in
  assert (not (W.Workspace_id.equal created.id second.id));
  assert (List.length again.tiles = List.length next.tiles + 2);
  W.apply
    next
    (Mutate
       { expected_revision = s.revision
       ; mutation = Instantiate_template { window = source.window; template }
       })
  |> error Conflict
;;

let%test_unit "invalid portable files are rejected before registry allocation" =
  let s = initial () in
  let window = (List.hd_exn s.windows).id in
  let bad_geometry : T.View.t =
    { kind = "timing"
    ; hidden = false
    ; geometry = { x = Int.max_value; y = 0; width = 1; height = 1 }
    }
  in
  let invalid =
    [ { T.generic with version = 999 }
    ; { T.generic with name = "  " }
    ; { T.generic with name = "bad\nname" }
    ; { T.generic with views = [ bad_geometry ] }
    ; { T.generic with
        views = List.init (T.max_views + 1) ~f:(fun _ -> List.hd_exn T.generic.views)
      }
    ]
  in
  List.iter invalid ~f:(fun template ->
    assert (Result.is_error (T.validate template));
    W.apply
      s
      (Mutate
         { expected_revision = s.revision
         ; mutation = Instantiate_template { window; template }
         })
    |> error Invalid_request);
  List.iter
    [ "("
    ; "((version 1) (name A) (views ()) (session_id forbidden))"
    ; String.make (T.max_encoded_bytes + 1) ' '
    ]
    ~f:(fun text -> assert (Result.is_error (T.decode text)));
  W.apply
    s
    (Mutate
       { expected_revision = s.revision
       ; mutation =
           Instantiate_template
             { window = W.Window_id.of_string "missing"; template = T.generic }
       })
  |> error Not_found;
  (* Failure after workspace allocation still cannot expose a partial import. *)
  let exhausted = { s with next_id = Int.max_value - 1 } in
  W.apply
    exhausted
    (Mutate
       { expected_revision = s.revision
       ; mutation = Instantiate_template { window; template = T.generic }
       })
  |> error Invalid_request;
  assert (exhausted.revision = s.revision);
  assert (List.length exhausted.workspaces = List.length s.workspaces);
  List.iter
    [ T.generic; T.asic; { T.generic with views = [] } ]
    ~f:(fun template ->
      let next = mutate s (Instantiate_template { window; template }) in
      W.validate next |> ok)
;;
