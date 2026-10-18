open! Core
open Bonsai_term

type t =
  | Running
  | Pending
  | Completed
  | Failed
  | Cancelled
  | Skipped
  | Not_requested
  | Unknown
  | Ready
  | Stale
  | Pin
  | Artifact
  | Log
  | Seed
  | Report
  | Trace
  | Info
[@@deriving enumerate]

type frames =
  { dot : View.t
  ; line : View.t
  }

let text icons kind =
  match (icons : Appearance.Icons.t) with
  | None_ -> ""
  | Ascii ->
    (match kind with
     | Running -> "|"
     | Pending -> ":"
     | Completed -> "+"
     | Failed -> "!"
     | Cancelled -> "x"
     | Skipped -> "-"
     | Not_requested -> "."
     | Unknown -> "?"
     | Ready -> ">"
     | Stale -> "~"
     | Pin -> "^"
     | Artifact -> "#"
     | Log -> "="
     | Seed -> "*"
     | Report -> "%"
     | Trace -> "/"
     | Info -> "i")
  | Unicode ->
    (match kind with
     | Running -> "⣷"
     | Pending -> "◷"
     | Completed -> "✓"
     | Failed -> "!"
     | Cancelled -> "×"
     | Skipped -> "↷"
     | Not_requested -> "·"
     | Unknown -> "?"
     | Ready -> "▸"
     | Stale -> "~"
     | Pin -> "⌖"
     | Artifact -> "◇"
     | Log -> "≡"
     | Seed -> "*"
     | Report -> "▤"
     | Trace -> "↝"
     | Info -> "i")
;;

let view ?frames icons kind =
  match icons, kind, frames with
  | Appearance.Icons.Unicode, Running, Some frames -> frames.dot
  | Ascii, Running, Some frames -> frames.line
  | _ -> View.text (text icons kind)
;;

let%test_unit "glyphs occupy one cell, ASCII is printable, Off is empty" =
  List.iter Appearance.Icons.all ~f:(fun icons ->
    List.iter all ~f:(fun kind ->
      let glyph = text icons kind in
      let expected = if Appearance.Icons.equal icons None_ then 0 else 1 in
      assert (Notty.I.width (View.Private.notty_image (view icons kind)) = expected);
      assert (Notty.I.width (Notty.I.string Notty.A.empty glyph) = expected);
      if Appearance.Icons.equal icons Ascii
      then
        assert (
          String.length glyph = 1
          && Char.to_int glyph.[0] >= 33
          && Char.to_int glyph.[0] <= 126)))
;;

let%test_unit "native frames are used only for running and respect icon mode" =
  let frames = { dot = View.text "D"; line = View.text "L" } in
  assert (phys_equal (view ~frames Unicode Running) frames.dot);
  assert (phys_equal (view ~frames Ascii Running) frames.line);
  List.iter all ~f:(fun kind ->
    assert (Notty.I.width (View.Private.notty_image (view ~frames None_ kind)) = 0));
  List.iter [ Appearance.Icons.Unicode; Ascii ] ~f:(fun icons ->
    assert (not (String.equal (text icons Unknown) (text icons Completed)));
    List.iter all ~f:(fun kind ->
      match kind with
      | Running -> ()
      | _ ->
        assert (not (phys_equal (view ~frames icons kind) frames.dot));
        assert (not (phys_equal (view ~frames icons kind) frames.line))))
;;
