(* Fixture: things that must NOT be picked up as capability usage. *)

(* A comment mentioning example syntax like < Cap.fake_one; .. > or
   caps should not be counted: it's just documentation. *)

let cmp (a : int) (b : int) = a < b
let cmp2 (a : int) (b : int) (c : int) = a < b && b > c
let neq (caps : int) = caps <> 0

let help_text = " usage: foo <initcmd> <Cap.bar> "
let another_string = "< caps; .. > looks like an annotation but is a string"

let ok_one (caps : < Cap.env; .. >) = ignore caps
