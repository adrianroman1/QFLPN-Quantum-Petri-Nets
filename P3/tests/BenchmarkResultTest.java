package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class BenchmarkResultTest {

    @Test
    void shouldCreateValidBenchmarkResult() {

        BenchmarkResult result =
                validResult();

        assertEquals(
                "QFLPN-1M",
                result.benchmarkId());

        assertEquals(
                1_000_000,
                result.dimension());

        assertEquals(
                2_000_000L,
                result.nonZeroCount());
    }

    @Test
    void shouldRejectBlankTimestamp() {

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
                        10.0,
                        5.0,
                        2.0,
                        100_000.0,
                        200_000.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "x86_64",
                        4_000_000_000L,
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void shouldRejectNonPositiveDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
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
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void shouldRejectNegativeSequentialTime() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        1,
                        4096,
                        0,
                        1,
                        -1.0,
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
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void shouldRejectInfiniteParallelTime() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
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
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void shouldRejectNaNSpeedup() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
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
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void shouldRejectNegativeAvailableMemory() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
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
                        "21",
                        "Linux",
                        "test"));
    }

    @Test
    void shouldRejectBlankCpu() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
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
                        1L,
                        "21",
                        "Linux",
                        "test"));
    }

    private static BenchmarkResult validResult() {

        return new BenchmarkResult(
                "2026-09-06T00:00:00Z",
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
                "21",
                "Linux",
                "JUnit validation");
    }
}
