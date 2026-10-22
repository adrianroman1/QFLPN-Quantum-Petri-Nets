package hpc.csr;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Locale;

/**
 * Thread-safe and process-safe writer for qflpn-benchmark-v2 CSV files.
 */
public final class BenchmarkResultWriter {

    private static final String HEADER = String.join(",",
            "timestamp",
            "run_id",
            "benchmark_id",
            "dimension",
            "non_zero_count",
            "parallelism",
            "threshold",
            "warmup_iterations",
            "measured_iterations",
            "sequential_mean_ms",
            "sequential_median_ms",
            "sequential_stddev_ms",
            "parallel_mean_ms",
            "parallel_median_ms",
            "parallel_stddev_ms",
            "speedup",
            "sequential_throughput_states_per_s",
            "parallel_throughput_states_per_s",
            "sequential_expected_error",
            "parallel_expected_error",
            "max_absolute_error",
            "setup_time_ms",
            "cpu",
            "max_jvm_memory_bytes",
            "free_jvm_heap_bytes",
            "java_version",
            "operating_system",
            "notes");

    private BenchmarkResultWriter() {
    }

    public static String csvHeader() {
        return HEADER;
    }

    public static Path defaultOutputPath() {
        return Path.of("benchmarks", "benchmark_results_v2.csv");
    }

    public static void append(BenchmarkResult result) throws IOException {
        append(defaultOutputPath(), result);
    }

    public static void append(Path path, BenchmarkResult result)
            throws IOException {

        if (path == null || result == null) {
            throw new IllegalArgumentException(
                    "path and result must not be null");
        }

        Path absolute = path.toAbsolutePath();
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
                throw new IOException("Unable to lock benchmark CSV");
            }

            long size = channel.size();
            boolean fresh = size == 0L;

            if (fresh) {
                writeFully(channel, ByteBuffer.wrap(
                        (HEADER + "\n").getBytes(StandardCharsets.UTF_8)));
            } else {
                validateExistingFile(channel, size);
            }

            byte[] row = (toCsvRow(result) + "\n")
                    .getBytes(StandardCharsets.UTF_8);

            channel.position(channel.size());
            writeFully(channel, ByteBuffer.wrap(row));
            channel.force(true);
        }
    }

    public static String toCsvRow(BenchmarkResult r) {
        if (r == null) {
            throw new IllegalArgumentException(
                    "result must not be null");
        }

        return String.join(",",
                q(r.timestamp()),
                q(r.runId()),
                q(r.benchmarkId()),
                Integer.toString(r.dimension()),
                Long.toString(r.nonZeroCount()),
                Integer.toString(r.parallelism()),
                Integer.toString(r.threshold()),
                Integer.toString(r.warmupIterations()),
                Integer.toString(r.measuredIterations()),
                f(r.sequentialMs()),
                f(r.sequentialMedianMs()),
                f(r.sequentialStdDevMs()),
                f(r.parallelMs()),
                f(r.parallelMedianMs()),
                f(r.parallelStdDevMs()),
                f(r.speedup()),
                f(r.sequentialThroughput()),
                f(r.parallelThroughput()),
                f(r.sequentialExpectedError()),
                f(r.parallelExpectedError()),
                f(r.maxAbsoluteError()),
                f(r.setupTimeMs()),
                q(r.cpu()),
                Long.toString(r.maxJvmMemoryBytes()),
                Long.toString(r.freeJvmHeapBytes()),
                q(r.javaVersion()),
                q(r.operatingSystem()),
                q(r.notes()));
    }

    private static void validateExistingFile(
            FileChannel channel,
            long size) throws IOException {

        if (size > Integer.MAX_VALUE) {
            throw new IOException(
                    "CSV file is too large for safe header validation");
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

        String content =
                StandardCharsets.UTF_8.decode(buffer).toString();

        int newline = content.indexOf('\n');

        if (newline < 0) {
            throw new IOException(
                    "Existing CSV has no complete header");
        }

        String firstLine = content.substring(0, newline);

        if (firstLine.endsWith("\r")) {
            firstLine = firstLine.substring(0, firstLine.length() - 1);
        }

        if (!HEADER.equals(firstLine)) {
            throw new IOException(
                    "V2 CSV header mismatch; refusing to append");
        }

        char last = content.charAt(content.length() - 1);

        if (last != '\n' && last != '\r') {
            throw new IOException(
                    "V2 CSV has an incomplete final record");
        }
    }

    private static void writeFully(
            FileChannel channel,
            ByteBuffer buffer) throws IOException {

        while (buffer.hasRemaining()) {
            channel.write(buffer);
        }
    }

    private static String f(double value) {
        if (!Double.isFinite(value)) {
            throw new IllegalArgumentException(
                    "CSV numeric values must be finite");
        }

        return String.format(Locale.ROOT, "%.12e", value);
    }

    private static String q(String value) {
        if (value == null) {
            throw new IllegalArgumentException(
                    "CSV text values must not be null");
        }

        boolean needsQuotes =
                value.indexOf(',') >= 0
                || value.indexOf('"') >= 0
                || value.indexOf('\n') >= 0
                || value.indexOf('\r') >= 0;

        if (!needsQuotes) {
            return value;
        }

        return "\"" + value.replace("\"", "\"\"") + "\"";
    }
}
