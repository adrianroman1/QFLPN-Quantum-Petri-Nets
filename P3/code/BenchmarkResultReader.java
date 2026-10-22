package hpc.csr;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Reads benchmark records written by BenchmarkResultWriter.
 * Supports quoted CSV fields, escaped quotes and multiline values.
 */
public final class BenchmarkResultReader {

    private static final int EXPECTED_FIELDS = 23;

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
        if (!Files.exists(inputPath) || !Files.isRegularFile(inputPath)) {
            throw new IOException(
                    "Benchmark CSV file does not exist or is not regular: "
                            + inputPath);
        }
        if (Files.size(inputPath) == 0L) {
            throw new IOException("Benchmark CSV is empty: missing header.");
        }

        String content = Files.readString(
                inputPath, StandardCharsets.UTF_8);

        final List<List<String>> records;
        try {
            records = parseCsv(content);
        } catch (IllegalArgumentException exception) {
            throw new IOException("Invalid CSV syntax.", exception);
        }

        if (records.isEmpty()
                || records.get(0).size() != EXPECTED_FIELDS
                || !String.join(",", records.get(0)).equals(
                        BenchmarkResultWriter.csvHeader())) {
            throw new IOException(
                    "Invalid benchmark CSV header; expected 23 columns.");
        }

        List<BenchmarkResult> results = new ArrayList<>();

        for (int i = 1; i < records.size(); i++) {
            List<String> fields = records.get(i);

            if (fields.size() == 1 && fields.get(0).isBlank()) {
                continue;
            }
            if (fields.size() != EXPECTED_FIELDS) {
                throw new IOException(
                        "Invalid CSV field count at record " + (i + 1)
                                + ": expected " + EXPECTED_FIELDS
                                + " but found " + fields.size());
            }

            try {
                results.add(fromFields(fields));
            } catch (RuntimeException exception) {
                throw new IOException(
                        "Invalid benchmark data at record " + (i + 1),
                        exception);
            }
        }

        return List.copyOf(results);
    }

    private static BenchmarkResult fromFields(List<String> f) {
        return new BenchmarkResult(
                f.get(0),
                f.get(1),
                Integer.parseInt(f.get(2)),
                Long.parseLong(f.get(3)),
                Integer.parseInt(f.get(4)),
                Integer.parseInt(f.get(5)),
                Integer.parseInt(f.get(6)),
                Integer.parseInt(f.get(7)),
                Double.parseDouble(f.get(8)),
                Double.parseDouble(f.get(9)),
                Double.parseDouble(f.get(10)),
                Double.parseDouble(f.get(11)),
                Double.parseDouble(f.get(12)),
                Double.parseDouble(f.get(13)),
                Double.parseDouble(f.get(14)),
                Double.parseDouble(f.get(15)),
                Double.parseDouble(f.get(16)),
                f.get(17),
                Long.parseLong(f.get(18)),
                Long.parseLong(f.get(19)),
                f.get(20),
                f.get(21),
                f.get(22));
    }

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

            if (afterQuote && c != ',' && c != '\r' && c != '\n') {
                throw new IllegalArgumentException(
                        "Unexpected character after closing quote.");
            }

            if (c == '"') {
                if (fieldStarted || field.length() != 0) {
                    throw new IllegalArgumentException(
                            "Quote inside unquoted CSV field.");
                }
                quoted = true;
                fieldStarted = true;
                afterQuote = false;
            } else if (c == ',' ) {
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

                if (c == '\r' && i + 1 < content.length()
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

        if (afterQuote || fieldStarted || !fields.isEmpty()
                || field.length() != 0) {
            fields.add(field.toString());
            records.add(List.copyOf(fields));
        }

        return records;
    }
}
