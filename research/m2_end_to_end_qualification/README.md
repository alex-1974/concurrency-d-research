# M2 end-to-end benchmark capture

For the pinned Taskflow, oneTBB and Rayon references, see the separate
[cross-language end-to-end capture](../m2_cross_language_reference/README.md).

This is one local diagnostic capture for issue #25, not release-wide evidence.
It compares identical deterministic fine, medium, coarse and irregular chunk
work through sequential D, Phobos `TaskPool.parallel`, per-batch
`Executor.submit`, public `Executor.parallelFor`, and a benchmark-only dynamic
worker loop. Every arm validates a matching checksum. The benchmark includes
executor/pool startup, result collection and shutdown.

## Capture

- Machine: Dell XPS 15, Intel Core i7-9750H (6 cores / 12 threads)
- OS: Ubuntu, Linux 6.17.0-22-generic x86_64
- Compiler: LDC 1.42.0, DMD frontend 2.112.1, LLVM 19.1.7
- Power profile observed before run: `cool`
- Command: `dub build --root=benchmarks/end-to-end --build=release --compiler=ldc2`, then
  `./benchmarks/end-to-end/concurrency-end-to-end-benchmark 4 20 5 1024`
- Capture: four independent process runs, each with 20 measured samples per
  arm and 5 warmups; max 4 workers, base work 1024
- Combined raw output with a `session` column:
  [`results/xps_ldc142_4sessions_80pairs.csv`](results/xps_ldc142_4sessions_80pairs.csv)
- The first process output is also retained separately at
  [`results/xps_ldc142_4workers_20samples.csv`](results/xps_ldc142_4workers_20samples.csv)
- Post-optimization capture (same four-process protocol):
  [`results/xps_ldc142_caller_participates_4sessions_80pairs.csv`](results/xps_ldc142_caller_participates_4sessions_80pairs.csv)
- Short-task capture (`baseIterations=64`, same protocol):
  [`results/xps_ldc142_caller_participates_short64_4sessions_80pairs.csv`](results/xps_ldc142_caller_participates_short64_4sessions_80pairs.csv)
- Reused-pool capture (eight work waves per timed arm):
  [`results/xps_ldc142_reused_8waves_4sessions_80pairs.csv`](results/xps_ldc142_reused_8waves_4sessions_80pairs.csv)
- Expanded grain sweep before the direct-claim experiment:
  [`results/xps_ldc142_grain_sweep_before_directclaim_4sessions_48pairs.csv`](results/xps_ldc142_grain_sweep_before_directclaim_4sessions_48pairs.csv)
- Longer grain confirmation on the restored caller-participation path:
  [`results/xps_ldc142_grain_confirm_4sessions_80pairs.csv`](results/xps_ldc142_grain_confirm_4sessions_80pairs.csv)
- Direct-first-range experiment:
  [`results/xps_ldc142_first_range_candidate_4sessions_48pairs.csv`](results/xps_ldc142_first_range_candidate_4sessions_48pairs.csv)
- Single-worker inline fast-path capture:
  [`results/xps_ldc142_single_worker_inline_4sessions_80pairs.csv`](results/xps_ldc142_single_worker_inline_4sessions_80pairs.csv)
- Caller-plus-workers manual control with the same post-dispatch join fence:
  [`results/xps_ldc142_scope_control_4sessions_80pairs.csv`](results/xps_ldc142_scope_control_4sessions_80pairs.csv)

## Result

Pooled paired median `parallelFor`/Phobos elapsed-time ratios at four workers,
selecting the best logical batch size from 1, 4, 16, 64 and 256 for each
workload:

| Workload | Batch | `parallelFor` / Phobos p50 | Interpretation |
|---|---:|---:|---|
| Fine | 256 | 1.203 | `parallelFor` median was 20.3% slower |
| Medium | 256 | 1.076 | 7.6% slower |
| Coarse | 256 | 1.087 | 8.7% slower |
| Irregular | 256 | 1.114 | 11.4% slower |

