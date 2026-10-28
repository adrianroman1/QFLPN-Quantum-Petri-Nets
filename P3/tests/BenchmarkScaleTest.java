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
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        assertEquals("QFLPN-1M", scale.benchmarkId());
        assertEquals(1_000_000, scale.dimension());
        assertEquals(2_000_000L, scale.nonZeroCount());

        assertEquals(
                BenchmarkScale.ScaleRole.TIMED_BENCHMARK,
                scale.role());

        assertTrue(scale.isTimedBenchmark());
        assertFalse(scale.isCorrectnessFixture());
        assertFalse(scale.isResourceEnvelopeOnly());
    }

    @Test
    void shouldDefineQflpn10MAsTimedBenchmark() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_10M;

        assertEquals("QFLPN-10M", scale.benchmarkId());
        assertEquals(10_000_000, scale.dimension());
        assertEquals(20_000_000L, scale.nonZeroCount());

        assertEquals(
                BenchmarkScale.ScaleRole.TIMED_BENCHMARK,
                scale.role());

        assertTrue(scale.isTimedBenchmark());
        assertFalse(scale.isCorrectnessFixture());
        assertFalse(scale.isResourceEnvelopeOnly());
    }

    @Test
    void shouldDefineQflpn70MAsTimedBenchmark() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_70M;

        assertEquals("QFLPN-70M", scale.benchmarkId());
        assertEquals(70_000_000, scale.dimension());
        assertEquals(140_000_000L, scale.nonZeroCount());

        assertEquals(
                BenchmarkScale.ScaleRole.TIMED_BENCHMARK,
                scale.role());

        assertTrue(scale.isTimedBenchmark());
    }

    @Test
    void shouldDefineQflpn100MAsTimedBenchmarkSubjectToPreflight() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_100M;

        assertEquals("QFLPN-100M", scale.benchmarkId());
        assertEquals(100_000_000, scale.dimension());
        assertEquals(200_000_000L, scale.nonZeroCount());

        assertEquals(
                BenchmarkScale.ScaleRole.TIMED_BENCHMARK,
                scale.role());

        assertTrue(scale.isTimedBenchmark());

        /*
         * Timed eligibility does not imply that every workload
         * can be allocated. Runtime memory and index-capacity
         * preflight remains mandatory.
         */
    }

    @Test
    void shouldExposeExactlyTheCanonicalScales() {
        BenchmarkScale[] scales = BenchmarkScale.values();

        assertEquals(5, scales.length);

        assertEquals(BenchmarkScale.QFLPN_12, scales[0]);
        assertEquals(BenchmarkScale.QFLPN_1M, scales[1]);
        assertEquals(BenchmarkScale.QFLPN_10M, scales[2]);
        assertEquals(BenchmarkScale.QFLPN_70M, scales[3]);
        assertEquals(BenchmarkScale.QFLPN_100M, scales[4]);
    }

    @Test
    void shouldResolveBenchmarkIdCaseInsensitively() {
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
                BenchmarkScale.QFLPN_100M,
                BenchmarkScale.fromBenchmarkId(" QFLPN-100M "));
    }

    @Test
    void shouldResolveEveryScaleFromDimension() {
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
    void shouldRejectBlankBenchmarkId() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId(""));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId(" "));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("\t\n"));
    }

    @Test
    void shouldRejectNullBenchmarkId() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId(null));
    }

    @Test
    void shouldRejectUnknownBenchmarkId() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("QFLPN-999"));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("QFLPN-30M"));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromBenchmarkId("UNKNOWN"));
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
                () -> BenchmarkScale.fromDimension(Integer.MAX_VALUE));
    }

    @Test
    void shouldCalculateModelledNonZeroCounts() {
        assertEquals(
                24L,
                BenchmarkScale.QFLPN_12.nonZeroCount());

        assertEquals(
                2_000_000L,
                BenchmarkScale.QFLPN_1M.nonZeroCount());

        assertEquals(
                20_000_000L,
                BenchmarkScale.QFLPN_10M.nonZeroCount());

        assertEquals(
                140_000_000L,
                BenchmarkScale.QFLPN_70M.nonZeroCount());

        assertEquals(
                200_000_000L,
                BenchmarkScale.QFLPN_100M.nonZeroCount());
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
    void shouldKeepCsrPayloadCalculationWithinLongRange() {
        for (BenchmarkScale scale : BenchmarkScale.values()) {
            long payload = scale.estimatedCsrArrayBytes();

            assertTrue(payload > 0L);
            assertTrue(payload >= scale.nonZeroCount() * 12L);
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
    }

    @Test
    void shouldProduceReadableDescriptionForTenMillionScale() {
        String description =
                BenchmarkScale.QFLPN_10M.toString();

        assertTrue(description.contains("QFLPN-10M"));
        assertTrue(description.contains("N=10000000"));
        assertTrue(description.contains("NNZ=20000000"));
        assertTrue(description.contains("TIMED_BENCHMARK"));
        assertTrue(description.contains("CSR-array-bytes=280000004"));
    }

    @Test
    void shouldProduceReadableDescriptionForCorrectnessFixture() {
        String description =
                BenchmarkScale.QFLPN_12.toString();

        assertTrue(description.contains("QFLPN-12"));
        assertTrue(description.contains("N=12"));
        assertTrue(description.contains("NNZ=24"));
        assertTrue(description.contains("CORRECTNESS_FIXTURE"));
    }

    @Test
    void shouldDistinguishModelledPayloadFromMeasuredMemory() {
        long payload =
                BenchmarkScale.QFLPN_100M.estimatedCsrArrayBytes();

        assertEquals(2_800_000_004L, payload);

        /*
         * This is only the theoretical payload of the three CSR arrays
         * under the NNZ = 2 * N assumption.
         *
         * It is not measured heap usage, peak memory consumption,
         * or a guarantee that the workload fits in the available heap.
         */
        assertTrue(payload > 0L);
    }
}
