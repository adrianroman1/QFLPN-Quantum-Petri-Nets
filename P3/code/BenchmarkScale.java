package hpc.csr;

/**
 * Canonical benchmark scales for the QFLPN CSR/SpMV implementation.
 *
 * Timed benchmark scales:
 *   1M, 10M and 70M.
 *
 * Resource-envelope scale:
 *   100M. This scale is reserved exclusively for memory modelling
 *   and resource preflight. It must never produce execution-time results.
 *
 * QFLPN_12 is retained as a correctness and compatibility fixture.
 */
public enum BenchmarkScale {

    /**
     * Small correctness and compatibility fixture.
     */
    QFLPN_12(
            "QFLPN-12",
            12,
            ScaleRole.CORRECTNESS_FIXTURE),

    /**
     * First timed scalability point.
     */
    QFLPN_1M(
            "QFLPN-1M",
            1_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Second timed scalability point.
     */
    QFLPN_10M(
            "QFLPN-10M",
            10_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Largest timed scalability point.
     */
    QFLPN_70M(
            "QFLPN-70M",
            70_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Resource-envelope-only point.
     *
     * No execution-time benchmark is permitted at this scale.
     */
    QFLPN_100M(
            "QFLPN-100M",
            100_000_000,
            ScaleRole.RESOURCE_ENVELOPE_ONLY);

    /**
     * Classification of a benchmark scale.
     */
    public enum ScaleRole {
        CORRECTNESS_FIXTURE,
        TIMED_BENCHMARK,
        RESOURCE_ENVELOPE_ONLY
    }

    private final String benchmarkId;
    private final int dimension;
    private final ScaleRole role;

    BenchmarkScale(
            String benchmarkId,
            int dimension,
            ScaleRole role) {

        if (benchmarkId == null || benchmarkId.isBlank()) {
            throw new IllegalArgumentException(
                    "Benchmark identifier must not be blank.");
        }

        if (dimension <= 0) {
            throw new IllegalArgumentException(
                    "Benchmark dimension must be positive.");
        }

        if (role == null) {
            throw new IllegalArgumentException(
                    "Benchmark scale role must not be null.");
        }

        this.benchmarkId = benchmarkId;
        this.dimension = dimension;
        this.role = role;
    }

    /**
     * Returns the stable benchmark identifier.
     */
    public String benchmarkId() {
        return benchmarkId;
    }

    /**
     * Returns the square matrix dimension N.
     */
    public int dimension() {
        return dimension;
    }

    /**
     * Returns the scale classification.
     */
    public ScaleRole role() {
        return role;
    }

    /**
     * Returns whether this scale is eligible for timed benchmarking.
     */
    public boolean isTimedBenchmark() {
        return role == ScaleRole.TIMED_BENCHMARK;
    }

    /**
     * Returns whether this scale is reserved for resource modelling.
     */
    public boolean isResourceEnvelopeOnly() {
        return role == ScaleRole.RESOURCE_ENVELOPE_ONLY;
    }

    /**
     * Returns whether this scale is a correctness fixture.
     */
    public boolean isCorrectnessFixture() {
        return role == ScaleRole.CORRECTNESS_FIXTURE;
    }

    /**
     * Returns the modelled number of non-zero elements.
     *
     * Assumption:
     *     NNZ = 2 * N
     *
     * This is a resource-model assumption, not a measured workload value.
     */
    public long nonZeroCount() {
        return Math.multiplyExact(2L, (long) dimension);
    }

    /**
     * Estimates the payload size of the CSR arrays.
     *
     * values:      8 bytes per non-zero element
     * columns:     4 bytes per non-zero element
     * rowPointers: 4 bytes per row pointer
     *
     * Formula:
     *     12 * NNZ + 4 * (N + 1)
     *
     * This excludes temporary buffers, JVM object and array headers,
     * vectors, thread stacks and garbage-collector overhead.
     *
     * It is not an estimate of peak JVM heap usage.
     */
    public long estimatedCsrArrayBytes() {
        long nnz = nonZeroCount();

        return Math.addExact(
                Math.multiplyExact(12L, nnz),
                Math.multiplyExact(
                        4L,
                        (long) dimension + 1L));
    }

    /**
     * Resolves a benchmark scale by identifier.
     *
     * Matching is case-insensitive and ignores surrounding whitespace.
     */
    public static BenchmarkScale fromBenchmarkId(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                    "Benchmark identifier must not be blank.");
        }

        String normalized = value.trim();

        for (BenchmarkScale scale : values()) {
            if (scale.benchmarkId.equalsIgnoreCase(normalized)) {
                return scale;
            }
        }

        throw new IllegalArgumentException(
                "Unknown benchmark identifier: " + value);
    }

    /**
     * Resolves a predefined scale from matrix dimension N.
     *
     * This method also resolves the 100M resource-envelope scale
     * and the QFLPN-12 correctness fixture.
     */
    public static BenchmarkScale fromDimension(int dimension) {
        for (BenchmarkScale scale : values()) {
            if (scale.dimension == dimension) {
                return scale;
            }
        }

        throw new IllegalArgumentException(
                "No predefined benchmark scale for N=" + dimension);
    }

    /**
     * Resolves a scale explicitly eligible for timed execution.
     *
     * Correctness fixtures and resource-envelope scales are rejected.
     */
    public static BenchmarkScale fromTimedDimension(int dimension) {
        BenchmarkScale scale = fromDimension(dimension);

        if (!scale.isTimedBenchmark()) {
            throw new IllegalArgumentException(
                    "N=" + dimension
                            + " is not eligible for timed benchmarking. "
                            + "Scale role: " + scale.role);
        }

        return scale;
    }

    @Override
    public String toString() {
        return benchmarkId
                + "(N=" + dimension
                + ", NNZ=" + nonZeroCount()
                + ", role=" + role
                + ", CSR-array-bytes=" + estimatedCsrArrayBytes()
                + ")";
    }
}
