open! Core
open Hardcaml_workbench_protocol

let run : Run_ref.t =
  { backend = Backend_id.of_string "asic"; id = "run:1"; build = None; label = None }
;;

let round_trip equal sexp_of of_sexp bin_size bin_write bin_read value =
  assert (equal value (of_sexp (sexp_of value)));
  let buffer = Bin_prot.Common.create_buf (bin_size value) in
  let length = bin_write buffer ~pos:0 value in
  let pos_ref = ref 0 in
  assert (equal value (bin_read buffer ~pos_ref));
  assert (!pos_ref = length)
;;

let%test_unit "inspection wire codecs preserve unknown values and provenance" =
  let row : Asic_inspection.Row.t =
    { id = "path:1"
    ; category = "setup"
    ; producer = "opensta"
    ; corner = Some "slow"
    ; group = Some "clock"
    ; name = "endpoint"
    ; value = None
    ; unit_ = Some "ns"
    ; status = "unavailable"
    ; source = "{\"path\":\"/public/timing.json\"}"
    ; fields = [ "startpoint", "a"; "endpoint", "b" ]
    }
  in
  round_trip
    Asic_inspection.Row.equal
    Asic_inspection.Row.sexp_of_t
    Asic_inspection.Row.t_of_sexp
    Asic_inspection.Row.bin_size_t
    Asic_inspection.Row.bin_write_t
    Asic_inspection.Row.bin_read_t
    row;
  let index : Asic_inspection.Index.t =
    { run
    ; execution_file = "/public/execution.json"
    ; execution_sha256 = String.make 64 'a'
    ; domain = "timing"
    ; stage = "routing"
    ; source_digest = String.make 64 'b'
    ; rows = [ row ]
    ; diagnostics = [ "missing corner" ]
    ; truncated = true
    ; cached_unverified = true
    }
  in
  round_trip
    Asic_inspection.Index.equal
    Asic_inspection.Index.sexp_of_t
    Asic_inspection.Index.t_of_sexp
    Asic_inspection.Index.bin_size_t
    Asic_inspection.Index.bin_write_t
    Asic_inspection.Index.bin_read_t
    index;
  let detail : Asic_inspection.Detail.t =
    { run
    ; domain = index.domain
    ; stage = index.stage
    ; source_digest = index.source_digest
    ; row_id = row.id
    ; text = ""
    ; error = Some "stale digest"
    }
  in
  round_trip
    Asic_inspection.Detail.equal
    Asic_inspection.Detail.sexp_of_t
    Asic_inspection.Detail.t_of_sexp
    Asic_inspection.Detail.bin_size_t
    Asic_inspection.Detail.bin_write_t
    Asic_inspection.Detail.bin_read_t
    detail;
  let snapshot : Asic.Snapshot.t =
    { configured = true
    ; flows = []
    ; description_json = None
    ; preview = None
    ; runs = []
    ; operations = []
    ; summaries = []
    ; finalizations = []
    ; artifacts = []
    ; artifact_pages = []
    ; artifact_byte_pages = []
    ; inspections = [ index ]
    ; inspection_details = [ detail ]
    ; cache_error = None
    }
  in
  round_trip
    Asic.Snapshot.equal
    Asic.Snapshot.sexp_of_t
    Asic.Snapshot.t_of_sexp
    Asic.Snapshot.bin_size_t
    Asic.Snapshot.bin_write_t
    Asic.Snapshot.bin_read_t
    snapshot;
  let legacy =
    match Asic.Snapshot.sexp_of_t snapshot with
    | Sexp.List fields ->
      Sexp.List
        (List.filter fields ~f:(function
          | Sexp.List
              (Sexp.Atom ("inspections" | "inspection_details" | "artifact_byte_pages")
              :: _) -> false
          | _ -> true))
    | _ -> assert false
  in
  assert (
    Asic.Snapshot.equal
      (Asic.Snapshot.t_of_sexp legacy)
      { snapshot with
        inspections = []
      ; inspection_details = []
      ; artifact_byte_pages = []
      });
  List.iter
    [ Asic.Operation.Inspect
        { run; domain = index.domain; stage = index.stage; refresh = false }
    ; Inspect { run; domain = index.domain; stage = index.stage; refresh = true }
    ; Inspect_detail
        { run
        ; domain = index.domain
        ; stage = index.stage
        ; source_digest = index.source_digest
        ; row_id = row.id
        }
    ; Read_artifact_bytes { run; artifact_id = "binary"; offset = 7; limit = 1024 }
    ]
    ~f:
      (round_trip
         Asic.Operation.equal
         Asic.Operation.sexp_of_t
         Asic.Operation.t_of_sexp
         Asic.Operation.bin_size_t
         Asic.Operation.bin_write_t
         Asic.Operation.bin_read_t)
;;

let%test_unit "inspection completion keys isolate full run and detail identities" =
  let index run domain stage = Asic_inspection.index_key ~run ~domain ~stage in
  assert (
    not
      (String.equal
         (index run "timing" "routing")
         (index { run with label = Some "different" } "timing" "routing")));
  let key digest row_id =
    Asic_inspection.detail_key
      ~run
      ~domain:"timing"
      ~stage:"routing"
      ~source_digest:digest
      ~row_id
  in
  assert (not (String.equal (key "a:b" "c") (key "a" "b:c")));
  assert (not (String.equal (key "digest" "row-1") (key "digest" "row-2")));
  assert (not (String.equal (key "digest-1" "row") (key "digest-2" "row")))
;;
