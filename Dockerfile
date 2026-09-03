# Build and test ocaml-caps with OCaml 4.14.2 via OPAM on Ubuntu Linux.
# See also .github/workflows/docker.yml for its use in Github Actions (GHA).

FROM ubuntu:22.04

# Setup a basic C dev environment
RUN apt-get update # needed otherwise can't find any package
RUN apt-get install -y build-essential autoconf automake pkgconf

# Setup OPAM and OCaml
RUN apt-get install -y opam
# Initialize opam (disable sandboxing due to Docker)
RUN opam init --disable-sandboxing -y
ARG OCAML_VERSION=4.14.2
RUN opam switch create ${OCAML_VERSION} -v

WORKDIR /src

# Install dependencies
COPY caps.opam ./
RUN opam install --deps-only -y ./caps.opam

# Now let's build from source
COPY . .

# Build
RUN eval $(opam env) && dune build

# Test
RUN eval $(opam env) && dune runtest
