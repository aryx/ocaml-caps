(* Fixture: re-exports another module's alias (module_name_of("cmd_.ml")
   = "Cmd_", first-letter-capitalized), and uses the bare alias, which
   must chase the ref one hop to Cmd_'s own definition. *)

type caps = Cmd_.caps

let main (caps : < caps; .. >) = ignore caps
