# ocaml-caps

## Overview

`Cap.ml` is a small library providing *capability types* to
use in a disciplined manner the UNIX system calls behind
standard library functions such as `Sys.command`, `Unix.fork`,
or even `Stdlib.open_in`.
When combined with the use of the Semgrep tool and
*capability rules*, it can offer stronger guarantees on a codebase.

## Documentation

See https://aryx.github.io/ocaml-caps/ for more information.
My OCaml workshop 2026 presentation is also available here:
https://www.youtube.com/watch?v=4t_2wLz9EOo
and the slides here:
https://aryx.github.io/ocaml-caps/caps.html 


You might find also useful the related https://github.com/aryx/ocaml-commons
project that provides a few additional modules using capabilities.

Here are a few projects currently using `Cap.ml`:
- https://github.com/aryx/osemgrep
- https://github.com/aryx/efuns
- https://github.com/aryx/mmm
- https://github.com/aryx/xix
which you can use as examples to follow. Start from their `Main.ml`
file and follow down how capabilities are passed and required.

## History

The library was developed in 2024 while I was working at Semgrep
but got extracted in its own repository in August 2026
(mostly as support for my OCaml workshop 2026 presentation).

## AI disclaimer

The OCaml code in this library was written by a human (me, Pad).
The code is actually very small. The Semgrep rules were also
written by me.

The `scripts/` were written by Claude Code to compute usage
statistics of capability types in OCaml projects.
The Dockerfile, GHA workflows, and a few other configuration
files were written by Claude Code, but mostly derived from
my other projects (and written by me).
