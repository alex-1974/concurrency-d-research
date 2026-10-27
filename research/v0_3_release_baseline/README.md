# v0.3.0 release performance baseline

This is a reproducible baseline for selecting the next performance experiment.
It runs the exact published `v0.3.0` source tree, rather than a release-candidate
tree, and makes no universal performance claim.

## XPS 15 / LDC 1.42

- Source: `concurrency-d` tag `v0.3.0`, commit
  `b4580d61cddadeeca3b99420a1aae2857b9de62e`.
- Host: Dell XPS 15, Intel Core i7-9750H, 6 cores / 12 threads; Ubuntu
  24.04-derived Linux 6.17 x86_64.
- Power profile: `cool`; fan and temperature telemetry were recorded in
  `metadata.json` before the capture.
- D toolchain: LDC 1.42.0, DMD frontend 2.112.1, LLVM 19.1.7; release build.
- Protocol: 4 independent processes, 20 measured pairs and 5 warmups per
  arm/configuration/session; 4 participants; 1,024 base iterations; eight-wave
  runtime-reuse arms. All outputs were checksum-validated.
- Capture command:

  ```sh
  python3 tools/validation/capture_m2_benchmark.py \
    benchmarks/end-to-end/concurrency-end-to-end-benchmark \
    /tmp/v0.3.0-xps --workers 4 --samples 20 --warmups 5 \
    --base-iterations 1024 --sessions 4
  ```

For the reusable adaptive range path, each ratio is concurrency-d elapsed time
divided by Phobos elapsed time for the same paired sample. Batch size is chosen
by pooled median from the tested sweep. P50/P95/P99 are nearest-rank quantiles
of the paired ratios, not ratios of independently aggregated quantiles.

| Workload | Selected minimum grain | P50 ratio | P95 ratio | P99 ratio |
|---|---:|---:|---:|---:|
| Fine | 1 | 0.9989 | 1.1480 | 1.2886 |
| Medium | 256 | 1.0063 | 1.0377 | 1.0494 |
| Coarse | 256 | 1.0017 | 1.0302 | 1.0875 |
| Irregular | 512 | 1.0084 | 1.0450 | 1.0712 |

The adaptive median is effectively at parity in this capture. The pooled
fine-work tail is elevated, but the per-session p95 ratios at grain 1 are
1.055, 1.227, 1.129 and 1.043. That spread makes a universal tail-latency
target premature. The medium, coarse and irregular p95 ratios are within
4.5% of Phobos. These results characterize one XPS and one workload matrix;
they do not predict another host or application.

## Native ARM64 / LDC 1.41

- Source: the same exact `v0.3.0` commit as above.
- Host: four-core Azure ARM64 runner, Arm Neoverse-N2; Ubuntu 24.04 / Linux
  6.17 aarch64.
- D toolchain: LDC 1.41.0; release build.
- Protocol: 4 independent sessions, 20 measured pairs and 5 warmups per
  arm/configuration/session; 4 participants; 1,024 base iterations; 80 pairs
  total per setting. The workflow verifies checksums and records host metadata.
- Workflow: [#40497118310](https://github.com/alex-1974/concurrency-d/actions/runs/40497118310).

| Workload | Selected minimum grain | P50 ratio | P95 ratio | P99 ratio |
|---|---:|---:|---:|---:|
| Fine | 512 | 1.0289 | 1.0493 | 1.0671 |
| Medium | 256 | 0.9974 | 0.9994 | 1.0016 |
| Coarse | 32 | 0.9975 | 1.0011 | 1.0095 |
| Irregular | 256 | 0.9973 | 1.0011 | 1.0048 |

At the pooled-median-selected grain, fine work is consistently about 3% slower
than Phobos; medium, coarse and irregular work are effectively at parity. The
four per-session fine p50 ratios are 1.026, 1.030, 1.030 and 1.028; p95 ratios
are 1.051, 1.041, 1.035 and 1.049. This is a small, repeatable gap on this
runner, not evidence that a high-risk scheduler redesign is warranted. The
best selected grain also differs from the XPS, reinforcing caller- and
machine-specific tuning.

Raw XPS and ARM64 CSVs, host/toolchain metadata and full benchmark summaries
are stored beside this report. These paired release-tag captures supersede
the earlier candidate captures for the v0.3.0 performance baseline.