Ratios are paired per sample; below 1.0 favors `parallelFor`. These are the
best observed batch choices within this sweep, not a universal tuning rule.
All four per-session medians at each selected batch were above 1.0, so the
observed disadvantage was consistent across process runs. Fine work remains
the clearest gap; increasing the grain to 256 narrowed the measured difference
but did not eliminate it. At the selected batch, pooled p95 ratios were 1.49
(fine), 1.27 (medium), 1.24 (coarse) and 1.50 (irregular). This supports
continued tuning of per-index scheduling overhead and tail behavior; it does
not support a claim that concurrency-d is faster than Phobos.

The initial 20-sample note used the summarizer's `concurrency`/Phobos ratio,
which represents per-batch `Executor.submit`, while labeling it as
`parallelFor`. That was an analysis error. The summarizer now reports paired
ratios separately for both executor arms; the table above uses the corrected
`parallelFor` measurements across all four sessions.

## Caller-participation experiment

The original helper scheduled one scoped task per executor worker. The revised
implementation runs one range worker on the calling thread and schedules only
`workerCount - 1` scoped tasks, matching the caller-participates pattern used
by Phobos while preserving the same dynamic range claims. DMD and LDC public
API checks passed, including callback-failure draining and executor reuse.
Four additional independent LDC processes used the same workload and command.

| Workload | Best batch | Before p50 ratio | After p50 ratio | After p95 ratio |
|---|---:|---:|---:|---:|
| Fine | 16 | 1.203 (batch 256) | 1.171 | 1.475 |
| Medium | 256 | 1.076 | 1.026 | 1.218 |
| Coarse | 256 | 1.087 | 1.049 | 1.214 |
| Irregular | 256 | 1.114 | 1.100 | 1.386 |

The caller-participation change improved the best observed median in every
workload; medium and coarse work moved within about 3–5% of Phobos. Fine work
is still about 17% slower, and the irregular tail remains noisy. Batch 16 was
best for fine work after the change; other selected batches remained 256.
This is a promising local optimization, not yet a release claim. The next
measurement should repeat after a clean rebuild and include a smaller base
iteration sweep to isolate scheduler overhead from kernel cost.

The shorter-task sweep (`baseIterations=64`) still favors Phobos at four
workers. Best observed paired medians were 1.260 (fine, batch 1), 1.243
(medium, batch 64), 1.236 (coarse, batch 256) and 1.312 (irregular, batch 64),
with 80 pairs each. `parallelFor` remained faster than fixed-batch `submit` at
those selected settings, but its margin to Phobos widened. Because each timed
arm constructs and shuts down its executor/pool, this one-shot workload may
weight startup more heavily than a consumer that reuses an executor. This
prompted the paired pool-reuse experiment below.

## Pool reuse experiment

The benchmark now has paired arms that keep one `TaskPool` or `Executor` alive
across eight identical work waves. Construction, all eight waves and final
shutdown are timed; reported chunk counts include all waves. Four independent
LDC processes produced 80 paired samples for each workload and batch size.

| Workload | Best batch | `parallelForReused` / `phobosReused` p50 | p95 |
|---|---:|---:|---:|
| Fine | 64 | 1.072 | 1.099 |
| Medium | 256 | 1.005 | 1.027 |
| Coarse | 64 | 1.003 | 1.032 |
| Irregular | 256 | 1.006 | 1.035 |

With pool reuse, median throughput is effectively at parity for medium, coarse
and irregular work. Fine work is about 7% slower at its best tested grain. This
indicates that one-shot startup is not the whole explanation for the earlier
gap and that fine-grain range overhead remains the clearest optimization
target. The persistent-pool capture makes the prior startup-heavy result easier
to interpret, while remaining specific to this XPS/LDC configuration.

## Fine-grain follow-up

