package hpc.csr;

/**
 * Immutable result record for a QFLPN CSR benchmark execution.
 *
 * Memory fields:
 * - maxJvmMemoryBytes: maximum heap size configured for the JVM.
 * - freeJvmHeapBytes: currently free heap memory at capture time.
 *
 * These values are JVM measurements and must not be interpreted
 * as total physical memory or operating-system available memory.
 */
public record BenchmarkResult(
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

    public BenchmarkResult {
        requireText(timestamp, "timestamp");
        requireText(benchmarkId, "benchmarkId");

        if (dimension <= 0) {
            throw new IllegalArgumentException(
                    "dimension must be > 0");
        }

        if (nonZeroCount < 0) {
            throw new IllegalArgumentException(
                    "nonZeroCount must be >= 0");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "parallelism must be > 0");
        }

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be > 0");
        }

        if (warmupIterations < 0) {
            throw new IllegalArgumentException(
                    "warmupIterations must be >= 0");
        }

        if (measuredIterations <= 0) {
            throw new IllegalArgumentException(
                    "measuredIterations must be > 0");
        }

        requireFinitePositive(sequentialMs, "sequentialMs");
        requireFinitePositive(parallelMs, "parallelMs");
        requireFinitePositive(speedup, "speedup");

        requireFiniteNonNegative(
                sequentialThroughput,
                "sequentialThroughput");

        requireFiniteNonNegative(
                parallelThroughput,
                "parallelThroughput");

        requireFiniteNonNegative(
                sequentialExpectedError,
                "sequentialExpectedError");

        requireFiniteNonNegative(
                parallelExpectedError,
                "parallelExpectedError");

        requireFiniteNonNegative(
                maxAbsoluteError,
                "maxAbsoluteError");

        requireFiniteNonNegative(
                setupTimeMs,
                "setupTimeMs");

        requireText(cpu, "cpu");

        if (maxJvmMemoryBytes <= 0L) {
            throw new IllegalArgumentException(
                    "maxJvmMemoryBytes must be > 0");
        }

        if (freeJvmHeapBytes < 0L) {
            throw new IllegalArgumentException(
                    "freeJvmHeapBytes must be >= 0");
        }

        if (freeJvmHeapBytes > maxJvmMemoryBytes) {
            throw new IllegalArgumentException(
                    "freeJvmHeapBytes cannot exceed maxJvmMemoryBytes");
        }

        requireText(javaVersion, "javaVersion");
        requireText(operatingSystem, "operatingSystem");

        if (notes == null) {
            throw new IllegalArgumentException(
                    "notes must not be null");
        }
    }

    private static void requireText(
            String value,
            String fieldName) {

        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                    fieldName + " must not be blank");
        }
    }

    private static void requireFinitePositive(
            double value,
            String fieldName) {

        if (!Double.isFinite(value) || value <= 0.0) {
            throw new IllegalArgumentException(
                    fieldName + " must be finite and > 0");
        }
    }

    private static void requireFiniteNonNegative(
            double value,
            String fieldName) {

        if (!Double.isFinite(value) || value < 0.0) {
            throw new IllegalArgumentException(
                    fieldName + " must be finite and >= 0");
        }
    }
}
