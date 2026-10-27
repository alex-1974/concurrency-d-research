#!/usr/bin/env python3
"""Reproduce the selected-grain summary for one cross-language capture."""
import argparse
import csv
import math
import statistics
from pathlib import Path

ARMS = {
    "D parallelFor": ("d", ("parallelForReused",)),
    "Phobos": ("d", ("phobosReused",)),
    "Taskflow": ("taskflow", ("static", "guided")),
    "oneTBB": ("onetbb", ("simple", "auto")),
    "Rayon": ("rayon", ("min_len", "max_len")),
}


def summarize(path, language, workload, arms):
    rows = list(csv.DictReader((path / f"{language}.csv").open(newline="")))
    selected = [
        row for row in rows
        if row["phase"] == "measure" and row["workload"] == workload
        and int(row["workers"]) == 4 and row["arm"] in arms
    ]
    by_arm_grain = {}
    for row in selected:
        key = (row["arm"], int(row["batch_size"]))
        by_arm_grain.setdefault(key, []).append(int(row["elapsed_ns"]))
    candidates = [
        (statistics.median(values), arm, grain, sorted(values))
        for (arm, grain), values in by_arm_grain.items()
    ]
    median_ns, arm, grain, values = min(candidates)
    p95_ns = values[math.ceil(0.95 * len(values)) - 1]
    return arm, grain, median_ns, p95_ns


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    for workload in ("fine", "medium", "coarse", "irregular"):
        values = [summarize(args.capture, language, workload, arms) for language, arms in ARMS.values()]
        cells = [f"{p50 / 1000:.1f} / {p95 / 1000:.1f} ({grain})" for _, grain, p50, p95 in values]
        print(f"{workload} | " + " | ".join(cells))


if __name__ == "__main__":
    main()
