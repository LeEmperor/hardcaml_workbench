open! Core

(* Public integration contract is in waveform_data.mli. In particular, rendering
   uses exact ticks relative to a bounded window, never a sampled approximation.
   Installed API inspected: hardcaml/wave_data_in_events_intf.ml and
   hardcaml_waveterm/kernel/{waveform_intf,render_intf}.ml. No VCD importer is
   exposed there. Waveform.to_string accepts our By_event without an event loop. *)
type time_unit = S | Ms | Us | Ns | Ps | Fs
type timescale = { magnitude : int; unit_ : time_unit }
type signal =
  { index : int
  ; identifier : string
  ; scope : string list
  ; reference : string
  ; range : string option
  ; name : string
  ; width : int
  ; kind : string
  }
type change = { time : int64; value : string }
type limits =
  { max_bytes : int
  ; max_signals : int
  ; max_width : int
  ; max_changes : int
  ; max_value_bytes : int
  }
type t =
  { declarations : signal array
  ; histories : change array String.Map.t
  ; scale : timescale
  ; last_time : int64
  ; count : int
  }

let default_limits =
  { max_bytes = 8 * 1024 * 1024
  ; max_signals = 4096
  ; max_width = 4096
  ; max_changes = 500_000
  ; max_value_bytes = 64 * 1024 * 1024
  }
;;

let signals t = Array.copy t.declarations
let timescale t = t.scale
let time_bounds t = 0L, t.last_time
let change_count t = t.count

let timescale_to_string scale =
  let unit_ =
    match scale.unit_ with
    | S -> "s" | Ms -> "ms" | Us -> "us" | Ns -> "ns" | Ps -> "ps" | Fs -> "fs"
  in
  Int.to_string scale.magnitude ^ " " ^ unit_
;;

exception Invalid_vcd of string
let invalid message = raise (Invalid_vcd message)
let unsupported message = invalid ("Unsupported VCD: " ^ message)
let limit message = invalid ("VCD limit exceeded: " ^ message)

let decimal text =
  (not (String.is_empty text)) && String.for_all text ~f:Char.is_digit
;;

let nonnegative_int64 text =
  if not (decimal text) then invalid ("Invalid timestamp: " ^ text);
  match Int64.of_string_opt text with
  | Some n when Int64.(n >= 0L) -> n
  | _ -> unsupported "timestamp exceeds signed int64 ticks"
;;

let positive_int text =
  if not (decimal text) then invalid ("Invalid positive integer: " ^ text);
  match Int.of_string_opt text with
  | Some n when n > 0 -> n
  | _ -> invalid ("Invalid positive integer: " ^ text)
;;

let parse_scale parts =
  let text = String.concat parts in
  let split = ref 0 in
  while !split < String.length text && Char.is_digit text.[!split] do
    incr split
  done;
  let magnitude = positive_int (String.prefix text !split) in
  if not (List.mem [ 1; 10; 100 ] magnitude ~equal:Int.equal)
  then unsupported "timescale magnitude must be 1, 10 or 100";
  let unit_ =
    match String.drop_prefix text !split with
    | "s" -> S | "ms" -> Ms | "us" -> Us | "ns" -> Ns | "ps" -> Ps | "fs" -> Fs
    | _ -> unsupported "timescale unit (expected s/ms/us/ns/ps/fs)"
  in
  { magnitude; unit_ }
;;

