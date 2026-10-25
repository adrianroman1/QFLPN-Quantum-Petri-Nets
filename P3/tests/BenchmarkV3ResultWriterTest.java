package hpc.csr;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class BenchmarkV3ResultWriterTest {

    @TempDir
    Path temporaryDirectory;

    @Test
    void headerContainsExactlyTheValidatorContractFields() {
        assertEquals(46, BenchmarkV3ResultWriter.HEADER.length);

        String header = BenchmarkV3ResultWriter.headerLine();

        assertTrue(header.startsWith(
                "timestamp,run_id,workflow_run_id,commit_sha"));
        assertTrue(header.contains("sequential_rows_per_second"));
        assertTrue(header.contains("parallel_nnz_per_second"));
        assertTrue(header.endsWith("status,verdict,notes"));
    }

    @Test
    void writerCreatesHeaderAndAppendsOneCompleteRow()
            throws IOException {

        Path csv = temporaryDirectory.resolve("benchmark_results_v3.csv");
        String[] fields = validRow();

        BenchmarkV3ResultWriter.append(csv, fields);

        String content = Files.readString(
                csv, StandardCharsets.UTF_8);

        String[] lines = content.stripTrailing().split("\\R");

        assertEquals(2, lines.length);
        assertEquals(BenchmarkV3ResultWriter.headerLine(), lines[0]);
        assertTrue(lines[1].startsWith(
                "2026-10-25T10:00:00Z,test-run,1234567890,"));
    }

    @Test
    void writerAppendsMultipleRowsWithoutDuplicatingHeader()
            throws IOException {

        Path csv = temporaryDirectory.resolve("multiple.csv");

        BenchmarkV3ResultWriter.append(csv, validRow());
        BenchmarkV3ResultWriter.append(csv, validRow());

        String[] lines = Files.readString(
                csv, StandardCharsets.UTF_8)
                .stripTrailing()
                .split("\\R");

        assertEquals(3, lines.length);
        assertEquals(BenchmarkV3ResultWriter.headerLine(), lines[0]);
    }

    @Test
    void writerRejectsWrongFieldCount() {
        Path csv = temporaryDirectory.resolve("wrong-count.csv");

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3ResultWriter.append(
                        csv, new String[] {"only-one-field"}));
    }

    @Test
    void writerRejectsNullField() {
        Path csv = temporaryDirectory.resolve("null-field.csv");
        String[] fields = validRow();
        fields[5] = null;

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3ResultWriter.append(csv, fields));
    }

    @Test
    void writerRejectsIncompatibleExistingHeader()
            throws IOException {

        Path csv = temporaryDirectory.resolve("wrong-header.csv");

        Files.writeString(
                csv,
                "timestamp,run_id,old_v2_field\n"
                        + "2026-10-25T10:00:00Z,old,1\n",
                StandardCharsets.UTF_8);

        assertThrows(
                IOException.class,
                () -> BenchmarkV3ResultWriter.append(csv, validRow()));
    }

    @Test
    void writerRejectsHeaderOnlyFile() throws IOException {
        Path csv = temporaryDirectory.resolve("header-only.csv");

        Files.writeString(
                csv,
                BenchmarkV3ResultWriter.headerLine() + "\n",
                StandardCharsets.UTF_8);

        assertThrows(
                IOException.class,
                () -> BenchmarkV3ResultWriter.append(csv, validRow()));
    }

    @Test
    void writerRejectsIncompleteLastRecord() throws IOException {
        Path csv = temporaryDirectory.resolve("incomplete.csv");

        Files.writeString(
                csv,
                BenchmarkV3ResultWriter.headerLine()
                        + "\npartial-record",
                StandardCharsets.UTF_8);

        assertThrows(
                IOException.class,
                () -> BenchmarkV3ResultWriter.append(csv, validRow()));
    }

    @Test
    void csvEscapingHandlesCommasQuotesAndNewlines() {
        String[] fields = validRow();
        fields[45] = "first, \"quoted\" line\nsecond line";

        String encoded = BenchmarkV3ResultWriter.encode(fields);

        assertTrue(encoded.contains(
                "\"first, \"\"quoted\"\" line\nsecond line\""));
    }

    private static String[] validRow() {
        return new String[] {
            "2026-10-25T10:00:00Z",
            "test-run",
            "1234567890",
            "0000000000000000000000000000000000000000",
            "QFLPN-V3-UNIFORM_2",
            "UNIFORM_2",
            "UNIFORM",
            "FIXED_2_PER_ROW",
            "4096",
            "8192",
            "2.0",
            "2.0",
            "2.0",
            "2",
            "4096",
            "FORK_JOIN",
            "NNZ_BALANCED_ROW_BOUNDARY",
            "2",
            "5",
            "1.0",
            "1.0",
            "0.0",
            "1.0",
            "1.0",
            "0.5",
            "0.5",
            "0.0",
            "0.5",
            "0.5",
            "2.0",
            "4096000.0",
            "8192000.0",
            "8192000.0",
            "16384000.0",
            "0.0",
            "0.0",
            "0.0",
            "0.1",
            "amd64;processors=8",
            "8589934592",
            "4294967296",
            "21.0.1",
            "Linux",
            "PASS",
            "IMPROVEMENT",
            "writer test"
        };
    }
}
