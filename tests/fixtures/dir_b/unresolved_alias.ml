(* Fixture: "caps" used without a local "type caps = < ... >" in this
   file. Must NOT be expanded; must be tallied as unresolved instead. *)

let f (caps : < caps; Cap.env; ..>) = ignore caps
