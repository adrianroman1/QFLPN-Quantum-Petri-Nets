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

class BenchmarkResultWriterTest {

    @TempDir
    Path temporaryDirectory;

    private static BenchmarkResult sampleResult(String id) {
        int dimension = id.equals("QFLPN-30M") ? 30_000_000
                : id.equals("QFLPN-12") ? 12 : 1_000_000;

        return new BenchmarkResult(
                "2026-10-20T10:00:00Z",
                id,
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
                500_000_000L,
                "21",
                "Linux",
                "JUnit sample result");
    }

    @Test
    void writesHeaderAndOneCompleteResult() throws IOException {
        Path output = temporaryDirectory.resolve("benchmark_results.csv");

        BenchmarkResultWriter.append(output, sampleResult("QFLPN-1M"));

        List<String> lines = Files.readAllLines(output);

        assertEquals(2, lines.size());
        assertEquals(BenchmarkResultWriter.csvHeader(), lines.get(0));
        assertTrue(lines.get(1).contains("QFLPN-1M"));
        assertTrue(lines.get(1).contains("4000000000"));
        assertTrue(lines.get(1).contains("500000000"));
    }

    @Test
    void appendsWithoutDuplicatingHeader() throws IOException {
        Path output = temporaryDirectory.resolve("benchmark_results.csv");

        BenchmarkResultWriter.append(output, sampleResult("QFLPN-1M"));
        BenchmarkResultWriter.append(output, sampleResult("QFLPN-30M"));

        List<String> lines = Files.readAllLines(output);

        assertEquals(3, lines.size());
        assertEquals(BenchmarkResultWriter.csvHeader(), lines.get(0));
        assertTrue(lines.get(1).contains("QFLPN-1M"));
        assertTrue(lines.get(2).contains("QFLPN-30M"));
    }

    @Test
    void createsParentDirectories() throws IOException {
        Path output = temporaryDirectory.resolve(
                "nested/results/benchmark_results.csv");

        BenchmarkResultWriter.append(output, sampleResult("QFLPN-12"));

        assertTrue(Files.exists(output));
        assertEquals(2, Files.readAllLines(output).size());
    }

    @Test
    void quotesCsvValuesContainingComma() throws IOException {
        Path output = temporaryDirectory.resolve("quoted.csv");

        BenchmarkResult result = new BenchmarkResult(
                "2026-10-20T10:00:00Z",
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
                "test CPU",
                4_000_000_000L,
                500_000_000L,
                "21",
                "Linux",
                "note, with comma");

        BenchmarkResultWriter.append(output, result);

        String row = Files.readAllLines(output).get(1);
        assertTrue(row.contains("\"note, with comma\""));
    }

    @Test
    void rejectsExistingFileWithWrongHeaderWithoutChangingIt()
            throws IOException {
        Path output = temporaryDirectory.resolve("invalid.csv");
        Files.writeString(output, "wrong,header\n");

        String original = Files.readString(output);

        assertThrows(IOException.class, () ->
                BenchmarkResultWriter.append(
                        output, sampleResult("QFLPN-test")));

        assertEquals(original, Files.readString(output));
    }

    @Test
    void rejectsHeaderOnlyFileWithoutChangingIt() throws IOException {
        Path output = temporaryDirectory.resolve("header-only.csv");
        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator());

        String original = Files.readString(output);

        assertThrows(IOException.class, () ->
                BenchmarkResultWriter.append(
                        output, sampleResult("QFLPN-test")));

        assertEquals(original, Files.readString(output));
    }

    @Test
    void rejectsFileWithoutFinalNewlineWithoutChangingIt()
            throws IOException {
        Path output = temporaryDirectory.resolve("truncated.csv");

        String original = BenchmarkResultWriter.csvHeader()
                + System.lineSeparator()
                + "incomplete-record";

        Files.writeString(output, original);

        assertThrows(IOException.class, () ->
                BenchmarkResultWriter.append(
                        output, sampleResult("QFLPN-test")));

        assertEquals(original, Files.readString(output));
    }

    @Test
    void rejectsNullPathAndNullResult() {
        assertThrows(IllegalArgumentException.class, () ->
                BenchmarkResultWriter.append(
                        (Path) null, sampleResult("QFLPN-test")));

        assertThrows(IllegalArgumentException.class, () ->
                BenchmarkResultWriter.append(
                        temporaryDirectory.resolve("null.csv"), null));
    }
}
