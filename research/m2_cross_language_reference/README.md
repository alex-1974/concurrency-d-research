# Cross-language end-to-end reference capture

This diagnostic addresses the C++/Rust reference part of concurrency-d issue
#25. It compares checksum-identical fine, medium, coarse and deterministic
irregular CPU work across D `parallelFor`/Phobos, Taskflow, oneTBB and Rayon.
It is not a universal scheduler ranking: the libraries expose different
partitioning policies, and this is one XPS host.

## Capture protocol

- Host: Dell XPS 15, Intel Core i7-9750H, 6 cores / 12 hardware threads.
- OS: Ubuntu x86_64, Linux 6.17.0-22-generic; platform profile `cool`.
- Work budget: 4 participants in each runtime; D, Taskflow and Rayon each
  include four workers/threads. oneTBB uses a four-slot task arena; its caller
  may participate according to oneTBB semantics.
- Workloads: the exact four workloads and wrapping 64-bit arithmetic kernel
  in `benchmarks/end-to-end/main.d` and the cross-language adapters.
- Granularity sweep: 1, 4, 8, 16, 32, 64, 128, 256 and 512.
- Four independent process sessions, seven measured samples and two warmups
  per arm/grain/session. Framework order rotates between sessions to distribute
  frequency and thermal drift. All adapters verify the checksum and all runs
  exited successfully.
- Work per item: base 512 iterations; medium scales by 8, coarse by 64, and
  irregular by 4 plus the deterministic per-index variation.
- D: LDC 1.42.0, DMD frontend 2.112.1, LLVM 19.1.7, release build.
- C++: GCC 15.3.0, C++20, `-O3 -DNDEBUG`.
- Taskflow: v4.1.0, commit
  `45366fe5bc4f2f8ec9aa590b40c504e296886865`.
- oneTBB: 2023.1.0, commit
  `3046c8b0c29df995980003ea24f4d78c80ec0c8d`.
- Rust: rustc 1.97.0, Cargo release profile, Rayon 1.12.0 and the checked-in
  Cargo lockfile.

The single-wave capture constructs and shuts down a new runtime in each sample
for D, Taskflow and Rayon. oneTBB's process-wide scheduler is initialized by
the executable's warmup samples and cannot be torn down between samples, so its
global startup is excluded; per-sample arena setup remains timed. The eight-wave
capture reuses the D executor and the matching library runtime/output storage
for eight work waves, includes runtime creation and shutdown once, and reports
the total eight-wave checksum and item count. The D benchmark's reused arms use
the same eight-wave pattern.

## Eight-wave reused-runtime result

The values below are pooled medians and nearest-rank p95 from the 28 measured
samples at the grain selected by the lowest pooled median for that arm and
workload. Values are total elapsed microseconds for all eight waves. Grain
policies are library-specific; best-grain selection is an observed tuning
result, not a portable recommendation.

| Workload | D `parallelFor` | Phobos | Taskflow | oneTBB | Rayon |
|---|---:|---:|---:|---:|---:|
| Fine | 478.9 / 537.5 (64) | 415.1 / 496.4 (64) | 1,940.4 / 2,067.4 (4) | 1,507.6 / 1,524.8 (256) | 388.0 / 455.6 (32) |
| Medium | 776.7 / 1,507.1 (8) | 686.4 / 737.3 (32) | 3,717.6 / 3,845.7 (4) | 3,075.8 / 3,351.3 (8) | 680.1 / 741.5 (16) |
| Coarse | 791.9 / 871.3 (1) | 696.0 / 779.9 (4) | 3,824.8 / 3,910.8 (8) | 3,073.0 / 3,286.9 (4) | 684.0 / 723.0 (4) |
| Irregular | 624.6 / 749.7 (8) | 560.0 / 630.9 (8) | 2,889.3 / 3,014.4 (4) | 2,339.2 / 2,458.3 (64) | 553.6 / 593.0 (32) |

Each cell gives `p50 / p95 (grain)`. The XPS capture does not show the D
executor beating Phobos or Rayon on these selected workloads. Its reused
`parallelFor` medians are about 11–15% above Phobos in the selected arms;
Rayon is around 1–7% below Phobos. Taskflow and oneTBB are materially slower
with these adapters and this compiler/host. These results are evidence against
a blanket performance-superiority claim. They do not negate the library's
consumer-controlled executor, typed task results, bounded admission, shutdown
and task-handoff contract; they do show that range-scheduling overhead remains
a worthwhile optimization target.

The medium-workload p95 for D includes a large outlier (1.51 ms) despite a
0.78 ms median. That tail is visible in the raw data and should not be hidden
by the median. Further repetitions and the native ARM64/LDC capture are still
required before closing issue #25.

## Single-wave result

The matching single-wave capture is retained for startup-sensitive consumers.
It includes per-sample executor/pool startup and shutdown for D, Taskflow and
Rayon. oneTBB's process-global initialization caveat above still applies.
Inspect the raw CSVs rather than merging these timings with the eight-wave
data; the measured work and runtime lifetime differ.

## Raw data

- [Single-wave raw CSVs and metadata](results/single-wave/)
- [Eight-wave reused raw CSVs and metadata](results/eight-wave-reuse/)
- Exact source snapshot and SHA-256 manifest are in [`sources/`](sources/).
  The maintained adapters are also in the `concurrency-d` repository under
  `benchmarks/cross-language/`.

The table is reproducible with:

```sh
python3 research/m2_cross_language_reference/summarize.py \
  research/m2_cross_language_reference/results/eight-wave-reuse
```

## Decision implication

Keep `parallelFor` as a small indexed CPU convenience, with caller-provided
fixed grain and an opt-in adaptive version. Document that users should retain
the executor for repeated work and tune against their own task sizes. Do not
add a claim that this API outperforms Phobos or general-purpose C++/Rust
libraries. The benchmark evidence supports continued optimization and clear
tradeoff documentation, not a universal winner statement.
