# Synchronous batch tuning screen: XPS, 2026-10-29

This is a local LDC 1.42 screen of `submitBatchAndWait`, not a baseline A/B
and not a portable performance claim. It covers 2,048 homogeneous logical
items, 4 executor workers, grain sizes 1/4/16/64/256, per-item recurrence
counts 0/8/64, one or four producers, and three capacity modes: one producer
with ingress/retention 2,048/2,048; four producers with 2,048/2,048; and four
producers with practical 256/512 limits. The latter omits grain 1 because an
atomic per-producer batch would exceed ingress capacity.

Each configuration has five independent process sessions with 15 measured
and five warmup samples per session. A checksum is checked on every sample.
Four-producer elapsed times include producer thread creation and join. The
per-session summary computes p50 and nearest-rank p95 independently; the
compact summary reports the median and range of those per-session quantiles.
Raw process rows and the complete host/compiler metadata are in the adjacent
CSV and JSON files. The metadata records the exact benchmark source commit and
SHA-256. The benchmark was captured from a local worktree before it was
committed; the checked-in source hash matches the captured benchmark source.

On the XPS 15 (Core i7-9750H, Linux 6.17, LDC 1.42), larger grains generally
lowered median completion time for this uniform workload. At four producers,
grain 256's median session p50 ranged from 201 to 211 microseconds in the
roomy-capacity mode, versus 216 to 219 microseconds at grain 64 for the 0/64
iteration cases; p95 was not consistently lower. With 256/512 capacity,
grain 256's median session p50 was 258 to 354 microseconds across the three
work amounts, versus 277 to 386 microseconds at grain 64. However, the
64-iteration four-producer runs had severe session-to-session spread (up to
1.9 ms in median session p50 and 4.3 ms in session p95), so those values do
not establish a stable optimum or tail-latency benefit.

This workload has uniform per-item cost and includes producer-thread setup in
the multi-producer timing. It does not model task-cost variance, application
work, or a direct one-task baseline. Use it only to guide follow-up measurements
with representative consumer work. Do not infer that grain 256 is generally
best.

The [matching native ARM64 screen](../arm64-2026-10-29/README.md) produced
similar median trends on a hosted Neoverse-N2 runner. It also found that p95
comparisons depend on task cost and capacity mode.
