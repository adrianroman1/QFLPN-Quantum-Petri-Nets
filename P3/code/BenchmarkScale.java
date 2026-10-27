package hpc.csr;

/**
 * Canonical benchmark scales for the QFLPN CSR/SpMV implementation.
 *
 * Timed benchmark scales:
 *   1M, 10M, 70M and 100M.
 *
 * QFLPN_12 is retained as a correctness and compatibility fixture.
 *
 * IMPORTANT:
 * A scale being eligible for timed benchmarking does not guarantee
 * that every workload fits in the available JVM heap or the current
 * CSR index representation. Each workload must pass the runtime
 * memory and index-capacity preflight before allocation.
 *
 * Resource-envelope estimates are supplementary information.
 * They must never be reported as measured execution times.
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
     * Third timed scalability point.
     */
    QFLPN_70M(
            "QFLPN-70M",
            70_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Fourth timed scalability point.
     *
     * Actual execution is permitted only after workload-specific
     * memory and CSR index-capacity preflight succeeds.
     */
    QFLPN_100M(
            "QFLPN-100M",
            100_000_000,
            ScaleRole.TIMED_BENCHMARK);

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
     * Returns whether this scale is reserved exclusively
     * for resource-envelope modelling.
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
     * This is a resource-model assumption.
     * It is not a measured workload value.
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
     * It is not an estimate of peak JVM heap usage and must not
     * replace the workload-specific memory preflight.
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
     * This method resolves all predefined scales, including
     * the QFLPN-12 correctness fixture.
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
     * Correctness fixtures and resource-envelope-only scales
     * are rejected.
     *
     * QFLPN-100M is eligible for timed execution, subject to
     * workload-specific runtime preflight.
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
