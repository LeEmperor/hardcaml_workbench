open Common

(** Full-width proportions and framed minimum heights. Give FS2 most of the evidence
    area's spare rows while retaining independent execution and log panels. *)
let sidebar_weight = 1

let main_weight = 2
let session_height = 7
let project_tests_height = 6
let selector_height = 7
let simulation_height = 12
let simulation_weight = 3
let execution_height = 6
let logs_height = 6

let definition : Definition.t =
  { id = "testing"
  ; name = "Testing"
  ; tiles =
      [ navigation
      ; session
      ; selector
      ; tile "project-tests"
      ; tile "simulation"
      ; tile "execution"
      ; tile "logs"
      ]
  ; layout =
      Stack
        [ navigation_leaf
        ; Weighted_columns
            [ ( sidebar_weight
              , Stack
                  [ leaf ~height:session_height ~weight:0 "live-status"
                  ; leaf ~height:project_tests_height "project-tests"
                  ] )
            ; ( main_weight
              , Stack
                  [ leaf ~height:selector_height ~weight:0 "run-selector"
                  ; leaf ~height:simulation_height ~weight:simulation_weight "simulation"
                  ; leaf ~height:execution_height "execution"
                  ; leaf ~height:logs_height "logs"
                  ] )
            ]
        ]
  }
;;
