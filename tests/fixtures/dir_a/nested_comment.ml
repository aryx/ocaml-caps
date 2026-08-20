(* Fixture: nested comment before a real annotation. Everything in this
   (* nested (* Cap.deeply_nested *) comment *) must be ignored. *)
let f (caps : < Cap.readdir; .. >) = ignore caps
