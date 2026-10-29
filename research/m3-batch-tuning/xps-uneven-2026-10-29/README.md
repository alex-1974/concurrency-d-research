# Uneven batch task-cost screen: XPS, 2026-10-29

This follow-up extends the uniform batch-tuning screen with a controlled
distribution of task costs. It uses 2,048 logical items, four executor
workers, 128 hot items with 64 extra recurrence iterations each, and compares
the hot items grouped at the start (`clustered`) with the same number spaced
evenly across the input (`scattered`). Base recurrence counts are 0, 8 and 64.
Both layouts perform the same total recurrence work for each base count; only
the grouping of expensive items into callables changes. The run covers grains
1/4/16/64/256, one or four producers, and the same roomy and bounded capacity
modes as the uniform screen.

Each configuration has five independent process sessions with 15 measured
and five warmup samples. Every sample checks its result checksum. Four-producer
timings include producer-thread creation and join. The metadata records the
exact source commit, benchmark binary hash, compiler and host. `observations.csv`
contains all process samples; individual session CSVs preserve the original
program output.

On this XPS 15 with LDC 1.42, increasing grain still reduced median completion
time across both cost layouts. For four producers and base cost 8, the median
session p50 at grain 256 was 156–158 microseconds in the roomy mode and
156–158 microseconds in bounded mode; at grain 64 it was 166–168 and
163–168 microseconds, respectively. At base cost 64, grain 256 remained
slightly faster at the median than grain 64 in both layouts. Clustered versus
scattered placement did not produce a consistent median winner. The p95
results were also mixed; one bounded, scattered, 64-iteration setting showed
large session spread. This run therefore does not support a claim that
smaller grains improve tail latency for this workload.

The experiment is synthetic and the difference between layouts is modest
relative to total timing and observed machine noise. It does not model arbitrary
slow tasks, I/O, or real application work. It supports retaining a configurable
grain and measuring representative workloads; it does not justify changing a
default scheduling policy.
