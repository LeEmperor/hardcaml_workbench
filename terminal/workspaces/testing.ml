open Common

(** Project-only investigation. The compact utility column keeps generic process tests and
    execution accessible without borrowing ASIC selection/provenance. *)
let pane kind =
  tile
    ~presentation:
      { inherit_presentation with
        run_reference = Some false
      ; binding_badge = Some "hidden"
      ; padding = Some 0
      ; hints = Some false
      ; compact_summary = Some true
      }
    kind
;;

let definition : Definition.t =
  { id = "testing"
  ; name = "Testing"
  ; tiles =
      [ navigation
      ; pane "live-status"
      ; pane "project-tests"
      ; pane "execution"
      ; pane "simulation-catalog"
      ; pane "simulation-attempts"
      ; pane "simulation-cases"
      ; pane "simulation-detail"
      ; pane "simulation-artifacts"
      ; pane "simulation-logs"
      ]
  ; layout =
      Stack
        [ navigation_leaf
        ; Weighted_columns
            [ ( 2
              , Stack
                  [ leaf ~height:6 ~weight:0 "live-status"
                  ; leaf ~height:6 "project-tests"
                  ; leaf ~height:6 "execution"
                  ] )
            ; ( 3
              , Stack
                  [ leaf ~height:12 ~weight:2 "simulation-catalog"
                  ; leaf ~height:7 "simulation-attempts"
                  ; leaf ~height:7 "simulation-cases"
                  ] )
            ; ( 3
              , Stack
                  [ leaf ~height:12 ~weight:2 "simulation-detail"
                  ; leaf ~height:7 "simulation-artifacts"
                  ; leaf ~height:7 "simulation-logs"
                  ] )
            ]
        ]
  }
;;
