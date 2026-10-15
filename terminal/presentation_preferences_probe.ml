open! Core
open Hardcaml_workbench_protocol
module P = Terminal_presentation.Presentation_preferences
module Host = Terminal_presentation.Workspace_host
module W = Workspace

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
        { preset = Minimal; color = Vivid; icons = None_; density = Comfortable }
    ; layout_mode = Preferred
    ; chrome = false
    }
    |> fun host ->
    Host.set_local
      host
      tile.id
      { Host.default_local with headers = false; filter = "not-persistent"; scroll = 23 }
  in
  match mode with
  | "write" -> P.save ~state_directory (P.capture ~project_key expected)
  | "read" ->
    let preferences = Option.value_exn (P.load ~state_directory ~project_key) in
    let restored = P.apply preferences host in
    assert (Terminal_presentation.Appearance.equal restored.appearance expected.appearance);
    assert (Host.equal_layout_mode restored.layout_mode expected.layout_mode);
    assert (not restored.chrome);
    assert (not (Host.local restored tile.id).headers);
    assert (String.is_empty (Host.local restored tile.id).filter);
    assert ((Host.local restored tile.id).scroll = 0);
    assert (Option.equal W.Snapshot.equal restored.registry (Some registry));
    let replacement =
      { registry with session_id = W.Session_id.of_string "new-session" }
    in
    let replaced = P.apply preferences (Host.receive Host.empty replacement) in
    assert (Host.local replaced tile.id).headers;
    assert (not replaced.chrome);
    assert (
      Option.is_none (P.load ~state_directory ~project_key:"other-project/inherited"))
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
  | _ -> failwith "Expected write, read, missing, malformed or save-error"
;;
