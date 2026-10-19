package hpc.csr;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Locale;

/**
 * Persists QFLPN CSR benchmark results in CSV format.
 *
 * Default output:
 * benchmarks/benchmark_results.csv
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
            Path.of("benchmarks", "benchmark_results.csv");

    private BenchmarkResultWriter() {
        // Utility class.
    }

    public static Path defaultOutputPath() {
        return DEFAULT_OUTPUT;
    }

    public static void append(BenchmarkResult result)
            throws IOException {

        append(DEFAULT_OUTPUT, result);
    }

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

        Path absolutePath = outputPath.toAbsolutePath();
        Path parent = absolutePath.getParent();

        if (parent != null) {
            Files.createDirectories(parent);
        }

        boolean writeHeader =
                !Files.exists(absolutePath)
                        || Files.size(absolutePath) == 0L;

        if (!writeHeader) {
            validateExistingCsv(absolutePath);
        }

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

            writer.write(toCsvRow(result));
            writer.newLine();
        }
    }

    /**
     * Validates the existing CSV before appending.
     *
     * The file must contain the exact expected header and
     * its final record must be terminated by CR or LF.
     */
    private static void validateExistingCsv(Path path)
            throws IOException {

        try (BufferedReader reader =
                     Files.newBufferedReader(
                             path,
                             StandardCharsets.UTF_8)) {

            String header = reader.readLine();

            if (!CSV_HEADER.equals(header)) {
                throw new IOException(
                        "Cannot append: invalid benchmark CSV header.");
            }
        }

        long size = Files.size(path);

        if (size == 0L) {
            throw new IOException(
                    "Cannot append: benchmark CSV is empty.");
        }

        try (SeekableByteChannel channel =
                     Files.newByteChannel(
                             path,
                             StandardOpenOption.READ)) {

            channel.position(size - 1L);

            ByteBuffer buffer = ByteBuffer.allocate(1);

            int bytesRead = channel.read(buffer);

            if (bytesRead != 1) {
                throw new IOException(
                        "Cannot inspect the final CSV byte.");
            }

            byte lastByte = buffer.array()[0];

            if (lastByte != '\n' && lastByte != '\r') {
                throw new IOException(
                        "Cannot append: existing CSV does not end "
                                + "with a record terminator.");
            }
        }
    }

    public static String toCsvRow(BenchmarkResult result) {

        if (result == null) {
            throw new IllegalArgumentException(
                    "result must not be null");
        }

        return String.join(
                ",",
                csv(result.timestamp()),
                csv(result.benchmarkId()),
                Integer.toString(result.dimension()),
                Long.toString(result.nonZeroCount()),
                Integer.toString(result.parallelism()),
                Integer.toString(result.threshold()),
                Integer.toString(result.warmupIterations()),
                Integer.toString(result.measuredIterations()),
                format(result.sequentialMs()),
                format(result.parallelMs()),
                format(result.speedup()),
                format(result.sequentialThroughput()),
                format(result.parallelThroughput()),
                format(result.sequentialExpectedError()),
                format(result.parallelExpectedError()),
                format(result.maxAbsoluteError()),
                format(result.setupTimeMs()),
                csv(result.cpu()),
                Long.toString(result.availableMemoryBytes()),
                csv(result.javaVersion()),
                csv(result.operatingSystem()),
                csv(result.notes()));
    }

    public static String csvHeader() {
        return CSV_HEADER;
    }

    private static String format(double value) {
        return String.format(
                Locale.ROOT,
                "%.12e",
                value);
    }

    /**
     * Escapes a value according to CSV rules.
     */
    private static String csv(String value) {

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
                + value.replace("\"", "\"\"")
                + "\"";
    }
}
