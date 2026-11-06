(* Capability-aware wrappers of the dangerous functions in Sys.ml *)

val argv : < Cap.argv; ..> -> string array
val set_signal : < Cap.signal; .. > -> int -> Sys.signal_behavior -> unit

(* the files: whether one is there, a directory, its names; one removed *)
val file_exists : < Cap.readdir; .. > -> string -> bool
val is_directory : < Cap.readdir; .. > -> string -> bool
val readdir : < Cap.readdir; .. > -> string -> string array
val remove : < Cap.open_out; .. > -> string -> unit
val chdir : < Cap.chdir; .. > -> string -> unit
val getenv: < Cap.env; .. > -> string -> string
(*val getenv_opt: < Cap.env; .. > -> string -> string option*)

(* DO NOT USE, use Cmd instead *)
val command: < Cap.fork; Cap.exec; Cap.wait; .. > -> string -> int

(* the processor time used: profiling, but a clock all the same *)
val time : < Cap.clock; .. > -> unit -> float
val getcwd : < Cap.env; .. > -> unit -> string
