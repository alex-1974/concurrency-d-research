# Single-task outlier batch screen: XPS, 2026-10-29

This screen tests a stronger cost imbalance than the paired clustered and
scattered layouts. Of 2,048 items, one item receives all 8,192 extra
recurrence iterations (128 × 64); the remaining items receive none of that
extra work. The total extra work is therefore equal to the previous 128-item
layouts. Base recurrence counts are 0, 8 and 64. The capture sweeps grains
1/4/16/64/256, one or four producers, and roomy or bounded capacity modes.

There are five independent process sessions and 15 measured plus five warmup
samples per configuration. Checksums are verified for every sample. Timings
for four producers include producer thread creation and join. The metadata
records the exact source commit, binary SHA-256, host and compiler. The
combined observations and individual session CSV files are retained here.

On this XPS 15 with LDC 1.42, the single outlier did not produce a consistent
case for smaller grains. In the four-producer roomy mode at base cost 8, grain
256 had a median session p50 of 168 microseconds and p95 of 204 microseconds;
grain 64 measured 176 and 246 microseconds. At base cost 64, grain 256 had a
slightly lower median than grain 64 (185 versus 188 microseconds), while its
p95 was higher (257 versus 223 microseconds). Under bounded capacity, grain
256 was faster at the median in the single-outlier 8- and 64-iteration cases,
but p95 differences still varied. Across all layouts, work amounts and
capacity modes, no grain had a reliable p95 advantage.

These whole-call timings include producer startup, and are sensitive to host
noise. One synthetic recurrence-heavy item is not a model for blocking work,
I/O, or arbitrary user callables. The results do not justify a scheduler
default change or automatic cost prediction; they support workload-specific
measurement and keeping grain choice explicit.
