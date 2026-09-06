package hpc.csr;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Locale;

/**
 * Persists QFLPN CSR benchmark results in CSV format.
 *
 * Default output:
 *
 * benchmarks/benchmark_results.csv
 *
 * The writer creates the parent directory and CSV header
 * automatically when necessary.
 */
public final class BenchmarkResultWriter {

    private static final String CSV_HEADER =
            "timestamp,"
                    + "benchmark_id,"
                    + "dimension,"
                    + "non_zero_count,"
                    + "parallelism,"
                    + "threshold,"
                    + "warmup_iterations,"
                    + "measured_iterations,"
                    + "sequential_ms,"
                    + "parallel_ms,"
                    + "speedup,"
                    + "sequential_throughput_states_per_s,"
                    + "parallel_throughput_states_per_s,"
                    + "sequential_expected_error,"
                    + "parallel_expected_error,"
                    + "max_absolute_error,"
                    + "setup_time_ms,"
                    + "cpu,"
                    + "available_memory_bytes,"
                    + "java_version,"
                    + "operating_system,"
                    + "notes";

    private static final Path DEFAULT_OUTPUT =
            Path.of(
                    "benchmarks",
                    "benchmark_results.csv");

    private BenchmarkResultWriter() {
        // Utility class.
    }

    /**
     * Returns the default benchmark result file.
     */
    public static Path defaultOutputPath() {
        return DEFAULT_OUTPUT;
    }

    /**
     * Appends one benchmark result to the default CSV file.
     *
     * @param result benchmark result to persist
     * @throws IOException if the file cannot be written
     */
    public static void append(
            BenchmarkResult result)
            throws IOException {

        append(
                DEFAULT_OUTPUT,
                result);
    }

    /**
     * Appends one benchmark result to the specified CSV file.
     *
     * The CSV header is written automatically if the file does
     * not exist or is empty.
     *
     * @param outputPath target CSV file
     * @param result benchmark result to persist
     * @throws IOException if the file cannot be written
     */
    public static void append(
            Path outputPath,
            BenchmarkResult result)
            throws IOException {

        if (outputPath == null) {
            throw new IllegalArgumentException(
                    "outputPath must not be null");
        }

        if (result == null) {
            throw new IllegalArgumentException(
                    "result must not be null");
        }

        Path absolutePath =
                outputPath.toAbsolutePath();

        Path parent =
                absolutePath.getParent();

        if (parent != null) {
            Files.createDirectories(parent);
        }

        boolean writeHeader =
                !Files.exists(absolutePath)
                        || Files.size(absolutePath) == 0L;

        try (BufferedWriter writer =
                     Files.newBufferedWriter(
                             absolutePath,
                             StandardCharsets.UTF_8,
                             StandardOpenOption.CREATE,
                             StandardOpenOption.WRITE,
                             StandardOpenOption.APPEND)) {

            if (writeHeader) {
                writer.write(CSV_HEADER);
                writer.newLine();
            }

            writer.write(
                    toCsvRow(result));

            writer.newLine();
        }
    }

    /**
     * Creates the CSV representation of one result.
     */
    public static String toCsvRow(
            BenchmarkResult result) {

        if (result == null) {
            throw new IllegalArgumentException(
                    "result must not be null");
        }

        return String.join(
                ",",
                csv(result.timestamp()),
                csv(result.benchmarkId()),
                Integer.toString(
                        result.dimension()),
                Long.toString(
                        result.nonZeroCount()),
                Integer.toString(
                        result.parallelism()),
                Integer.toString(
                        result.threshold()),
                Integer.toString(
                        result.warmupIterations()),
                Integer.toString(
                        result.measuredIterations()),
                format(result.sequentialMs()),
                format(result.parallelMs()),
                format(result.speedup()),
                format(
                        result.sequentialThroughput()),
                format(
                        result.parallelThroughput()),
                format(
                        result.sequentialExpectedError()),
                format(
                        result.parallelExpectedError()),
                format(
                        result.maxAbsoluteError()),
                format(
                        result.setupTimeMs()),
                csv(result.cpu()),
                Long.toString(
                        result.availableMemoryBytes()),
                csv(result.javaVersion()),
                csv(result.operatingSystem()),
                csv(result.notes()));
    }

    /**
     * Returns the CSV header.
     */
    public static String csvHeader() {
        return CSV_HEADER;
    }

    private static String format(
            double value) {

        return String.format(
                Locale.ROOT,
                "%.12e",
                value);
    }

    /**
     * Escapes a value according to RFC-style CSV rules.
     */
    private static String csv(
            String value) {

        if (value == null) {
            return "";
        }

        boolean requiresQuotes =
                value.indexOf(',') >= 0
                        || value.indexOf('"') >= 0
                        || value.indexOf('\n') >= 0
                        || value.indexOf('\r') >= 0;

        if (!requiresQuotes) {
            return value;
        }

        return "\""
                + value.replace(
                        "\"",
                        "\"\"")
                + "\"";
    }
}
