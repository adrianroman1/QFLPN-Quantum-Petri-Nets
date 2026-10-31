package hpc.csr;

/**
 * Canonical benchmark scales for the QFLPN CSR/SpMV implementation.
 *
 * Timed benchmark scales:
 *   1M, 10M, 70M and 100M.
 *
 * QFLPN_12 is retained as a correctness and compatibility fixture.
 *
 * The enum values are the authoritative scale catalog. Do not add
 * dimensions in validators, scripts or workflow configuration.
 *
 * Resource estimates are conservative models, not measured memory
 * consumption and not evidence that a workload was executed.
 */
public enum BenchmarkScale {

    QFLPN_12(
            "QFLPN-12",
            12,
            ScaleRole.CORRECTNESS_FIXTURE),

    QFLPN_1M(
            "QFLPN-1M",
            1_000_000,
            ScaleRole.TIMED_BENCHMARK),

    QFLPN_10M(
            "QFLPN-10M",
            10_000_000,
            ScaleRole.TIMED_BENCHMARK),

    QFLPN_70M(
            "QFLPN-70M",
            70_000_000,
            ScaleRole.TIMED_BENCHMARK),

    QFLPN_100M(
            "QFLPN-100M",
            100_000_000,
            ScaleRole.TIMED_BENCHMARK);

    public enum ScaleRole {
        CORRECTNESS_FIXTURE,
        TIMED_BENCHMARK,
        RESOURCE_ENVELOPE_ONLY
    }

    private static final long BYTES_PER_DOUBLE = Double.BYTES;
    private static final long BYTES_PER_INT = Integer.BYTES;

    /*
     * Four double vectors are used by the current BenchmarkRunner:
     * input, sequential output, parallel output and analytical oracle.
     */
    private static final long VECTOR_COUNT = 4L;

    /*
     * During construction through the public SparseMatrixCSR constructor,
     * the raw CSR arrays and normalized CSR arrays can coexist.
     */
    private static final long CSR_CONSTRUCTION_COPIES = 2L;

    /*
     * The generated benchmark matrix has exactly two entries per row.
     * The normalization scratch buffer is therefore long[2].
     */
    private static final long NORMALIZATION_SCRATCH_BYTES =
            2L * Long.BYTES;

    /*
     * Conservative headroom:
     *   25% above the modelled live-array payload;
     *   plus 64 MiB for JVM/object/runtime overhead.
     *
     * This is a preflight policy, not a measured peak-memory value.
     */
    private static final long SAFETY_MARGIN_NUMERATOR = 5L;
    private static final long SAFETY_MARGIN_DENOMINATOR = 4L;
    private static final long FIXED_HEAP_RESERVE_BYTES =
            64L * 1024L * 1024L;

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

    public String benchmarkId() {
        return benchmarkId;
    }

    public int dimension() {
        return dimension;
    }

    public ScaleRole role() {
        return role;
    }

    public boolean isTimedBenchmark() {
        return role == ScaleRole.TIMED_BENCHMARK;
    }

    public boolean isResourceEnvelopeOnly() {
        return role == ScaleRole.RESOURCE_ENVELOPE_ONLY;
    }

    public boolean isCorrectnessFixture() {
        return role == ScaleRole.CORRECTNESS_FIXTURE;
    }

    /**
     * Modelled workload NNZ.
     *
     * The benchmark matrix is generated with exactly two entries per row.
     */
    public long nonZeroCount() {
        return Math.multiplyExact(2L, (long) dimension);
    }

    /**
     * Payload of the three CSR arrays:
     *
     * values:      8 * NNZ bytes
     * columns:     4 * NNZ bytes
     * rowPointers: 4 * (N + 1) bytes
     *
     * Formula: 12 * NNZ + 4 * (N + 1).
     */
    public long estimatedCsrArrayBytes() {
        long nnz = nonZeroCount();

        return Math.addExact(
                Math.multiplyExact(
                        BYTES_PER_DOUBLE + BYTES_PER_INT,
                        nnz),
                Math.multiplyExact(
                        BYTES_PER_INT,
                        (long) dimension + 1L));
    }

