package hpc.csr;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Reads benchmark results from RFC-style CSV records.
 *
 * Supports:
 * - quoted fields;
 * - escaped double quotes;
 * - commas inside quoted fields;
 * - CR, LF and CRLF inside quoted fields;
 * - multiple physical lines inside one CSV record.
 */
public final class BenchmarkResultReader {

    private static final int EXPECTED_FIELDS = 22;

    private BenchmarkResultReader() {
        // Utility class.
    }

    public static List<BenchmarkResult> read()
            throws IOException {

        return read(
                BenchmarkResultWriter.defaultOutputPath());
    }

    public static List<BenchmarkResult> read(
            Path inputPath)
            throws IOException {

        if (inputPath == null) {
            throw new IllegalArgumentException(
                    "inputPath must not be null");
        }

        if (!Files.exists(inputPath)) {
            throw new IOException(
                    "Benchmark CSV file does not exist: "
                            + inputPath);
        }

        String content = Files.readString(
                inputPath,
                StandardCharsets.UTF_8);

        List<List<String>> records =
                parseCsv(content);

        if (records.isEmpty()) {
            return List.of();
        }

        List<String> header = records.get(0);

        if (header.size() != EXPECTED_FIELDS
                || !String.join(",", header).equals(
                        BenchmarkResultWriter.csvHeader())) {

            throw new IOException(
                    "Invalid benchmark CSV header.");
        }

        List<BenchmarkResult> results =
                new ArrayList<>();

        for (int i = 1; i < records.size(); i++) {

            List<String> fields = records.get(i);

            if (fields.size() == 1
                    && fields.get(0).isBlank()) {
                continue;
            }

            if (fields.size() != EXPECTED_FIELDS) {
                throw new IOException(
                        "Invalid CSV field count at record "
                                + (i + 1)
                                + ": expected "
                                + EXPECTED_FIELDS
                                + " but found "
                                + fields.size());
            }

            try {
                results.add(fromFields(fields));
            } catch (RuntimeException exception) {
                throw new IOException(
                        "Invalid benchmark data at record "
                                + (i + 1),
                        exception);
            }
        }

        return List.copyOf(results);
    }

    private static BenchmarkResult fromFields(
            List<String> fields) {

        return new BenchmarkResult(
                fields.get(0),
                fields.get(1),
                Integer.parseInt(fields.get(2)),
                Long.parseLong(fields.get(3)),
                Integer.parseInt(fields.get(4)),
                Integer.parseInt(fields.get(5)),
                Integer.parseInt(fields.get(6)),
                Integer.parseInt(fields.get(7)),
                Double.parseDouble(fields.get(8)),
                Double.parseDouble(fields.get(9)),
                Double.parseDouble(fields.get(10)),
                Double.parseDouble(fields.get(11)),
                Double.parseDouble(fields.get(12)),
                Double.parseDouble(fields.get(13)),
                Double.parseDouble(fields.get(14)),
                Double.parseDouble(fields.get(15)),
                Double.parseDouble(fields.get(16)),
                fields.get(17),
                Long.parseLong(fields.get(18)),
                fields.get(19),
                fields.get(20),
                fields.get(21));
    }

    /**
     * Parses complete CSV content.
     *
     * Newline characters terminate records only when
     * the parser is outside a quoted field.
     */
    private static List<List<String>> parseCsv(
            String content) {

        List<List<String>> records =
                new ArrayList<>();

        List<String> fields =
                new ArrayList<>();

        StringBuilder field =
                new StringBuilder();

        boolean quoted = false;
        boolean afterClosingQuote = false;
        boolean fieldStarted = false;

        for (int i = 0; i < content.length(); i++) {

            char c = content.charAt(i);

            if (quoted) {

                if (c == '"') {

                    if (i + 1 < content.length()
                            && content.charAt(i + 1) == '"') {

                        field.append('"');
                        i++;

                    } else {

                        quoted = false;
                        afterClosingQuote = true;
                    }

                } else {

                    field.append(c);
                }

                continue;
            }

            if (afterClosingQuote) {

                if (c == ',') {

                    fields.add(field.toString());
                    field.setLength(0);
                    afterClosingQuote = false;
                    fieldStarted = false;
                    continue;
                }

                if (c == '\r' || c == '\n') {

                    fields.add(field.toString());
                    records.add(List.copyOf(fields));

                    fields.clear();
                    field.setLength(0);
                    afterClosingQuote = false;
                    fieldStarted = false;

                    if (c == '\r'
                            && i + 1 < content.length()
                            && content.charAt(i + 1) == '\n') {
                        i++;
                    }

                    continue;
                }

                throw new IllegalArgumentException(
                        "Unexpected character after closing quote.");
            }

            if (c == '"') {

                if (fieldStarted || field.length() != 0) {
                    throw new IllegalArgumentException(
                            "Unexpected quote inside unquoted field.");
                }

                quoted = true;
                fieldStarted = true;

            } else if (c == ',') {

                fields.add(field.toString());
                field.setLength(0);
                fieldStarted = false;

            } else if (c == '\r' || c == '\n') {

                fields.add(field.toString());
                records.add(List.copyOf(fields));

                fields.clear();
                field.setLength(0);
                fieldStarted = false;

                if (c == '\r'
                        && i + 1 < content.length()
                        && content.charAt(i + 1) == '\n') {
                    i++;
                }

            } else {

                field.append(c);
                fieldStarted = true;
            }
        }

        if (quoted) {
            throw new IllegalArgumentException(
                    "Unclosed quoted CSV field.");
        }

        if (afterClosingQuote
                || fieldStarted
                || !fields.isEmpty()
                || field.length() != 0) {

            fields.add(field.toString());
            records.add(List.copyOf(fields));
        }

        return records;
    }
}
