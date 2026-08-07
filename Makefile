
default:
	dune build
clean:
	dune clean
test:
	dune runtest
install:
	dune install

setup:
	opam install --confirm-level=unsafe-yes --deps-only .
