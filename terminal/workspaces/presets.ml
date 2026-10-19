open! Core

let starters = [ Overview.definition; Timing.definition; Testing.definition ]
let all = starters @ [ Waveforms.definition ]
let find id = List.find all ~f:(fun d -> String.equal d.Definition.id id)

(** Safe after Get, after import, on reconnect, and concurrently from multiple clients.
    The service atomically persists both defaults and their completion marker. *)
let bootstrap =
  Hardcaml_workbench_protocol.Workspace.Operation.Bootstrap
    (List.map starters ~f:Definition.template)
;;

let for_arrangement (w : Hardcaml_workbench_protocol.Workspace.Arrangement.t) =
  Option.bind w.preset ~f:find
;;

(** Machine-readable S-expression; the Python seeder consumes this directly. *)
let export_sexp () = [%sexp (all : Definition.t list)]
