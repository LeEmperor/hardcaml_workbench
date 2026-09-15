(lang dune 3.22)

(name hardcaml_workbench)

(generate_opam_files true)

(source
 (github LeEmperor/hardcaml_workbench))

(authors "Bohdan Purtell <bohdanpurtell@gmail.com>")

(maintainers "Bohdan Purtell <bohdanpurtell@gmail.com>")

(package
 (name hardcaml_workbench)
 (synopsis "Hardcaml workbench")
 (description
  "Synthesizable blocks written in Hardcaml. Installs as one wrapped library named\nhardcaml_workbench.")
 (depends
  (ocaml
   (>= 5.1))
  ; The installed library surface (lib/). Everything below is test or repo tooling
  ; and must not be forced on a consumer.
  core
  hardcaml
  hardcaml_circuits
  ppx_hardcaml
  ppx_jane
  ; Test frameworks: test/ only.
  (hardcaml_step_testbench :with-test)
  (hardcaml_waveterm :with-test)
  (ppx_expect :with-test)
  (base_quickcheck :with-test)
  (alcotest :with-test)
  ; Repo tooling: bin/generate.exe. Never installed, but needed for a root
  ; `dune build`, so they ride with-test rather than being dropped.
  (core_unix :with-test)
  (jane_rope :with-test)
  ; Web app (Bonsai, compiled to JS with js_of_ocaml). Not part of the installed
  ; library surface, so it rides with-test like the rest of the repo tooling.
  (bonsai :with-test)
  (bonsai_web :with-test)
  (js_of_ocaml :with-test)
  (js_of_ocaml-ppx :with-test)
  (ppx_css :with-test)
  (ppx_js_style :with-dev-setup)
  (ocamlformat :with-dev-setup)
  (ocaml-lsp-server :with-dev-setup)))
