package hpc.csr;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Locale;

/** Writes only the versioned V2 schema; never edits the historical 23-column CSV. */
public final class BenchmarkResultWriter {
    private static final String HEADER = String.join(",",
        "timestamp","run_id","benchmark_id","dimension","non_zero_count","parallelism","threshold",
        "warmup_iterations","measured_iterations","sequential_mean_ms","sequential_median_ms","sequential_stddev_ms",
        "parallel_mean_ms","parallel_median_ms","parallel_stddev_ms","speedup",
        "sequential_throughput_states_per_s","parallel_throughput_states_per_s",
        "sequential_expected_error","parallel_expected_error","max_absolute_error","setup_time_ms","cpu",
        "max_jvm_memory_bytes","free_jvm_heap_bytes","java_version","operating_system","notes");
    private BenchmarkResultWriter() {}
    public static String csvHeader() { return HEADER; }
    public static Path defaultOutputPath() { return Path.of("benchmarks", "benchmark_results_v2.csv"); }
    public static void append(BenchmarkResult r) throws IOException { append(defaultOutputPath(), r); }
    public static void append(Path path, BenchmarkResult r) throws IOException {
        if (path == null || r == null) throw new IllegalArgumentException("path/result must not be null");
        Path p = path.toAbsolutePath(); Files.createDirectories(p.getParent());
        boolean fresh = !Files.exists(p) || Files.size(p) == 0;
        if (!fresh) {
            String first = Files.readAllLines(p, StandardCharsets.UTF_8).get(0);
            if (!HEADER.equals(first)) throw new IOException("V2 CSV header mismatch; refusing to append");
            byte[] bytes = Files.readAllBytes(p);
            if (bytes.length == 0 || (bytes[bytes.length-1] != '\n' && bytes[bytes.length-1] != '\r'))
                throw new IOException("V2 CSV lacks final record terminator");
        }
        String row = String.join(",", q(r.timestamp()),q(r.runId()),q(r.benchmarkId()),
            Integer.toString(r.dimension()),Long.toString(r.nonZeroCount()),Integer.toString(r.parallelism()),Integer.toString(r.threshold()),
            Integer.toString(r.warmupIterations()),Integer.toString(r.measuredIterations()),f(r.sequentialMs()),f(r.sequentialMedianMs()),f(r.sequentialStdDevMs()),
            f(r.parallelMs()),f(r.parallelMedianMs()),f(r.parallelStdDevMs()),f(r.speedup()),f(r.sequentialThroughput()),f(r.parallelThroughput()),
            f(r.sequentialExpectedError()),f(r.parallelExpectedError()),f(r.maxAbsoluteError()),f(r.setupTimeMs()),q(r.cpu()),
            Long.toString(r.maxJvmMemoryBytes()),Long.toString(r.freeJvmHeapBytes()),q(r.javaVersion()),q(r.operatingSystem()),q(r.notes()));
        String prefix = fresh ? HEADER + "\n" : "";
        Files.writeString(p, prefix + row + "\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }
    private static String f(double d) { return String.format(Locale.ROOT,"%.12e",d); }
    private static String q(String s) { if (s.indexOf(',')<0 && s.indexOf('"')<0 && s.indexOf('\n')<0 && s.indexOf('\r')<0) return s; return "\""+s.replace("\"","\"\"")+"\""; }
}