An expanded sweep added grains 8, 32, 128 and 512 and used 48 paired samples
per combination across four processes. For fine work at four workers, grain
128 produced the best exploratory median ratio (1.038) against Phobos, but its
p95 was 1.368 and process-level medians varied. A prototype that reserved the
caller's first range before other workers claimed work did not demonstrate a
reliable improvement in a follow-up capture; that code was removed. The
caller-participation implementation remains, and the expanded grain choices
are now covered by the maintained benchmark. Treat grain 128 as a candidate to
test for uniform fine work, not a default recommendation.

A longer confirmation with 80 pairs per combination did not reproduce grain
128 as the fine-work winner. Grain 32 had the best median (1.110) but a p95 of
1.318 against Phobos at four workers; its four process-level medians were
between 1.098 and 1.192. Grain 128's median was 1.157. This rejects a fixed
grain recommendation from these runs and leaves per-call tuning dependent on
the workload and host.

The expanded sweep also exposed avoidable atomic claims when the executor has
only one worker. `parallelFor` now copies the callback once and directly loops
over all indices when its effective worker count is one. A four-process
confirmation used 20 samples per arm and the same 1, 2, 4, 8, 16, 32, 64, 128,
256 and 512 grain sweep. At one worker and grain 1, the fine-work
`parallelForReused`/Phobos median ratio moved from 1.141 to 1.059; p95 moved
from 1.204 to 1.130. Medium work at the same grain moved from 1.042 to 1.027.
The public API test now checks complete single-worker traversal, callback
exception propagation and executor reuse after failure. This is a targeted
optimization for the single-worker path; the multi-worker fine-work gap
remains.

## Scope-overhead control

The benchmark-only `dynamicForReused` arm now matches `parallelForReused` in
caller-plus-workers budget, dynamic range claims, per-index result writes,
eight-wave pool reuse, post-dispatch task-return waits and completed-record
reclamation. Its workers are submitted explicitly rather than through
`TaskScope`. Across 80 paired fine-work samples at four workers and grain 8,
the manual arm's median elapsed-time ratio was 0.976 versus public
`parallelForReused`; process-level medians ranged from 0.952 to 0.983. Both
remained slower than Phobos at that setting (1.093 and 1.124 median ratios,
respectively). This suggests the public scope wrapper accounts for only part
of the remaining difference; the result is too small and host-specific to
justify bypassing `TaskScope` in the API. No production scheduling change was
made from this control.

## Limits and next experiments

This is repeated process-level evidence on one machine under a `cool` profile.
It does not compare Taskflow, Rayon or oneTBB. A native ARM64/LDC capture is
now available below; both sets remain host-specific. Keep work sizes,
validation, worker budgets and lifecycle timing equivalent when changing the
harness.

## Native ARM64 / LDC capture

The PR workflow captured the same checksum-validated benchmark on a native
four-core ARM64 GitHub runner, using LDC 1.41.0 and four independent sessions
with seven measured samples and two warmups per arm/minimum-grain setting.
The host is an Azure Neoverse-N2 runner; the artifact records the exact
platform, compiler, revision and command. Each table cell below is the best
paired median ratio against the matching Phobos arm among tested minimum grain
sizes for four workers. `parallelForAdaptiveReused` uses guided claims with
the shown minimum grain. `n=28` paired samples per row; ratios below 1 favor
concurrency-d.

| Workload | One-shot `parallelFor` / Phobos, grain (p50 / p95) | Reused `parallelFor` / Phobos, grain (p50 / p95) | Reused adaptive / Phobos, min grain (p50 / p95) |
|---|---:|---:|---:|
| Fine | 1.051 / 1.415 (1) | 1.029 / 1.413 (1) | **0.771 / 1.124 (1)** |
| Medium | 1.057 / 1.119 (512) | 0.996 / 1.003 (512) | 0.995 / 0.998 (512) |
| Coarse | 1.051 / 1.078 (128) | 0.996 / 1.015 (32) | 0.996 / 1.002 (128) |
| Irregular | 1.059 / 1.094 (256) | 0.997 / 1.003 (256) | 0.995 / 1.001 (512) |

