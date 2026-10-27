# Fine adaptive range profile and divisor qualification

This research note records profiling and controlled candidate screens against the exact `v0.3.0` release. The implementation remains unchanged: divisor 8 is still the release baseline, and divisor 4 did not qualify as a replacement. XPS call-graph captures and ARM64 end-to-end timing/counter data now exist. The ARM64 hosted VM cannot sample call graphs, so issue #49's cross-architecture profile and separated cost breakdown remain incomplete.

## Profile method and findings

### Checksum-verified XPS profiles

The current XPS captures supersede the earlier reports marked `-superseded` below. The LDC release binaries use the exact `v0.3.0` source, four workers, 1024 items, eight waves, grain 1, and 5000 independent executor runs per mode. Each run checked its full checksum against serial work and the aggregate checksum. `perf record -F 997 -e cycles:u --call-graph dwarf,8192` reported zero lost samples. The short callback performs 16 LCG steps per item; the heavy callback performs 1024.

For short callbacks, `RangeWorker.opCall` accounts for 61.97% of adaptive samples and 81.73% of fixed-grain samples; the callback lambda accounts for 8.06% and 2.44%. For heavy callbacks, the callback lambda accounts for 91.61% of adaptive and 77.48% of fixed samples, while `RangeWorker.opCall` accounts for 4.25% and 17.69%. These are sampled CPU-cycle shares, not wall-clock ratios. They suggest callback work dominates the heavy case and executor range-worker work is prominent for the short case. `opCall` combines range processing and callback invocation, so it does not isolate the atomic claim operation. The process-level captures also do not separate dispatch, blocked join/drain time, executor construction, or shutdown. No optimization decision follows from these profiles alone.

Reports: [`xps-adaptive-short-checksum-verified.txt`](reports/xps-adaptive-short-checksum-verified.txt), [`xps-fixed-short-checksum-verified.txt`](reports/xps-fixed-short-checksum-verified.txt), [`xps-adaptive-heavy-checksum-verified.txt`](reports/xps-adaptive-heavy-checksum-verified.txt), and [`xps-fixed-heavy-checksum-verified.txt`](reports/xps-fixed-heavy-checksum-verified.txt). Raw perf data files remain local because they are large; the reports preserve the sampled call stacks and zero-lost-sample headers.

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

## Native ARM64 comparison

A GitHub-hosted `ubuntu-24.04-arm` runner completed four checksum-validated sessions on an ARM Neoverse-N2 (4 cores, no SMT), using LDC 1.41.0. The exact v0.3.0 library source was paired with the same benchmark harness; temporary divisor-4 and divisor-16 trees changed only the guided divisor constant. Each session covered six workload shapes, 1/4 workers, grain 1/64, five warmups and 20 measured samples. The benchmark's fixed arm is the within-process control. All 11,520 measured records completed and fixed/adaptive checksums matched.

Raw captures and runner metadata are in [`results/arm64/`](results/arm64/); [`analyze_arm64_divisor_qualification.py`](analyze_arm64_divisor_qualification.py) reproduces the per-session and pooled p50/p95/p99 summary. The ratio is `(candidate adaptive / candidate fixed) / (divisor-8 adaptive / divisor-8 fixed)`; values below one favor the candidate.

Divisor 4's short-uniform, four-worker, grain-1 median ratio was 0.917 pooled, with session medians 0.953, 0.881, 0.960 and 0.859. That is a consistent short-task signal on this runner. Across the other settings, results were mostly near parity or mixed; heavy-suffix, four-worker, grain-1 regressed 8.2% at the pooled median, while its upper percentiles were noisier. Divisor 16 regressed short-uniform four-worker grain-1 by 11.1% and medium-uniform by 16.7% at pooled medians, so it is rejected. Divisor 4 is not selected as the default: its benefit is workload-specific, the XPS data were less consistent, and tail results do not show a broad win.

This is a native ARM64 end-to-end timing capture, not a hardware-counter call-graph profile. The hosted runner exposes its CPU model and architecture but does not provide controlled thermals or an identical environment across runs. PR #51 adds checked short/heavy adaptive/fixed workloads and attempts `perf record`; the runner reports that the PMU does not support sampling/overflow interrupts, including after setting `perf_event_paranoid=0` on the ephemeral VM. A software-counter fallback successfully records one process run per mode: task-clock, context switches, migrations, and page faults. Checksums matched in all four runs. These single-run counters are exploratory only and cannot be substituted for sampled profiles or paired statistical evidence. The capture artifact is [`fine-adaptive-arm64`](https://github.com/alex-1974/concurrency-d/actions/runs/40539907150).

