open! Core
open Hardcaml_workbench_protocol

(** Client UI preference, deliberately separate from provider runs and the daemon
    workspace registry. The stable project/environment key is checked on load. *)
type t =
  { schema_version : int
  ; project_key : string
  ; selection : Asic.Selection.t
  }
[@@deriving sexp]

let create ~project_key selection = { schema_version = 1; project_key; selection }

let decode ~project_key sexp =
  let stored = t_of_sexp sexp in
  if stored.schema_version <> 1 then failwith "Unsupported terminal preference schema";
  if not (String.equal stored.project_key project_key)
  then failwith "Terminal preference project/environment mismatch";
  stored.selection
;;

let path ~state_directory ~project_key =
  Filename.concat state_directory ("launch-" ^ Plain_rpc.digest project_key ^ ".sexp")
;;

let available (selection : Asic.Selection.t) (flows : Asic.Flow.t list) =
  List.exists flows ~f:(fun flow ->
    String.equal flow.id selection.flow
    && List.mem flow.profiles selection.profile ~equal:String.equal)
;;

let%test_unit "preferences retain exact inputs, reject other project contexts, and never \
               choose a fallback"
  =
  let selection : Asic.Selection.t =
    { flow = "fixture"
    ; profile = "custom"
    ; endpoint = "synthesis"
    ; assignments = [ "WIDTH=4" ]
    }
  in
  let sexp = sexp_of_t (create ~project_key:"project/environment" selection) in
  assert (Asic.Selection.equal (decode ~project_key:"project/environment" sexp) selection);
  assert (Result.is_error (Or_error.try_with (fun () -> decode ~project_key:"other" sexp)));
  assert (not (available selection []));
  assert (
    not
      (available
         selection
         [ { id = "fixture"
           ; profiles = [ "default" ]
           ; default_profile = "default"
           ; fresh_stage_endpoints = []
           }
         ]))
;;
