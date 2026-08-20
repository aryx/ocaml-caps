# ocaml-caps

`Cap.ml` is a small library providing *capability types* to
use in a disciplined manner the UNIX system calls behind
standard library functions such as `Sys.command`, `Unix.fork`,
or even `Stdlib.open_in`.
When combined with the use of the Semgrep tool and
*capability rules*, it can offer stronger guarantees on a codebase.

See https://aryx.github.io/ocaml-caps/caps.html for more information
as well as https://aryx.github.io/ocaml-caps/
