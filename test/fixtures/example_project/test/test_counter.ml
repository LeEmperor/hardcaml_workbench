open! Core
open! Hardcaml

module Sim = Cyclesim.With_interface (Fixture_counter.Counter.I) (Fixture_counter.Counter.O)

let () =
  let scope = Scope.create ~flatten_design:true () in
  let sim = Sim.create (Fixture_counter.Counter.create scope) in
  let inputs = Cyclesim.inputs sim in
  let outputs = Cyclesim.outputs sim in
  inputs.clear_i := Bits.vdd;
  Cyclesim.cycle sim;
  inputs.clear_i := Bits.gnd;
  List.iter [ 1; 2; 3; 4; 5 ] ~f:(fun expected ->
    Cyclesim.cycle sim;
    let actual = Bits.to_int_trunc !(outputs.count_o) in
    if actual <> expected
    then raise_s [%message "counter mismatch" (expected : int) (actual : int)])
;;
