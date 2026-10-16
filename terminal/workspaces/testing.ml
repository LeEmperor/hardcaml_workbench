open Common

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
      shell
        ~sidebar:[ leaf "project-tests" ]
        ~evidence:(List.map leaf [ "simulation"; "execution"; "logs" ])
  }
;;
