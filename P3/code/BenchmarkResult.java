package hpc.csr;

/** Immutable V2 benchmark record. The historical 23-column CSV is not changed. */
public record BenchmarkResult(
        String timestamp, String runId, String benchmarkId,
        int dimension, long nonZeroCount, int parallelism, int threshold,
        int warmupIterations, int measuredIterations,
        double sequentialMs, double sequentialMedianMs, double sequentialStdDevMs,
        double parallelMs, double parallelMedianMs, double parallelStdDevMs,
        double speedup, double sequentialThroughput, double parallelThroughput,
        double sequentialExpectedError, double parallelExpectedError,
        double maxAbsoluteError, double setupTimeMs, String cpu,
        long maxJvmMemoryBytes, long freeJvmHeapBytes,
        String javaVersion, String operatingSystem, String notes) {

    public BenchmarkResult {
        text(timestamp, "timestamp"); text(runId, "runId"); text(benchmarkId, "benchmarkId");
        text(cpu, "cpu"); text(javaVersion, "javaVersion"); text(operatingSystem, "operatingSystem");
        if (notes == null) throw new IllegalArgumentException("notes must not be null");
        if (dimension <= 0 || nonZeroCount < 0 || parallelism <= 0 || threshold <= 0
                || warmupIterations < 0 || measuredIterations <= 0)
            throw new IllegalArgumentException("Invalid benchmark dimensions/configuration");
        positive(sequentialMs, "sequentialMs"); positive(sequentialMedianMs, "sequentialMedianMs");
        nonnegative(sequentialStdDevMs, "sequentialStdDevMs");
        positive(parallelMs, "parallelMs"); positive(parallelMedianMs, "parallelMedianMs");
        nonnegative(parallelStdDevMs, "parallelStdDevMs"); positive(speedup, "speedup");
        nonnegative(sequentialThroughput, "sequentialThroughput");
        nonnegative(parallelThroughput, "parallelThroughput");
        nonnegative(sequentialExpectedError, "sequentialExpectedError");
        nonnegative(parallelExpectedError, "parallelExpectedError");
        nonnegative(maxAbsoluteError, "maxAbsoluteError"); nonnegative(setupTimeMs, "setupTimeMs");
        if (maxJvmMemoryBytes <= 0 || freeJvmHeapBytes < 0 || freeJvmHeapBytes > maxJvmMemoryBytes)
            throw new IllegalArgumentException("Invalid JVM heap measurements");
    }
    private static void text(String s, String n) { if (s == null || s.isBlank()) throw new IllegalArgumentException(n + " must not be blank"); }
    private static void positive(double v, String n) { if (!Double.isFinite(v) || v <= 0) throw new IllegalArgumentException(n + " must be finite and > 0"); }
    private static void nonnegative(double v, String n) { if (!Double.isFinite(v) || v < 0) throw new IllegalArgumentException(n + " must be finite and >= 0"); }
}
