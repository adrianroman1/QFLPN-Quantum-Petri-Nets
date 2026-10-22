package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class BenchmarkResultTest {

    private static BenchmarkResult validResult() {
        return new BenchmarkResult(
                "2026-10-20T10:00:00Z",
                "QFLPN-100",
                100,
                200L,
                2,
                4096,
                1,
                2,
                20.0,
                10.0,
                2.0,
                5000.0,
                10000.0,
                0.0,
                0.0,
                0.0,
                1.5,
                "test-cpu",
                4_000_000_000L,
                500_000_000L,
                "21",
                "Linux",
                "JUnit test");
    }

    @Test
    void createsValidResultWithBothMemoryFields() {
        BenchmarkResult result = validResult();

        assertEquals("QFLPN-100", result.benchmarkId());
        assertEquals(100, result.dimension());
        assertEquals(200L, result.nonZeroCount());
        assertEquals(4_000_000_000L, result.maxJvmMemoryBytes());
        assertEquals(500_000_000L, result.freeJvmHeapBytes());
    }

    @Test
    void rejectsBlankTimestamp() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "", "QFLPN-100", 100, 200L,
                        2, 4096, 1, 2,
                        20.0, 10.0, 2.0,
                        5000.0, 10000.0,
                        0.0, 0.0, 0.0, 1.5,
                        "test-cpu",
                        4_000_000_000L, 500_000_000L,
                        "21", "Linux", "test"));
    }

    @Test
    void rejectsBlankBenchmarkId() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", " ", 100, 200L,
                        2, 4096, 1, 2,
                        20.0, 10.0, 2.0,
                        5000.0, 10000.0,
                        0.0, 0.0, 0.0, 1.5,
                        "test-cpu",
                        4_000_000_000L, 500_000_000L,
                        "21", "Linux", "test"));
    }

    @Test
    void rejectsNonPositiveDimension() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 0, 0L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNegativeNonZeroCount() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, -1L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNonPositiveParallelism() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        0, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNonPositiveThreshold() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 0, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNegativeWarmupIterations() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, -1, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNonPositiveMeasuredIterations() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 0,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNonPositiveOrNonFiniteTimes() {
        assertInvalidTiming(0.0, 1.0);
        assertInvalidTiming(-1.0, 1.0);
        assertInvalidTiming(Double.NaN, 1.0);
        assertInvalidTiming(1.0, Double.POSITIVE_INFINITY);
    }

    private static void assertInvalidTiming(
            double sequentialMs,
            double parallelMs) {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        sequentialMs, parallelMs, 1.0,
                        1.0, 1.0, 0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsInvalidSpeedup() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, Double.NaN,
                        1.0, 1.0, 0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNegativeOrNonFiniteThroughput() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0,
                        -1.0, 1.0, 0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));

        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0,
                        1.0, Double.POSITIVE_INFINITY,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNegativeErrorMetrics() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        -1.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsNegativeSetupTime() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, -1.0,
                        "cpu", 1L, 0L, "21", "Linux", ""));
    }

    @Test
    void rejectsInvalidJvmMemoryValues() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 0L, 0L, "21", "Linux", ""));

        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 100L, 101L, "21", "Linux", ""));
    }

    @Test
    void rejectsBlankEnvironmentFieldsAndNullNotes() {
        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        " ", 1L, 0L, "21", "Linux", ""));

        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "", "Linux", ""));

        assertThrows(IllegalArgumentException.class, () ->
                new BenchmarkResult(
                        "2026-10-20T10:00:00Z", "QFLPN-test", 10, 20L,
                        1, 1, 0, 1,
                        1.0, 1.0, 1.0, 1.0, 1.0,
                        0.0, 0.0, 0.0, 0.0,
                        "cpu", 1L, 0L, "21", "Linux", null));
    }
}
