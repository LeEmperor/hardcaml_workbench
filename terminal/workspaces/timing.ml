open Common

let definition : Definition.t =
  { id = "timing"
  ; name = "Timing"
  ; tiles =
      [ navigation
      ; session
      ; selector
      ; checklist
      ; tile "timing"
      ; tile "cts"
      ; tile "routing"
      ]
  ; layout =
      shell
        ~sidebar:[ checklist_leaf ]
        ~evidence:(List.map leaf [ "timing"; "cts"; "routing" ])
  }
;;
