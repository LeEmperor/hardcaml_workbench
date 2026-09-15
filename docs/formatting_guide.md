# Hardware Source Formatting Guide

## 1. Purpose

This guide is the source of truth for coding style in this repository. It covers file
headers, port naming, the `I_Regs`/`I_Wires` paradigm, and when to use `Always` versus plain
`Signal` for registers and combinational logic. It will later cover testbench structure.

New modules should follow these conventions, and existing modules should be brought in line
when edited.

The rules apply primarily to synthesizable modules under `lib/`. Testbench-local variables,
software-only helpers, and direction-neutral value types follow the exceptions described
below.

## 2. File headers

Every OCaml hardware source file begins with four comments in this order:

```ocaml
(* University of Florida *)
(* Author: Bohdan Purtell *)
(* Module: "module_name.ml" *)
(* Short description of the module.

   Additional paragraphs remain inside the fourth comment. Continuation lines use the
   indentation shown here.
*)
```

The header fields mean:

1. The first comment identifies the university.
2. The second comment identifies the author.
3. The third comment contains the source filename in quotation marks.
4. The fourth comment describes the module, its boundaries, and any important implementation
   context.

When editing or formatting a file:

- Preserve the four comments as separate comments.
- Preserve their order.
- Do not combine the university, author, module, and description into one block.
- Do not remove the quotation marks around the module filename.
- Keep longer design notes inside the fourth comment.
- Update the module filename if the file itself is renamed.

## 3. Module layout

A hardware source file declares its pieces in this order:

1. Header comments (section 2)
2. `open!` lines (`Core`, `Hardcaml`, `Signal`, then any project helpers)
3. Configuration and value types (`Config`, direction-neutral records)
4. `module I` and `module O` (sections 4 and 7)
5. `module States`, if the module has an FSM (section 8.4)
6. `module I_Regs` and `module I_Wires` (section 8)
7. `let create (scope : Scope.t) (i : _ I.t) : _ O.t = ...`
8. `let hierarchical ?instance scope i = ...`, if the module is instantiated by a parent

## 4. External port names

Hardcaml module ports use lower snake case and an explicit direction suffix.

### 4.1 Input ports

Every field in a module's `I` interface ends in `_i`:

```ocaml
module I = struct
  type 'a t =
    { clock_i : 'a
    ; reset_i : 'a
    ; data_i : 'a [@bits 8]
    ; valid_i : 'a
    }
  [@@deriving hardcaml]
end
```

### 4.2 Output ports

Every field in a module's `O` interface ends in `_o`:

```ocaml
module O = struct
  type 'a t =
    { data_o : 'a [@bits 8]
    ; valid_o : 'a
    ; error_o : 'a
    }
  [@@deriving hardcaml]
end
```

The suffix rule applies to every external port category, including:

- Clocks and resets
- Data and control buses
- Valid and ready handshakes
- Enables
- Status and error indicators
- Debug ports

Signal direction is always relative to the module declaring the `I` or `O` interface, not
relative to the board, peripheral, or remote endpoint.

## 5. Direction-neutral types

Do not add `_i` or `_o` to fields of a type that represents a value rather than a directional
module interface.

```ocaml
module Word = struct
  type 'a t =
    { data : 'a [@bits 8]
    ; control : 'a [@bits 2]
    }
  [@@deriving hardcaml]
end
```

`Word.data` and `Word.control` remain unsuffixed because `Word` has no inherent direction.
The port containing that value receives the suffix at the module boundary.

Other direction-neutral types include:

- FIFO words
- Decoded instructions
- Internal pipeline records
- Parsed headers
- Test vectors and expected-value records
- `I_Regs` and `I_Wires` records (section 8)

## 6. Internal signal names

Internal signals and local OCaml bindings do not require `_i` or `_o`. Use a concise name
that describes the signal's role:

```ocaml
let spec = Reg_spec.create ~clock:i.clock_i ~clear:i.reset_i () in
let data = reg spec i.data_i in
{ O.data_o = data }
```

This distinction keeps direction suffixes meaningful:

- `i.clock_i` is an external input port.
- `data` is an internal signal.
- `O.data_o` is an external output port.

Avoid carrying `_i` or `_o` through an entire internal pipeline merely because the original
value entered through an input or will eventually drive an output.

## 7. Interface comments

Group related ports by function and clock domain. Place the comment immediately before the
first field in the group:

