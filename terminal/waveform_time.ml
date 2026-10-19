open! Core

type scale =
  | Cells_per_tick of int
  | Ticks_per_cell of int

type cursor =
  | Left
  | Right
  | Column of int
[@@deriving equal, sexp_of]

type t =
  { columns : int
  ; start : int64
  ; stop : int64
  ; scale : scale
  }

let scale_of_code code =
  if code < -1_000_000 || code > 1_000_000 then invalid_arg "Waveform raster code limit";
  if code = -1
  then Cells_per_tick 1
  else if code < -1
  then Ticks_per_cell (-code)
  else Cells_per_tick (2 * (code + 1))
;;

let capacity ~code ~columns =
  if columns < 1 || columns > 4096 then invalid_arg "Waveform raster column limit";
  match scale_of_code code with
  | Cells_per_tick n -> (columns + n - 1) / n
  | Ticks_per_cell n -> columns * n
;;

let create ~code ~columns ~start ~stop =
  if Int64.(start < 0L || stop < start) then invalid_arg "Invalid waveform time window";
  let length = capacity ~code ~columns in
  { columns
  ; start
  ; stop = Int64.(start + min (stop - start) (of_int length - 1L))
  ; scale = scale_of_code code
  }
;;

let columns t = t.columns
let start t = t.start
let stop t = t.stop
let scale t = t.scale

