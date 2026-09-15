open! Core
open! Hardcaml
open! Signal

let command =
  Command.basic
    ~summary:"Generate Verilog RTL for hardcaml_workbench"
    (let%map_open.Command () = return () in
     fun () -> print_endline "no circuits yet")
;;

(* let () = Command_unix.run command *)
