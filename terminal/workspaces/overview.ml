open Common

(** Source-level layout policy. Weights divide the whole available width, not just spare
    space after minima. Heights include each tile's frame. *)
let sidebar_weight = 1

let main_weight = 2
let session_height = 7
let selector_height = 7
let checklist_height = 10
let planned_run_height = 10
let checklist_weight = 1
let planned_run_weight = 1
let summary_height = 5

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
              horizontal_stages = Some false
            ; compact_summary = Some true
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
      ; compact "planned-run"
      ]
  ; layout =
      Stack
        [ navigation_leaf
        ; Weighted_columns
            [ ( sidebar_weight
              , Stack
                  [ leaf ~height:session_height ~weight:0 "live-status"
                  ; leaf ~height:selector_height ~weight:0 "run-selector"
                  ; leaf
                      ~height:checklist_height
                      ~weight:checklist_weight
                      "stage-checklist"
                  ; leaf
                      ~height:planned_run_height
                      ~weight:planned_run_weight
                      "planned-run"
                  ] )
            ; ( main_weight
              , Stack
                  (List.map
                     (fun kind -> leaf ~height:summary_height kind)
                     [ "synthesis"
                     ; "timing"
                     ; "placement"
                     ; "routing"
                     ; "checks"
                     ; "finalization"
                     ]) )
            ]
        ]
  }
;;
