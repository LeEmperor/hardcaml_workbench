(lang hardcaml-workbench 1)

(project
 (name hardcaml-counter-fixture))

(dune
 (driver ./workbench/project_driver.exe)
 (build_alias @all)
 (test_alias @runtest))
