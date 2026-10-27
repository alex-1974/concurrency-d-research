import concurrency : Executor;
import std.exception : enforce;
import std.stdio : writeln;

private ulong job(size_t id) @safe nothrow
{
    ulong value = id + 1;
    foreach (step; 0 .. 1024)
        value = value * 1664525UL + 1013904223UL + step;
    return value;
}

private ulong expectedChecksum()
{
    ulong sum;
    foreach (id; 0 .. 1024) sum += job(id);
    return sum * 8;
}

private ulong run(bool adaptive)
{
    auto executor = new Executor(4, 256, 1025);
    scope (exit) executor.closeAndJoin();
    auto values = new ulong[1024];
    ulong checksum;
    foreach (_; 0 .. 8)
    {
        if (adaptive)
            executor.parallelForAdaptive(values.length, 1, (size_t id) { values[id] = job(id); });
        else
            executor.parallelFor(values.length, 1, (size_t id) { values[id] = job(id); });
        foreach (value; values) checksum += value;
    }
    executor.closeAndJoin();
    return checksum;
}

void main(string[] args)
{
    enforce(args.length == 2, "usage: profile adaptive|fixed");
    const adaptive = args[1] == "adaptive";
    const expected = expectedChecksum();
    ulong total;
    foreach (_; 0 .. 5000)
    {
        const actual = run(adaptive);
        enforce(actual == expected, "checksum mismatch");
        total += actual;
    }
    enforce(total == expected * 5000, "aggregate checksum mismatch");
    writeln("PROFILE_RESULT mode=", adaptive ? "adaptive" : "fixed", " repeats=5000 checksum=", expected, " aggregate=", total);
}
