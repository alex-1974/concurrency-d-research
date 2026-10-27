#!/usr/bin/env python3
"""Summarize paired adaptive min-grain ratios against grain 1."""
import argparse
import csv
import pathlib
import statistics
from collections import defaultdict


def percentile(values, p):
    ordered = sorted(values)
    return ordered[max(0, (len(ordered) * p + 99) // 100 - 1)]


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True, type=pathlib.Path)
parser.add_argument("inputs", nargs="+", type=pathlib.Path)
args = parser.parse_args()

paired = defaultdict(dict)
for path in args.inputs:
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("phase") != "measure" or row.get("arm") != "parallelForAdaptiveReused":
                continue
            if row.get("workers") != "4":
                continue
            if "divisor" in row and row["divisor"] != "8":
                continue
            key = (int(row["session"]), int(row["sample"]), row["workload"])
            grain = int(row["batch_size"])
            if grain in paired[key]:
                raise SystemExit(f"duplicate adaptive measurement: {key}, grain={grain}")
            paired[key][grain] = int(row["elapsed_ns"])

ratios = defaultdict(list)
for key, grains in paired.items():
    if set(grains) != {1, 4, 16, 64}:
        raise SystemExit(f"incomplete grain sweep for {key}: {sorted(grains)}")
    if 1 not in grains:
        continue
    for grain, elapsed in grains.items():
        if grain != 1:
            ratios[(key[0], key[2], grain)].append(elapsed / grains[1])

if not ratios:
    raise SystemExit("no paired adaptive measurements for workers=4")
if any(len(values) != 20 for values in ratios.values()):
    bad = {key: len(values) for key, values in ratios.items() if len(values) != 20}
    raise SystemExit(f"expected 20 measured pairs per session/workload/grain: {bad}")

groups = defaultdict(list)
for (session, workload, grain), values in ratios.items():
    groups[(workload, grain, str(session))].extend(values)
    groups[(workload, grain, "pooled")].extend(values)

args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("w", newline="") as stream:
    fields = ["workload", "grain", "session", "samples", "p50", "p95", "p99"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for (workload, grain, session), values in sorted(groups.items()):
        writer.writerow({
            "workload": workload, "grain": grain, "session": session,
            "samples": len(values), "p50": statistics.median(values),
            "p95": percentile(values, 95), "p99": percentile(values, 99),
        })
print(f"wrote {args.output} ({len(groups)} summaries)")
