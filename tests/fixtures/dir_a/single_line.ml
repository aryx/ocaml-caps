(* Fixture: simple single-line capability annotations. *)

let with_open_in (caps : < Cap.open_in; .. >) f file =
  f (open_in (Fpath.to_string file))

let system (caps : < Cap.fork; Cap.exec; Cap.wait; ..>) cmd =
  ignore caps;
  ignore cmd

let noop () = ()
