open! Core
open Hardcaml_workbench_protocol
module W = Workspace
module Host = Workspace_host

(** This file contains only client presentation choices. In particular, neither
    registry/run state nor transient navigation belongs in this schema. *)
type tile_headers =
  { tile : W.Tile_id.t
  ; workspace : W.Workspace_id.t
  ; kind : string
  ; headers : bool
  }
[@@deriving sexp]

type t =
  { schema_version : int
  ; project_key : string
  ; appearance : Appearance.t
  ; layout_mode : Host.layout_mode
  ; chrome : bool
  ; main_hints : bool option [@sexp.option]
  ; palette_hints : bool option [@sexp.option]
  ; session : W.Session_id.t option
  ; tile_headers : tile_headers list
  }
[@@deriving sexp]

let path ~state_directory ~project_key =
  Filename.concat
    state_directory
    ("presentation-" ^ Plain_rpc.digest project_key ^ ".sexp")
;;

(* Schema 2 adds the independent main-window/palette hint choices (WB-019). Schema 1 files
   remain readable: they predate the choices, so both hint areas stay visible. *)
let schema_version = 2

let capture ~project_key (host : Host.t) =
  { schema_version
  ; project_key
  ; appearance = host.appearance
  ; layout_mode = host.layout_mode
  ; chrome = host.chrome
  ; main_hints = Some host.main_hints
  ; palette_hints = Some host.palette_hints
  ; session = Option.map host.registry ~f:(fun registry -> registry.session_id)
  ; tile_headers =
      Option.value_map host.registry ~default:[] ~f:(fun registry ->
        (* Only explicit header overrides persist; absent tiles inherit policy. *)
        List.filter_map registry.tiles ~f:(fun tile ->
          Option.map (Host.local host tile.id).presentation.header ~f:(fun headers ->
            { tile = tile.id; workspace = tile.workspace; kind = tile.kind; headers })))
  }
;;

let decode ~project_key content =
  if String.length content > 64 * 1024
  then failwith "Terminal presentation preference size limit exceeded";
  let stored = t_of_sexp (Sexp.of_string content) in
  (match stored.schema_version, stored.main_hints, stored.palette_hints with
   | 1, None, None | 2, Some _, Some _ -> ()
   | (1 | 2), _, _ -> failwith "Terminal presentation hint fields do not match schema"
   | _ -> failwith "Unsupported terminal presentation preference schema");
  if not (String.equal stored.project_key project_key)
  then failwith "Terminal presentation preference project/environment mismatch";
  if Option.is_none stored.session && not (List.is_empty stored.tile_headers)
  then failwith "Tile header preferences require a workspace session";
  let ids = List.map stored.tile_headers ~f:(fun tile -> W.Tile_id.to_string tile.tile) in
  if List.contains_dup ids ~compare:String.compare
  then failwith "Duplicate terminal tile header preference";
  stored
;;

let encode t = Sexp.to_string_hum (sexp_of_t t) ^ "\n"

let apply_headers t (host : Host.t) =
  match host.registry with
  | None -> host
  | Some registry ->
    List.fold registry.tiles ~init:host ~f:(fun host tile ->
      let header =
        if Option.equal W.Session_id.equal t.session (Some registry.session_id)
        then
          List.find t.tile_headers ~f:(fun pref ->
            W.Tile_id.equal pref.tile tile.id
            && W.Workspace_id.equal pref.workspace tile.workspace
            && String.equal pref.kind tile.kind)
          |> Option.map ~f:(fun pref -> pref.headers)
        else None
      in
      let local = Host.local host tile.id in
      Host.set_local
        host
        tile.id
        { local with presentation = { local.presentation with header } })
;;

let apply t (host : Host.t) =
  apply_headers
    t
    { host with
      appearance = t.appearance
    ; layout_mode = t.layout_mode
    ; chrome = t.chrome
    ; main_hints = Option.value t.main_hints ~default:true
    ; palette_hints = Option.value t.palette_hints ~default:true
    }
;;

(** Restoration is a one-shot handoff, not a policy replayed on every poll. Consume even a
    mismatching/empty registry: removed identities must not regain old preferences if
    their IDs are subsequently reused. *)
let receive pending host snapshot =
  let host = Host.receive host snapshot in
  Option.value_map pending ~default:host ~f:(fun saved -> apply_headers saved host), None
;;

(* Reads and writes run on the caller's I/O worker. Rename is in the same directory:
   readers see a complete old or new file, never a partial sexp. *)
