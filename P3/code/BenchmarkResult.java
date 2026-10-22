package hpc.csr;

/**
 * Immutable benchmark result.
 * Canonical format: qflpn-benchmark-v2 (28 CSV columns).
 */
public record BenchmarkResult(
        String timestamp,
        String runId,
        String benchmarkId,
        int dimension,
        long nonZeroCount,
        int parallelism,
        int threshold,
        int warmupIterations,
        int measuredIterations,
        double sequentialMs,
        double sequentialMedianMs,
        double sequentialStdDevMs,
        double parallelMs,
        double parallelMedianMs,
        double parallelStdDevMs,
        double speedup,
        double sequentialThroughput,
        double parallelThroughput,
        double sequentialExpectedError,
        double parallelExpectedError,
        double maxAbsoluteError,
        double setupTimeMs,
        String cpu,
        long maxJvmMemoryBytes,
        long freeJvmHeapBytes,
        String javaVersion,
        String operatingSystem,
        String notes) {

    public BenchmarkResult {
        requireText(timestamp, "timestamp");
        requireText(runId, "runId");
        requireText(benchmarkId, "benchmarkId");
        requireText(cpu, "cpu");
        requireText(javaVersion, "javaVersion");
        requireText(operatingSystem, "operatingSystem");

        if (notes == null) {
            throw new IllegalArgumentException("notes must not be null");
        }

        if (dimension <= 0 || nonZeroCount < 0
                || parallelism <= 0 || threshold <= 0
                || warmupIterations < 0 || measuredIterations <= 0) {
            throw new IllegalArgumentException(
                    "Invalid benchmark dimensions or configuration");
        }

        positive(sequentialMs, "sequentialMs");
        positive(sequentialMedianMs, "sequentialMedianMs");
        nonnegative(sequentialStdDevMs, "sequentialStdDevMs");

        positive(parallelMs, "parallelMs");
        positive(parallelMedianMs, "parallelMedianMs");
        nonnegative(parallelStdDevMs, "parallelStdDevMs");

        positive(speedup, "speedup");
        nonnegative(sequentialThroughput, "sequentialThroughput");
        nonnegative(parallelThroughput, "parallelThroughput");
        nonnegative(sequentialExpectedError, "sequentialExpectedError");
        nonnegative(parallelExpectedError, "parallelExpectedError");
        nonnegative(maxAbsoluteError, "maxAbsoluteError");
        nonnegative(setupTimeMs, "setupTimeMs");

        if (maxJvmMemoryBytes <= 0
                || freeJvmHeapBytes < 0
                || freeJvmHeapBytes > maxJvmMemoryBytes) {
            throw new IllegalArgumentException(
                    "Invalid JVM memory measurements");
        }
    }

    /**
     * Backward-compatible constructor for the historical 23-argument API.
     *
     * The old format did not contain runId, medians or standard deviations.
     * The mean values are used as median fallbacks and standard deviations
     * are set to zero. New benchmark code must use the canonical constructor.
     */
    public BenchmarkResult(
            String timestamp,
            String benchmarkId,
            int dimension,
            long nonZeroCount,
            int parallelism,
            int threshold,
            int warmupIterations,
            int measuredIterations,
            double sequentialMs,
            double parallelMs,
            double speedup,
            double sequentialThroughput,
            double parallelThroughput,
            double sequentialExpectedError,
            double parallelExpectedError,
            double maxAbsoluteError,
            double setupTimeMs,
            String cpu,
            long maxJvmMemoryBytes,
            long freeJvmHeapBytes,
            String javaVersion,
            String operatingSystem,
            String notes) {

        this(
                timestamp,
                "legacy-" + benchmarkId,
                benchmarkId,
                dimension,
                nonZeroCount,
                parallelism,
                threshold,
                warmupIterations,
                measuredIterations,
                sequentialMs,
                sequentialMs,
                0.0,
                parallelMs,
                parallelMs,
                0.0,
                speedup,
                sequentialThroughput,
                parallelThroughput,
                sequentialExpectedError,
                parallelExpectedError,
                maxAbsoluteError,
                setupTimeMs,
                cpu,
                maxJvmMemoryBytes,
                freeJvmHeapBytes,
                javaVersion,
                operatingSystem,
                notes);
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                    name + " must not be blank");
        }
    }

    private static void positive(double value, String name) {
        if (!Double.isFinite(value) || value <= 0.0) {
            throw new IllegalArgumentException(
                    name + " must be finite and greater than zero");
        }
    }

    private static void nonnegative(double value, String name) {
        if (!Double.isFinite(value) || value < 0.0) {
            throw new IllegalArgumentException(
                    name + " must be finite and nonnegative");
        }
    }
}
