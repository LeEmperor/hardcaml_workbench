open Common

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
        ; Columns
            [ Narrow
                (Leaf { kind = "live-status"; min_width = 30; min_height = 7; weight = 0 })
            ; selector_leaf
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
