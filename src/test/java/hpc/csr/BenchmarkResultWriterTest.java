package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class BenchmarkResultWriterTest {

    @TempDir
    Path temporaryDirectory;

    @Test
    void shouldWriteHeaderAndOneResult() throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        BenchmarkResult result =
                sampleResult(
                        "QFLPN-1M");

        BenchmarkResultWriter.append(
                output,
                result);

        assertTrue(
                Files.exists(output));

        List<String> lines =
                Files.readAllLines(output);

        assertEquals(
                2,
                lines.size());

        assertEquals(
                BenchmarkResultWriter.csvHeader(),
                lines.get(0));

        assertTrue(
                lines.get(1).contains(
                        "QFLPN-1M"));

        assertTrue(
                lines.get(1).contains(
                        "1000000"));

        assertTrue(
                lines.get(1).contains(
                        "1.250000000000e+01"));
    }

    @Test
    void shouldAppendResultsWithoutDuplicatingHeader()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        BenchmarkResult first =
                sampleResult(
                        "QFLPN-1M");

        BenchmarkResult second =
                sampleResult(
                        "QFLPN-30M");

        BenchmarkResultWriter.append(
                output,
                first);

        BenchmarkResultWriter.append(
                output,
                second);

        List<String> lines =
                Files.readAllLines(output);

        assertEquals(
                3,
                lines.size());

        assertEquals(
                BenchmarkResultWriter.csvHeader(),
                lines.get(0));

        assertTrue(
                lines.get(1).contains(
                        "QFLPN-1M"));

        assertTrue(
                lines.get(2).contains(
                        "QFLPN-30M"));
    }

    @Test
    void shouldCreateParentDirectories()
            throws IOException {

        Path output =
                temporaryDirectory
                        .resolve("results")
                        .resolve("nested")
                        .resolve("benchmark_results.csv");

        BenchmarkResult result =
                sampleResult(
                        "QFLPN-12");

        BenchmarkResultWriter.append(
                output,
                result);

        assertTrue(
                Files.exists(output));

        assertEquals(
                2,
                Files.readAllLines(output).size());
    }

    @Test
    void shouldQuoteCsvValuesContainingComma()
            throws IOException {

        Path output =
                temporaryDirectory.resolve(
                        "benchmark_results.csv");

        BenchmarkResult result =
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
                        "x86_64",
                        4_000_000_000L,
                        "21",
                        "Linux",
                        "test note, with comma");

        BenchmarkResultWriter.append(
                output,
                result);

        String row =
                Files.readAllLines(
                        output)
                        .get(1);

        assertTrue(
                row.contains(
                        "\"test note, with comma\""));
    }

    private static BenchmarkResult sampleResult(
            String benchmarkId) {

        return new BenchmarkResult(
                "2026-09-06T00:00:00Z",
                benchmarkId,
                benchmarkId.equals("QFLPN-30M")
                        ? 30_000_000
                        : benchmarkId.equals("QFLPN-12")
                        ? 12
                        : 1_000_000,
                benchmarkId.equals("QFLPN-30M")
                        ? 60_000_000L
                        : benchmarkId.equals("QFLPN-12")
                        ? 24L
                        : 2_000_000L,
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
                "JUnit sample result");
    }
}