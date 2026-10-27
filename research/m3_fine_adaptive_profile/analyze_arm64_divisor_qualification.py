#!/usr/bin/env python3
"""Validate and summarize native ARM64 divisor 4/16 vs divisor 8 runs."""
import csv
from pathlib import Path

ROOT = Path(__file__).with_name("results") / "arm64"
DIVISORS = (4, 8, 16)
WORKLOADS = ("short_uniform", "medium_uniform", "long_uniform",
             "scattered_hotspots", "heavy_prefix", "heavy_suffix")
WORKERS = (1, 4)
GRAINS = (1, 64)
SAMPLES = range(5, 25)


def percentile(values, p):
    values = sorted(values)
    position = (len(values) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def read_sessions():
    data = {d: {} for d in DIVISORS}
    for divisor in DIVISORS:
        for session in range(1, 5):
            path = ROOT / f"divisor{divisor}-session{session}.csv"
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            measured = [r for r in rows if r["phase"] == "measure"]
            assert len(measured) == 960, (path, len(measured))
            by = {}
            for row in measured:
                key = (int(row["sample"]), row["workload"], int(row["workers"]),
                       int(row["batch_size"]), row["arm"])
                by[key] = row
            assert len(by) == 960, path
            for sample in SAMPLES:
                for workload in WORKLOADS:
                    for workers in WORKERS:
                        for grain in GRAINS:
                            fixed = by[(sample, workload, workers, grain, "parallelForReused")]
                            adaptive = by[(sample, workload, workers, grain,
                                           "parallelForAdaptiveReused")]
                            assert fixed["checksum"] == adaptive["checksum"], (
                                divisor, session, sample, workload, workers, grain)
            data[divisor][session] = by
    return data


def main():
    data = read_sessions()
    output = ROOT / "divisor4-16-vs-divisor8-summary.csv"
    with output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["divisor", "workload", "workers", "grain", "session",
                         "pairs", "p50_ratio", "p95_ratio", "p99_ratio"])
        for divisor in (4, 16):
            for workload in WORKLOADS:
                for workers in WORKERS:
                    for grain in GRAINS:
                        pooled = []
                        for session in range(1, 5):
                            candidate = data[divisor][session]
                            baseline = data[8][session]
                            ratios = []
                            for sample in SAMPLES:
                                prefix = (sample, workload, workers, grain)
                                c_adapt = int(candidate[(*prefix, "parallelForAdaptiveReused")]["elapsed_ns"])
                                c_fixed = int(candidate[(*prefix, "parallelForReused")]["elapsed_ns"])
                                b_adapt = int(baseline[(*prefix, "parallelForAdaptiveReused")]["elapsed_ns"])
                                b_fixed = int(baseline[(*prefix, "parallelForReused")]["elapsed_ns"])
                                ratios.append((c_adapt / c_fixed) / (b_adapt / b_fixed))
                            pooled.extend(ratios)
                            writer.writerow([divisor, workload, workers, grain, session,
                                             len(ratios), *(f"{percentile(ratios, p):.4f}"
                                                            for p in (.50, .95, .99))])
                        writer.writerow([divisor, workload, workers, grain, "pooled",
                                         len(pooled), *(f"{percentile(pooled, p):.4f}"
                                                        for p in (.50, .95, .99))])
    print(f"Validated {len(DIVISORS) * 4 * 960} measured records and checksums; wrote {output}")


if __name__ == "__main__":
    main()