Issue #49's required cross-architecture breakdown of claim/dispatch/callback/join costs remains outstanding. The next useful step is to add explicit benchmark phase instrumentation (with the same pinned baseline and paired protocol) for components that sampling cannot distinguish, then obtain ARM64 call-stack samples on a host that exposes PMU sampling. Keep v0.4.0 TBD until that evidence and the remaining correctness/performance gates pass.

## Cross-architecture phase diagnostic

PR #52 added a checksum-validated diagnostic against the exact `v0.3.0`
commit `b4580d61cddadeeca3b99420a1aae2857b9de62e`. Both XPS and native
Neoverse-N2 ARM64 captures completed four sessions with 20 measured samples
and five warmups. Each dataset contains 1,800 rows. The diagnostic checks
fixed/adaptive range coverage exactly once before timing, then compares serial,
fixed grain-1 and adaptive grain-1 work for no-op, 16-step and 1024-step
callbacks. It also measures `TaskScope` submission-body and post-body intervals
for 4, 16 and 64 tasks. The post-body interval includes join/drain and cleanup;
it does not isolate a pure join primitive.

The primary diagnostic ratio is paired adaptive/fixed elapsed time; values
below one mean the existing adaptive path is faster than fixed grain 1. The
pooled p50/p95/p99 ratios were:

| Platform | No-op callback | Short callback | Heavy callback |
|---|---:|---:|---:|
| XPS, LDC 1.42 | 0.765 / 0.860 / 0.934 | 0.774 / 1.053 / 1.664 | 0.883 / 1.098 / 2.438 |
| Neoverse-N2, LDC 1.41 | 0.631 / 0.657 / 0.755 | 0.653 / 0.688 / 0.705 | 0.888 / 0.940 / 0.956 |

The current adaptive policy therefore has a repeatable median advantage over
fixed grain 1 for these fine no-op/short workloads on both platforms; heavy
work is near 11% faster at the median. This compares existing scheduling
policies and does not measure an optimization against the release baseline.
XPS tail ratios vary sharply between captures (the final short/heavy p99 values
are 1.664 and 2.438), despite stable directions in session medians. Treat these
upper-tail ratios as host-noise-sensitive and do not use them to justify a
scheduler change. The TaskScope samples indicate post-body medians around
10–24 microseconds for no-op batches of 4–64 tasks on XPS and 13–24 microseconds
on ARM64, but task execution overlaps submission, and these values do not
decompose `parallelFor`'s internal join.

Raw CSV, summary percentiles and host metadata are in
[`results/phase_diagnostic/`](results/phase_diagnostic/). The ARM64 capture is
also available as the [workflow artifact run](https://github.com/alex-1974/concurrency-d/actions/runs/40544424436).
The ARM64 PMU still refuses call-graph sampling; `perf` software counters are
available but cannot identify claim/dispatch/callback stacks. Consequently,
issue #49 remains open and no production scheduler change is selected.

## Adaptive minimum-grain screen

PR #53 expanded the native ARM64 matrix to grains 1, 4, 16 and 64 and
alternated grain order across sessions. An equivalent four-session XPS screen
used the same exact-tag library source, LDC 1.42, four workers, six workload
shapes, 20 measured samples and five warmups. Every fixed/adaptive pair had a
matching checksum. The [raw XPS capture](results/grain_screen/xps/raw.csv),
[ARM64 divisor-8 sessions](results/grain_screen/arm64/) and the
[reproducible ratio analyzer](analyze_grain_screen.py) are retained with
metadata and p50/p95/p99 summaries.

Ratios below one mean adaptive execution at the candidate minimum grain was
faster than adaptive grain 1 for the same session/sample. The short-uniform,
four-worker p50 ratios were 0.861/0.990 for grain 4, 0.844/0.879 for grain 16,
and 0.747/0.822 for grain 64 (XPS/ARM64). Grain 64 clears the 15% median gate
on both platforms; grain 16 misses it on ARM64. Grain 64 also has repeatable
upper-tail regressions: heavy-suffix p95 ratios were 1.375 on XPS and 1.120 on
ARM64, while long-uniform p95 ratios were 1.122 and 1.230. Its heavy-suffix
median regressed about 4% on both platforms. These results fail the control
guardrails, so grain 64 is not a general default recommendation. For known,
uniform short callbacks, grain 64 is a useful setting to test against the
consumer's own complete workload; do not assume it helps irregular or
long-running work. Grain 1 remains the baseline default.