let parse ?(limits = default_limits) bytes =
  try
    if List.exists
         [ limits.max_bytes; limits.max_signals; limits.max_width
         ; limits.max_changes; limits.max_value_bytes ]
         ~f:(fun n -> n <= 0)
    then invalid "VCD limits must be positive";
    if String.length bytes > limits.max_bytes then limit "input bytes";
    (* A streaming token cursor avoids making a second token list proportional
       to the entire artifact. Whitespace is precisely the VCD ASCII subset. *)
    let position = ref 0 in
    let whitespace = function ' ' | '\t' | '\r' | '\n' -> true | _ -> false in
    let next () =
      while !position < String.length bytes && whitespace bytes.[!position] do
        incr position
      done;
      if !position = String.length bytes then None
      else (
        let first = !position in
        while !position < String.length bytes && not (whitespace bytes.[!position]) do
          let c = Char.to_int bytes.[!position] in
          if c < 33 || c > 126 then invalid "Non-ASCII/control byte in VCD token";
          incr position
        done;
        let length = !position - first in
        if length > 8192 && length - 1 > limits.max_width then limit "token length";
        Some (String.sub bytes ~pos:first ~len:length))
    in
    let required () =
      match next () with Some s -> s | None -> invalid "Truncated VCD"
    in
    let body () =
      let rec loop acc count =
        match required () with
        | "$end" -> List.rev acc
        | token ->
          if count >= 8192 then limit "directive tokens";
          loop (token :: acc) (count + 1)
      in
      loop [] 0
    in
    let scope = ref [] in
    let scale = ref None in
    let declarations = ref [] in
    let declaration_count = ref 0 in
    let widths = String.Table.create () in
    let names = String.Hash_set.create () in
    let rec header () =
      match required () with
      | "$comment" | "$date" | "$version" -> ignore (body () : string list); header ()
      | "$timescale" ->
        if Option.is_some !scale then invalid "Duplicate timescale";
        scale := Some (parse_scale (body ()));
        header ()
      | "$scope" ->
        (match body () with
         | [ ("module" | "task" | "function" | "begin" | "fork"); name ] ->
           if List.length !scope >= 128 then limit "hierarchy depth";
           if String.length name + List.sum (module Int) !scope ~f:(fun s -> String.length s + 1) > 1024
           then limit "hierarchy path length";
           scope := name :: !scope
         | _ -> invalid "Malformed/unsupported scope declaration");
        header ()
      | "$upscope" ->
        if not (List.is_empty (body ())) then invalid "Malformed upscope";
        (match !scope with
         | [] -> invalid "Unbalanced upscope"
         | _ :: rest -> scope := rest);
        header ()
      | "$var" ->
        let kind, width, identifier, reference, range =
          match body () with
          | [ kind; width; identifier; reference ] -> kind, width, identifier, reference, None
          | [ kind; width; identifier; reference; range ] ->
            kind, width, identifier, reference, Some range
          | _ -> invalid "Malformed variable declaration"
        in
        if not (List.mem
                  [ "wire"; "reg"; "integer"; "parameter"; "supply0"; "supply1"
                  ; "tri"; "tri0"; "tri1"; "triand"; "trior"; "trireg"; "wand"; "wor"
                  ; "time" ] kind ~equal:String.equal)
        then unsupported ("variable kind " ^ kind);
        let width = positive_int width in
        if width > limits.max_width then limit "signal width";
        Option.iter range ~f:(fun range ->
          if not (String.is_prefix range ~prefix:"[" && String.is_suffix range ~suffix:"]")
          then invalid "Malformed signal range";
          let inner = String.sub range ~pos:1 ~len:(String.length range - 2) in
          let integer text =
            let digits = if String.is_prefix text ~prefix:"-" then String.drop_prefix text 1 else text in
            if not (decimal digits) then invalid "Malformed signal range";
            match Int64.of_string_opt text with
            | Some x -> x
            | None -> invalid "Signal range integer overflow"
          in
          match String.split inner ~on:':' with
          | [ bit ] -> ignore (integer bit : int64);
            if width <> 1 then invalid "Single-bit range with non-scalar width"
          | [ left; right ] ->
            let left = integer left and right = integer right in
            (* Compare using bounded addition rather than overflowing subtraction. *)
            let low = Int64.min left right and high = Int64.max left right in
            let delta = Int64.of_int (width - 1) in
            if Int64.(low > max_value - delta) || not (Int64.equal Int64.(low + delta) high)
            then invalid "Signal range disagrees with declared width"
          | _ -> invalid "Malformed signal range");
        if !declaration_count >= limits.max_signals then limit "signal declarations";
        (match Hashtbl.find widths identifier with
         | Some previous when previous <> width -> invalid "Alias identifier has inconsistent width"
         | _ -> Hashtbl.set widths ~key:identifier ~data:width);
        let scope = List.rev !scope in
        let name = String.concat ~sep:"." (scope @ [ reference ^ Option.value range ~default:"" ]) in
        if String.length name > 1024 then limit "signal path length";
        if Hash_set.mem names name then invalid ("Duplicate signal name: " ^ name);
        Hash_set.add names name;
        declarations :=
          { index = !declaration_count; identifier; scope; reference; range; name; width; kind }
          :: !declarations;
        incr declaration_count;
        header ()
      | "$enddefinitions" ->
        if not (List.is_empty (body ())) then invalid "Malformed enddefinitions";
        if not (List.is_empty !scope) then invalid "Unclosed scope"
      | token -> unsupported ("header directive " ^ token)
    in
    header ();
    let scale = match !scale with Some s -> s | None -> unsupported "missing timescale" in
    if !declaration_count = 0 then invalid "VCD contains no signals";
    let histories = String.Table.create () in
    let now = ref 0L in
    let count = ref 0 in
    let value_bytes = ref 0 in
    let add identifier value ~scalar =
      let width =
        match Hashtbl.find widths identifier with
        | Some width -> width
        | None -> invalid ("Value for undeclared identifier: " ^ identifier)
      in
      if scalar && width <> 1 then invalid "Scalar assignment to a bus";
      let value = String.lowercase value in
      if String.is_empty value
         || not (String.for_all value ~f:(function '0' | '1' | 'x' | 'z' -> true | _ -> false))
      then invalid "Invalid four-state binary value";
      if String.length value > width then invalid "Vector exceeds declared width";
      if !count >= limits.max_changes then limit "value changes";
      if width > limits.max_value_bytes - !value_bytes then limit "expanded value bytes";
      value_bytes := !value_bytes + width;
      incr count;
      (* IEEE VCD abbreviated vectors extend x/z with themselves, binary with 0. *)
      let extension = match value.[0] with 'x' -> 'x' | 'z' -> 'z' | _ -> '0' in
      let value = String.make (width - String.length value) extension ^ value in
      Hashtbl.update histories identifier ~f:(fun old ->
        { time = !now; value } :: Option.value old ~default:[])
    in
    let rec data in_dump =
      match next () with
      | None -> if in_dump then invalid "Unterminated dump directive"
      | Some "$end" ->
        if not in_dump then invalid "Unexpected $end";
        data false
      | Some "$comment" -> ignore (body () : string list); data in_dump
      | Some ("$dumpvars" | "$dumpall") ->
        if in_dump then invalid "Nested dump directive";
        data true
      | Some ("$dumpoff" | "$dumpon") ->
        unsupported "dump on/off gaps (export to an external viewer)"
      | Some token ->
        (match token.[0] with
         | '#' ->
           if in_dump then invalid "Timestamp inside dump directive";
           let time = nonnegative_int64 (String.drop_prefix token 1) in
           if Int64.(time < !now) then invalid "Timestamps are not monotonic";
           now := time
         | '0' | '1' | 'x' | 'X' | 'z' | 'Z' ->
           add (String.drop_prefix token 1) (String.prefix token 1) ~scalar:true
         | 'b' | 'B' -> add (required ()) (String.drop_prefix token 1) ~scalar:false
         | 'r' | 'R' | 's' | 'S' -> unsupported "real/string value changes"
         | _ -> unsupported ("data token " ^ token));
        data in_dump
    in
    data false;
    let histories =
      Hashtbl.to_alist histories
      |> List.map ~f:(fun (identifier, changes) -> identifier, Array.of_list_rev changes)
      |> String.Map.of_alist_exn
    in
    Ok
      { declarations = Array.of_list_rev !declarations
      ; histories
      ; scale
      ; last_time = !now
      ; count = !count
      }
  with
  | Invalid_vcd message -> Or_error.error_string message
