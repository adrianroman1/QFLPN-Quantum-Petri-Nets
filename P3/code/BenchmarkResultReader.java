package hpc.csr;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Strict reader for qflpn-benchmark-v2 CSV files.
 */
public final class BenchmarkResultReader {

    private static final int EXPECTED_FIELDS = 28;

    private BenchmarkResultReader() {
    }

    public static List<BenchmarkResult> read() throws IOException {
        return read(BenchmarkResultWriter.defaultOutputPath());
    }

    public static List<BenchmarkResult> read(Path inputPath)
            throws IOException {

        if (inputPath == null) {
            throw new IllegalArgumentException(
                    "inputPath must not be null");
        }

        if (!Files.exists(inputPath)
                || !Files.isRegularFile(inputPath)) {
            throw new IOException(
                    "Benchmark CSV does not exist or is not a regular file: "
                            + inputPath);
        }

        if (Files.size(inputPath) == 0L) {
            throw new IOException(
                    "Benchmark CSV is empty; header is missing");
        }

        String content = Files.readString(
                inputPath, StandardCharsets.UTF_8);

        final List<List<String>> records;

        try {
            records = parseCsv(content);
        } catch (IllegalArgumentException exception) {
            throw new IOException(
                    "Invalid CSV syntax", exception);
        }

        if (records.isEmpty()
                || records.get(0).size() != EXPECTED_FIELDS
                || !String.join(",", records.get(0)).equals(
                        BenchmarkResultWriter.csvHeader())) {
            throw new IOException(
                    "Invalid V2 CSV header; expected exactly 28 columns");
        }

        List<BenchmarkResult> results = new ArrayList<>();

        for (int i = 1; i < records.size(); i++) {
            List<String> fields = records.get(i);

            if (fields.size() == 1 && fields.get(0).isEmpty()) {
                continue;
            }

            if (fields.size() != EXPECTED_FIELDS) {
                throw new IOException(
                        "Invalid field count at record " + (i + 1)
                                + ": expected " + EXPECTED_FIELDS
                                + ", found " + fields.size());
            }

            try {
                results.add(fromFields(fields));
            } catch (RuntimeException exception) {
                throw new IOException(
                        "Invalid benchmark values at record " + (i + 1),
                        exception);
            }
        }

        return List.copyOf(results);
    }

    private static BenchmarkResult fromFields(List<String> f) {
        return new BenchmarkResult(
                f.get(0),
                f.get(1),
                f.get(2),
                integer(f, 3),
                longValue(f, 4),
                integer(f, 5),
                integer(f, 6),
                integer(f, 7),
                integer(f, 8),
                decimal(f, 9),
                decimal(f, 10),
                decimal(f, 11),
                decimal(f, 12),
                decimal(f, 13),
                decimal(f, 14),
                decimal(f, 15),
                decimal(f, 16),
                decimal(f, 17),
                decimal(f, 18),
                decimal(f, 19),
                decimal(f, 20),
                decimal(f, 21),
                f.get(22),
                longValue(f, 23),
                longValue(f, 24),
                f.get(25),
                f.get(26),
                f.get(27));
    }

    private static int integer(List<String> fields, int index) {
        return Integer.parseInt(fields.get(index));
    }

    private static long longValue(List<String> fields, int index) {
        return Long.parseLong(fields.get(index));
    }

    private static double decimal(List<String> fields, int index) {
        double value = Double.parseDouble(fields.get(index));

        if (!Double.isFinite(value)) {
            throw new IllegalArgumentException(
                    "Non-finite numeric value in column " + index);
        }

        return value;
    }

    /**
     * Parses RFC-4180-style CSV records, including quoted commas,
     * escaped quotes and embedded CR/LF characters.
     */
    private static List<List<String>> parseCsv(String content) {
        List<List<String>> records = new ArrayList<>();
        List<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();

        boolean quoted = false;
        boolean afterQuote = false;
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
                        afterQuote = true;
                    }
                } else {
                    field.append(c);
                }
                continue;
            }

            if (afterQuote
                    && c != ','
                    && c != '\r'
                    && c != '\n') {
                throw new IllegalArgumentException(
                        "Unexpected character after closing quote");
            }

            if (c == '"') {
                if (fieldStarted || field.length() != 0) {
                    throw new IllegalArgumentException(
                            "Quote inside an unquoted field");
                }

                quoted = true;
                fieldStarted = true;
                afterQuote = false;

            } else if (c == ',') {
                fields.add(field.toString());
                field.setLength(0);
                fieldStarted = false;
                afterQuote = false;

            } else if (c == '\r' || c == '\n') {
                fields.add(field.toString());
                records.add(List.copyOf(fields));

                fields.clear();
                field.setLength(0);
                fieldStarted = false;
                afterQuote = false;

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
                    "Unclosed quoted CSV field");
        }

        if (afterQuote
                || fieldStarted
                || !fields.isEmpty()
                || field.length() != 0) {
            fields.add(field.toString());
            records.add(List.copyOf(fields));
        }

        return records;
    }
}
