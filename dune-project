(lang dune 3.22)

(name hardcaml_workbench)

(generate_opam_files true)

(source
 (github LeEmperor/hardcaml_workbench))

(authors "Bohdan Purtell <bohdanpurtell@gmail.com>")

(maintainers "Bohdan Purtell <bohdanpurtell@gmail.com>")

(package
 (name hardcaml_workbench)
 (synopsis "A local development workbench for independent Hardcaml projects")
 (description
  "A standalone native OCaml and Bonsai Web application for inspecting, running,\nmeasuring, and debugging independently owned Hardcaml projects.")
 (allow_empty)
 (depends
  (ocaml
   (>= 5.1))
  ; Portable shared protocol and application code.
  core
  ppx_jane
  ; Native daemon, backend, and adapters.
  core_unix
  ; Browser application and JavaScript build.
  bonsai
  bonsai_web
  js_of_ocaml
  js_of_ocaml-ppx
  ppx_css
  ; Repository development tools.
  (ppx_js_style :with-dev-setup)
  (ocamlformat :with-dev-setup)
  (ocaml-lsp-server :with-dev-setup)))
