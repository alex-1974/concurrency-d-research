#!/usr/bin/env python3
"""Summarize paired divisor-4 vs divisor-8 benchmark sessions."""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).with_name("results")
rows = defaultdict(dict)
for divisor in (4, 8):
    for session in range(1, 5):
        path = ROOT / f"divisor{divisor}-session{session}.csv"
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["phase"] != "measure":
                    continue
                key = (session, int(row["sample"]), row["workload"], int(row["workers"]), int(row["batch_size"]), row["arm"])
                rows[key][divisor] = row

# Every measurement must have its counterpart and both scheduler arms must
# compute the same checksum for each implementation and paired input.
assert len(rows) == 4 * 20 * 6 * 2 * 2 * 2
for key, pair in rows.items():
    assert set(pair) == {4, 8}, key
    assert pair[4]["checksum"] == pair[8]["checksum"], key

ratios = defaultdict(list)
for session in range(1, 5):
    keys = [k for k in rows if k[0] == session]
    by_setting = defaultdict(dict)
    for key in keys:
        _, sample, workload, workers, grain, arm = key
        by_setting[(workload, workers, grain, sample)][arm] = rows[key]
    for (workload, workers, grain, sample), arms in by_setting.items():
        fixed = "parallelForReused"
        adaptive = "parallelForAdaptiveReused"
        assert set(arms) == {fixed, adaptive}
        b_fixed, c_fixed = (int(arms[fixed][d]["elapsed_ns"]) for d in (8, 4))
        b_adapt, c_adapt = (int(arms[adaptive][d]["elapsed_ns"]) for d in (8, 4))
        # Difference-in-differences isolates the changed adaptive policy from
        # session-level elapsed-time variation in the fixed control.
        ratio = (c_adapt / c_fixed) / (b_adapt / b_fixed)
        ratios[(workload, workers, grain, session)].append(ratio)

out = ROOT / "divisor4-vs-divisor8-summary.csv"
with out.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["workload", "workers", "grain", "session", "pairs", "p50_ratio", "p95_ratio", "p99_ratio"])
    for (workload, workers, grain, session), values in sorted(ratios.items()):
        w.writerow([workload, workers, grain, session, len(values), *(f"{statistics.quantiles(values, n=100)[i-1]:.4f}" for i in (50,95,99))])
    for workload, workers, grain in sorted({k[:3] for k in ratios}):
        values = [v for (wl, wk, gr, _), vs in ratios.items() if (wl,wk,gr)==(workload,workers,grain) for v in vs]
        q = statistics.quantiles(values, n=100)
        w.writerow([workload, workers, grain, "pooled", len(values), *(f"{q[i-1]:.4f}" for i in (50,95,99))])
print(f"Wrote {out}; verified {len(rows)} checksummed arm records and {sum(map(len, ratios.values()))} paired ratios.")
