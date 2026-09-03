
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

# This will fail if caps.opam isn't up-to-date (in git),
# and dune isn't installed yet. You can always install dune with
# 'opam install dune' to get started.
caps.opam: dune-project
	dune build $@

build-docker:
	docker build -t "caps" .
build-docker-ocaml5:
	docker build -t "caps" --build-arg OCAML_VERSION=5.2.1 .
