(* University of Florida *)
(* Author: Bohdan Purtell *)
(* Module: "counter.ml" *)
(* A deterministic four-bit counter used only by the external Workbench fixture. *)

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