let load ~state_directory ~project_key =
  let path = path ~state_directory ~project_key in
  match Sys_unix.file_exists path with
  | `No -> None
  | `Unknown -> failwith ("Cannot inspect terminal presentation preferences: " ^ path)
  | `Yes ->
    let size = (Core_unix.stat path).st_size in
    if Int64.(size > 65536L)
    then failwith "Terminal presentation preference size limit exceeded";
    Some (decode ~project_key (In_channel.read_all path))
;;

let save ~state_directory t =
  let data = encode t in
  (* Do not write a file that our reader would reject. *)
  ignore (decode ~project_key:t.project_key data : t);
  Core_unix.mkdir_p state_directory ~perm:0o700;
  let temp = Filename_unix.temp_file ~in_dir:state_directory ".presentation-" ".tmp" in
  Exn.protect
    ~finally:(fun () ->
      if Poly.equal (Sys_unix.file_exists temp) `Yes then Core_unix.unlink temp)
    ~f:(fun () ->
      Out_channel.write_all temp ~data;
      Core_unix.rename ~src:temp ~dst:(path ~state_directory ~project_key:t.project_key))
;;

let%test_unit "restart restores presentation, never navigation or daemon state" =
  let registry = W.initial ~session_id:(W.Session_id.of_string "retained-session") in
  let host = Host.receive Host.empty registry in
  let tile = List.hd_exn registry.tiles in
  let host =
    Host.set_local
      host
      tile.id
      { Host.default_local with
        presentation = { Host.default_local.presentation with header = Some false }
      ; filter = "temporary"
      ; scroll = 99
      }
  in
  let host =
    { host with
      appearance =
        { preset = Studio
        ; color = Restrained
        ; scheme = Slate
        ; icons = Unicode
        ; density = Comfortable
        }
    ; layout_mode = Preferred
    ; chrome = false
    ; focus = Some (List.last_exn registry.tiles).id
    }
  in
  let stored =
    decode ~project_key:"root/env" (encode (capture ~project_key:"root/env" host))
  in
  let refreshed = apply stored host in
  assert (String.equal (Host.local refreshed tile.id).filter "temporary");
  assert ((Host.local refreshed tile.id).scroll = 99);
  assert (Option.equal W.Tile_id.equal refreshed.focus host.focus);
  let restarted = apply stored (Host.receive Host.empty registry) in
  assert (Appearance.equal restarted.appearance host.appearance);
  assert (Host.equal_layout_mode restarted.layout_mode Preferred);
  assert (not restarted.chrome);
  assert (
    Option.equal
      Bool.equal
      (Host.local restarted tile.id).presentation.header
      (Some false));
  assert (String.is_empty (Host.local restarted tile.id).filter);
  assert ((Host.local restarted tile.id).scroll = 0);
  assert (Option.is_none restarted.palette);
  assert (Option.equal W.Tile_id.equal restarted.focus (Some tile.id));
  assert (Option.equal W.Snapshot.equal restarted.registry (Some registry));
  let encoded = encode stored in
  assert (not (String.is_substring encoded ~substring:"temporary"));
  let other_session =
    { registry with session_id = W.Session_id.of_string "replacement" }
  in
  let replaced = apply stored (Host.receive restarted other_session) in
  assert (Option.is_none (Host.local replaced tile.id).presentation.header);
  assert (Appearance.equal replaced.appearance host.appearance);
  let changed_kind =
    { registry with
      tiles = List.map registry.tiles ~f:(fun t -> { t with kind = "new-kind" })
    }
  in
  assert (
    Option.is_none
      (Host.local (apply stored (Host.receive Host.empty changed_kind)) tile.id)
        .presentation
        .header);
  let changed_workspace =
    { registry with
      tiles =
        List.map registry.tiles ~f:(fun tile ->
          { tile with workspace = W.Workspace_id.of_string "another-workspace" })
    }
  in
  assert (
    Option.is_none
      (Host.local (apply stored (Host.receive Host.empty changed_workspace)) tile.id)
        .presentation
        .header);
  let removed = apply stored (Host.receive Host.empty { registry with tiles = [] }) in
  assert (List.is_empty removed.locals)
;;

let%test_unit "strict schema validation and isolated identities" =
  let stored = capture ~project_key:"root/env" Host.empty in
  let rejects value =
    assert (
      Result.is_error (Or_error.try_with (fun () -> decode ~project_key:"root/env" value)))
  in
  rejects "(";
  rejects (encode { stored with schema_version = 3 });
  rejects (encode { stored with main_hints = None });
  rejects (encode { stored with schema_version = 1 });
  rejects
    (String.substr_replace_first
       (encode stored)
       ~pattern:"(main_hints true)"
       ~with_:"(main_hints maybe)");
  rejects (encode { stored with project_key = "root/other-env" });
  rejects (String.make ((64 * 1024) + 1) ' ');
  rejects "((unknown true))";
  rejects
    (String.substr_replace_first
       (encode stored)
       ~pattern:"Instrument"
       ~with_:"Unknown_skin");
  rejects
    (String.substr_replace_first
       (encode stored)
       ~pattern:"(chrome true)"
       ~with_:"(chrome perhaps)");
  let pref =
    { tile = W.Tile_id.of_string "tile"
    ; workspace = W.Workspace_id.of_string "ws"
    ; kind = "log"
    ; headers = false
    }
  in
  rejects (encode { stored with tile_headers = [ pref ] });
  rejects
    (encode
       { stored with
         session = Some (W.Session_id.of_string "s")
       ; tile_headers = [ pref; pref ]
       });
  assert (
    not
      (String.equal
         (path ~state_directory:"state" ~project_key:"root/env")
         (path ~state_directory:"state" ~project_key:"root/other-env")));
  assert (
    not
      (String.equal
         (path ~state_directory:"state" ~project_key:"root/env")
         (Launch_preferences.path ~state_directory:"state" ~project_key:"root/env")))
