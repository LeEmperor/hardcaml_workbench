open! Core
open Hardcaml_workbench_protocol
module Wire = Hardcaml_workbench_protocol.Asic_inspection
module Public = Asic_public

let index_limit = 2 * 1024 * 1024
let detail_limit = 64 * 1024

let validate_selection ~domain ~stage =
  Public.require
    (List.mem [ "timing"; "clocks"; "physical"; "routing" ] domain ~equal:String.equal
     && List.mem
          [ "synthesis"; "floorplan"; "placement"; "cts"; "routing"; "signoff" ]
          stage
          ~equal:String.equal)
    "Invalid inspection domain/stage"
;;

let validate_digest digest =
  Public.require
    (String.length digest = 64
     && String.for_all digest ~f:(function
       | '0' .. '9' | 'a' .. 'f' -> true
       | _ -> false))
    "Invalid inspection digest"
;;

let validate_row_id id =
  Public.require
    ((not (String.is_empty id)) && String.length id <= 4096)
    "Invalid inspection row ID"
;;

let boolean = function
  | `Bool b -> b
  | _ -> failwith "Expected inspection boolean"
;;

let number = function
  | `Null -> None
  | `Int n -> Some (Float.of_int n)
  | `Intlit n ->
    let value = Float.of_string n in
    Public.require (Float.is_finite value) "Nonfinite inspection value";
    Some value
  | `Float f when Float.is_finite f -> Some f
  | _ -> failwith "Expected finite inspection value"
;;

let require_fields names = function
  | `Assoc fields ->
    List.iter names ~f:(fun name ->
      Public.require
        (List.Assoc.mem fields name ~equal:String.equal)
        ("Missing inspection field: " ^ name))
  | _ -> failwith "Expected inspection object"
;;

let row j : Wire.Row.t =
  require_fields
    [ "id"
    ; "category"
    ; "producer"
    ; "corner"
    ; "group"
    ; "name"
    ; "value"
    ; "unit"
    ; "status"
    ; "source"
    ; "fields"
    ]
    j;
  let field name = Public.field name j in
  let id = Public.text (field "id") in
  validate_row_id id;
  let source = Public.text (field "source") in
  ignore (Public.decode source : Yojson.Safe.t);
  { id
  ; category = Public.text (field "category")
  ; producer = Public.text (field "producer")
  ; corner = Public.optional_text (field "corner")
  ; group = Public.optional_text (field "group")
  ; name = Public.text (field "name")
  ; value = number (field "value")
  ; unit_ = Public.optional_text (field "unit")
  ; status = Public.text (field "status")
  ; source
  ; fields =
      List.map
        (Public.list (field "fields"))
        ~f:(function
          | `List [ `String key; `String value ] -> key, value
          | _ -> failwith "Expected inspection string pair")
  }
;;

(** The path is supplied only by the registered run, never by the client. Hash the actual
    bytes at the exact canonical public path, and fence the attempt as well. *)
let execution_hash ~(registered : Asic.Run.t) ~execution_file =
  Public.require
    (Option.equal String.equal registered.execution_file (Some execution_file)
     && String.equal (Filename_unix.realpath execution_file) execution_file)
    "Inspection requires the registered canonical execution file";
  let bytes = Asic_evidence_file.read_bounded execution_file (8 * 1024 * 1024) in
  let execution = Public.decode bytes in
  Public.require
    (Poly.equal
       (Public.field "attempt_id" execution)
       (`String registered.reference.stream_id))
    "Inspection execution attempt mismatch";
  Public.digest bytes
;;

