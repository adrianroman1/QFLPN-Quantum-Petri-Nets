package hpc.csr;

/**
 * Predefined benchmark scales used by the QFLPN CSR project.
 *
 * These identifiers provide a stable vocabulary for experiments
 * and for the doctoral research documentation.
 */
public enum BenchmarkScale {

    QFLPN_12(
            "QFLPN-12",
            12),

    QFLPN_1M(
            "QFLPN-1M",
            1_000_000),

    QFLPN_30M(
            "QFLPN-30M",
            30_000_000);

    private final String benchmarkId;

    private final int dimension;

    BenchmarkScale(
            String benchmarkId,
            int dimension) {

        this.benchmarkId =
                benchmarkId;

        this.dimension =
                dimension;
    }

    public String benchmarkId() {
        return benchmarkId;
    }

    public int dimension() {
        return dimension;
    }

    public long nonZeroCount() {
        return 2L * dimension;
    }

    /**
     * Resolves a benchmark scale from its identifier.
     *
     * @param value identifier such as QFLPN-1M
     * @return matching benchmark scale
     * @throws IllegalArgumentException when unknown
     */
    public static BenchmarkScale fromBenchmarkId(
            String value) {

        if (value == null
                || value.isBlank()) {

            throw new IllegalArgumentException(
                    "Benchmark identifier must not be blank.");
        }

        for (BenchmarkScale scale :
                values()) {

            if (scale.benchmarkId.equalsIgnoreCase(
                    value.trim())) {

                return scale;
            }
        }

        throw new IllegalArgumentException(
                "Unknown benchmark identifier: "
                        + value);
    }

    /**
     * Resolves a benchmark scale from N.
     *
     * @param dimension benchmark matrix dimension
     * @return predefined scale
     * @throws IllegalArgumentException when N is not predefined
     */
    public static BenchmarkScale fromDimension(
            int dimension) {

        for (BenchmarkScale scale :
                values()) {

            if (scale.dimension == dimension) {
                return scale;
            }
        }

        throw new IllegalArgumentException(
                "No predefined benchmark scale for N="
                        + dimension);
    }

    @Override
    public String toString() {

        return benchmarkId
                + "(N="
                + dimension
                + ", NNZ="
                + nonZeroCount()
                + ")";
    }
}