let cursor t time =
  if Int64.(time < t.start)
  then Left
  else if Int64.(time > t.stop)
  then Right
  else (
    let delta = Int64.(time - t.start) in
    let column =
      match t.scale with
      | Cells_per_tick n -> Int64.(delta * of_int n)
      | Ticks_per_cell n -> Int64.(delta / of_int n)
    in
    (* [create] bounded the visible window before this multiplication, so an
       expanded tick's first cell is always in [0, columns). *)
    Column (Int64.to_int_exn column))
;;

let cell_bounds t ~column =
  if column < 0 || column >= t.columns
  then None
  else (
    let offset, count =
      match t.scale with
      | Cells_per_tick n -> column / n, 1
      | Ticks_per_cell n -> column * n, n
    in
    let offset = Int64.of_int offset in
    if Int64.(offset > t.stop - t.start)
    then None
    else (
      let first = Int64.(t.start + offset) in
      Some (first, Int64.(first + min (t.stop - first) (of_int count - 1L)))))
;;

let format_time (timescale : Waveform_data.timescale) time =
  if Int64.(time < 0L) then invalid_arg "Negative VCD physical time";
  let zeroes =
    match timescale.magnitude with
    | 1 -> 0
    | 10 -> 1
    | 100 -> 2
    | _ -> invalid_arg "Unsupported VCD timescale magnitude"
  in
  let unit_ =
    match timescale.unit_ with
    | S -> "s"
    | Ms -> "ms"
    | Us -> "us"
    | Ns -> "ns"
    | Ps -> "ps"
    | Fs -> "fs"
  in
  let number =
    if Int64.equal time 0L then "0" else Int64.to_string time ^ String.make zeroes '0'
  in
  number ^ " " ^ unit_
;;

type label =
  { tick : int64
  ; column : int
  ; text_column : int
  ; text : string
  }

type ruler =
  { labels : label list
  ; major_columns : int list
  ; minor_columns : int list
  }

let ruler t ~timescale =
  let last_column =
    match cursor t t.stop with
    | Column c -> c
    | Left | Right -> assert false
  in
  let text_width =
    Int.max
      (String.length (format_time timescale t.start))
      (String.length (format_time timescale t.stop))
  in
  let desired_cells = text_width + 2 in
  let minimum_step =
    match t.scale with
    | Cells_per_tick n -> Int.max 1 ((desired_cells + n - 1) / n)
    | Ticks_per_cell n -> desired_cells * n
  in
  let rec nice power =
    match List.find [ power; power * 2; power * 5 ] ~f:(fun n -> n >= minimum_step) with
    | Some n -> n
    | None -> nice (power * 10)
  in
  let step = nice 1 in
  let step =
    match t.scale with
    | Cells_per_tick _ -> step
    | Ticks_per_cell n -> (step + n - 1) / n * n
  in
  let minor =
    match t.scale with
    | Cells_per_tick _ -> Int.max 1 (step / 5)
    | Ticks_per_cell n -> Int.max (2 * n) (step / 5 / n * n)
  in
  let aligned stride =
    let stride = Int64.of_int stride in
    let remainder = Int64.rem t.start stride in
    let offset = if Int64.equal remainder 0L then 0L else Int64.(stride - remainder) in
    if Int64.(offset > t.stop - t.start)
    then []
    else (
      let rec loop tick columns =
        let column =
          match cursor t tick with
          | Column c -> c
          | _ -> assert false
        in
        let columns = column :: columns in
        if Int64.(t.stop - tick < stride)
        then List.rev columns
        else loop Int64.(tick + stride) columns
      in
      loop Int64.(t.start + offset) [])
  in
  let major_columns =
    0 :: last_column :: aligned step |> List.dedup_and_sort ~compare:Int.compare
  in
  let minor_columns =
    aligned minor
    |> List.dedup_and_sort ~compare:Int.compare
    |> List.filter ~f:(fun c -> not (List.mem major_columns c ~equal:Int.equal))
  in
  let candidate column =
    match cell_bounds t ~column with
    | None -> None
    | Some (tick, _) ->
      let text = format_time timescale tick in
      if String.length text > t.columns
      then None
      else
        Some
          { tick
          ; column
          ; text_column = Int.min column (t.columns - String.length text)
          ; text
          }
  in
  let apart a b =
    a.text_column + String.length a.text + 2 <= b.text_column
    || b.text_column + String.length b.text + 2 <= a.text_column
  in
  let endpoints =
    [ 0; last_column ]
    |> List.dedup_and_sort ~compare:Int.compare
    |> List.filter_map ~f:candidate
    |> List.fold ~init:[] ~f:(fun placed label ->
      if List.for_all placed ~f:(apart label) then label :: placed else placed)
  in
  let labels =
    major_columns
    |> List.filter ~f:(fun c -> c <> 0 && c <> last_column)
    |> List.filter_map ~f:candidate
    |> List.fold ~init:endpoints ~f:(fun placed label ->
      if List.for_all placed ~f:(apart label) then label :: placed else placed)
    |> List.sort ~compare:(fun a b -> Int.compare a.text_column b.text_column)
  in
  { labels; major_columns; minor_columns }
;;

let%test_unit "exact mapping, compressed/expanded partial end and huge physical units" =
  let expanded = create ~code:1 ~columns:10 ~start:100L ~stop:200L in
  assert (Int64.equal (stop expanded) 102L);
  assert (equal_cursor (cursor expanded 100L) (Column 0));
  assert (equal_cursor (cursor expanded 101L) (Column 4));
  assert (equal_cursor (cursor expanded 102L) (Column 8));
  assert (
    Option.equal
      [%equal: int64 * int64]
      (cell_bounds expanded ~column:9)
      (Some (102L, 102L)));
  assert (
    equal_cursor (cursor expanded 99L) Left && equal_cursor (cursor expanded 103L) Right);
  let compressed = create ~code:(-4) ~columns:10 ~start:100L ~stop:110L in
  assert (equal_cursor (cursor compressed 107L) (Column 1));
  assert (equal_cursor (cursor compressed 110L) (Column 2));
  assert (
    Option.equal
      [%equal: int64 * int64]
      (cell_bounds compressed ~column:2)
      (Some (108L, 110L)));
  assert (Option.is_none (cell_bounds compressed ~column:3));
  let high =
    create ~code:(-4) ~columns:10 ~start:Int64.(max_value - 9L) ~stop:Int64.max_value
  in
  assert (equal_cursor (cursor high Int64.max_value) (Column 2));
  assert (
    String.equal
      (format_time { magnitude = 100; unit_ = Ns } Int64.max_value)
      "922337203685477580700 ns");
  assert (String.equal (format_time { magnitude = 10; unit_ = Ps } 0L) "0 ps");
  assert (
    String.equal
      (format_time { magnitude = 10; unit_ = Ps } 9007199254740993L)
      "90071992547409930 ps")
;;

let%test_unit "ruler labels stay exact, separate and inside real cells at all UI widths" =
  List.iter [ -16; -4; -3; -1; 0; 2; 3; 31 ] ~f:(fun code ->
    List.iter [ 5; 32; 80; 120; 230 ] ~f:(fun columns ->
      List.iter
        [ 0L; 123L; Int64.(max_value - 5000L) ]
        ~f:(fun start ->
          let mapping = create ~code ~columns ~start ~stop:Int64.(start + 4095L) in
          let timescale : Waveform_data.timescale = { magnitude = 100; unit_ = Fs } in
          let ruler = ruler mapping ~timescale in
          List.iter ruler.labels ~f:(fun label ->
            assert (String.equal label.text (format_time timescale label.tick));
            assert (equal_cursor (cursor mapping label.tick) (Column label.column));
            assert (
              Int64.equal
                label.tick
                (fst (Option.value_exn (cell_bounds mapping ~column:label.column))));
            assert (
              label.text_column >= 0
              && label.text_column + String.length label.text <= columns));
          let rec separate = function
            | a :: (b :: _ as rest) ->
              assert (a.text_column + String.length a.text + 2 <= b.text_column);
              separate rest
            | _ -> ()
          in
          separate ruler.labels;
          List.iter (ruler.major_columns @ ruler.minor_columns) ~f:(fun column ->
            assert (Option.is_some (cell_bounds mapping ~column))))))
;;