;;

let history t signal =
  if signal.index < 0 || signal.index >= Array.length t.declarations
     || not (phys_equal signal t.declarations.(signal.index))
  then invalid_arg "Waveform_data: signal does not belong to this trace";
  Map.find t.histories signal.identifier |> Option.value ~default:[||]
;;

let changes t signal = Array.copy (history t signal)

let value_in_history changes time =
  let low = ref 0 and high = ref (Array.length changes) in
  while !low < !high do
    let middle = !low + ((!high - !low) / 2) in
    if Int64.(changes.(middle).time <= time) then low := middle + 1 else high := middle
  done;
  if !low = 0 then None else Some changes.(!low - 1).value
;;

let value_at t signal ~time = value_in_history (history t signal) time
let values_at t ~time = Array.map t.declarations ~f:(fun signal -> signal, value_at t signal ~time)

let to_waveterm t ~signals ~start ~stop =
  Or_error.try_with (fun () ->
    let fail message = failwith ("Unsupported waveform render conversion: " ^ message) in
    if Int64.(start < 0L || stop < start || stop > t.last_time)
    then fail "window lies outside trace time bounds";
    let span = Int64.(stop - start) in
    if Int64.(span >= 1_000_000L) then fail "window exceeds 1,000,000 exact ticks; zoom in";
    if List.length signals > 64 then fail "select at most 64 signals";
    (* Installed Bits.create takes an inclusive maximum time, not a length. *)
    let max_time = ref (Int64.to_int_exn span) in
    let converted_changes = ref 0 in
    let converted_value_bytes = ref 0 in
    let cache = String.Table.create () in
    let waves =
      List.map signals ~f:(fun signal ->
        let events = history t signal in
        let bits value =
          if !converted_changes >= 100_000 then fail "more than 100,000 converted events";
          if String.length value > (16 * 1024 * 1024) - !converted_value_bytes
          then fail "more than 16 MiB converted value bits";
          incr converted_changes;
          converted_value_bytes := !converted_value_bytes + String.length value;
          if not (String.for_all value ~f:(function '0' | '1' -> true | _ -> false))
          then fail (signal.name ^ " contains X/Z; installed renderer is two-state");
          Hardcaml.Bits.of_bit_string value
        in
        let data =
          Hashtbl.find_or_add cache signal.identifier ~default:(fun () ->
            let initial =
              match value_in_history events start with
              | None -> fail (signal.name ^ " is uninitialized at window start")
              | Some value -> bits value
            in
            let data = Hardcaml.Wave_data_in_events.Bits.create signal.width max_time in
            let store = Hardcaml.Wave_data_in_events.Bits.event_store data in
            Hardcaml.Wave_data_in_events.Bits.Event_store.insert store 0 initial;
            Array.iter events ~f:(fun change ->
              if Int64.(change.time > start && change.time <= stop)
              then Hardcaml.Wave_data_in_events.Bits.Event_store.insert store
                     (Int64.to_int_exn Int64.(change.time - start)) (bits change.value));
            data)
        in
        { Hardcaml.Wave_data.Wave.name = signal.name
        ; width = signal.width
        ; typ = Hardcaml.Wave_data.Type.Internal
        ; wave_format = Hardcaml.Wave_format.Bit_or Hardcaml.Wave_format.Hex
        ; is_pseudo_clock = false
        ; wave_data = data
        })
      |> Array.of_list
    in
    Hardcaml.Wave_data.By_event waves)