let identity ~(registered : Asic.Run.t) ~execution_file ~execution_sha256 ~domain ~stage j
  =
  validate_selection ~domain ~stage;
  validate_digest execution_sha256;
  Public.require
    (Option.equal String.equal registered.execution_file (Some execution_file))
    "Inspection execution is not registered";
  let j = Public.envelope j "hardcaml-asic.inspection" 1 in
  List.iter
    [ "execution_file", execution_file
    ; "execution_sha256", execution_sha256
    ; "attempt_id", registered.reference.stream_id
    ; "domain", domain
    ; "stage", stage
    ]
    ~f:(fun (key, expected) ->
      Public.require
        (Poly.equal (Public.field key j) (`String expected))
        ("Inspection identity mismatch: " ^ key));
  let digest = Public.text (Public.field "source_digest" j) in
  validate_digest digest;
  digest
;;

let validate_index (index : Wire.Index.t) =
  validate_selection ~domain:index.domain ~stage:index.stage;
  validate_digest index.source_digest;
  validate_digest index.execution_sha256;
  ignore (Public.absolute index.execution_file : string);
  Public.require (List.length index.rows <= 4096) "Inspection exceeds 4096 rows";
  let ids = List.map index.rows ~f:(fun r -> r.Wire.Row.id) in
  Public.require
    (List.length ids = List.length (List.dedup_and_sort ids ~compare:String.compare))
    "Duplicate inspection row ID";
  List.iter index.rows ~f:(fun row ->
    validate_row_id row.id;
    Option.iter row.value ~f:(fun value ->
      Public.require (Float.is_finite value) "Nonfinite cached inspection value");
    ignore (Public.decode row.source : Yojson.Safe.t));
  Public.require
    (String.length (Sexp.to_string_mach (Wire.Index.sexp_of_t index)) <= index_limit)
    "Normalized inspection exceeds 2MiB"
;;

let parse_index ~registered ~execution_file ~execution_sha256 ~domain ~stage j =
  Public.require
    (String.length (Yojson.Safe.to_string j) <= index_limit)
    "Inspection response exceeds 2MiB";
  let source_digest =
    identity ~registered ~execution_file ~execution_sha256 ~domain ~stage j
  in
  let index : Wire.Index.t =
    { run = registered.Asic.Run.run
    ; execution_file
    ; execution_sha256
    ; domain
    ; stage
    ; source_digest
    ; rows = List.map (Public.list (Public.field "rows" j)) ~f:row
    ; diagnostics = List.map (Public.list (Public.field "diagnostics" j)) ~f:Public.text
    ; truncated = boolean (Public.field "truncated" j)
    ; cached_unverified = false
    }
  in
  validate_index index;
  index
;;

let parse_detail ~registered ~(index : Wire.Index.t) ~row_id j =
  validate_row_id row_id;
  Public.require
    (Run_ref.equal registered.Asic.Run.run index.run)
    "Wrong inspection detail run";
  let digest =
    identity
      ~registered
      ~execution_file:index.execution_file
      ~execution_sha256:index.execution_sha256
      ~domain:index.domain
      ~stage:index.stage
      j
  in
  Public.require
    (String.equal digest index.source_digest
     && Poly.equal (Public.field "row_id" j) (`String row_id)
     && List.exists index.rows ~f:(fun r -> String.equal r.id row_id))
    "Inspection detail digest/row mismatch";
  let text = Public.text (Public.field "detail" j) in
  Public.require (String.length text <= detail_limit) "Inspection detail exceeds 64KiB";
  { Wire.Detail.run = index.run
  ; domain = index.domain
  ; stage = index.stage
  ; source_digest = index.source_digest
  ; row_id
  ; text
  ; error = None
  }
;;

module Blob = struct
  type t =
    { digest : string
    ; index : Wire.Index.t
    }
  [@@deriving sexp]
end

module Cache = struct
  type t =
    { version : int
    ; identity : string
    ; entries : Blob.t list
    }
  [@@deriving sexp]
end

let cache_path ~state_dir ~identity =
  Filename.concat state_dir ("asic-" ^ Public.digest identity ^ "-inspections-v1.sexp")
;;

let index_digest index = Public.digest (Sexp.to_string_mach (Wire.Index.sexp_of_t index))

let key (index : Wire.Index.t) =
  Wire.index_key ~run:index.run ~domain:index.domain ~stage:index.stage
;;

let read_cache ~state_dir ~identity =
  let path = cache_path ~state_dir ~identity in
  if Poly.equal (Sys_unix.file_exists path) `No
  then []
  else (
    let bytes = Asic_evidence_file.read_bounded path ((8 * index_limit) + 65536) in
    let cache = Cache.t_of_sexp (Sexp.of_string bytes) in
    Public.require
      (cache.version = 1
       && String.equal cache.identity identity
       && List.length cache.entries <= 8)
      "Incompatible inspection cache identity/budget";
    List.iter cache.entries ~f:(fun blob ->
      validate_index blob.index;
      Public.require
        (String.equal blob.digest (index_digest blob.index))
        "Corrupt inspection cache digest");
    let keys = List.map cache.entries ~f:(fun b -> key b.index) in
    Public.require
      (List.length keys = List.length (List.dedup_and_sort keys ~compare:String.compare))
      "Duplicate inspection cache identity";
    cache.entries)
;;

let load ~state_dir ~identity ~run ~execution_file ~domain ~stage =
  let wanted = Wire.index_key ~run ~domain ~stage in
  let blob =
    List.find (read_cache ~state_dir ~identity) ~f:(fun b ->
      String.equal (key b.index) wanted)
    |> Option.value_exn ~message:"No cached inspection"
  in
  Public.require
    (String.equal blob.index.execution_file execution_file)
    "Stale cached inspection execution";
  { blob.index with cached_unverified = true }
;;

let save ?(rebuild_invalid = false) ~state_dir ~identity index =
  validate_index index;
  let index = { index with Wire.Index.cached_unverified = false } in
  let entries =
    match Or_error.try_with (fun () -> read_cache ~state_dir ~identity) with
    | Ok entries -> entries
    | Error _ when rebuild_invalid -> []
    | Error error -> Error.raise error
  in
  let entries =
    List.take
      ({ Blob.digest = index_digest index; index }
       :: List.filter entries ~f:(fun b -> not (String.equal (key b.index) (key index))))
      8
  in
  let data = Sexp.to_string_mach (Cache.sexp_of_t { version = 1; identity; entries }) in
  Public.require
    (String.length data <= (8 * index_limit) + 65536)
    "Inspection cache exceeds byte budget";
  Core_unix.mkdir_p state_dir ~perm:0o700;
  let temporary = Filename_unix.temp_file ~in_dir:state_dir ".asic-inspection-" ".tmp" in
  Exn.protect
    ~finally:(fun () ->
      if Poly.equal (Sys_unix.file_exists temporary) `Yes then Core_unix.unlink temporary)
    ~f:(fun () ->
      Out_channel.write_all temporary ~data;
      Core_unix.rename ~src:temporary ~dst:(cache_path ~state_dir ~identity))
;;
