(* Capability-aware wrappers of the dangerous functions in Stdlib.ml *)

val exit : < Cap.exit; .. > -> int -> 'a
