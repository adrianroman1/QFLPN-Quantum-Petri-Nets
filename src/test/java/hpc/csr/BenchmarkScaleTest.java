package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BenchmarkScaleTest {

    @Test
    void shouldDefineQflpn12() {

        BenchmarkScale scale =
                BenchmarkScale.QFLPN_12;

        assertEquals(
                "QFLPN-12",
                scale.benchmarkId());

        assertEquals(
                12,
                scale.dimension());

        assertEquals(
                24L,
                scale.nonZeroCount());
    }

    @Test
    void shouldDefineQflpn1M() {

        BenchmarkScale scale =
                BenchmarkScale.QFLPN_1M;

        assertEquals(
                "QFLPN-1M",
                scale.benchmarkId());

        assertEquals(
                1_000_000,
                scale.dimension());

        assertEquals(
                2_000_000L,
                scale.nonZeroCount());
    }

    @Test
    void shouldDefineQflpn30M() {

        BenchmarkScale scale =
                BenchmarkScale.QFLPN_30M;

        assertEquals(
                "QFLPN-30M",
                scale.benchmarkId());

        assertEquals(
                30_000_000,
                scale.dimension());

        assertEquals(
                60_000_000L,
                scale.nonZeroCount());
    }

    @Test
    void shouldResolveScaleFromBenchmarkId() {

        assertEquals(
                BenchmarkScale.QFLPN_12,
                BenchmarkScale.fromBenchmarkId(
                        "QFLPN-12"));

        assertEquals(
                BenchmarkScale.QFLPN_1M,
                BenchmarkScale.fromBenchmarkId(
                        "qflpn-1m"));

        assertEquals(
                BenchmarkScale.QFLPN_30M,
                BenchmarkScale.fromBenchmarkId(
                        " QFLPN-30M "));
    }

    @Test
    void shouldResolveScaleFromDimension() {

        assertEquals(
                BenchmarkScale.QFLPN_12,
                BenchmarkScale.fromDimension(12));

        assertEquals(
                BenchmarkScale.QFLPN_1M,
                BenchmarkScale.fromDimension(
                        1_000_000));

        assertEquals(
                BenchmarkScale.QFLPN_30M,
                BenchmarkScale.fromDimension(
                        30_000_000));
    }

    @Test
    void shouldRejectBlankBenchmarkId() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        BenchmarkScale.fromBenchmarkId(
                                " "));
    }

    @Test
    void shouldRejectUnknownBenchmarkId() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        BenchmarkScale.fromBenchmarkId(
                                "QFLPN-999"));
    }

    @Test
    void shouldRejectUnknownDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        BenchmarkScale.fromDimension(
                                12345));
    }

    @Test
    void shouldProduceReadableDescription() {

        String description =
                BenchmarkScale.QFLPN_1M.toString();

        assertTrue(
                description.contains(
                        "QFLPN-1M"));

        assertTrue(
                description.contains(
                        "N=1000000"));

        assertTrue(
                description.contains(
                        "NNZ=2000000"));
    }
}
