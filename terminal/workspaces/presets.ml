open! Core

let all = [ Overview.definition; Timing.definition; Testing.definition ]
let find id = List.find all ~f:(fun d -> String.equal d.Definition.id id)

let for_arrangement (w : Hardcaml_workbench_protocol.Workspace.Arrangement.t) =
  Option.bind w.preset ~f:find
;;

(** Machine-readable S-expression; the Python seeder consumes this directly. *)
let export_sexp () = [%sexp (all : Definition.t list)]
