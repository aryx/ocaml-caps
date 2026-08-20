
(* get error message if put the wrong caps *)
(* val restart: < Cap.fork; Cap.exit; ..> -> unit -> unit *)
val restart: < Cap.fork; Cap.wait; Cap.exit; ..> -> unit -> unit
