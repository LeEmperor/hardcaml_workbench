open Common

let compact kind =
  tile
    ~presentation:
      { inherit_presentation with
        compact_summary = Some true
      ; run_reference = Some false
      ; hints = Some false
      }
    kind
;;

let definition : Definition.t =
  { id = "overview"
  ; name = "Overview"
  ; tiles =
      [ navigation
      ; session
      ; selector
      ; { checklist with
          presentation =
            { inherit_presentation with
              horizontal_stages = Some true
            ; run_reference = Some false
            ; hints = Some false
            }
        }
      ; compact "synthesis"
      ; compact "timing"
      ; compact "placement"
      ; compact "routing"
      ; compact "checks"
      ; compact "finalization"
      ]
  ; layout =
      Stack
        [ navigation_leaf
        ; Columns [ Narrow session_leaf; selector_leaf ]
        ; leaf ~height:5 ~weight:0 "stage-checklist"
        ; Columns [ leaf ~height:6 "synthesis"; leaf ~height:6 "timing" ]
        ; Columns [ leaf ~height:6 "placement"; leaf ~height:6 "routing" ]
        ; Columns [ leaf ~height:6 "checks"; leaf ~height:6 "finalization" ]
        ]
  }
;;