    /**
     * Payload of the four double vectors used by BenchmarkRunner.
     *
     * This excludes array headers and JVM object overhead.
     */
    public long estimatedVectorBytes() {
        return Math.multiplyExact(
                Math.multiplyExact(
                        (long) dimension,
                        BYTES_PER_DOUBLE),
                VECTOR_COUNT);
    }

    /**
     * Conservative estimate of the simultaneous array payload during
     * matrix construction:
     *
     *   raw CSR arrays
     *   + normalized CSR arrays
     *   + four benchmark vectors
     *   + normalization scratch buffer.
     *
     * The estimate deliberately assumes that raw and normalized CSR
     * arrays coexist during construction.
     */
    public long estimatedPeakArrayPayloadBytes() {
        long csrCopies = Math.multiplyExact(
                CSR_CONSTRUCTION_COPIES,
                estimatedCsrArrayBytes());

        return Math.addExact(
                Math.addExact(csrCopies, estimatedVectorBytes()),
                NORMALIZATION_SCRATCH_BYTES);
    }

    /**
     * Conservative heap requirement used by runtime preflight.
     *
     * Adds a 25% safety margin and a fixed 64 MiB reserve to the
     * modelled simultaneous array payload.
     */
    public long requiredHeapBytes() {
        long payload = estimatedPeakArrayPayloadBytes();

        long scaled = Math.floorDiv(
                Math.addExact(
                        Math.multiplyExact(
                                payload,
                                SAFETY_MARGIN_NUMERATOR),
                        SAFETY_MARGIN_DENOMINATOR - 1L),
                SAFETY_MARGIN_DENOMINATOR);

        return Math.addExact(
                scaled,
                FIXED_HEAP_RESERVE_BYTES);
    }

    /**
     * Returns the currently available heap capacity according to
     * maxHeapBytes - usedHeapBytes.
     */
    public static long availableHeapBytes(
            long maxHeapBytes,
            long usedHeapBytes) {

        if (maxHeapBytes <= 0L) {
            throw new IllegalArgumentException(
                    "Maximum heap size must be positive.");
        }

        if (usedHeapBytes < 0L || usedHeapBytes > maxHeapBytes) {
            throw new IllegalArgumentException(
                    "Used heap must be between zero and maximum heap.");
        }

        return maxHeapBytes - usedHeapBytes;
    }

    /**
     * Checks whether the available heap satisfies this scale's
     * conservative memory requirement.
     */
    public boolean hasSufficientHeap(
            long maxHeapBytes,
            long usedHeapBytes) {

        long available = availableHeapBytes(
                maxHeapBytes,
                usedHeapBytes);

        return available >= requiredHeapBytes();
    }

    /**
     * Performs fail-closed memory and Java-array-index preflight.
     *
     * This method must be called before allocating benchmark arrays.
     */
    public void requirePreflight(
            long maxHeapBytes,
            long usedHeapBytes) {

        long nnz = nonZeroCount();

        if (nnz > Integer.MAX_VALUE) {
            throw new IllegalStateException(
                    benchmarkId
                            + " exceeds Java int-indexed CSR array capacity: NNZ="
                            + nnz);
        }

        if ((long) dimension + 1L > Integer.MAX_VALUE) {
            throw new IllegalStateException(
                    benchmarkId
                            + " exceeds Java row-pointer array capacity: N="
                            + dimension);
        }

        long available = availableHeapBytes(
                maxHeapBytes,
                usedHeapBytes);

        long required = requiredHeapBytes();

        if (available < required) {
            throw new IllegalStateException(
                    "MEMORY_PREFLIGHT_FAILED"
                            + "; benchmark_id=" + benchmarkId
                            + "; dimension=" + dimension
                            + "; nnz=" + nnz
                            + "; available_heap_bytes=" + available
                            + "; required_heap_bytes=" + required
                            + "; estimated_array_payload_bytes="
                            + estimatedPeakArrayPayloadBytes());
        }
    }

    /**
     * Resolves a benchmark scale by its canonical identifier.
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
     * Resolves any predefined scale, including the correctness fixture.
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
     * Resolves a scale eligible for timed benchmarking.
     *
     * A timed scale must still pass runtime memory and index preflight.
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
                + ", estimated-peak-array-payload-bytes="
                + estimatedPeakArrayPayloadBytes()
                + ", required-heap-bytes=" + requiredHeapBytes()
                + ")";
    }
}
