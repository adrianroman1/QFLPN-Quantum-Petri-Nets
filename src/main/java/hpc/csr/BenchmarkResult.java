package hpc.csr;

/**
 * Immutable result record for a QFLPN CSR benchmark execution.
 *
 * This class contains the numerical and execution metadata that
 * will be persisted in the benchmark results CSV file.
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
        long availableMemoryBytes,
        String javaVersion,
        String operatingSystem,
        String notes) {

    /**
     * Validates the benchmark result.
     */
    public BenchmarkResult {

        if (timestamp == null || timestamp.isBlank()) {
            throw new IllegalArgumentException(
                    "timestamp must not be blank");
        }

        if (benchmarkId == null || benchmarkId.isBlank()) {
            throw new IllegalArgumentException(
                    "benchmarkId must not be blank");
        }

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

        if (sequentialMs < 0.0) {
            throw new IllegalArgumentException(
                    "sequentialMs must be >= 0");
        }

        if (parallelMs < 0.0) {
            throw new IllegalArgumentException(
                    "parallelMs must be >= 0");
        }

        if (speedup < 0.0) {
            throw new IllegalArgumentException(
                    "speedup must be >= 0");
        }

        if (sequentialThroughput < 0.0) {
            throw new IllegalArgumentException(
                    "sequentialThroughput must be >= 0");
        }

        if (parallelThroughput < 0.0) {
            throw new IllegalArgumentException(
                    "parallelThroughput must be >= 0");
        }

        if (sequentialExpectedError < 0.0) {
            throw new IllegalArgumentException(
                    "sequentialExpectedError must be >= 0");
        }

        if (parallelExpectedError < 0.0) {
            throw new IllegalArgumentException(
                    "parallelExpectedError must be >= 0");
        }

        if (maxAbsoluteError < 0.0) {
            throw new IllegalArgumentException(
                    "maxAbsoluteError must be >= 0");
        }

        if (setupTimeMs < 0.0) {
            throw new IllegalArgumentException(
                    "setupTimeMs must be >= 0");
        }

        if (cpu == null || cpu.isBlank()) {
            throw new IllegalArgumentException(
                    "cpu must not be blank");
        }

        if (availableMemoryBytes < 0L) {
            throw new IllegalArgumentException(
                    "availableMemoryBytes must be >= 0");
        }

        if (javaVersion == null || javaVersion.isBlank()) {
            throw new IllegalArgumentException(
                    "javaVersion must not be blank");
        }

        if (operatingSystem == null
                || operatingSystem.isBlank()) {

            throw new IllegalArgumentException(
                    "operatingSystem must not be blank");
        }

        if (notes == null) {
            throw new IllegalArgumentException(
                    "notes must not be null");
        }
    }
}
