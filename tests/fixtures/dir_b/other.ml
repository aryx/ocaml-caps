(* Fixture in a second directory, to test per-directory aggregation. *)

let chdir (caps : < Cap.chdir; ..>) dir = ignore caps; ignore dir
let kill (caps : < Cap.kill; .. >) pid = ignore caps; ignore pid
let getenv (caps : < Cap.env; ..>) name = ignore caps; ignore name
