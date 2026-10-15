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
  ; session : W.Session_id.t option
  ; tile_headers : tile_headers list
  }
[@@deriving sexp]

let path ~state_directory ~project_key =
  Filename.concat
    state_directory
    ("presentation-" ^ Plain_rpc.digest project_key ^ ".sexp")
;;

let capture ~project_key (host : Host.t) =
  { schema_version = 1
  ; project_key
  ; appearance = host.appearance
  ; layout_mode = host.layout_mode
  ; chrome = host.chrome
  ; session = Option.map host.registry ~f:(fun registry -> registry.session_id)
  ; tile_headers =
      Option.value_map host.registry ~default:[] ~f:(fun registry ->
        List.map registry.tiles ~f:(fun tile ->
          { tile = tile.id
          ; workspace = tile.workspace
          ; kind = tile.kind
          ; headers = (Host.local host tile.id).headers
          }))
  }
;;

let decode ~project_key content =
  if String.length content > 64 * 1024
  then failwith "Terminal presentation preference size limit exceeded";
  let stored = t_of_sexp (Sexp.of_string content) in
  if stored.schema_version <> 1
  then failwith "Unsupported terminal presentation preference schema";
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

let apply t (host : Host.t) =
  let host =
    { host with
      appearance = t.appearance
    ; layout_mode = t.layout_mode
    ; chrome = t.chrome
    }
  in
  match host.registry with
  | None -> host
  | Some registry ->
    List.fold registry.tiles ~init:host ~f:(fun host tile ->
      let headers =
        if Option.equal W.Session_id.equal t.session (Some registry.session_id)
        then
          List.find t.tile_headers ~f:(fun pref ->
            W.Tile_id.equal pref.tile tile.id
            && W.Workspace_id.equal pref.workspace tile.workspace
            && String.equal pref.kind tile.kind)
          |> Option.value_map ~default:Host.default_local.headers ~f:(fun pref ->
            pref.headers)
        else Host.default_local.headers
      in
      Host.set_local host tile.id { (Host.local host tile.id) with headers })
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
      { Host.default_local with headers = false; filter = "temporary"; scroll = 99 }
  in
  let host =
    { host with
      appearance =
        { preset = Studio; color = Restrained; icons = Unicode; density = Comfortable }
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
  assert (not (Host.local restarted tile.id).headers);
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
  assert (Host.local replaced tile.id).headers;
  assert (Appearance.equal replaced.appearance host.appearance);
  let changed_kind =
    { registry with
      tiles = List.map registry.tiles ~f:(fun t -> { t with kind = "new-kind" })
    }
  in
  assert
    (Host.local (apply stored (Host.receive Host.empty changed_kind)) tile.id).headers;
  let changed_workspace =
    { registry with
      tiles =
        List.map registry.tiles ~f:(fun tile ->
          { tile with workspace = W.Workspace_id.of_string "another-workspace" })
    }
  in
  assert
    (Host.local (apply stored (Host.receive Host.empty changed_workspace)) tile.id)
      .headers;
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
  rejects (encode { stored with schema_version = 2 });
  rejects (encode { stored with project_key = "root/other-env" });
  rejects (String.make ((64 * 1024) + 1) ' ');
  rejects "((unknown true))";
  rejects
    (String.substr_replace_first
       (encode stored)
       ~pattern:"Structured"
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
