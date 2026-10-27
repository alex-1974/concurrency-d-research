# Fine adaptive range profile and divisor qualification

This research note records profiling and a controlled candidate screen against the exact `v0.3.0` release. The implementation remains unchanged: divisor 8 is still the release baseline, and divisor 4 did not qualify as a replacement. This is XPS-only evidence; issue #49's native ARM64 profile and remaining release gates are still outstanding.

## Profile method and findings

- Release tree: `b4580d61cddadeeca3b99420a1aae2857b9de62e` (`v0.3.0`).
- CPU: Intel Core i7-9750H, 6 cores / 12 threads; kernel `6.17.0-22-generic`.
- Compiler: LDC 1.42.0, LLVM 19.1.7; flags `-O3 -g -release`.
- `perf record -F 997 -e cycles:u --call-graph dwarf,8192`; recordings reported zero lost samples.
- Four-worker Executor reused for eight waves per invocation; each wave applies 1024 indexed callbacks at minimum/fixed grain 1. Callback bodies run 1024 LCG steps (heavy) or 16 (short).
- `parallelForAdaptive` was profiled against `parallelFor` at grain 1, both from the exact release source.

The first profiling harness XORed an even number of identical checksums, so its printed zero did not validate results. The retained profile captures are therefore diagnostic only and marked `-superseded`. A corrected harness was separately run against the exact same release code path and verified each invocation against a serial checksum; exact-once counters also passed for baseline and temporary divisor variants. The profiles show where CPU cycles went, but are not paired timings or checksum-bearing runs.

| Callback work | Adaptive samples | Fixed-grain samples | Observation |
|---|---:|---:|---|
| 1024 LCG steps | `RangeWorker.opCall` 4.25%; callback lambda 91.61% | `RangeWorker.opCall` 17.69%; callback lambda 77.48% | Callback work dominates. |
| 16 LCG steps | `RangeWorker.opCall` 61.97%; callback lambda 8.06% | `RangeWorker.opCall` 81.73%; callback lambda 2.44% | Range claiming is the largest sampled CPU cost for very short callbacks. |

In the short-callback adaptive profile, mutex, spin-lock and condition-wait symbols each account for about 1–2% or less. `cycles:u` excludes sleeping and kernel scheduling time, so the profile says nothing about off-CPU join latency. The claim loop is a plausible optimization target, but profiling alone does not demonstrate an end-to-end gain.

Harnesses: [`profile_heavy_callback.d`](profile_heavy_callback.d) and [`profile_short_callback.d`](profile_short_callback.d). Retained old reports are in [`reports/`](reports/) and marked superseded. Raw `perf.data` files were not retained in the repository.

## Divisor 4 versus divisor 8

A full qualification screen compared exact `v0.3.0` baseline divisor 8 with a temporary divisor-4 build. Only the guided divisor constant differed. The official `benchmarks/adaptive-ranges` harness ran six workload shapes (`short_uniform`, `medium_uniform`, `long_uniform`, `scattered_hotspots`, `heavy_prefix`, `heavy_suffix`), 1 and 4 workers, grain 1 and 64, five warmups and 20 measured samples per setting, across four sessions. Fixed and adaptive arms were paired; binary order alternated. Every result was checked against its expected checksum, and baseline/candidate checksums matched. The harness/runner monitored CPU throttling, fan readings and package temperature; no throttling was observed and the maximum recorded package temperature stayed below 90°C.

Raw files and environment metadata are under [`results/`](results/). The analysis script validates the checksums and pairs runs, then calculates the difference-in-differences ratio `(candidate adaptive / candidate fixed) / (baseline adaptive / baseline fixed)`. Values below 1 favor divisor 4. Session percentiles and pooled percentiles are in [`divisor4-vs-divisor8-summary.csv`](results/divisor4-vs-divisor8-summary.csv).

The pooled median ratio was 0.911 for short uniform, 4 workers, grain 1 (about 8.9% lower) and 0.886 for medium uniform at the same setting (about 11.4% lower). Those apparent gains were not consistent across sessions: short uniform's session medians ranged from 0.871 to 0.984; medium uniform included one session at 1.021. Long uniform stayed near parity, and coarse-grain and irregular-cost settings were mixed. Tail ratios were often highly variable. The screen therefore does not establish a repeatable broad improvement and does not justify changing the default policy.

The earlier four-pair exploratory screen is retained in [`divisor4-vs-divisor8-screen.csv`](divisor4-vs-divisor8-screen.csv), with its limits described in the companion note. Divisor 16 is excluded because its initial timing screen lacked checksum enforcement.

## Decision and next evidence

No library source or public API changed. Keep divisor 8 and `v0.3.0` as the baseline; do not cut a performance-driven release from this experiment. Next, investigate a more targeted claim-path optimization, then require fresh correctness and end-to-end qualification on XPS plus a native ARM64 profile/benchmark before selecting a candidate. Issue #49 remains open, and v0.4.0 remains TBD until its gates pass.
