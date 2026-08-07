(* Capability-aware wrappers of the functions in Random.ml *)

val int : < Cap.random; .. > -> int -> int
val get_state : < Cap.random; ..> -> unit -> Random.State.t
