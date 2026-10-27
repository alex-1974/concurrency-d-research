# Dynamic range scheduling diagnostic

Date: 2026-10-23. This is a local design diagnostic, not release qualification.

## Question and arms

Compare fixed task batching with dynamic range claims for the same indexed CPU
work. The maintained `benchmarks/end-to-end` harness in `concurrency-d` runs
the following checksum-equivalent arms:

- `concurrency`: one submitted callable per fixed range, using the default
  `WorkSize.small` inbox policy.
- `parallelFor`: the public range API; up to one worker task per executor
  worker claims contiguous ranges using the supplied grain size. It uses an
  overflow-safe fetch-add fast path when the counter has enough headroom and a
  saturating CAS fallback near `size_t.max`. These long-lived worker tasks use
  `WorkSize.large` so inbox prefetch does not collect several worker loops in
  one thread.
- `dynamicFor`: a benchmark-only manual loop that submits the same number of
  worker tasks and claims ranges with an atomic fetch-add.
- `phobos`: `TaskPool.parallel` with the same grain as `workUnitSize`. The pool
  has `workers - 1` background threads because the caller participates.

All arms return the same checksum. The workload is deterministic and has four
shapes: fine (1,024 items), medium (256), coarse (32), and irregular (256, with
item cost varying deterministically). Base iteration counts were 64 for the
tiny-work run and 4,096 for the heavier run. Workers 1, 2 and 4 and grain sizes
1, 4, 16, 64 and 256 were tested; arm order rotates within the process.

## Captures

Raw CSV files, including warmups and every measured row, are stored beside this
note. `ldc142_cas_*` retains the preceding saturating-CAS-only version;
`ldc142_*` is the overflow-safe fetch-add fast path used for the final ratios.

- `ldc142_tiny.csv`: `4 20 3 64` (20 measured samples, 3 warmups).
- `ldc142_heavy.csv`: `4 5 2 4096` (5 measured samples, 2 warmups).

The paired median elapsed-time ratios below aggregate workers 2 and 4 and grain
sizes 1, 4, 16 and 64. A value below 1 means `parallelFor` was faster than the
fixed `concurrency` arm; the final column compares it with Phobos.

| Workload | Tiny: parallelFor / fixed submit | Tiny: parallelFor / manual dynamic | Tiny: parallelFor / Phobos | Heavy: parallelFor / fixed submit | Heavy: parallelFor / manual dynamic | Heavy: parallelFor / Phobos |
|---|---:|---:|---:|---:|---:|---:|
| Fine | 0.590 | 1.031 | 1.477 | 0.844 | 0.991 | 1.107 |
| Medium | 0.831 | 1.018 | 1.510 | 0.990 | 0.987 | 1.080 |
| Coarse | 0.950 | 0.996 | 1.530 | 0.974 | 1.016 | 1.072 |
| Irregular | 0.813 | 1.011 | 1.527 | 0.940 | 0.993 | 1.069 |

This supports the shape of the API: dynamic claims substantially reduce the
cost of scheduling many tiny indexed items and remain close to fixed batching
for the heavier cases. The fast path also brings the public API within about
3% of the manual dynamic loop in the tiny groups. It does **not** show parity
with Phobos; Phobos was faster in all these groups. It also does not establish
a portable speedup or a universal best grain size. The 20-sample tiny run is
stronger evidence than the five-sample heavy diagnostic, but both are from one
host and process session.

## Environment and reproducibility

- Host CPU: Intel Core i7-9750H, 6 cores / 12 logical CPUs.
- OS: Linux 6.17.0-22-generic.
- Compiler: LDC 1.42.0 release; host target reported as Skylake.
- Platform profile: `cool`; no CPU pinning or frequency lock was applied.
- `concurrency-d` base commit: `d0c45438a5fd7f39bb97a9c33193a508dc9dc9b1`;
  benchmark and `parallelFor` were dirty working-tree sources. Source hashes:
  `executor.d` `f18dc397289a00fb57f6d5be63983a824a596823528c7d72667cba638c8c49d5`
  (the earlier CAS-only candidate was
  `dee88db400f45e36c4c2a15ebda6cd34e3cebf5d6becdde1ff0c4b254eb625e8`),
  `benchmarks/end-to-end/main.d`
  `3784f192b5651ba362189adb1c060b46cb10e5c4574b4e5e996d409b4f54e0f8`.

Rebuild with `dub build --root=benchmarks/end-to-end --compiler=ldc2
--build=release`, then run the two commands above from the library repository
root. Recheck the hashes and record CPU/power conditions when comparing a later
implementation.
