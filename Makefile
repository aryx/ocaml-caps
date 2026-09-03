
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

# Release a new version to opam. Bump the version in dune-project (and add
# an entry to CHANGES.md) before running this.
#
# We use dune-release (opam install dune-release) for tag/distrib/publish:
# it tags the commit, pushes the tag, builds the source tarball, and creates
# a GitHub release with that tarball attached.
#
# For the last step, submitting to opam-repository, we use opam-publish
# (opam install opam-publish) instead of `dune-release opam submit`.
# dune-release's opam submit (as of dune-release.2.2.0) does NOT fork
# ocaml/opam-repository for you: it requires a fork you already created on
# GitHub, cloned locally, and configured in ~/.config/dune/release.yml
# (this is what "expecting a writable opam-repository fork" means if you
# haven't set that up). opam-publish instead forks ocaml/opam-repository
# under your account itself, builds the opam package from the GitHub
# release we just published, shows you the diff to confirm, and opens the
# PR -- no pre-existing fork or local clone needed.
opam-release:
	dune-release lint
	dune-release tag
	dune-release distrib
	dune-release publish
	opam-publish aryx/ocaml-caps

release: opam-release
