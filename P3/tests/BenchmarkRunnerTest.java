package hpc.csr;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class BenchmarkRunnerTest {

    @Test
    void computesMeanMedianAndPopulationDeviation() {
        double[] x = {1.0, 2.0, 3.0, 4.0};

        assertEquals(2.5, BenchmarkRunner.mean(x), 1e-12);
        assertEquals(2.5, BenchmarkRunner.median(x), 1e-12);
        assertEquals(
                Math.sqrt(1.25),
                BenchmarkRunner.populationStdDev(x),
                1e-12);
    }

    @Test
    void medianHandlesOddSampleCount() {
        assertEquals(
                2.0,
                BenchmarkRunner.median(new double[] {9, 2, 1}),
                1e-12);
    }

    @Test
    void rejectsEmptySamples() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.mean(new double[0]));
    }

    @Test
    void rejectsNonFiniteSamples() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.median(
                        new double[] {1, Double.NaN}));
    }

    @Test
    void comparesAgainstIndependentVector() {
        assertEquals(
                0.0,
                BenchmarkRunner.maxAbsoluteError(
                        new double[] {1.5, 1.5},
                        new double[] {1.5, 1.5}),
                0.0);
    }

    @Test
    void rejectsDifferentVectorLengths() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.maxAbsoluteError(
                        new double[] {1},
                        new double[] {1, 2}));
    }

    @Test
    void acceptsSufficientHeapForOneMillionScale() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        long required = scale.requiredHeapBytes();
        long maxHeap = required + 128L * 1024L * 1024L;

        assertDoesNotThrow(
                () -> BenchmarkRunner.requireMemoryPreflight(
                        scale,
                        maxHeap,
                        0L));
    }

    @Test
    void rejectsInsufficientHeapForOneMillionScale() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_1M;

        long required = scale.requiredHeapBytes();

        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.requireMemoryPreflight(
                        scale,
                        required - 1L,
                        0L));

        assertTrue(
                exception.getMessage().contains(
                        "MEMORY_PREFLIGHT_FAILED"));
    }

    @Test
    void rejectsNullScaleBeforeAllocation() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.requireMemoryPreflight(
                        null,
                        1_000_000_000L,
                        0L));
    }

    @Test
    void rejectsThreeHundredMillionWhenHeapIsInsufficient() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_300M;

        // 32 GB decimal: deliberately below the modelled requirement.
        long simulatedMaxHeap = 32_000_000_000L;
        long simulatedUsedHeap = 128L * 1024L * 1024L;

        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.requireMemoryPreflight(
                        scale,
                        simulatedMaxHeap,
                        simulatedUsedHeap));

        assertTrue(
                exception.getMessage().contains(
                        "MEMORY_PREFLIGHT_FAILED"));

        assertTrue(
                exception.getMessage().contains(
                        "QFLPN-300M"));
    }

    @Test
    void acceptsThreeHundredMillionWhenModelledHeapIsSufficient() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_300M;

        long required = scale.requiredHeapBytes();
        long simulatedMaxHeap =
                required + 128L * 1024L * 1024L;

        assertDoesNotThrow(
                () -> BenchmarkRunner.requireMemoryPreflight(
                        scale,
                        simulatedMaxHeap,
                        0L));
    }

    @Test
    void rejectsInvalidHeapMeasurementsBeforeBenchmarkAllocation() {
        BenchmarkScale scale = BenchmarkScale.QFLPN_300M;

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.requireMemoryPreflight(
                        scale,
                        0L,
                        0L));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.requireMemoryPreflight(
                        scale,
                        100L,
                        101L));
    }

    @Test
    void benchmarkScaleIdentifierIsCanonicalForThreeHundredMillion() {
        assertEquals(
                "QFLPN-300M",
                BenchmarkScale.fromTimedDimension(300_000_000)
                        .benchmarkId());
    }

    @Test
    void correctnessFixtureIsNotEligibleForTimedBenchmarking() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromTimedDimension(12));
    }

    @Test
    void unsupportedDimensionIsRejectedByCanonicalCatalog() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkScale.fromTimedDimension(30_000_000));
    }
}
