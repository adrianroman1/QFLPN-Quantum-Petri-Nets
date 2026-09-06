package hpc.csr;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Reads QFLPN CSR benchmark results from CSV files.
 *
 * The reader expects the CSV format produced by
 * BenchmarkResultWriter.
 */
public final class BenchmarkResultReader {

    private BenchmarkResultReader() {
        // Utility class.
    }

    /**
     * Reads all benchmark results from the default CSV file.
     *
     * @return immutable list of benchmark results
     * @throws IOException if the file cannot be read
     */
    public static List<BenchmarkResult> read()
            throws IOException {

        return read(
                BenchmarkResultWriter.defaultOutputPath());
    }

    /**
     * Reads all benchmark results from the specified CSV file.
     *
     * @param inputPath CSV file
     * @return immutable list of benchmark results
     * @throws IOException if the file cannot be read
     */
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

        List<BenchmarkResult> results =
                new ArrayList<>();

        try (BufferedReader reader =
                     Files.newBufferedReader(
                             inputPath,
                             StandardCharsets.UTF_8)) {

            String header =
                    reader.readLine();

            if (header == null) {
                return List.of();
            }

            if (!header.equals(
                    BenchmarkResultWriter.csvHeader())) {

                throw new IOException(
                        "Invalid benchmark CSV header.");
            }

            String line;

            int lineNumber = 1;

            while ((line = reader.readLine()) != null) {

                lineNumber++;

                if (line.isBlank()) {
                    continue;
                }

                List<String> fields =
                        parseCsvLine(line);

                if (fields.size() != 22) {

                    throw new IOException(
                            "Invalid CSV field count at line "
                                    + lineNumber
                                    + ": expected 22 but found "
                                    + fields.size());
                }

                try {

                    results.add(
                            fromFields(fields));

                } catch (RuntimeException exception) {

                    throw new IOException(
                            "Invalid benchmark data at line "
                                    + lineNumber,
                            exception);
                }
            }
        }

        return List.copyOf(results);
    }

    private static BenchmarkResult fromFields(
            List<String> fields) {

        return new BenchmarkResult(
                fields.get(0),
                fields.get(1),
                Integer.parseInt(
                        fields.get(2)),
                Long.parseLong(
                        fields.get(3)),
                Integer.parseInt(
                        fields.get(4)),
                Integer.parseInt(
                        fields.get(5)),
                Integer.parseInt(
                        fields.get(6)),
                Integer.parseInt(
                        fields.get(7)),
                Double.parseDouble(
                        fields.get(8)),
                Double.parseDouble(
                        fields.get(9)),
                Double.parseDouble(
                        fields.get(10)),
                Double.parseDouble(
                        fields.get(11)),
                Double.parseDouble(
                        fields.get(12)),
                Double.parseDouble(
                        fields.get(13)),
                Double.parseDouble(
                        fields.get(14)),
                Double.parseDouble(
                        fields.get(15)),
                Double.parseDouble(
                        fields.get(16)),
                fields.get(17),
                Long.parseLong(
                        fields.get(18)),
                fields.get(19),
                fields.get(20),
                fields.get(21));
    }

    /**
     * Parses one CSV row.
     *
     * Supports quoted fields and escaped double quotes.
     */
    private static List<String> parseCsvLine(
            String line) {

        List<String> fields =
                new ArrayList<>();

        StringBuilder current =
                new StringBuilder();

        boolean quoted =
                false;

        for (int i = 0;
             i < line.length();
             i++) {

            char character =
                    line.charAt(i);

            if (character == '"') {

                if (quoted
                        && i + 1 < line.length()
                        && line.charAt(i + 1) == '"') {

                    current.append('"');
                    i++;

                } else {

                    quoted =
                            !quoted;
                }

            } else if (character == ','
                    && !quoted) {

                fields.add(
                        current.toString());

                current.setLength(0);

            } else {

                current.append(
                        character);
            }
        }

        if (quoted) {
            throw new IllegalArgumentException(
                    "Unclosed quoted CSV field.");
        }

        fields.add(
                current.toString());

        return fields;
    }
}
