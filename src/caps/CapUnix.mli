(* Capability-aware wrappers of the dangerous functions in Unix.ml *)

(* See also commons/CapExec.ml *)
val execv : < Cap.exec; .. > -> string -> string array -> unit
val execve : < Cap.exec; .. > -> string -> string array -> string array -> unit
(*val execvp : < Cap.exec; .. > -> string -> string array -> 'a*)

val environment : < Cap.env; ..> -> unit -> string array

(* You should use CapExec.ml instead *)
val system : < Cap.exec; Cap.fork; Cap.wait; .. > -> string -> Unix.process_status

val fork : < Cap.fork; .. > -> unit -> int
val wait : < Cap.wait; .. > -> unit -> int * Unix.process_status
val waitpid : 
  < Cap.wait; .. > -> Unix.wait_flag list -> int -> int * Unix.process_status
val kill: < Cap.kill; ..> -> int -> int -> unit

val chdir: < Cap.chdir; ..> -> string -> unit

val unlink: < Cap.open_out; .. > -> string -> string -> unit

(*
val alarm : <  Cap.time_limit; .. > -> int -> int

val setitimer :
  < Cap.time_limit; .. > ->
  Unix.interval_timer ->
  Unix.interval_timer_status ->
  Unix.interval_timer_status
*)
