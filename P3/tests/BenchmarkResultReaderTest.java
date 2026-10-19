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

        Path output = temporaryDirectory.resolve(
                "benchmark_results.csv");

        BenchmarkResult expected =
                sampleResult("QFLPN-1M");

        BenchmarkResultWriter.append(output, expected);

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(output);

        assertEquals(1, results.size());

        BenchmarkResult actual = results.get(0);

        assertEquals(expected.timestamp(), actual.timestamp());
        assertEquals(expected.benchmarkId(), actual.benchmarkId());
        assertEquals(expected.dimension(), actual.dimension());
        assertEquals(expected.nonZeroCount(), actual.nonZeroCount());
        assertEquals(expected.sequentialMs(), actual.sequentialMs());
        assertEquals(expected.parallelMs(), actual.parallelMs());
        assertEquals(expected.speedup(), actual.speedup());
        assertEquals(expected.cpu(), actual.cpu());
        assertEquals(expected.notes(), actual.notes());
    }

    @Test
    void shouldReadMultipleBenchmarkResults()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "benchmark_results.csv");

        BenchmarkResultWriter.append(
                output, sampleResult("QFLPN-12"));

        BenchmarkResultWriter.append(
                output, sampleResult("QFLPN-1M"));

        BenchmarkResultWriter.append(
                output, sampleResult("QFLPN-30M"));

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(output);

        assertEquals(3, results.size());
        assertEquals("QFLPN-12",
                results.get(0).benchmarkId());
        assertEquals("QFLPN-1M",
                results.get(1).benchmarkId());
        assertEquals("QFLPN-30M",
                results.get(2).benchmarkId());
    }

    @Test
    void shouldPreserveCommaInsideQuotedField()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "comma.csv");

        String notes = "note with comma, preserved";

        BenchmarkResult expected =
                sampleResultWithNotes(notes);

        BenchmarkResultWriter.append(output, expected);

        BenchmarkResult actual =
                BenchmarkResultReader.read(output).get(0);

        assertEquals(notes, actual.notes());
    }

    @Test
    void shouldPreserveMultilineNotesExactly()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "multiline.csv");

        String notes =
                "prima linie\n"
                + "a doua linie\n"
                + "a treia linie";

        BenchmarkResult expected =
                sampleResultWithNotes(notes);

        BenchmarkResultWriter.append(output, expected);

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(output);

        assertEquals(1, results.size());

        BenchmarkResult actual = results.get(0);

        assertEquals(
                expected.notes(),
                actual.notes());
    }

    @Test
    void shouldPreserveCarriageReturnAndLineFeed()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "crlf.csv");

        String notes =
                "first\r\n"
                + "second\r\n"
                + "third";

        BenchmarkResult expected =
                sampleResultWithNotes(notes);

        BenchmarkResultWriter.append(output, expected);

        BenchmarkResult actual =
                BenchmarkResultReader.read(output).get(0);

        assertEquals(notes, actual.notes());
    }

    @Test
    void shouldPreserveEscapedQuotesAndNewlines()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "quotes.csv");

        String notes =
                "first \"quoted\" line\n"
                + "second \"quoted\" line";

        BenchmarkResult expected =
                sampleResultWithNotes(notes);

        BenchmarkResultWriter.append(output, expected);

        BenchmarkResult actual =
                BenchmarkResultReader.read(output).get(0);

        assertEquals(notes, actual.notes());
    }

    @Test
    void shouldReadHeaderOnlyFile()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "header.csv");

        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator());

        assertTrue(
                BenchmarkResultReader.read(output).isEmpty());
    }

    @Test
    void shouldRejectEmptyFile()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "empty.csv");

        Files.writeString(output, "");

        assertThrows(
                IOException.class,
                () -> BenchmarkResultReader.read(output));
    }

    @Test
    void shouldRejectFileContainingOnlyNewlines()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "newlines-only.csv");

        Files.writeString(
                output,
                System.lineSeparator());

        assertThrows(
                IOException.class,
                () -> BenchmarkResultReader.read(output));
    }

    @Test
    void shouldRejectMissingFile() {

        Path output = temporaryDirectory.resolve(
                "missing.csv");

        assertThrows(
                IOException.class,
                () -> BenchmarkResultReader.read(output));
    }

    @Test
    void shouldRejectInvalidHeader()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "invalid-header.csv");

        Files.writeString(output, "invalid,header");

        assertThrows(
                IOException.class,
                () -> BenchmarkResultReader.read(output));
    }

    @Test
    void shouldRejectInvalidFieldCount()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "invalid-count.csv");

        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator()
                        + "only,three,fields"
                        + System.lineSeparator());

        assertThrows(
                IOException.class,
                () -> BenchmarkResultReader.read(output));
    }

    @Test
    void shouldRejectUnclosedQuotedField()
            throws IOException {

        Path output = temporaryDirectory.resolve(
                "unclosed.csv");

        String malformed =
                BenchmarkResultWriter.csvHeader()
                + System.lineSeparator()
                + "\"unclosed";

        Files.writeString(output, malformed);

        assertThrows(
                IOException.class,
                () -> BenchmarkResultReader.read(output));
    }

    private static BenchmarkResult sampleResult(
            String benchmarkId) {

        int dimension = switch (benchmarkId) {
            case "QFLPN-12" -> 12;
            case "QFLPN-30M" -> 30_000_000;
            default -> 1_000_000;
        };

        return new BenchmarkResult(
                "2026-09-06T00:00:00Z",
                benchmarkId,
                dimension,
                2L * dimension,
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

    private static BenchmarkResult sampleResultWithNotes(
            String notes) {

        return new BenchmarkResult(
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
                notes);
    }
}
