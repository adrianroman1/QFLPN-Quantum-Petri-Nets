package hpc.csr;

/**
 * Canonical benchmark scales for the QFLPN CSR/SpMV implementation.
 *
 * Timed benchmark scales:
 *   1M, 2M, 7M, 10M and 30M.
 *
 * Resource-envelope scale:
 *   100M. This scale is reserved for memory modelling and resource
 *   preflight. It must not be used to publish execution-time results.
 *
 * QFLPN_12 is retained as a small compatibility and correctness fixture.
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
    QFLPN_2M(
            "QFLPN-2M",
            2_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Third timed scalability point.
     */
    QFLPN_7M(
            "QFLPN-7M",
            7_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Fourth timed scalability point.
     */
    QFLPN_10M(
            "QFLPN-10M",
            10_000_000,
            ScaleRole.TIMED_BENCHMARK),

    /**
     * Largest planned timed scalability point.
     */
    QFLPN_30M(
            "QFLPN-30M",
            30_000_000,
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

        /**
         * Small fixture for correctness and compatibility tests.
         */
        CORRECTNESS_FIXTURE,

        /**
         * Scale eligible for timed benchmark execution.
         */
        TIMED_BENCHMARK,

        /**
         * Scale used only for resource and memory modelling.
         */
        RESOURCE_ENVELOPE_ONLY
    }

    /**
     * Identifier used in reports and benchmark artifacts.
     */
    private final String benchmarkId;

    /**
     * Matrix dimension N.
     */
    private final int dimension;

    /**
     * Intended experimental role.
     */
    private final ScaleRole role;

    BenchmarkScale(
            String benchmarkId,
            int dimension,
            ScaleRole role) {

        if (benchmarkId == null
                || benchmarkId.isBlank()) {

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
     *
     * @return identifier such as QFLPN-1M
     */
    public String benchmarkId() {

        return benchmarkId;
    }

    /**
     * Returns the square matrix dimension N.
     *
     * @return matrix dimension
     */
    public int dimension() {

        return dimension;
    }

    /**
     * Returns the scale classification.
     *
     * @return benchmark role
     */
    public ScaleRole role() {

        return role;
    }

    /**
     * Returns whether this scale is eligible for timed benchmarking.
     *
     * The 100M resource-envelope scale is deliberately excluded.
     *
     * @return true only for timed benchmark scales
     */
    public boolean isTimedBenchmark() {

        return role == ScaleRole.TIMED_BENCHMARK;
    }

    /**
     * Returns whether this scale is reserved for resource modelling.
     *
     * @return true only for the resource-envelope scale
     */
    public boolean isResourceEnvelopeOnly() {

        return role == ScaleRole.RESOURCE_ENVELOPE_ONLY;
    }

    /**
     * Returns whether this scale is a correctness fixture.
     *
     * @return true only for the small correctness fixture
     */
    public boolean isCorrectnessFixture() {

        return role == ScaleRole.CORRECTNESS_FIXTURE;
    }

    /**
     * Returns the modelled number of non-zero elements.
     *
     * The current scalability model assumes:
     *
     *     NNZ = 2 * N
     *
     * This is a scale model, not a measurement of a generated workload.
     *
     * @return modelled non-zero count
     */
    public long nonZeroCount() {

        return 2L * dimension;
    }

    /**
     * Estimates the payload size of the CSR arrays under the current
     * storage model:
     *
     *   values:     8 bytes per non-zero element (double)
     *   columns:    4 bytes per non-zero element (int)
     *   rowPointers: 4 bytes per row pointer (int)
     *
     * Formula:
     *
     *   12 * NNZ + 4 * (N + 1)
     *
     * This estimate excludes JVM object headers, array headers,
     * temporary construction buffers, input/output vectors, thread
     * stacks, garbage-collector overhead and all non-CSR allocations.
     *
     * It is therefore a lower-level CSR payload estimate, not a
     * prediction of peak JVM heap usage.
     *
     * @return estimated CSR array payload in bytes
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
     * Resolves a benchmark scale from its identifier.
     *
     * Matching is case-insensitive and ignores surrounding whitespace.
     *
     * @param value identifier such as QFLPN-1M
     * @return matching benchmark scale
     * @throws IllegalArgumentException when the identifier is blank
     *                                   or unknown
     */
    public static BenchmarkScale fromBenchmarkId(
            String value) {

        if (value == null
                || value.isBlank()) {

            throw new IllegalArgumentException(
                    "Benchmark identifier must not be blank.");
        }

        String normalized = value.trim();

        for (BenchmarkScale scale : values()) {

            if (scale.benchmarkId.equalsIgnoreCase(
                    normalized)) {

                return scale;
            }
        }

        throw new IllegalArgumentException(
                "Unknown benchmark identifier: " + value);
    }

    /**
     * Resolves a predefined scale from matrix dimension N.
     *
     * This method also resolves the 100M resource-envelope scale.
     * Call isTimedBenchmark() before starting a timed experiment.
     *
     * @param dimension matrix dimension
     * @return matching predefined scale
     * @throws IllegalArgumentException when N is not predefined
     */
    public static BenchmarkScale fromDimension(
            int dimension) {

        for (BenchmarkScale scale : values()) {

            if (scale.dimension == dimension) {
                return scale;
            }
        }

        throw new IllegalArgumentException(
                "No predefined benchmark scale for N="
                        + dimension);
    }

    /**
     * Resolves a scale that is explicitly eligible for timed execution.
     *
     * The resource-envelope scale and correctness fixture are rejected.
     *
     * @param dimension matrix dimension
     * @return timed benchmark scale
     * @throws IllegalArgumentException when N is not a timed scale
     */
    public static BenchmarkScale fromTimedDimension(
            int dimension) {

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
                + "(N="
                + dimension
                + ", NNZ="
                + nonZeroCount()
                + ", role="
                + role
                + ", CSR-array-bytes="
                + estimatedCsrArrayBytes()
                + ")";
    }
}
