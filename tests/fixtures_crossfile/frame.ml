(* Fixture: "open Efuns" brings the unqualified "frame_caps" alias into
   scope, defined in efuns.ml, not this file. *)

open Efuns

let redraw (caps : < frame_caps; .. >) = ignore caps
