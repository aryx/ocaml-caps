
default:
	dune build
clean:
	dune clean
test:
	dune runtest
install:
	dune install

demo:
	dune exec demos/foo.exe

setup:
	opam install --confirm-level=unsafe-yes --deps-only .
