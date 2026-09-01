(* Capability-aware wrappers of the dangerous functions in Stdlib.ml *)

(* deprecated, use Exit.exit now *)
val exit : < Cap.exit; .. > -> int -> 'a

(* deprecated, use FS.with_open_in now *)
val open_in : < Cap.open_in; ..> -> string -> in_channel
