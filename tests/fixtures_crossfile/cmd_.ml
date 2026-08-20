(* Fixture: alias definition referenced via a one-hop re-export from
   main.ml ("type caps = Cmd_.caps"). *)

type caps = < Cap.stdout; Cap.chdir >