;;

let%test_unit "VCD hierarchy, aliases, buses, exact times and unknown extension" =
  let input =
    "$timescale 10 ps $end\n$scope module top $end\n\
     $var wire 1 ! clk $end\n$var wire 4 # bus [3:0] $end\n\
     $scope module child $end\n$var wire 4 # alias [0:3] $end\n\
     $upscope $end\n$upscope $end\n$enddefinitions $end\n\
     $dumpvars 0! b1 # $end\n#9007199254740993\n1! bx #\n\
     #9007199254740994\nbz #\n#9007199254740995\nb1010 #\n"
  in
  let t = Or_error.ok_exn (parse input) in
  let ss = signals t in
  assert (String.equal ss.(2).name "top.child.alias[0:3]");
  assert (String.equal (timescale_to_string (timescale t)) "10 ps");
  assert (Int64.equal (snd (time_bounds t)) 9007199254740995L);
  assert (Option.equal String.equal (value_at t ss.(1) ~time:0L) (Some "0001"));
  assert (Option.equal String.equal (value_at t ss.(2) ~time:9007199254740993L) (Some "xxxx"));
  assert (Option.equal String.equal (value_at t ss.(1) ~time:9007199254740994L) (Some "zzzz"));
  assert (Or_error.is_error (to_waveterm t ~signals:[ss.(1)] ~start:9007199254740993L ~stop:9007199254740995L));
  assert (Or_error.is_ok (to_waveterm t ~signals:[ss.(1)] ~start:9007199254740995L ~stop:9007199254740995L))
