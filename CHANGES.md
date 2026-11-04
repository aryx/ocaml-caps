## 0.1.1 (unreleased)

- `Cap.clock` (in `misc`, beside `random`): the time, read or waited for;
  `CapUnix.gettimeofday`, `time`, `sleepf`, `sleep`, `CapSys.time`.
- `Cap.pipe` (in `process_multi`): `CapUnix.pipe`, `socketpair`.
- `CapUnix.getpid`, `getppid`, `getcwd`, `gethostname` and `CapSys.getcwd`,
  under `Cap.env`.
- The Semgrep rules forbid the bare calls (`forbid-clock`, `forbid-process`).

## 0.1.0 (2026-09-03)

- Initial public release: `Cap.ml` capability types and `CapSys`/`CapUnix`/`CapStdlib`
  wrappers, plus the Semgrep capability rules used to enforce their use.
