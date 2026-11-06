
let chdir (caps : < Cap.chdir; ..>) = 
  let _ = caps#chdir in
  (* nosemgrep: use-caps *)
  Sys.chdir

let argv (caps : < Cap.argv; .. >) = 
  let _ = caps#argv in
  (* nosemgrep: do-not-use-argv *)
  Sys.argv

let set_signal (caps : < Cap.signal; .. >) =
  let _ = caps#signal in
  (* nosemgrep: use-caps *)
  Sys.set_signal

(* the files *)
let file_exists (caps : < Cap.readdir; .. >) file =
  let _ = caps#readdir file in
  (* nosemgrep: use-caps *)
  Sys.file_exists file
let is_directory (caps : < Cap.readdir; .. >) file =
  let _ = caps#readdir file in
  (* nosemgrep: use-caps *)
  Sys.is_directory file
let readdir (caps : < Cap.readdir; .. >) dir =
  let _ = caps#readdir dir in
  (* nosemgrep: use-caps *)
  Sys.readdir dir
let remove (caps : < Cap.open_out; .. >) file =
  let _ = caps#open_out file in
  (* nosemgrep: use-caps *)
  Sys.remove file

let getenv (caps : < Cap.env; ..>) = 
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Sys.getenv
(* TODO: add to ocaml-light
let getenv_opt (caps : < Cap.env; ..>) = 
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Sys.getenv_opt
*)

let command (caps : < Cap.fork; Cap.exec; Cap.wait; .. >) cmd = 
  let _ = caps#fork in
  let _ = caps#exec cmd in
  let _ = caps#wait in
  (* nosemgrep: use-caps *)
  Sys.command cmd

(* the processor time used: profiling, but a clock all the same *)
let time (caps : < Cap.clock; ..>) =
  let _ = caps#clock in
  (* nosemgrep: use-caps *)
  Sys.time

let getcwd (caps : < Cap.env; ..>) =
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Sys.getcwd
