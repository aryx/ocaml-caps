let execv (caps : < Cap.exec; ..>) cmd argv = 
  let _ = caps#exec cmd in
  (* nosemgrep: use-caps *)
  Unix.execv cmd argv
let execve (caps : < Cap.exec; ..>) cmd argv env = 
  let _ = caps#exec cmd in
  (* nosemgrep: use-caps *)
  Unix.execve cmd argv env
let system (caps : < Cap.fork; Cap.exec; Cap.wait; ..>) cmd =
  let _ = caps#fork in
  let _ = caps#exec cmd in
  let _ = caps#wait in
  (* nosemgrep: use-caps *)
  Unix.system cmd
let fork (caps : < Cap.fork; ..>) =
  let _ = caps#fork in
  (* nosemgrep: use-caps *)
  Unix.fork
let wait (caps : < Cap.wait; ..>) = 
  let _ = caps#wait in
  (* nosemgrep: use-caps *)
  Unix.wait
let waitpid (caps : < Cap.wait; ..>) = 
  let _ = caps#wait in
  (* nosemgrep: use-caps *)
  Unix.waitpid
let kill (caps : < Cap.kill; ..>) = 
  let _ = caps#kill in
  (* nosemgrep: use-caps *)
  Unix.kill
let environment (caps : < Cap.env; ..>) = 
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Unix.environment
let chdir (caps : < Cap.chdir; ..>) = 
  let _ = caps#chdir in
  (* nosemgrep: use-caps *)
  Unix.chdir
let unlink (caps : < Cap.open_out; ..>) file =
  let _ = caps#open_out file in
  (* nosemgrep: use-caps *)
  Unix.unlink

(*
let alarm _caps = Unix.alarm
let setitimer _caps = Unix.setitimer
*)

(* the clock: the time, read or waited for *)
let gettimeofday (caps : < Cap.clock; ..>) =
  let _ = caps#clock in
  (* nosemgrep: use-caps *)
  Unix.gettimeofday
let time (caps : < Cap.clock; ..>) =
  let _ = caps#clock in
  (* nosemgrep: use-caps *)
  Unix.time
let sleepf (caps : < Cap.clock; ..>) =
  let _ = caps#clock in
  (* nosemgrep: use-caps *)
  Unix.sleepf
let sleep (caps : < Cap.clock; ..>) =
  let _ = caps#clock in
  (* nosemgrep: use-caps *)
  Unix.sleep

(* pipes *)
let pipe (caps : < Cap.pipe; ..>) =
  let _ = caps#pipe in
  (* nosemgrep: use-caps *)
  Unix.pipe
let socketpair (caps : < Cap.pipe; ..>) =
  let _ = caps#pipe in
  (* nosemgrep: use-caps *)
  Unix.socketpair

(* what the process is told about where it runs, as its environment *)
let getpid (caps : < Cap.env; ..>) =
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Unix.getpid
let getppid (caps : < Cap.env; ..>) =
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Unix.getppid
let getcwd (caps : < Cap.env; ..>) =
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Unix.getcwd
let gethostname (caps : < Cap.env; ..>) =
  let _ = caps#env in
  (* nosemgrep: use-caps *)
  Unix.gethostname
