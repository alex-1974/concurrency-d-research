# concurrency-d-research

Research, experiments, prototypes, raw measurements and historical design evidence
for [concurrency-d](https://github.com/alex-1974/concurrency-d).

The library does not depend on this repository. Production source, active
regression/release gates, maintained qualification benchmarks, user documentation
and concise decisions remain in concurrency-d. Experimental schedulers, compiler
probes and detailed evidence belong here. Research results require review before
becoming public contracts; conditional notification remains unpromoted.

## Preserved evidence

The working corpus combines R0 scheduler/task research, M1 lifetime research
through P42.20, and the current public M0 candidate evidence. See
[PROVENANCE.md](PROVENANCE.md) for exact sources. Every research-bearing remote
branch tip at migration time also has an immutable, path-preserving snapshot
under `snapshots/COMMIT/`; conflicting historical versions are preserved there.
`SOURCE_REFS.json` maps branch names to pinned commits. `SNAPSHOT_MANIFEST.json`
records every imported file, mode, size, Git blob and SHA-256.

The corpus root combines evidence from different source commits and is not a
single runnable library tree. For reproduction, prepare the exact original
library checkout and use the scripts associated with that snapshot:

```sh
python3 tools/verify_snapshot.py
python3 tools/prepare_workspace.py COMMIT /absolute/path/to/new-workspace
```

Preparation checks out the original library commit and verifies its imported
research files against the manifest. It does not run benchmarks or claim that
historical measurements have been repeated. Compiler, hardware and workload
requirements remain in the original experiment descriptions. Detailed evidence
may refer to the original library history; migration does not rewrite that history.

## Development acknowledgement

Assisted by AI.

The library has been developed and reviewed with assistance from multiple AI
systems and models. API compatibility, source correctness and release decisions
remain subject to maintainer review and the repository's verification gates.

## License

MIT, see [LICENSE](LICENSE). Original third-party notices remain applicable.
