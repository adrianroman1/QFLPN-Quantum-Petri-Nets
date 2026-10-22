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

    @Test
    void writesCurrentTwentyThreeColumnSchema()
            throws IOException {

        Path output = temporaryDirectory.resolve("benchmark.csv");

        BenchmarkResultWriter.append(output, sampleResult());

        List<String> lines = Files.readAllLines(output);

        assertEquals(2, lines.size());
        assertEquals(
                BenchmarkResultWriter.csvHeader(),
                lines.get(0));

        String[] columns = lines.get(1).split(",", -1);

        assertEquals(23, columns.length);
        assertEquals("4000000000", columns[18]);
        assertEquals("500000000", columns[19]);
    }

    @Test
    void appendsWithoutDuplicatingHeader()
            throws IOException {

        Path output = temporaryDirectory.resolve("benchmark.csv");

        BenchmarkResultWriter.append(output, sampleResult());
        BenchmarkResultWriter.append(output, sampleResult());

        List<String> lines = Files.readAllLines(output);

        assertEquals(3, lines.size());
        assertEquals(
                BenchmarkResultWriter.csvHeader(),
                lines.get(0));
    }

    @Test
    void createsParentDirectories()
            throws IOException {

        Path output = temporaryDirectory
                .resolve("nested")
                .resolve("results")
                .resolve("benchmark.csv");

        BenchmarkResultWriter.append(output, sampleResult());

        assertTrue(Files.exists(output));
        assertEquals(2, Files.readAllLines(output).size());
    }

    @Test
    void quotesCsvValuesContainingComma()
            throws IOException {

        Path output = temporaryDirectory.resolve("quoted.csv");

        BenchmarkResult result = new BenchmarkResult(
                "2026-10-20T10:00:00Z",
                "QFLPN-test",
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
                "note, with comma");

        BenchmarkResultWriter.append(output, result);

        String row = Files.readAllLines(output).get(1);

        assertTrue(row.contains("\"note, with comma\""));
    }

    @Test
    void rejectsExistingFileWithOldSchema()
            throws IOException {

        Path output = temporaryDirectory.resolve("old-schema.csv");

        Files.writeString(
                output,
                "timestamp,benchmark_id,available_memory_bytes"
                        + System.lineSeparator()
                        + "old,data,123"
                        + System.lineSeparator());

        String before = Files.readString(output);

        assertThrows(
                IOException.class,
                () -> BenchmarkResultWriter.append(
                        output,
                        sampleResult()));

        assertEquals(before, Files.readString(output));
    }

    @Test
    void rejectsHeaderOnlyExistingFile()
            throws IOException {

        Path output = temporaryDirectory.resolve("header-only.csv");

        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator());

        assertThrows(
                IOException.class,
                () -> BenchmarkResultWriter.append(
                        output,
                        sampleResult()));
    }

    @Test
    void rejectsFileWithoutFinalNewline()
            throws IOException {

        Path output = temporaryDirectory.resolve("truncated.csv");

        Files.writeString(
                output,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator()
                        + "incomplete-record");

        assertThrows(
                IOException.class,
                () -> BenchmarkResultWriter.append(
                        output,
                        sampleResult()));
    }

    @Test
    void rejectsNullResult() {

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkResultWriter.append(
                        temporaryDirectory.resolve("null.csv"),
                        null));
    }

    private static BenchmarkResult sampleResult() {
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
                "JUnit test result");
    }
}