The fine adaptive median is about 23% below Phobos at minimum grain 1, while
its p95 remains about 12% higher, so the tail and process-level variability
matter. For the other three workloads, reused fixed and adaptive modes are
near Phobos parity. One-shot fixed `parallelFor` is about 5–6% slower by median.
This is useful evidence that consumer-selected minimum grain and guided claims
can help the fine workload; it is not a guarantee for other machines or cost
profiles, and it does not erase the noisy tail. Do not generalize from the
best grain selected after the sweep into an automatic default.

- [Raw CSV, metadata, reproducible summarizer and full summary](results/native-arm64-ldc141/)
- Workflow run: [#40484245846](https://github.com/alex-1974/concurrency-d/actions/runs/40484245846)
- Tested source commit: `9627d8595a06c5e3ad4500ccf06048cd72b7f581` (PR merge tree
  recorded separately in the capture metadata).

## Static initial-range experiment

A further prototype assigned one grain-sized range to each participant before
starting the dynamic claims, then used the shared atomic counter only for the
remaining ranges. This aimed to avoid simultaneous first claims. The code
passed the DMD and LDC test suites. Four independent LDC processes repeated
the standard 80-pair capture; raw rows are retained at
[`results/xps_ldc142_static_initial_ranges_4sessions_80pairs.csv`](results/xps_ldc142_static_initial_ranges_4sessions_80pairs.csv).

At four workers, pooled best-grain ratios changed from 1.116 to 1.105 for
fine work, from 1.006 to 1.009 for medium, from 1.004 to 1.005 for coarse,
and from 1.001 to 1.008 for irregular work. The fine-work p95 at grain 32
worsened from 1.222 to 1.535; other grains also showed mixed tail movement.
The small median changes did not reproduce consistently across workloads, so
the static initial assignment was removed. Only the established single-worker
fast path remains in production. This experiment does not support a general
multi-worker scheduling change.

## Adaptive claim-size experiment and opt-in API

Two benchmark-only adaptive strategies were compared before selecting an API
shape. Guided claims use a CAS reservation sized as the larger of the minimum
grain and half the remaining domain per participant; progressive claims start
at the minimum and double after each successful claim. Both preserve caller
participation, executor-worker budget, result writes, eight-wave reuse, and
post-dispatch waits. Their four-process captures are retained as
[`guided prototype`](results/xps_ldc142_guided_prototype_4sessions_80pairs.csv)
and [`progressive prototype`](results/xps_ldc142_progressive_prototype_4sessions_80pairs.csv).
The guided variant had lower medians than progressive on fine work and slightly
better tails, so guided claims were implemented as an opt-in public API.

`Executor.parallelForAdaptive(itemCount, minGrainSize, body)` defines the
argument as a lower bound: claims begin larger and shrink toward it. The
existing `parallelFor` contract remains unchanged, with `grainSize` as a strict
maximum claim size. The public path passed DMD and LDC tests, including exact
once-only index visits, zero-grain rejection, callback-error draining and
executor reuse. A final LDC 1.42 capture used four independent process runs,
20 measured pairs per configuration, 5 warmups, the Dell XPS 15 and the same
reused eight-wave workloads. Raw data is at
[`results/xps_ldc142_adaptive_public_4sessions_80pairs.csv`](results/xps_ldc142_adaptive_public_4sessions_80pairs.csv).

At four workers, best-grain pooled paired ratios against reused Phobos were:

| Workload | Adaptive minimum | Adaptive p50 | Adaptive p95 | Fixed `parallelFor` p50 |
|---|---:|---:|---:|---:|
| Fine, uniform | 1 | 1.005 | 1.177 | 1.115 |
| Medium, uniform | 256 | 1.008 | 1.031 | 1.009 |
| Coarse, uniform | 512 | 1.005 | 1.031 | 1.004 |
| Irregular | 512 | 1.008 | 1.033 | 1.008 |

The adaptive API closes most of the fine-work median gap on this host, with a
better p95 than fixed `parallelFor` at its best grain. Medium and irregular
work remain near parity; coarse work is slightly slower, within the observed
noise. This supports keeping it opt-in for large domains of cheap, roughly
uniform items, not changing the default scheduler. The result is local LDC
performance evidence, not a portable guarantee; cost variation can make larger
early claims leave a longer tail. The public docs explain the lower-bound
semantics and recommend measuring both APIs for the consumer workload.

## Relaxed ordering for the adaptive range counter

The adaptive CAS counter only allocates disjoint index intervals; it does not
publish callback state or result values. Those are published by task admission
and observed after the structured scope join. The implementation therefore
uses `MemoryOrder.raw` for adaptive counter loads and CAS operations. This is
still atomic and preserves unique claims, without ordering unrelated memory.
DMD and LDC tests passed after the change. A second four-process LDC capture
is retained at
[`results/xps_ldc142_adaptive_relaxed_claim_order_4sessions_80pairs.csv`](results/xps_ldc142_adaptive_relaxed_claim_order_4sessions_80pairs.csv).
At four workers, the best fine-work p50/p95 ratio versus reused Phobos changed
from 1.0045/1.1769 to 1.0004/1.1735. Medium and coarse p50s were effectively
unchanged; irregular p50 was also nearly unchanged, while its p95 varied more.
This is no material or consistent performance gain on this x86 host, but the
relaxed ordering directly matches the counter's coordination-only role.

## Adaptive scheduling across item costs and worker counts

A focused benchmark held 1,024 indexed items and eight reused-executor waves
constant while varying item cost: 16 iterations (short uniform), 256 (medium
uniform), 4,096 (long uniform), and 128 to 1,024 deterministic iterations
(high variation, up to 8x). It compared fixed `parallelFor` with
`parallelForAdaptive` at grains 1, 4, 16, 64, 256 and 512, using 1, 2 and 4
workers. Four independent LDC 1.42 process runs each had 20 measured samples
and 5 warmups per configuration; all arms checked the same checksum. The
observed platform was the XPS 15 / i7-9750H under `cool`, Ubuntu Linux
6.17.0-22-generic x86_64.

At a matched grain/minimum of 1, the pooled paired adaptive/fixed median ratios
were:

| Item cost | 1 worker | 2 workers | 4 workers |
|---|---:|---:|---:|
| Short uniform | 1.007 | 0.488 | 0.677 |
| Medium uniform | 0.998 | 0.623 | 0.734 |
| Long uniform | 1.001 | 0.960 | 0.966 |
| High variation | 0.997 | 0.856 | 0.873 |

Below 1 favors adaptive. Its strongest effect is when callers choose minimum 1
and would otherwise incur one atomic claim per item: at two and four workers,
adaptive claims were faster across all cost profiles. At one worker both APIs
take the direct sequential path and are effectively tied. The p95 ratios at
minimum 1 also favored adaptive for short, medium and high-variation items at
two and four workers; long uniform work at four workers was close to parity.

When each implementation's grain was tuned independently, best median elapsed
time was generally close:

| Item cost | 1 worker | 2 workers | 4 workers |
|---|---:|---:|---:|
| Short uniform | 1.031 | 1.046 | 1.011 |
| Medium uniform | 0.997 | 0.989 | 1.034 |
| Long uniform | 1.004 | 0.990 | 0.997 |
| High variation | 0.997 | 1.014 | 1.012 |

These ratios are adaptive-best median divided by fixed-best median; values
above 1 mean adaptive was slower. A fixed grain selected with prior knowledge
of the workload often matches or slightly beats adaptive. The adaptive API's
measured value is reducing sensitivity to that tuning: setting a small minimum
avoids the large fixed-grain-1 overhead while retaining balancing claims. It
is not a general peak-throughput win. The docs now describe this distinction
and point to the focused benchmark command. Raw rows and the paired summary
are retained at
[`results/xps_ldc142_adaptive_cost_sweep_4sessions_80pairs.csv`](results/xps_ldc142_adaptive_cost_sweep_4sessions_80pairs.csv)
and [`results/xps_ldc142_adaptive_cost_sweep_summary.json`](results/xps_ldc142_adaptive_cost_sweep_summary.json).

## Cost-cluster sensitivity and guided divisor

The initial high-variation profile scattered expensive items by a deterministic
hash. A follow-up held the cost distribution constant (one eighth of items at
8x cost, the rest at base cost) and compared scattered, heavy-prefix and
heavy-suffix placement. Four more LDC processes used the same 20-pair, 5-warmup
protocol across 1, 2 and 4 workers. Raw data is retained at
[`results/xps_ldc142_adaptive_cluster_divisor4_4sessions_80pairs.csv`](results/xps_ldc142_adaptive_cluster_divisor4_4sessions_80pairs.csv).

With the original guided formula (`remaining / (workers * 2)`), heavy-prefix
items caused adaptive's best median to be 8.8% slower than the independently
tuned fixed method at two workers and 24.6% slower at four workers. The first
large claim could take most of the expensive prefix. I changed the guided
formula to target roughly four claims per participant (`remaining / (workers *
4)`). In a repeated capture, adaptive's best median was 4.7% slower at two
workers and 1.8% slower at four for this prefix pattern. The per-process
four-worker ratios at the selected adaptive/fixed grain were 1.040, 1.006,
1.116 and 0.991; one process had substantial tail outliers across multiple
workloads, so pooled p95 comparisons are noisy.

For scattered hotspots, the best medians remained within roughly 2.3% of fixed
with either divisor. Uniform long work paid a small scheduling cost with the
smaller guided claims, generally around 1%. Heavy-suffix results were also near
parity, with a small adaptive regression. The divisor-four policy therefore
substantially reduces the repeatable front-loaded hotspot penalty while
keeping the other tested medians close to fixed scheduling. It remains opt-in;
fixed `parallelFor` is the recommended choice when expensive items are known to
be clustered at the beginning. The public documentation now calls out this
case and the benchmark includes all three hotspot placements. The summarized
paired output is at
[`results/xps_ldc142_adaptive_cluster_divisor4_summary.json`](results/xps_ldc142_adaptive_cluster_divisor4_summary.json).


## Guided divisor eight follow-up

A further four-process capture compared `remaining / (workers * 8)` with the
divisor-four result above, using the same LDC 1.42 host, four 20-pair sessions,
5 warmups, six grains and the same six profiles. Raw paired data is retained at
[`results/xps_ldc142_adaptive_cluster_divisor8_4sessions_80pairs.csv`](results/xps_ldc142_adaptive_cluster_divisor8_4sessions_80pairs.csv),
with the paired summary at
[`results/xps_ldc142_adaptive_cluster_divisor8_summary.json`](results/xps_ldc142_adaptive_cluster_divisor8_summary.json).

At four workers, independently grain-tuned adaptive medians for the
heavy-prefix profile were 0.5%, 0.8%, 0.8% and 1.8% slower than fixed claims
across the four processes. Divisor four varied more in that profile, from 0.5%
faster to 3.4% slower. At two workers, divisor eight ratios were 1.8%, 7.5%,
0.6% faster and 1.5% slower, so that result is less consistent. Divisor eight
also improved the pooled best-grain ratio for scattered hotspots at four
workers (2.4% faster than fixed); for medium uniform work it was about 3.4%
slower at two and four workers. Long uniform work stayed near parity. These are
medians from one host and short CPU-bound runs, not general performance
guarantees.

The public guided-claim target is now about eight claims per participant. It
keeps front-loaded hotspots near fixed scheduling in the repeated four-worker
captures, while adaptive scheduling remains optional and fixed claims remain
preferable when the cost layout is known.

## Result-handle wait-queue follow-up

The bounded streaming benchmark exposed a tradeoff in result notification.
The shared-condition implementation retained a fast atomic ready-result path
and performed well on producer wall time, but every completion broadcast woke
waiters for unrelated handles. A per-handle mutex/condition prototype reduced
median task latency but increased producer wall time by roughly 20% in the
initial probe. The selected follow-up keeps one notifier mutex per executor
and lazily creates a condition for a result cell only when a caller actually
waits; completion then wakes only waiters for that cell. Ready results retain
the atomic fast path and allocate no condition.

Four paired LDC 1.42 captures on the Dell XPS 15 compared the shared condition
with the lazy per-cell condition. Each capture used 10 measured pairs and 3
warmups per producer count, 4 workers, 2,048 tasks, 256 iterations per task,
and a capacity of four tasks per producer. Raw data is retained at
[`results/xps_ldc142_result_wait_queue_4sessions_80pairs.csv`](results/xps_ldc142_result_wait_queue_4sessions_80pairs.csv).
Pooled medians were:

| Producers | Shared p50 latency | Lazy p50 latency | Shared producer wall | Lazy producer wall |
|---:|---:|---:|---:|---:|
| 4 | 17.9 us | 16.5 us | 6.82 ms | 6.88 ms |
| 8 | 46.6 us | 27.4 us | 7.13 ms | 7.03 ms |
| 16 | 56.4 us | 48.4 us | 7.68 ms | 7.76 ms |
| 32 | 131.1 us | 90.4 us | 8.16 ms | 7.99 ms |

The lazy queue reduced p50 latency in all four configurations, by 8% to 41%,
with producer wall time within 1% at 4–16 producers and 2% lower at 32. The
p95 latency was similar overall: it was 6% worse at 4 producers, 9% worse at 8,
5% worse at 16, and 1% lower at 32. This is a latency improvement with a
slightly weaker middle-range tail, not an across-the-board speedup. The result
supports the lazy per-cell wait queue for the current implementation; these
measurements are limited to this host and workload and make no portable
performance claim.

## Non-helping Phobos streaming comparison

Review found that Phobos `Task.yieldForce` may execute its target on the
calling producer when that task has not started. A direct streaming comparison
would therefore give Phobos up to `producers` extra compute threads. The
maintained streaming benchmark now fences each producer until its task has
entered a pool worker before calling `yieldForce`. Four paired LDC 1.42 process
captures on the Dell XPS 15 used 4 pool workers, 2,048 tasks, 256 iterations,
capacity four per producer, 10 measured pairs and 3 warmups per configuration.
The fence overhead is part of the Phobos arm; no producer executes task work.
Raw data is retained at
[`results/xps_ldc142_streaming_nonhelping_producers_4sessions_40pairs.csv`](results/xps_ldc142_streaming_nonhelping_producers_4sessions_40pairs.csv).

| Producers | Concurrency / Phobos producer wall | Concurrency p50 latency | Phobos p50 latency | Concurrency p95 latency | Phobos p95 latency |
|---:|---:|---:|---:|---:|---:|
| 4 | 2.025 | 18.1 us | 17.6 us | 129.8 us | 44.9 us |
| 8 | 3.423 | 28.5 us | 22.8 us | 273.1 us | 44.0 us |
| 16 | 2.905 | 55.2 us | 54.2 us | 564.0 us | 74.3 us |
| 32 | 2.652 | 95.4 us | 112.1 us | 994.7 us | 134.1 us |

This small-task stream still favors Phobos on producer wall time, while
median latency is close through 16 producers and lower for concurrency at 32.
Concurrency's p95 grows sharply as producer count rises. These results show a
workload-specific throughput/tail tradeoff and motivate further bounded-stream
optimization; they do not support a general ranking between the libraries.
