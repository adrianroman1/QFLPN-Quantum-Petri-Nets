package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class BenchmarkResultTest {

    @Test
    void createsValidBenchmarkResult() {
        BenchmarkResult result = validResult();

        assertEquals("QFLPN-1M", result.benchmarkId());
        assertEquals(1_000_000, result.dimension());
        assertEquals(2_000_000L, result.nonZeroCount());
        assertEquals(4_000_000_000L, result.maxJvmMemoryBytes());
        assertEquals(500_000_000L, result.freeJvmHeapBytes());
    }

    @Test
    void rejectsBlankTimestamp() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "",
                        "QFLPN-1M",
                        1_000_000,
                        2_000_000L,
                        8,
                        4096,
                        2,
                        3,
                        12.5,
                        6.25,
                        2.0,
                        80_000.0,
                        160_000.0,
                        0.0,
                        0.0,
                        0.0,
                        3.0,
                        "test-cpu",
                        4_000_000_000L,
                        500_000_000L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsNonPositiveDimension() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        0,
                        0L,
                        1,
                        1,
                        0,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1L,
                        0L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsNegativeNonZeroCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        -1L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1L,
                        0L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsNonPositiveSequentialTime() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        0.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1L,
                        0L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsInfiniteParallelTime() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        Double.POSITIVE_INFINITY,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1L,
                        0L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsNaNSpeedup() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        1.0,
                        Double.NaN,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1L,
                        0L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsNegativeMaximumJvmMemory() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        -1L,
                        0L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsNegativeFreeJvmHeap() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1_000L,
                        -1L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsFreeHeapAboveMaximumJvmMemory() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "test-cpu",
                        1_000L,
                        1_001L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void rejectsBlankCpu() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-10-20T10:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "",
                        1_000L,
                        500L,
                        "21",
                        "Linux",
                        "test"));
    }

    private static BenchmarkResult validResult() {
        return new BenchmarkResult(
                "2026-10-20T10:00:00Z",
                "QFLPN-1M",
                1_000_000,
                2_000_000L,
                8,
                4096,
                2,
                3,
                12.5,
                6.25,
                2.0,
                80_000.0,
                160_000.0,
                0.0,
                0.0,
                0.0,
                3.0,
                "x86_64; processors=8",
                4_000_000_000L,
                500_000_000L,
                "21",
                "Linux",
                "JUnit validation");
    }
}
