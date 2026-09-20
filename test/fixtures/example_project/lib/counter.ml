(* University of Florida *)
(* Author: Bohdan Purtell *)
(* Module: "counter.ml" *)
(* A deterministic counter and repeated-instance top used only by the external Workbench
   fixture. *)

open! Core
open! Hardcaml
open! Signal

module I = struct
  type 'a t =
    { clock_i : 'a
    ; clear_i : 'a
    }
  [@@deriving hardcaml]
end

module O = struct
  type 'a t = { count_o : 'a [@bits 4] } [@@deriving hardcaml]
end

let create (_scope : Scope.t) (i : _ I.t) : _ O.t =
  let spec = Reg_spec.create ~clock:i.clock_i ~clear:i.clear_i () in
  let count = reg_fb spec ~width:4 ~f:(fun count -> count +:. 1) in
  { O.count_o = count }
;;

let circuit ~width =
  if width <= 0 then invalid_arg "counter width must be positive";
  let clock_i = input "clock_i" 1 in
  let clear_i = input "clear_i" 1 in
  let spec = Reg_spec.create ~clock:clock_i ~clear:clear_i () in
  let count = reg_fb spec ~width ~f:(fun count -> count +:. 1) in
  Circuit.create_exn ~name:"counter" [ output "count_o" count ]
;;

let hierarchical_circuit ~width =
  let database = Circuit_database.create () in
  let child_name = circuit ~width |> Circuit_database.insert database in
  let clock_i = input "clock_i" 1 in
  let clear_i = input "clear_i" 1 in
  let instantiate instance =
    let instantiation =
      Instantiation.create
        ()
        ~name:child_name
        ~instance
        ~inputs:[ "clock_i", clock_i; "clear_i", clear_i ]
        ~outputs:[ "count_o", width ]
    in
    Instantiation.output instantiation "count_o"
  in
  let primary = instantiate "u_counter_0" in
  let mirror = instantiate "u_counter_1" in
  ( Circuit.create_exn
      ~name:"counter_top"
      [ output "count_o" primary; output "mirror_count_o" mirror ]
  , database )
;;
