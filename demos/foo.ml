(* Demo for the "A Capability Type System for OCaml" talk (OCaml
 * Workshop 2026, slides in docs/ocaml2026/slides/caps.slp).
 *
 * restart() needs exactly the capabilities its type says and nothing
 * else: fork a child that "execs" a new version of the program, while
 * the parent waits for it. The OCaml typechecker checks (and infers)
 * this for us, for free.
 *)

let restart (caps : < Cap.fork; Cap.wait; Cap.exit; .. >) () =
  match CapUnix.fork caps () with
  | 0 ->
      print_endline "[child] pretending to exec a new version...";
      CapStdlib.exit caps 0
  | _pid -> (
      let _, status = CapUnix.wait caps () in
      match status with
      | Unix.WEXITED n -> Printf.printf "[parent] child exited with code %d\n%!" n
      | Unix.WSIGNALED n ->
          Printf.printf "[parent] child was killed by signal %d\n%!" n
      | Unix.WSTOPPED n ->
          Printf.printf "[parent] child was stopped by signal %d\n%!" n)

(* The only door in: Cap.main hands the entry point *every* capability;
 * the entry point then downcasts (:>) to give restart() only the
 * subset it actually needs. *)
let () =
  Cap.main (fun (caps : Cap.all_caps) ->
      restart (caps :> < Cap.fork; Cap.wait; Cap.exit; .. >) ())
