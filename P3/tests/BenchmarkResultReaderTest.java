package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class BenchmarkResultReaderTest {

    @TempDir
    Path temporaryDirectory;

    @Test
    void shouldReadOneBenchmarkResult()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        BenchmarkResult expected =
                sampleResult(
                        "QFLPN-1M");

        BenchmarkResultWriter.append(
                output,
                expected);

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(
                        output);

        assertEquals(
                1,
                results.size());

        BenchmarkResult actual =
                results.get(0);

        assertEquals(
                expected.timestamp(),
                actual.timestamp());

        assertEquals(
                expected.benchmarkId(),
                actual.benchmarkId());

        assertEquals(
                expected.dimension(),
                actual.dimension());

        assertEquals(
                expected.nonZeroCount(),
                actual.nonZeroCount());

        assertEquals(
                expected.sequentialMs(),
                actual.sequentialMs());

        assertEquals(
                expected.parallelMs(),
                actual.parallelMs());

        assertEquals(
                expected.speedup(),
                actual.speedup());

        assertEquals(
                expected.cpu(),
                actual.cpu());

        assertEquals(
                expected.notes(),
                actual.notes());
    }

    @Test
    void shouldReadMultipleBenchmarkResults()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        BenchmarkResult first =
                sampleResult(
                        "QFLPN-12");

        BenchmarkResult second =
                sampleResult(
                        "QFLPN-1M");

        BenchmarkResult third =
                sampleResult(
                        "QFLPN-30M");

        BenchmarkResultWriter.append(
                output,
                first);

        BenchmarkResultWriter.append(
                output,
                second);

        BenchmarkResultWriter.append(
                output,
                third);

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(
                        output);

        assertEquals(
                3,
                results.size());

        assertEquals(
                "QFLPN-12",
                results.get(0).benchmarkId());

        assertEquals(
                "QFLPN-1M",
                results.get(1).benchmarkId());

        assertEquals(
                "QFLPN-30M",
                results.get(2).benchmarkId());
    }

    @Test
    void shouldPreserveCommaInsideQuotedField()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        BenchmarkResult expected =
                new BenchmarkResult(
                        "2026-09-06T00:00:00Z",
                        "QFLPN-test",
                        12,
                        24L,
                        8,
                        4096,
                        2,
                        3,
                        10.0,
                        5.0,
                        2.0,
                        1200.0,
                        2400.0,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        "x86_64; processors=8",
                        4_000_000_000L,
                        "21",
                        "Linux",
                        "note with comma, preserved");

        BenchmarkResultWriter.append(
                output,
                expected);

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(
                        output);

        assertEquals(
                1,
                results.size());

        assertEquals(
                "note with comma, preserved",
                results.get(0).notes());
    }

    @Test
    void shouldReturnEmptyListForHeaderOnlyFile()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator());

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(
                        output);

        assertTrue(
                results.isEmpty());
    }

    @Test
    void shouldRejectMissingFile() {

        Path output =
                temporaryDirectory.resolve(
                        "missing.csv");

        assertThrows(
                IOException.class,
                () ->
                        BenchmarkResultReader.read(
                                output));
    }

    @Test
    void shouldRejectInvalidHeader()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "invalid.csv");

        Files.writeString(
                output,
                "invalid,header"
                        + System.lineSeparator());

        assertThrows(
                IOException.class,
                () ->
                        BenchmarkResultReader.read(
                                output));
    }

    @Test
    void shouldRejectInvalidFieldCount()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "invalid.csv");

        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator()
                        + "only,three,fields"
                        + System.lineSeparator());

        assertThrows(
                IOException.class,
                () ->
                        BenchmarkResultReader.read(
                                output));
    }

    private static BenchmarkResult sampleResult(
            String benchmarkId) {

        int dimension =
                switch (benchmarkId) {
                    case "QFLPN-12" ->
                            12;
                    case "QFLPN-30M" ->
                            30_000_000;
                    default ->
                            1_000_000;
                };

        long nonZeroCount =
                2L * dimension;

        return new BenchmarkResult(
                "2026-09-06T00:00:00Z",
                benchmarkId,
                dimension,
                nonZeroCount,
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
                "JUnit reader test");
    }
}
