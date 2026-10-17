open Common

(** Top-row proportions divide the full width. Heights include tile frames; the
    investigation tree below remains independent of these Session/selector settings. *)
let session_weight = 1

let selector_weight = 2
let session_min_width = 30
let session_height = 7
let selector_height = 7

let definition : Definition.t =
  { id = "timing"
  ; name = "Timing"
  ; tiles =
      [ navigation
      ; session
      ; selector
      ; tile "timing-paths"
      ; tile "timing-detail"
      ; tile "timing-context"
      ]
  ; layout =
      Stack
        [ navigation_leaf
        ; Weighted_columns
            [ ( session_weight
              , Leaf
                  { kind = "live-status"
                  ; min_width = session_min_width
                  ; min_height = session_height
                  ; weight = 0
                  } )
            ; selector_weight, leaf ~height:selector_height ~weight:0 "run-selector"
            ]
        ; Columns
            [ Leaf { kind = "timing-paths"; min_width = 32; min_height = 10; weight = 2 }
            ; Stack
                [ Leaf
                    { kind = "timing-detail"
                    ; min_width = 48
                    ; min_height = 10
                    ; weight = 3
                    }
                ; Leaf
                    { kind = "timing-context"
                    ; min_width = 48
                    ; min_height = 8
                    ; weight = 2
                    }
                ]
            ]
        ]
  }
;;
