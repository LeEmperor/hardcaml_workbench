open! Core
open Hardcaml_workbench_protocol
module P = Terminal_presentation.Presentation_preferences
module Host = Terminal_presentation.Workspace_host
module W = Workspace

let choose host id =
  let command =
    Host.catalog host ~project:None ~jobs:[]
    |> List.find_exn ~f:(fun command -> String.equal command.id id)
  in
  match command.action with
  | Set_presentation (tile, overrides) -> Host.set_presentation host tile overrides
  | _ -> failwith "Expected catalog presentation action"
;;

(* Invoked in separate processes by the restart test; uses the production store,
   serializer and host restoration rather than a second preference implementation. *)
let () =
  let argv = Sys.get_argv () in
  let mode = argv.(1)
  and state_directory = argv.(2) in
  let project_key = "restart-fixture/inherited" in
  let registry = W.initial ~session_id:(W.Session_id.of_string "restart-session") in
  let host = Host.receive Host.empty registry in
  let tile = List.hd_exn registry.tiles in
  let expected =
    { host with
      appearance =
        { preset = Minimal
        ; color = Vivid
        ; scheme = Slate
        ; icons = None_
        ; density = Comfortable
        }
    ; layout_mode = Preferred
    ; chrome = false
    }
    |> fun host ->
    let host, save = choose host "tile.headers" in
    assert save;
    let local = Host.local host tile.id in
    Host.set_local host tile.id { local with filter = "not-persistent"; scroll = 23 }
  in
  match mode with
  | "write" -> P.save ~state_directory (P.capture ~project_key expected)
  | "read" ->
    let preferences = Option.value_exn (P.load ~state_directory ~project_key) in
    let restored = P.apply preferences host in
    assert (Terminal_presentation.Appearance.equal restored.appearance expected.appearance);
    assert (Host.equal_layout_mode restored.layout_mode expected.layout_mode);
    assert (not restored.chrome);
    assert (
      Option.equal
        Bool.equal
        (Host.local restored tile.id).presentation.header
        (Host.local expected tile.id).presentation.header);
    assert (String.is_empty (Host.local restored tile.id).filter);
    assert ((Host.local restored tile.id).scroll = 0);
    assert (Option.equal W.Snapshot.equal restored.registry (Some registry));
    let replacement =
      { registry with session_id = W.Session_id.of_string "new-session" }
    in
    let replaced = P.apply preferences (Host.receive Host.empty replacement) in
    assert (Option.is_none (Host.local replaced tile.id).presentation.header);
    assert (not replaced.chrome);
    assert (
      Option.is_none (P.load ~state_directory ~project_key:"other-project/inherited"))
  | "reset" ->
    let preferences = Option.value_exn (P.load ~state_directory ~project_key) in
    let restored, pending =
      P.receive (Some preferences) (P.apply preferences host) registry
    in
    let restored, save = choose restored "tile.presentation.title" in
    assert (not save);
    let reset, save = choose restored "tile.presentation.reset" in
    assert save;
    let polled, pending =
      P.receive pending reset { registry with revision = registry.revision + 1 }
    in
    assert (Option.is_none pending);
    assert (Option.is_none (Host.local polled tile.id).presentation.header);
    P.save ~state_directory (P.capture ~project_key polled)
  | "read-reset" ->
    let preferences = Option.value_exn (P.load ~state_directory ~project_key) in
    assert (List.is_empty preferences.tile_headers);
    let restored = P.apply preferences host in
    assert (Option.is_none (Host.local restored tile.id).presentation.header);
    assert (Option.is_none (Host.local restored tile.id).presentation.title);
    let inherited = { host with appearance = expected.appearance } in
    assert (
      Bool.equal (Host.policy restored tile).header (Host.policy inherited tile).header);
    assert (Terminal_presentation.Appearance.equal restored.appearance expected.appearance)
  | "missing" -> assert (Option.is_none (P.load ~state_directory ~project_key))
  | "malformed" ->
    let path = P.path ~state_directory ~project_key in
    let before = In_channel.read_all path in
    assert (
      Result.is_error (Or_error.try_with (fun () -> P.load ~state_directory ~project_key)));
    assert (String.equal before (In_channel.read_all path))
  | "save-error" ->
    assert (
      Result.is_error
        (Or_error.try_with (fun () ->
           P.save ~state_directory (P.capture ~project_key expected))))
  | _ -> failwith "Unknown preference probe mode"
;;
