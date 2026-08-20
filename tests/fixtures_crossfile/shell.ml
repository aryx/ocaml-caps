(* Fixture: defines its own local alias, referenced by other files via
   a module-qualified name (cross-file resolution test). *)

type caps = < Cap.exec; Cap.fork; Cap.wait >

let run (caps : < caps; .. >) = ignore caps
