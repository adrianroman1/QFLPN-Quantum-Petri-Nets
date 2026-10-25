package hpc.csr;

import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Objects;

/**
 * Independent CSV writer for QFLPN Benchmark V3.
 * Does not read, append to, or modify the V2 result file.
 */
public final class BenchmarkV3ResultWriter {

    public static final String[] HEADER = {
        "timestamp", "run_id", "workflow_run_id", "commit_sha",
        "benchmark_id", "workload_id", "matrix_family", "distribution",
        "dimension", "non_zero_count", "nnz_min_per_row",
        "nnz_avg_per_row", "nnz_max_per_row", "parallelism",
        "threshold_rows", "parallel_strategy", "split_policy",
        "warmup_iterations", "measured_iterations",
        "sequential_mean_ms", "sequential_median_ms",
        "sequential_stddev_ms", "sequential_min_ms",
        "sequential_max_ms", "parallel_mean_ms", "parallel_median_ms",
        "parallel_stddev_ms", "parallel_min_ms", "parallel_max_ms",
        "speedup", "sequential_rows_per_second",
        "parallel_rows_per_second", "sequential_nnz_per_second",
        "parallel_nnz_per_second", "sequential_expected_error",
        "parallel_expected_error", "max_absolute_error",
        "setup_time_ms", "cpu", "max_jvm_memory_bytes",
        "free_jvm_heap_bytes", "java_version", "operating_system",
        "status", "verdict", "notes"
    };

    private BenchmarkV3ResultWriter() {
    }

    public static Path defaultOutputPath() {
        return Path.of("P3", "benchmarks", "benchmark_results_v3.csv");
    }

    public static String headerLine() {
        return String.join(",", HEADER);
    }

    public static void append(String[] fields) throws IOException {
        append(defaultOutputPath(), fields);
    }

    public static void append(Path path, String[] fields)
            throws IOException {

        Objects.requireNonNull(path, "path must not be null");
        Objects.requireNonNull(fields, "fields must not be null");

        if (fields.length != HEADER.length) {
            throw new IllegalArgumentException(
                    "V3 row must contain exactly " + HEADER.length
                            + " fields; got " + fields.length);
        }

        for (int i = 0; i < fields.length; i++) {
            if (fields[i] == null) {
                throw new IllegalArgumentException(
                        "V3 field must not be null: " + HEADER[i]);
            }
        }

        Path absolute = path.toAbsolutePath().normalize();
        Path parent = absolute.getParent();

        if (parent != null) {
            Files.createDirectories(parent);
        }

        try (FileChannel channel = FileChannel.open(
                absolute,
                StandardOpenOption.CREATE,
                StandardOpenOption.READ,
                StandardOpenOption.WRITE);
             FileLock lock = channel.lock()) {

            if (!lock.isValid()) {
                throw new IOException("Unable to lock V3 CSV");
            }

            long size = channel.size();

            if (size == 0L) {
                writeFully(channel, ByteBuffer.wrap(
                        (headerLine() + "\n")
                                .getBytes(StandardCharsets.UTF_8)));
            } else {
                validateExistingHeader(channel, size);
            }

            String row = encode(fields) + "\n";
            channel.position(channel.size());
            writeFully(channel, ByteBuffer.wrap(
                    row.getBytes(StandardCharsets.UTF_8)));
            channel.force(true);
        }
    }

    private static void validateExistingHeader(
            FileChannel channel,
            long size) throws IOException {

        if (size > Integer.MAX_VALUE) {
            throw new IOException("V3 CSV is too large for header validation");
        }

        ByteBuffer buffer = ByteBuffer.allocate((int) size);
        channel.position(0);

        while (buffer.hasRemaining()) {
            int count = channel.read(buffer);
            if (count < 0) {
                break;
            }
        }

        buffer.flip();

        String content = StandardCharsets.UTF_8.decode(buffer).toString();
        if (content.isBlank()) {
            throw new IOException("Existing V3 CSV is blank");
        }

        String normalized = content.replace("\r\n", "\n")
                .replace('\r', '\n');

        int newline = normalized.indexOf('\n');
        if (newline < 0) {
            throw new IOException("Existing V3 CSV has no complete header");
        }

        String actualHeader = normalized.substring(0, newline);
        if (!headerLine().equals(actualHeader)) {
            throw new IOException(
                    "V3 CSV header mismatch; refusing to append");
        }

        if (normalized.length() == newline + 1) {
            throw new IOException(
                    "Existing V3 CSV contains a header but no data rows");
        }

        if (!normalized.endsWith("\n")) {
            throw new IOException(
                    "Existing V3 CSV has an incomplete final record");
        }
    }

    static String encode(String[] fields) {
        StringBuilder result = new StringBuilder();

        for (int i = 0; i < fields.length; i++) {
            if (i > 0) {
                result.append(',');
            }

            String value = fields[i];
            boolean quote = value.indexOf(',') >= 0
                    || value.indexOf('"') >= 0
                    || value.indexOf('\n') >= 0
                    || value.indexOf('\r') >= 0;

            if (quote) {
                result.append('"')
                        .append(value.replace("\"", "\"\""))
                        .append('"');
            } else {
                result.append(value);
            }
        }

        return result.toString();
    }

    private static void writeFully(
            FileChannel channel,
            ByteBuffer buffer) throws IOException {

        while (buffer.hasRemaining()) {
            channel.write(buffer);
        }
    }
}
