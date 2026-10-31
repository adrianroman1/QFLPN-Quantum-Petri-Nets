package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BenchmarkScaleTest {

    @Test
    void shouldDefineQflpn12AsCorrectnessFixture() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_12;

        assertEquals("QFLPN-12", scale.benchmarkId());
        assertEquals(12, scale.dimension());
        assertEquals(24L, scale.nonZeroCount());

        assertEquals(
                BenchmarkScale.ScaleRole.CORRECTNESS_FIXTURE,
                scale.role());

        assertTrue(scale.isCorrectnessFixture());
        assertFalse(scale.isTimedBenchmark());
        assertFalse(scale.isResourceEnvelopeOnly());
    }

    @Test
    void shouldDefineQflpn1MAsTimedBenchmark() {
        assertTimedScale(
                BenchmarkScale.QFLPN_1M,
                "QFLPN-1M",
                1_000_000,
                2_000_000L);
    }

    @Test
    void shouldDefineQflpn10MAsTimedBenchmark() {
        assertTimedScale(
                BenchmarkScale.QFLPN_10M,
                "QFLPN-10M",
                10_000_000,
                20_000_000L);
    }

    @Test
    void shouldDefineQflpn70MAsTimedBenchmark() {
        assertTimedScale(
                BenchmarkScale.QFLPN_70M,
                "QFLPN-70M",
                70_000_000,
                140_000_000L);
    }

    @Test
    void shouldDefineQflpn100MAsTimedBenchmarkSubjectToPreflight() {
        assertTimedScale(
                BenchmarkScale.QFLPN_100M,
                "QFLPN-100M",
                100_000_000,
                200_000_000L);
    }

    private static void assertTimedScale(
            BenchmarkScale scale,
            String benchmarkId,
            int dimension,
            long nnz) {

        assertEquals(benchmarkId, scale.benchmarkId());
        assertEquals(dimension, scale.dimension());
        assertEquals(nnz, scale.nonZeroCount());

        assertEquals(
                BenchmarkScale.ScaleRole.TIMED_BENCHMARK,
                scale.role());

        assertTrue(scale.isTimedBenchmark());
        assertFalse(scale.isCorrectnessFixture());
        assertFalse(scale.isResourceEnvelopeOnly());
    }

    @Test
    void shouldExposeExactlyTheExistingCanonicalScales() {
        BenchmarkScale[] scales = BenchmarkScale.values();

        assertEquals(5, scales.length);

        assertEquals(BenchmarkScale.QFLPN_12, scales[0]);
        assertEquals(BenchmarkScale.QFLPN_1M, scales[1]);
        assertEquals(BenchmarkScale.QFLPN_10M, scales[2]);
        assertEquals(BenchmarkScale.QFLPN_70M, scales[3]);
        assertEquals(BenchmarkScale.QFLPN_100M, scales[4]);
    }

    @Test
    void shouldNotContainThirtyMillionScale() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("QFLPN-30M"));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromDimension(30_000_000));
    }

    @Test
    void shouldResolveBenchmarkIdsCaseInsensitively() {
        assertEquals(
                BenchmarkScale.QFLPN_12,
                BenchmarkScale.fromBenchmarkId("QFLPN-12"));

        assertEquals(
                BenchmarkScale.QFLPN_1M,
                BenchmarkScale.fromBenchmarkId("qflpn-1m"));

        assertEquals(
                BenchmarkScale.QFLPN_10M,
                BenchmarkScale.fromBenchmarkId("QFLPN-10M"));

        assertEquals(
                BenchmarkScale.QFLPN_70M,
                BenchmarkScale.fromBenchmarkId("qflpn-70m"));

        assertEquals(
                BenchmarkScale.QFLPN_100M,
                BenchmarkScale.fromBenchmarkId("QFLPN-100M"));
    }

    @Test
    void shouldIgnoreSurroundingWhitespaceInBenchmarkId() {
        assertEquals(
                BenchmarkScale.QFLPN_12,
                BenchmarkScale.fromBenchmarkId(" QFLPN-12 "));

        assertEquals(
                BenchmarkScale.QFLPN_1M,
                BenchmarkScale.fromBenchmarkId("  QFLPN-1M  "));

        assertEquals(
                BenchmarkScale.QFLPN_10M,
                BenchmarkScale.fromBenchmarkId(" QFLPN-10M "));

        assertEquals(
                BenchmarkScale.QFLPN_70M,
                BenchmarkScale.fromBenchmarkId(" QFLPN-70M "));

        assertEquals(
                BenchmarkScale.QFLPN_100M,
                BenchmarkScale.fromBenchmarkId(" QFLPN-100M "));
    }

    @Test
    void shouldRejectNullBlankAndUnknownBenchmarkIds() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId(null));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId(""));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId(" "));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("\t\n"));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("UNKNOWN"));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("QFLPN-999"));
    }

    @Test
    void shouldResolveEveryCanonicalDimension() {
        assertEquals(
                BenchmarkScale.QFLPN_12,
                BenchmarkScale.fromDimension(12));

        assertEquals(
                BenchmarkScale.QFLPN_1M,
                BenchmarkScale.fromDimension(1_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_10M,
                BenchmarkScale.fromDimension(10_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_70M,
                BenchmarkScale.fromDimension(70_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_100M,
                BenchmarkScale.fromDimension(100_000_000));
    }

    @Test
    void shouldRejectUnknownDimensions() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromDimension(0));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromDimension(-1));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromDimension(12_345));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromDimension(30_000_000));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromDimension(Integer.MAX_VALUE));
    }

    @Test
    void shouldResolveOnlyTimedScalesForTimedExecution() {
        assertEquals(
                BenchmarkScale.QFLPN_1M,
                BenchmarkScale.fromTimedDimension(1_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_10M,
                BenchmarkScale.fromTimedDimension(10_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_70M,
                BenchmarkScale.fromTimedDimension(70_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_100M,
                BenchmarkScale.fromTimedDimension(100_000_000));
    }

    @Test
    void shouldRejectCorrectnessFixtureForTimedExecution() {
        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromTimedDimension(12));

        assertTrue(exception.getMessage().contains("not eligible"));
    }

    @Test
    void shouldCalculateModelledNonZeroCounts() {
        assertEquals(24L, BenchmarkScale.QFLPN_12.nonZeroCount());
        assertEquals(2_000_000L, BenchmarkScale.QFLPN_1M.nonZeroCount());
        assertEquals(20_000_000L, BenchmarkScale.QFLPN_10M.nonZeroCount());
        assertEquals(140_000_000L, BenchmarkScale.QFLPN_70M.nonZeroCount());
        assertEquals(200_000_000L, BenchmarkScale.QFLPN_100M.nonZeroCount());
    }

    @Test
    void shouldCalculateCsrArrayPayloadForSmallFixture() {
        assertEquals(
                340L,
                BenchmarkScale.QFLPN_12.estimatedCsrArrayBytes());
    }

    @Test
    void shouldCalculateCsrArrayPayloadForOneMillionRows() {
        assertEquals(
                28_000_004L,
                BenchmarkScale.QFLPN_1M.estimatedCsrArrayBytes());
    }

    @Test
    void shouldCalculateCsrArrayPayloadForTenMillionRows() {
        assertEquals(
                280_000_004L,
                BenchmarkScale.QFLPN_10M.estimatedCsrArrayBytes());
    }

    @Test
    void shouldCalculateCsrArrayPayloadForSeventyMillionRows() {
        assertEquals(
                1_960_000_004L,
                BenchmarkScale.QFLPN_70M.estimatedCsrArrayBytes());
    }

    @Test
    void shouldCalculateCsrArrayPayloadForOneHundredMillionRows() {
        assertEquals(
                2_800_000_004L,
                BenchmarkScale.QFLPN_100M.estimatedCsrArrayBytes());
    }

    @Test
    void shouldCalculateFourBenchmarkVectors() {
        assertEquals(
                32L * 1_000_000L,
                BenchmarkScale.QFLPN_1M.estimatedVectorBytes());

        assertEquals(
                32L * 100_000_000L,
                BenchmarkScale.QFLPN_100M.estimatedVectorBytes());
    }

    @Test
    void shouldIncludeBothCsrConstructionRepresentationsInPeakPayload() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        long expected =
                2L * scale.estimatedCsrArrayBytes()
                        + scale.estimatedVectorBytes()
                        + 2L * Long.BYTES;

        assertEquals(
                expected,
                scale.estimatedPeakArrayPayloadBytes());
    }

    @Test
    void shouldAddSafetyMarginAndFixedReserveToHeapRequirement() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        long payload = scale.estimatedPeakArrayPayloadBytes();

        long expected =
                (payload * 5L + 3L) / 4L
                        + 64L * 1024L * 1024L;

        assertEquals(expected, scale.requiredHeapBytes());
        assertTrue(scale.requiredHeapBytes() > payload);
    }

    @Test
    void shouldCalculateAvailableHeapCorrectly() {
        assertEquals(
                3_000L,
                BenchmarkScale.availableHeapBytes(
                        4_000L,
                        1_000L));
    }

    @Test
    void shouldRejectInvalidHeapMeasurements() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.availableHeapBytes(0L, 0L));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.availableHeapBytes(-1L, 0L));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.availableHeapBytes(100L, -1L));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.availableHeapBytes(100L, 101L));
    }

    @Test
    void shouldPassPreflightWhenHeapCapacityIsSufficient() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        long required = scale.requiredHeapBytes();
        long maxHeap = required + 128L * 1024L * 1024L;

        assertTrue(scale.hasSufficientHeap(maxHeap, 0L));

        scale.requirePreflight(maxHeap, 0L);
    }

    @Test
    void shouldFailPreflightWhenHeapCapacityIsInsufficient() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        long required = scale.requiredHeapBytes();

        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> scale.requirePreflight(
                        required - 1L,
                        0L));

        assertTrue(
                exception.getMessage().contains(
                        "MEMORY_PREFLIGHT_FAILED"));
    }

    @Test
    void shouldRejectHundredMillionWhenHeapIsInsufficient() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_100M;

        long simulatedMaxHeap = 4_190_000_000L;
        long simulatedUsedHeap = 128L * 1024L * 1024L;

        assertFalse(
                scale.hasSufficientHeap(
                        simulatedMaxHeap,
                        simulatedUsedHeap));

        assertThrows(
                IllegalStateException.class,
                () -> scale.requirePreflight(
                        simulatedMaxHeap,
                        simulatedUsedHeap));
    }

    @Test
    void shouldKeepAllScaleEstimatesPositiveAndMonotonic() {
        BenchmarkScale previous = null;

        for (BenchmarkScale scale : BenchmarkScale.values()) {
            assertTrue(scale.nonZeroCount() > 0L);
            assertTrue(scale.estimatedCsrArrayBytes() > 0L);
            assertTrue(scale.estimatedVectorBytes() > 0L);
            assertTrue(scale.estimatedPeakArrayPayloadBytes() > 0L);
            assertTrue(scale.requiredHeapBytes() > 0L);

            if (previous != null) {
                assertTrue(
                        scale.estimatedCsrArrayBytes()
                                > previous.estimatedCsrArrayBytes());

                assertTrue(
                        scale.requiredHeapBytes()
                                > previous.requiredHeapBytes());
            }

            previous = scale;
        }
    }

    @Test
    void shouldProduceReadableDescriptionForTimedScale() {
        String description =
                BenchmarkScale.QFLPN_1M.toString();

        assertTrue(description.contains("QFLPN-1M"));
        assertTrue(description.contains("N=1000000"));
        assertTrue(description.contains("NNZ=2000000"));
        assertTrue(description.contains("TIMED_BENCHMARK"));
        assertTrue(description.contains("CSR-array-bytes=28000004"));
        assertTrue(description.contains("required-heap-bytes="));
    }

    @Test
    void shouldDistinguishModelledPayloadFromMeasuredMemory() {
        long payload =
                BenchmarkScale.QFLPN_100M.estimatedCsrArrayBytes();

        assertEquals(2_800_000_004L, payload);

        /*
         * This value is a theoretical payload estimate for CSR arrays.
         * It is not measured heap use, peak resident memory, or proof
         * that a 100M workload can execute on a particular runner.
         */
        assertTrue(payload > 0L);
    }
}
