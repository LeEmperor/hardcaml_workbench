open! Core
open Hardcaml_workbench_protocol

module Log_fetch = struct
  type t =
    | Not_requested
    | Fetching
    | Received of { eof : bool }
    | Error of string
  [@@deriving equal, sexp]
end

let middle_truncate ~width text =
  if width <= 0
  then ""
  else if String.length text <= width
  then text
  else if width <= 3
  then String.prefix text width
  else (
    let available = width - 3 in
    let final_component =
      String.rfindi text ~f:(fun _ char -> Char.equal char '/')
      |> Option.map ~f:(fun index -> String.drop_prefix text index)
    in
    let prefix_length, suffix_length =
      match final_component with
      | Some suffix when String.length suffix < available ->
        available - String.length suffix, String.length suffix
      | _ ->
        let prefix_length = (available + 1) / 2 in
        prefix_length, available - prefix_length
    in
    String.prefix text prefix_length ^ "..." ^ String.suffix text suffix_length)
;;

let wrap_path ~width ~indent path =
  let content_width = width - String.length indent in
  if content_width <= 0
  then [ String.prefix indent (Int.max 0 width) ]
  else (
    let rec loop remaining lines =
      if String.length remaining <= content_width
      then List.rev ((indent ^ remaining) :: lines)
      else (
        let break =
          let rec search index =
            if index <= 0
            then None
            else if Char.equal remaining.[index] '/'
            then Some index
            else search (index - 1)
          in
          search (content_width - 1)
        in
        let length = Option.value break ~default:content_width in
        let line = String.prefix remaining length in
        let rest = String.drop_prefix remaining length in
        loop rest ((indent ^ line) :: lines))
    in
    loop path [])
;;

let wrap_value ~width ~indent value =
  let content_width = width - String.length indent in
  if content_width <= 0
  then [ String.prefix indent (Int.max 0 width) ]
  else
    String.to_list value
    |> List.chunks_of ~length:content_width
    |> List.map ~f:(fun chars -> indent ^ String.of_char_list chars)
;;

let job_outcome_lines (job : Job.t) =
  let process =
    match job.exit_status with
    | Some (Exited code) -> sprintf "Process: exited with code %d" code
    | Some (Signaled { signal }) -> "Process: terminated by signal " ^ signal
    | Some (Launch_failed _) -> "Process: launch failed"
    | None when Job.is_terminal job -> "Process: outcome unavailable"
    | None -> "Process: not finished"
  in
  let failure =
    match job.exit_status, job.failure with
    | Some (Launch_failed { reason }), _ -> Some ("Launch failure: " ^ reason)
    | _, Some reason -> Some ("Failure reason: " ^ reason)
    | _, None when Job.State.equal job.state Failed ->
      Some "Failure reason: none reported; see process outcome"
    | _ -> None
  in
  [ "STATUS: " ^ Job.State.to_string job.state; process ] @ Option.to_list failure
;;

let empty_log_notice ~job_state ~fetch =
  match fetch with
  | Log_fetch.Not_requested -> Some "(logs have not been fetched yet)"
  | Fetching -> Some "(fetching stdout/stderr...)"
  | Error message -> Some ("(log retrieval failed: " ^ message ^ ")")
  | Received { eof = true } -> Some "(job finished without stdout/stderr output)"
  | Received { eof = false } ->
    (match job_state with
     | Job.State.Running -> Some "(job is running; no stdout/stderr output so far)"
     | Complete | Failed | Cancelled ->
       Some "(job finished; waiting for remaining stdout/stderr)"
     | Queued | Starting -> Some "(job has not produced stdout/stderr output yet)")
;;

let%test_unit "job outcome follows state and process status, not failure absence" =
  let job state exit_status failure =
    { (Job.create
         ~id:(Job_id.of_string "job")
         ~kind:{ namespace = "dune"; name = "build" }
         ~project:(Project_id.of_string "project")
         ~created_at:(Timestamp.of_time_ns Time_ns.epoch))
      with
      state
    ; exit_status
    ; failure
    }
  in
  [%test_result: string list]
    (job_outcome_lines (job Complete (Some (Exited 0)) None))
    ~expect:[ "STATUS: Complete"; "Process: exited with code 0" ];
  [%test_result: string list]
    (job_outcome_lines (job Failed (Some (Exited 2)) None))
    ~expect:
      [ "STATUS: Failed"
      ; "Process: exited with code 2"
      ; "Failure reason: none reported; see process outcome"
      ];
  [%test_result: string list]
    (job_outcome_lines
       (job Failed (Some (Launch_failed { reason = "missing dune" })) None))
    ~expect:[ "STATUS: Failed"; "Process: launch failed"; "Launch failure: missing dune" ];
  [%test_result: string list]
    (job_outcome_lines (job Cancelled (Some (Signaled { signal = "TERM" })) None))
    ~expect:[ "STATUS: Cancelled"; "Process: terminated by signal TERM" ];
  [%test_result: string list]
    (job_outcome_lines (job Running None None))
    ~expect:[ "STATUS: Running"; "Process: not finished" ]
;;

let%test_unit "empty log notices distinguish fetch, drain, and EOF" =
  let notice state fetch = empty_log_notice ~job_state:state ~fetch in
  [%test_result: string option]
    (notice Running Not_requested)
    ~expect:(Some "(logs have not been fetched yet)");
  [%test_result: string option]
    (notice Running (Received { eof = false }))
    ~expect:(Some "(job is running; no stdout/stderr output so far)");
  [%test_result: string option]
    (notice Complete (Received { eof = false }))
    ~expect:(Some "(job finished; waiting for remaining stdout/stderr)");
  [%test_result: string option]
    (notice Complete (Received { eof = true }))
    ~expect:(Some "(job finished without stdout/stderr output)");
  [%test_result: string option]
    (notice Failed (Error "connection lost"))
    ~expect:(Some "(log retrieval failed: connection lost)")
;;

let%test_unit "middle truncation preserves location and final directory when it fits" =
  let root = "/home/wayne/devel/jane/hardcaml_workbench/test/fixtures/example_project" in
  [%test_result: string]
    (middle_truncate ~width:45 root)
    ~expect:"/home/wayne/devel/jane/har.../example_project";
  [%test_result: int] (String.length (middle_truncate ~width:20 root)) ~expect:20;
  [%test_result: string] (middle_truncate ~width:20 root) ~expect:"/.../example_project"
;;

let%test_unit "path wrapping prefers separators and bounds long components" =
  let path = "/home/wayne/a_component_that_exceeds_the_width/example_project" in
  let lines = wrap_path ~width:18 ~indent:"  " path in
  List.iter lines ~f:(fun line -> assert (String.length line <= 18));
  [%test_result: string]
    (lines |> List.map ~f:(fun line -> String.drop_prefix line 2) |> String.concat)
    ~expect:path;
  assert (List.exists lines ~f:(String.is_prefix ~prefix:"  /example_project"))
;;