```ocaml
module I = struct
  type 'a t =
    { (* System clock domain. Synchronous active-high reset. *)
      clock_i : 'a
    ; reset_i : 'a
    ; en_i : 'a
    ; (* Host loader -> instruction memory. *)
      load_addr_i : 'a [@bits 8]
    ; load_data_i : 'a [@bits 8]
    ; load_valid_i : 'a
    }
  [@@deriving hardcaml]
end
```

Comments should identify:

- The producer and consumer when that relationship is not obvious
- The clock domain
- Whether reset is synchronous or asynchronous
- Any nonstandard validity or integration behavior
- Important ownership boundaries

Do not repeat information already made obvious by the field name and type.

## 8. Internal state: `I_Regs`, `I_Wires`, and the `Always`/`Signal` split

### 8.1 What `Always` is

`Always.Variable.reg spec ~enable ~width` is not a different kind of register. It creates:

1. a `Signal.wire` holding the next value, and
2. a `Signal.reg spec ~enable` of that wire, exposed as `.value`.

`Always.Variable.wire ~default` is the same idea without the register: a wire whose value is
`default` unless something assigns it.

The next-value wire is only driven when `Always.compile [...]` runs. `compile` gathers every
`var <-- x` in the `if_`/`when_`/`switch` tree and builds one priority mux per variable. When
no branch assigns a register in a given cycle, it holds its value. When no branch assigns a
wire, it takes its default.

**`compile` only drives variables that appear in its statement list.** A variable that is
never assigned stays an undriven wire. The design builds, but circuit creation fails once that
signal is reachable from an output. Every `I_Regs` and `I_Wires` field must be assigned
somewhere inside `compile`, even if only as a default.

### 8.2 When to use which

Use **plain `Signal`** when a signal's next value is one expression:

- Pipeline and delay registers: `reg spec ~enable d`
- Free-running or simple enabled counters: `reg_fb spec ~enable ~width ~f:(fun x -> x +:. 1)`
- Datapath muxing that does not depend on FSM state

```ocaml
let data_q = reg spec ~enable:i.en_i i.data_i -- "data_q" in
let tick_count =
  reg_fb spec ~enable:i.en_i ~width:8 ~f:(fun c -> c +:. 1) -- "tick_count"
in
```

When a plain register's input is computed later in `create`, for example because it depends
on something that reads the register, declare a `wire` first and assign it with `<--` once
the source exists:

```ocaml
let next_addr = wire 8 in
let addr = reg spec ~enable:i.en_i next_addr -- "addr" in
(* ... logic that reads addr ... *)
next_addr <-- computed_addr;
```

Use **`Always` with `I_Regs`/`I_Wires`** when several FSM states or conditions assign the same
signal differently. An example is a PC that holds in `Idle_s`, increments in `Fetch_s`, and
loads a branch target in `Execute_s`. Writing that as nested `mux2` chains on `sm.is State`
works, but becomes hard to read quickly.

Mixing both in one module is expected: plain `reg`/`reg_fb` for pipeline stages and simple
counters, and `I_Regs`/`I_Wires` for the signals the FSM controls. Do not move a signal into
`I_Regs` just because the module has an FSM. Only move it if the FSM actually assigns it.

### 8.3 `I_Regs` and `I_Wires`

FSM-controlled state is declared in two direction-neutral interface records:

```ocaml
(* Registered state. Every field must be assigned inside [compile]. *)
module I_Regs = struct
  type 'a t =
    { pc : 'a [@bits 8]
    ; i_mem_waddr : 'a [@bits 8]
    ; i_mem_wren : 'a
    ; i_mem_wrdata : 'a [@bits 8]
    }
  [@@deriving hardcaml]
end

(* Combinational (Moore) strobes -- default 0, raised in-state. *)
module I_Wires = struct
  type 'a t = { pc_inc : 'a } [@@deriving hardcaml]
end
```

Conventions:

- `I_Regs` holds registered values; `I_Wires` holds combinational values.
- Fields are unsuffixed (section 5), because these records are internal, not ports.
- Each record carries a one-line comment stating whether its fields are registered or
  combinational, and their default behavior.
- If a module has no wires or no registers, omit that record. Do not declare an empty one.

Instantiate them at the top of `create`, bound to `r` and `w`, with waveform name prefixes
`reg_` and `wire_`:

```ocaml
let create (scope : Scope.t) (i : _ I.t) : _ O.t =
  let open Always in
  let spec = Reg_spec.create ~clock:i.clock_i ~clear:i.reset_i () in
  let ( -- ) = Scope.naming scope in
  (* state machine *)
  let sm = State_machine.create (module States) ~enable:i.en_i spec in
  (* regs *)
  let r = I_Regs.Of_always.reg ~enable:i.en_i spec in
  I_Regs.Of_always.apply_names ~prefix:"reg_" ~naming_op:(Scope.naming scope) r;
  (* wires *)
  let w = I_Wires.Of_always.wire Signal.zero in
  I_Wires.Of_always.apply_names ~prefix:"wire_" ~naming_op:(Scope.naming scope) w;
  ...
```

Short local aliases such as `let pc = r.pc in` are allowed when they make `compile` easier to
read. Keep them grouped under an `(* aliases *)` comment.

### 8.4 States

- FSM states live in `module States` with
  `[@@deriving sexp_of, compare ~localize, enumerate]`.
- State constructors use capitalized snake case with an `_s` suffix: `Idle_s`, `Fetch_s`,
  `Decode_s`, `Execute_s`.
- Create the state machine with `State_machine.create (module States) ~enable spec`, bound to
  `sm`.

### 8.5 Structure of `compile`

Order the statement list in three commented sections:

```ocaml
compile
  [ (* registered defaults *)
    r.i_mem_waddr <-- r.i_mem_waddr.value
  ; r.i_mem_wren <--. 0
  ; when_ w.pc_inc.value [ r.pc <-- r.pc.value +:. 1 ]
  ; (* Moore outputs per state *)
    sm.switch ~default:[] [ Fetch_s, [ w.pc_inc <--. 1 ] ]
  ; (* next-state logic *)
    sm.switch
      ~default:[ sm.set_next Idle_s ]
      [ Idle_s, [ sm.set_next Fetch_s ]
      ; Fetch_s, [ sm.set_next Decode_s ]
      ; Decode_s, [ sm.set_next Execute_s ]
      ; Execute_s, [ sm.set_next Fetch_s ]
      ]
  ]
```

1. **Registered defaults** assign every `I_Regs` field that the later sections do not always
   assign. Choose a hold (`r.x <-- r.x.value`) or a pulse (`r.x <--. 0`) explicitly for each.
   Later statements override earlier ones, so defaults come first.
2. **Moore outputs** raise `I_Wires` fields and registered enables per state.
3. **Next-state logic** contains `sm.set_next` transitions and any register updates tied to a
   transition.

Read `I_Regs`/`I_Wires` fields through `.value` everywhere outside the left-hand side of `<--`,
including in the output record and in any plain-`Signal` logic.

## 9. Port references in implementation code

Access inputs through the typed input record:

```ocaml
let spec = Reg_spec.create ~clock:i.clock_i ~clear:i.reset_i () in
```

Construct outputs using their complete suffixed field names:

```ocaml
{ O.data_o = data
; valid_o = valid
; error_o = error
}
```

Comments that name an external port should use its complete `_i` or `_o` name. Comments that
describe a protocol concept rather than a concrete port may use the protocol name without a
suffix.

## 10. Tests and documentation

Testbenches access the same generated interface fields and therefore use the same suffixes:

```ocaml
i.reset_i := Bits.vdd;
expect_int "output valid" o.valid_o 0;
```

Interface tables and signal-specific prose in documentation must also use the complete port
names. When a port is renamed, update:

- The declaring `I` or `O` record
- All implementation references
- Testbench drivers and monitors
- Documentation tables and prose
- Generated-RTL or integration scripts that refer to the port by name

### 10.1 Testbench architecture

_To be defined._ This section will cover testbench file layout, shared driver/monitor
helpers, expect-test versus waveform tests, and VCD output locations.

## 11. Formatting and verification

Use the repository formatter and lint configuration rather than manually aligning code:

```sh
./scripts/with-switch.sh dune build @fmt
./scripts/with-switch.sh dune build @lint
./scripts/with-switch.sh dune build
```

Exception: a `create` body may be wrapped in `[@@@ocamlformat "disable"]` /
`[@@@ocamlformat "enable"]` when hand alignment makes `Always` blocks or alias groups
noticeably easier to read. Keep the disabled region limited to `create`.

Before considering a naming or formatting change complete:

1. Confirm all `I` fields end in `_i`.
2. Confirm all `O` fields end in `_o`.
3. Confirm direction-neutral record fields, including `I_Regs` and `I_Wires`, remain
   unsuffixed.
4. Confirm the four-part source header remains intact.
5. Confirm every `I_Regs` and `I_Wires` field is assigned inside `compile`.
6. Search for stale port names in source, tests, documentation, and integration code.
7. Run formatting, lint, affected tests, and the build.
