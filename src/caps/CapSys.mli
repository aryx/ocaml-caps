(* Capability-aware wrappers of the dangerous functions in Sys.ml *)

val argv : < Cap.argv; ..> -> string array
val set_signal : < Cap.signal; .. > -> int -> Sys.signal_behavior -> unit
val chdir : < Cap.chdir; .. > -> string -> unit
val getenv: < Cap.env; .. > -> string -> string
val getenv_opt: < Cap.env; .. > -> string -> string option

(* DO NOT USE, use Cmd instead *)
val command: < Cap.fork; Cap.exec; Cap.wait; .. > -> string -> int
