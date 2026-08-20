(* Fixture: multi-line capability annotations, an alias definition,
   inline comments inside the block, and "caps" alias usage. *)

type caps = <
    Cap.stdin; Cap.stdout; Cap.stderr;
    Cap.open_in; (* for 'r' *)
    Cap.open_out; (* for 'w' *)
  >

let restrict_caps rflag (x : < caps; ..>) =
  ignore rflag;
  ignore x

let main (caps : <caps; Cap.stdout; Cap.stderr; ..>) (argv : string array) : unit =
  ignore caps;
  ignore argv
