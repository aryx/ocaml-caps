(lang dune 3.7)

(name caps)
(map_workspace_root false)

(generate_opam_files)
(version 0.1.1)

(source (github aryx/ocaml-caps))
(maintainers "Yoann Padioleau <yoann.padioleau@gmail.com>")
(authors "Yoann Padioleau <yoann.padioleau@gmail.com>")
(license "LGPL-2.1-only WITH OCaml-LGPL-linking-exception")

;; Packages

(package (name caps)
  (synopsis "Capability types and rules for OCaml")
  (description "Capability types (Cap.ml) enforcing restricted I/O access across a codebase.")
)
