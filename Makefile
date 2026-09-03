
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

# Release a new version to opam, via dune-release (opam install dune-release).
# This tags the current commit, pushes it, creates a GitHub release with the
# generated tarball, and opens a PR against opam-repository. Bump the version
# in dune-project (and add an entry to CHANGES.md) before running this.
opam-release:
	dune-release lint
	dune-release tag
	dune-release distrib
	dune-release publish
	dune-release opam pkg
	dune-release opam submit

release: opam-release
