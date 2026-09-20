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
  "A standalone native OCaml application for inspecting, running, measuring, and\ndebugging independently owned Hardcaml projects.")
 (depends
  (ocaml
   (>= 5.1))
  ; Portable shared protocol and application code.
  core
  ppx_jane
   ; Native daemon, backend, and adapters.
   core_unix
   bonsai
   bonsai_term
   async
   cohttp-async
   cryptokit
   ; Repository development tools.
  (ppx_js_style :with-dev-setup)
  (ocamlformat :with-dev-setup)
   (ocaml-lsp-server :with-dev-setup)))

(package
 (name hardcaml_workbench_web)
 (synopsis "Optional browser client for Hardcaml Workbench")
 (description
  "The optional Bonsai Web client and precompiled browser assets for Hardcaml Workbench.")
 (allow_empty)
 (depends
  (ocaml
   (>= 5.1))
  core
  ppx_jane
  bonsai
  bonsai_web
  js_of_ocaml
  js_of_ocaml-ppx
  ppx_css
  (ppx_js_style :with-dev-setup)
  (ocamlformat :with-dev-setup)))
