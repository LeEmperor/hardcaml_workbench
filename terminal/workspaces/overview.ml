open Common

let definition : Definition.t =
  { id = "overview"
  ; name = "Overview"
  ; tiles =
      [ navigation
      ; session
      ; selector
      ; checklist
      ; tile "synthesis"
      ; tile "timing"
      ; tile "checks"
      ]
  ; layout =
      shell
        ~sidebar:[ checklist_leaf ]
        ~evidence:(List.map leaf [ "synthesis"; "timing"; "checks" ])
  }
;;
