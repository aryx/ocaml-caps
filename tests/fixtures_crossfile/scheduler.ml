(* Fixture: uses another module's alias by qualified name, and via a
   ":>" coercion. Only resolvable with tree-wide (collect()) context,
   not standalone scan_file(). *)

let build (caps : < Shell.caps; Cap.env; .. >) = ignore caps
let narrow (caps : < Shell.caps; .. >) = (caps :> < Cap.exec >)
