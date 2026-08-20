(* Fixture: lives inside a directory declared as a git submodule in
   .gitmodules -- must be skipped by default. *)

let g (caps : < Cap.network; Cap.exec; .. >) = ignore caps
