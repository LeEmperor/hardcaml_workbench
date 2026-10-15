open! Core
open Hardcaml_workbench_protocol
module Artifacts = Hardcaml_workbench_backend.Asic_artifacts
module Reference = Asic_artifact.Reference

let require condition message = if not condition then failwith message

let hash bytes =
  Cryptokit.hash_string (Cryptokit.Hash.sha256 ()) bytes
  |> Cryptokit.transform_string (Cryptokit.Hexa.encode ())
;;

let json fields = `Assoc fields
let str s = `String s
let write path bytes = Out_channel.write_all path ~data:bytes
let write_json path value = write path (Yojson.Safe.to_string value)

let rejects f =
  require (Result.is_error (Or_error.try_with f)) "Expected invalid evidence"
;;

let read_error r =
  let page = Artifacts.read ~reference:r ~offset:0 ~limit:1024 in
  require
    (Option.is_some page.error
     && String.is_empty page.text
     && page.next_offset = 0
     && page.limit = 1024)
    "Read error leaked bytes, advanced offset, or lost requested limit"
;;

(* Entirely synthetic filesystem fixtures. These never invoke a provider or tools. *)
let fixture
  ?(source = "metrics.csv")
  ?(declared = true)
  ?(extra = [])
  ?(selected = [])
  ?(checkpoints = [])
  ()
  =
  let root = Core_unix.mkdtemp "/tmp/workbench-artifacts-" |> Filename_unix.realpath in
  let path name = Filename.concat root name in
  let execution_file = path "execution.json" in
  let execution = Yojson.Safe.to_string (json [ "attempt_id", str "run-1" ]) in
  write execution_file execution;
  let metrics = "x,y\n1,2\n" in
  write (path "metrics.csv") metrics;
  write (path "acceptance.txt") "pass\n";
  write (path "postcheck.json") "{}\n";
  List.iter extra ~f:(fun (name, bytes) -> write (path name) bytes);
  let selected = `List selected in
  let results =
    json
      [ "schema_version", `Int 1
      ; "run_id", str "terminal-1"
      ; ( "provenance"
        , json
            [ "contract", str "hardcaml-asic.segment-finalization"
            ; "operation", str (path "operation.json")
            ; "selected_evidence", selected
            ] )
      ; "raw_artifacts", `List (List.map extra ~f:(fun (name, _) -> str name))
      ; "metrics", json [ "area", json [ "source", str source ] ]
      ]
  in
  let results_bytes = Yojson.Safe.to_string results in
  write (path "results.json") results_bytes;
  let ref_ name bytes = json [ "path", str (path name); "sha256", str (hash bytes) ] in
  let inventory =
    (if declared then [ "metrics.csv", json [ "sha256", str (hash metrics) ] ] else [])
    @ List.map extra ~f:(fun (name, bytes) -> name, json [ "sha256", str (hash bytes) ])
  in
  let operation =
    json
      [ "schema_version", `Int 1
      ; "contract", str "hardcaml-asic.segment-finalization"
      ; "attempt_id", str "terminal-1"
      ; "status", str "completed"
      ; ( "execution"
        , json
            [ "path", str execution_file
            ; "sha256", str (hash execution)
            ; "attempt_id", str "run-1"
            ] )
      ; "results", ref_ "results.json" results_bytes
      ; "acceptance_report", ref_ "acceptance.txt" "pass\n"
      ; "postcheck_record", str (path "postcheck.json")
      ; "postcheck_sha256", str (hash "{}\n")
      ; "mapped_files", json inventory
      ; "selected_evidence", selected
      ; "selected_checkpoints", `List checkpoints
      ]
  in
  write_json (path "operation.json") operation;
  let terminal : Asic.Terminal_result.t =
    { attempt = root
    ; results_file = path "results.json"
    ; results_digest = hash results_bytes
    ; operation_status = "completed"
    ; physical_completion = "full"
    ; acceptance = "pass"
    ; timing_goal = "pass"
    ; metrics = []
    ; checks = []
    ; evidence =
        Yojson.Safe.to_string (json [ "operation", operation; "results", results ])
    }
  in
  let summary : Asic.Summary.t =
    { run =
        { backend = Backend_id.of_string "asic"
        ; id = "run-1"
        ; build = None
        ; label = None
        }
    ; source_digest = "fixture"
    ; execution_file
    ; plan_identity = None
    ; cell_count = None
    ; cells = []
    ; metrics = []
    ; terminal = Some terminal
    ; timing = []
    ; completion = "completed"
    ; acceptance = "pass"
    ; producer = "fixture"
    ; observed_at = "fixture"
    ; freshness = Validated
    }
  in
  root, summary
;;

let find catalog name =
  List.find_exn catalog ~f:(fun r ->
    String.equal (Filename.basename r.Reference.path) name)
;;

let test_catalog () =
  let root, summary = fixture () in
  let catalog = Artifacts.list ~summary in
  require (List.length catalog = 4) "Expected exact supported receipt/source set";
  require (List.equal Reference.equal catalog (Artifacts.list ~summary)) "Unstable IDs";
  let metrics = find catalog "metrics.csv" in
  require (String.equal metrics.sha256 (hash "x,y\n1,2\n")) "Wrong SHA-256";
  require
    (not (String.is_substring metrics.label ~substring:"observed"))
    "Declared hash mislabeled";
  read_error { metrics with path = "/etc/passwd" };
  read_error { metrics with id = "unlisted-id" };
  read_error { metrics with run = { metrics.run with id = "other-run" } };
  read_error { metrics with terminal_attempt = "/other-attempt" };
  read_error { metrics with sha256 = String.make 64 '0' };
  rejects (fun () ->
    Artifacts.list ~summary:{ summary with run = { summary.run with id = "other-run" } });
  write (Filename.concat root "metrics.csv") "tampered";
  read_error metrics;
  rejects (fun () -> Artifacts.list ~summary);
  let root, summary = fixture () in
  write (Filename.concat root "results.json") "{}";
  rejects (fun () -> Artifacts.list ~summary);
  let root, summary = fixture () in
  write (Filename.concat root "operation.json") "{}";
  rejects (fun () -> Artifacts.list ~summary);
  let observed_root, summary = fixture ~declared:false () in
  let observed = find (Artifacts.list ~summary) "metrics.csv" in
  require
    (String.is_substring
       observed.label
       ~substring:"observed SHA-256; not provider-declared")
    "Observed hash presented as provider-declared";
  write (Filename.concat observed_root "metrics.csv") "new observed bytes\n";
  read_error observed;
  let updated = find (Artifacts.list ~summary) "metrics.csv" in
  require (not (String.equal observed.id updated.id)) "ID not bound to content hash";
  let _, summary = fixture () in
  require
    (List.is_empty (Artifacts.list ~summary:{ summary with terminal = None }))
    "Invented catalog";
  let name = String.make 210 'n' ^ ".txt" in
  let root, summary = fixture ~source:name ~declared:false () in
  write (Filename.concat root name) "x";
  let r = find (Artifacts.list ~summary) name in
  require
    (String.length r.label <= 160
     && String.is_substring r.label ~substring:"..."
     && String.is_suffix r.label ~suffix:" [observed SHA-256; not provider-declared]")
    "Long label was not honestly truncated"
;;

let test_pages () =
  let raw = "a\195\169\240\159\152\128\n\t\027[31mred\r\001\194\133end" in
  let _, summary =
    fixture
      ~extra:
        [ "unicode.txt", raw; "chip.gds", "\000\255binary"; "invalid.txt", "\192\128" ]
      ()
  in
  let catalog = Artifacts.list ~summary in
  let reference = find catalog "unicode.txt" in
  let page offset limit = Artifacts.read ~reference ~offset ~limit in
  let first = page 0 2 in
  let smaller = page 0 1 in
  require
    (first.limit = 2
     && smaller.limit = 1
     && (not (Asic_artifact.Page.equal first smaller))
     && Asic_artifact.Page.equal first { smaller with limit = 2 })
    "Same-offset pages with different requested limits lost their identities";
  let key offset limit =
    Asic_artifact.read_key ~run:reference.run ~artifact_id:reference.id ~offset ~limit
  in
  require
    (String.equal (key 0 2) ("artifact-read:run-1:" ^ reference.id ^ ":0:2")
     && String.equal (key 0 2) (key 0 2)
     && (not (String.equal (key 0 1) (key 0 2)))
     && not (String.equal (key 0 2) (key 1 2)))
    "Shared read key is unstable or omits paging arguments";
  require
    (String.equal first.text "a" && first.next_offset = 1 && not first.eof)
    "UTF-8 split";
  let second = page first.next_offset 2 in
  require
    (String.equal second.text "\195\169" && second.next_offset = 3)
    "Unicode corrupted";
  require (Option.is_some (page 3 1).error) "Too-small scalar page accepted";
  require (Option.is_some (page 2 8).error) "Continuation offset accepted";
  let full = page 0 65536 in
  require
    (String.equal full.text "a\195\169\240\159\152\128\n\t[31mredend"
     && full.eof
     && full.next_offset = String.length raw)
    "Controls or raw offsets incorrect";
  let eof = page full.next_offset 1 in
  require
    (eof.eof && String.is_empty eof.text && Option.is_none eof.error)
    "EOF inaccurate";
  List.iter
    [ -1, 1; 0, 0; 0, 65537; String.length raw + 1, 1 ]
    ~f:(fun (offset, limit) ->
      let result = page offset limit in
      require
        (Option.is_some result.error && result.offset = offset && result.limit = limit)
        "Invalid page accepted or requested paging arguments lost on error");
  List.iter [ "chip.gds"; "invalid.txt" ] ~f:(fun name ->
    let r = find catalog name in
    require (String.equal r.kind "binary") "Binary classification failed";
    read_error r);
  let _, summary = fixture ~extra:[ "large.txt", String.make (65536 + 20) 'x' ] () in
  let reference = find (Artifacts.list ~summary) "large.txt" in
  let page = Artifacts.read ~reference ~offset:0 ~limit:65536 in
  require
    (String.length page.text = 65536 && (not page.eof) && page.next_offset = 65536)
    "Page cap/eof"
;;

let test_containment_and_replacement () =
  let outside, _ = fixture () in
  let absolute = Filename.concat outside "metrics.csv" in
  let _, summary = fixture ~source:absolute () in
  rejects (fun () -> Artifacts.list ~summary);
  let root, summary = fixture ~source:"../metrics.csv" () in
  ignore (root : string);
  rejects (fun () -> Artifacts.list ~summary);
  let root, summary = fixture ~source:"escape.csv" ~declared:false () in
  Core_unix.symlink ~target:absolute ~link_name:(Filename.concat root "escape.csv");
  rejects (fun () -> Artifacts.list ~summary);
  let root, summary = fixture () in
  let r = find (Artifacts.list ~summary) "metrics.csv" in
  let path = Filename.concat root "metrics.csv" in
  Core_unix.unlink path;
  Core_unix.symlink ~target:absolute ~link_name:path;
  read_error r;
  Core_unix.unlink path;
  Core_unix.mkfifo path ~perm:0o600;
  read_error r;
  Core_unix.unlink path;
  write path (String.make ((16 * 1024 * 1024) + 1) 'x');
  read_error r;
  rejects (fun () -> Artifacts.list ~summary);
  let _, summary =
    fixture ~extra:(List.init 30 ~f:(fun i -> Int.to_string i ^ ".txt", "x")) ()
  in
  rejects (fun () -> Artifacts.list ~summary)
;;

let test_selected_checkpoint_sources () =
  let outside, _ = fixture () in
  let source = Filename.concat outside "metrics.csv" in
  let selected =
    json
      [ "source", str source
      ; "sha256", str (hash "x,y\n1,2\n")
      ; "mapped", str "metrics.csv"
      ; "boundary", str "signoff"
      ]
  in
  let checkpoint boundary path = json [ "boundary", str boundary; "path", str path ] in
  let _, summary =
    fixture ~selected:[ selected ] ~checkpoints:[ checkpoint "signoff" outside ] ()
  in
  let catalog = Artifacts.list ~summary in
  let reference =
    List.find_exn catalog ~f:(fun r -> String.equal r.Reference.path source)
  in
  let page = Artifacts.read ~reference ~offset:0 ~limit:1024 in
  require
    (Option.is_none page.error && String.equal page.text "x,y\n1,2\n")
    "Exact hash-bearing checkpoint source unavailable";
  let _, summary =
    fixture ~selected:[ selected ] ~checkpoints:[ checkpoint "routing" outside ] ()
  in
  rejects (fun () -> Artifacts.list ~summary);
  let _, summary = fixture ~selected:[ selected ] ~checkpoints:[] () in
  rejects (fun () -> Artifacts.list ~summary);
  let selected = json [ "source", str source; "boundary", str "signoff" ] in
  let _, summary =
    fixture ~selected:[ selected ] ~checkpoints:[ checkpoint "signoff" outside ] ()
  in
  require
    (not
       (List.exists (Artifacts.list ~summary) ~f:(fun r ->
          String.equal r.Reference.path source)))
    "Unhashed external source entered catalog"
;;

let () =
  test_catalog ();
  test_pages ();
  test_containment_and_replacement ();
  test_selected_checkpoint_sources ()
;;
