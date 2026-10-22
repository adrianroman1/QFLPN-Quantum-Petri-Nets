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

    private BenchmarkResult sample(String notes) {
        return new BenchmarkResult(
                "2026-10-22T10:00:00Z",
                "QFLPN-12",
                12,
                24L,
                2,
                4096,
                1,
                2,
                20.0,
                10.0,
                2.0,
                600.0,
                1200.0,
                0.0,
                0.0,
                0.0,
                1.5,
                "test-cpu",
                4_000_000_000L,
                500_000_000L,
                "21",
                "Linux",
                notes);
    }

    @Test
    void roundTripsAllTwentyThreeFields() throws IOException {
        Path csv = temporaryDirectory.resolve("results.csv");
        BenchmarkResult expected = sample("complete result");

        BenchmarkResultWriter.append(csv, expected);

        BenchmarkResult actual =
                BenchmarkResultReader.read(csv).get(0);

        assertEquals(expected, actual);
        assertEquals(4_000_000_000L, actual.maxJvmMemoryBytes());
        assertEquals(500_000_000L, actual.freeJvmHeapBytes());
    }

    @Test
    void readsMultipleRecords() throws IOException {
        Path csv = temporaryDirectory.resolve("multiple.csv");

        BenchmarkResultWriter.append(csv, sample("first"));
        BenchmarkResultWriter.append(csv, sample("second"));

        List<BenchmarkResult> results =
                BenchmarkResultReader.read(csv);

        assertEquals(2, results.size());
        assertEquals("first", results.get(0).notes());
        assertEquals("second", results.get(1).notes());
    }

    @Test
    void preservesCommaQuotesAndMultilineNotes() throws IOException {
        Path csv = temporaryDirectory.resolve("quoted.csv");
        String notes = "first, \"quoted\" line\nsecond line";

        BenchmarkResultWriter.append(csv, sample(notes));

        assertEquals(
                notes,
                BenchmarkResultReader.read(csv).get(0).notes());
    }

    @Test
    void acceptsHeaderOnlyFile() throws IOException {
        Path csv = temporaryDirectory.resolve("header.csv");

        Files.writeString(
                csv,
                BenchmarkResultWriter.csvHeader()
                        + System.lineSeparator());

        assertTrue(BenchmarkResultReader.read(csv).isEmpty());
    }

    @Test
    void rejectsEmptyFile() throws IOException {
        Path csv = temporaryDirectory.resolve("empty.csv");
        Files.writeString(csv, "");

        assertThrows(IOException.class,
                () -> BenchmarkResultReader.read(csv));
    }

    @Test
    void rejectsMissingFile() {
        Path csv = temporaryDirectory.resolve("missing.csv");

        assertThrows(IOException.class,
                () -> BenchmarkResultReader.read(csv));
    }

    @Test
    void rejectsInvalidHeader() throws IOException {
        Path csv = temporaryDirectory.resolve("bad-header.csv");
        Files.writeString(csv, "wrong,header\n");

        assertThrows(IOException.class,
                () -> BenchmarkResultReader.read(csv));
    }

    @Test
    void rejectsInvalidFieldCount() throws IOException {
        Path csv = temporaryDirectory.resolve("bad-row.csv");

        Files.writeString(
                csv,
                BenchmarkResultWriter.csvHeader()
                        + "\nonly,three,fields\n");

        assertThrows(IOException.class,
                () -> BenchmarkResultReader.read(csv));
    }

    @Test
    void rejectsUnclosedQuotedField() throws IOException {
        Path csv = temporaryDirectory.resolve("unclosed.csv");

        Files.writeString(
                csv,
                BenchmarkResultWriter.csvHeader()
                        + "\n\"unfinished");

        assertThrows(IOException.class,
                () -> BenchmarkResultReader.read(csv));
    }

    @Test
    void rejectsNullPath() {
        assertThrows(IllegalArgumentException.class,
                () -> BenchmarkResultReader.read(null));
    }
}
