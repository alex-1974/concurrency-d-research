# Synchronous batch tuning screen: native ARM64, 2026-10-29

This companion capture used the same benchmark and dimensions as the XPS
screen: 2,048 homogeneous items; four executor workers; per-item recurrence
counts 0/8/64; grains 1/4/16/64/256; one/four producers; roomy and 256/512
ingress/retention modes; five process sessions, 15 measured samples plus five
warmups per session. It ran natively on a hosted Neoverse-N2 runner with LDC
1.41. All checksums passed. GitHub Actions run [40869310847](https://github.com/alex-1974/concurrency-d/actions/runs/40869310847)
contains the original artifact; the CSV and JSON files here preserve the full
observations, per-session quantiles, compact summary and machine metadata.

With four producers and roomy capacities, grain 256 had median session p50s
of 201–219 μs for the three work amounts, versus 216–228 μs at grain 64. The
median session p95 was lower at grain 256 for the 8- and 64-iteration cases,
but slightly higher for zero iterations. Under 256/512 capacities, grain 256
had median session p50s of 193–220 μs, versus 205–223 μs at grain 64; its
median session p95 was lower for zero and eight iterations, and effectively
similar at 64 iterations. One-producer medians also generally fell as grain
increased.

This supports testing grains 64–256 for uniform, throughput-oriented work on
this runner, but does not prove p95 gains on other machines. The measurements
use equal-cost items and include producer thread startup/join in four-producer
cases. They do not model variable task costs or application work. Read this
alongside the XPS capture; neither screen establishes a universal best batch
size.
