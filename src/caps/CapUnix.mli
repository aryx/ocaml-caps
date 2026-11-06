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
*)

(* a timer, which ends in a signal (SIGALRM, SIGVTALRM, SIGPROF) *)
val setitimer :
  < Cap.signal; .. > ->
  Unix.interval_timer ->
  Unix.interval_timer_status ->
  Unix.interval_timer_status

(* the end of the process, at once: no at_exit, nothing flushed (a forked
 * child's way out) *)
val _exit : < Cap.exit; .. > -> int -> 'a

(* a named pipe made, a file *)
val mkfifo : < Cap.open_out; .. > -> string -> Unix.file_perm -> unit

(* the network: a host's addresses; a socket, connected or listening *)
val getaddrinfo :
  < Cap.network; .. > ->
  string -> string -> Unix.getaddrinfo_option list -> Unix.addr_info list
val socket :
  < Cap.network; .. > ->
  ?cloexec:bool -> Unix.socket_domain -> Unix.socket_type -> int ->
  Unix.file_descr
val connect : < Cap.network; .. > -> Unix.file_descr -> Unix.sockaddr -> unit
val bind : < Cap.network; .. > -> Unix.file_descr -> Unix.sockaddr -> unit
val listen : < Cap.network; .. > -> Unix.file_descr -> int -> unit
val accept :
  < Cap.network; .. > ->
  ?cloexec:bool -> Unix.file_descr -> Unix.file_descr * Unix.sockaddr

(* the clock: the time, read or waited for *)
val gettimeofday : < Cap.clock; .. > -> unit -> float
val time : < Cap.clock; .. > -> unit -> float
val sleepf : < Cap.clock; .. > -> float -> unit
val sleep : < Cap.clock; .. > -> int -> unit

(* pipes *)
val pipe :
  < Cap.pipe; .. > -> ?cloexec:bool -> unit -> Unix.file_descr * Unix.file_descr
val socketpair :
  < Cap.pipe; .. > -> ?cloexec:bool -> Unix.socket_domain -> Unix.socket_type ->
  int -> Unix.file_descr * Unix.file_descr

(* what the process is told about where it runs, as its environment *)
val getpid : < Cap.env; .. > -> unit -> int
val getppid : < Cap.env; .. > -> unit -> int
val getcwd : < Cap.env; .. > -> unit -> string
val gethostname : < Cap.env; .. > -> unit -> string