;;

let%test_unit "catalog header/reset intent survives polling without replaying sparse \
               overrides"
  =
  let registry = W.initial ~session_id:(W.Session_id.of_string "catalog-preferences") in
  let tile = List.hd_exn registry.tiles in
  let choose host id =
    let command =
      Host.catalog host ~project:None ~jobs:[]
      |> List.find_exn ~f:(fun command -> String.equal command.id id)
    in
    match command.action with
    | Set_presentation (id, overrides) -> Host.set_presentation host id overrides
    | _ -> assert false
  in
  let host = Host.receive Host.empty registry in
  let inherited = (Host.policy host tile).header in
  let toggled, save = choose host "tile.headers" in
  assert save;
  assert (Bool.equal (Host.policy toggled tile).header (not inherited));
  let titled, save = choose toggled "tile.presentation.title" in
  assert (not save);
  let saved = capture ~project_key:"catalog" titled in
  assert (List.length saved.tile_headers = 1);
  let starting = apply saved Host.empty in
  let restored, pending = receive (Some saved) starting registry in
  assert (Option.is_none pending);
  assert (Bool.equal (Host.policy restored tile).header (not inherited));
  assert (Option.is_none (Host.local restored tile.id).presentation.title);
  let titled, _ = choose restored "tile.presentation.title" in
  let reset, save = choose titled "tile.presentation.reset" in
  assert save;
  assert (Bool.equal (Host.policy reset tile).header inherited);
  (* A newer appearance and reset must survive polling even before the save worker
     completes; the initially loaded snapshot has already been consumed. *)
  let reset = { reset with chrome = false; layout_mode = Preferred } in
  let polled, pending =
    receive pending reset { registry with revision = registry.revision + 1 }
  in
  assert (Option.is_none pending);
  assert ((not polled.chrome) && Host.equal_layout_mode polled.layout_mode Preferred);
  assert (Option.is_none (Host.local polled tile.id).presentation.header);
  assert (Option.is_none (Host.local polled tile.id).presentation.title);
  let saved_reset = capture ~project_key:"catalog" polled in
  assert (List.is_empty saved_reset.tile_headers);
  let restarted = apply saved_reset (Host.receive Host.empty registry) in
  assert (Bool.equal (Host.policy restarted tile).header inherited);
  (* Consuming a missing identity is final, even if an ID is later reused. *)
  let absent, pending = receive (Some saved) starting { registry with tiles = [] } in
  let readded, _ =
    receive pending absent { registry with revision = registry.revision + 2 }
  in
  assert (Option.is_none (Host.local readded tile.id).presentation.header);
  let ignored, save =
    Host.set_presentation
      absent
      tile.id
      { Tile_presentation.inherit_ with header = Some true }
  in
  assert ((not save) && List.is_empty ignored.locals)
;;

let%test_unit "main-window and palette hints persist independently of global chrome" =
  let registry = W.initial ~session_id:(W.Session_id.of_string "hint-preferences") in
  let base = Host.receive Host.empty registry in
  List.iter [ true; false ] ~f:(fun chrome ->
    List.iter [ true; false ] ~f:(fun main_hints ->
      List.iter [ true; false ] ~f:(fun palette_hints ->
        let host = { base with chrome; main_hints; palette_hints } in
        let stored =
          decode ~project_key:"root/env" (encode (capture ~project_key:"root/env" host))
        in
        let restored = apply stored (Host.receive Host.empty registry) in
        assert (Bool.equal restored.chrome chrome);
        assert (Bool.equal restored.main_hints main_hints);
        assert (Bool.equal restored.palette_hints palette_hints))));
  (* A schema 1 file (written before WB-019) keeps its chrome choice and shows hints. *)
  let legacy =
    { (capture ~project_key:"root/env" { base with chrome = false }) with
      schema_version = 1
    ; main_hints = None
    ; palette_hints = None
    }
  in
  let encoded = encode legacy in
  assert (not (String.is_substring encoded ~substring:"hints"));
  let restored =
    apply
      (decode ~project_key:"root/env" encoded)
      { base with main_hints = false; palette_hints = false }
  in
  assert (not restored.chrome);
  assert (restored.main_hints && restored.palette_hints)
;;