;;

let test_header =
  "$timescale 1ns $end $scope module t $end $var wire 1 ! a $end \
   $upscope $end $enddefinitions $end "
;;

let%test_unit "VCD repeated timestamps, uninitialized state and terminal time" =
  let t = Or_error.ok_exn (parse (test_header ^ "#5 0! #5 1! #10")) in
  let s = (signals t).(0) in
  assert (Option.is_none (value_at t s ~time:4L));
  assert (Option.equal String.equal (value_at t s ~time:5L) (Some "1"));
  assert (Int64.equal (snd (time_bounds t)) 10L);
  assert (Or_error.is_error (to_waveterm t ~signals:[s] ~start:0L ~stop:10L));
  assert (Or_error.is_ok (to_waveterm t ~signals:[s] ~start:5L ~stop:10L))
;;

let%test_unit "VCD explicit malformed, unsupported and resource rejection" =
  List.iter
    [ "#3 0! #2 1!"; "0?"; "b10 !"; "r1.2 !"; "$dumpoff 0! $end"
    ; "$dumpvars 0!"; "#9223372036854775808"; "#-1"; "$end"; "bq !" ]
    ~f:(fun body -> assert (Or_error.is_error (parse (test_header ^ body))));
  assert (Or_error.is_error (parse "$enddefinitions $end"));
  assert (Or_error.is_error (parse ~limits:{ default_limits with max_bytes = 3 } test_header));
  assert (Or_error.is_error (parse ~limits:{ default_limits with max_changes = 1 } (test_header ^ "0! 1!")));
  assert (Or_error.is_error (parse ~limits:{ default_limits with max_value_bytes = 1 } (test_header ^ "0! 1!")))
;;

let%test_unit "Sparse renderer conversion preserves exact rebased events and length" =
  let t = Or_error.ok_exn (parse (test_header ^ "0! #9007199254740993 1! #9007199254740997 0!")) in
  let converted =
    Or_error.ok_exn
      (to_waveterm t ~signals:(Array.to_list (signals t))
         ~start:9007199254740992L ~stop:9007199254740997L)
  in
  (match converted with
   | Hardcaml.Wave_data.By_cycle _ -> assert false
   | Hardcaml.Wave_data.By_event waves ->
     let data = waves.(0).wave_data in
     let module D = Hardcaml.Wave_data_in_events.Bits in
     assert (D.length data = 6);
     assert (Hardcaml.Bits.to_int_trunc (D.get data 0) = 0);
     assert (Hardcaml.Bits.to_int_trunc (D.get data 1) = 1);
     assert (Hardcaml.Bits.to_int_trunc (D.get data 4) = 1);
     assert (Hardcaml.Bits.to_int_trunc (D.get data 5) = 0));
  let rendered =
    Hardcaml_waveterm.Waveform.to_string ~display_width:80 ~display_height:8 converted
  in
  assert (String.is_substring rendered ~substring:"t.a")
;;
