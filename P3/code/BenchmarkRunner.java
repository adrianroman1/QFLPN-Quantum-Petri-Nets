package hpc.csr;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ForkJoinPool;

/**
 * Reproducible CSR sparse matrix-vector benchmark.
 *
 * Includes warm-up, alternating measurement order, descriptive statistics,
 * an independent analytical oracle and versioned result persistence.
 */
public final class BenchmarkRunner {

    private static final int DEFAULT_N = 1_000_000;
    private static final int DEFAULT_WARMUP = 5;
    private static final int DEFAULT_ITERATIONS = 10;
    private static final int DEFAULT_THRESHOLD = 4096;

    private static final double EPSILON = 1.0e-12;

    private BenchmarkRunner() {
    }

    public static void main(String[] args) {
        Config config = Config.parse(args);
        String runId = createRunId();

        long setupStart = System.nanoTime();

        SparseMatrixCSR matrix = createMatrix(config.n());

        double[] input = new double[config.n()];
        double[] sequentialOutput = new double[config.n()];
        double[] parallelOutput = new double[config.n()];
        double[] oracle = new double[config.n()];

        Arrays.fill(input, 1.0);
        Arrays.fill(oracle, 1.5);

        double setupMs = milliseconds(
                System.nanoTime() - setupStart);

        ForkJoinPool pool =
                new ForkJoinPool(config.parallelism());

        try {
            executeBenchmark(
                    matrix,
                    input,
                    sequentialOutput,
                    parallelOutput,
                    oracle,
                    config,
                    pool,
                    runId,
                    setupMs);
        } finally {
            pool.shutdown();
        }
    }

    private static void executeBenchmark(
            SparseMatrixCSR matrix,
            double[] input,
            double[] sequentialOutput,
            double[] parallelOutput,
            double[] oracle,
            Config config,
            ForkJoinPool pool,
            String runId,
            double setupMs) {

        // Warm-up is deliberately excluded from measured samples.
        for (int i = 0; i < config.warmup(); i++) {
            matrix.multiplyInto(input, sequentialOutput);
            matrix.multiplyParallelInto(
                    input,
                    parallelOutput,
                    config.threshold(),
                    pool);
        }

        double[] sequentialTimes =
                new double[config.iterations()];
        double[] parallelTimes =
                new double[config.iterations()];

        // Alternate order to reduce systematic order bias.
        for (int i = 0; i < config.iterations(); i++) {
            long start;

            if ((i & 1) == 0) {
                start = System.nanoTime();
                matrix.multiplyInto(input, sequentialOutput);
                sequentialTimes[i] =
                        milliseconds(System.nanoTime() - start);

                start = System.nanoTime();
                matrix.multiplyParallelInto(
                        input,
                        parallelOutput,
                        config.threshold(),
                        pool);
                parallelTimes[i] =
                        milliseconds(System.nanoTime() - start);
            } else {
                start = System.nanoTime();
                matrix.multiplyParallelInto(
                        input,
                        parallelOutput,
                        config.threshold(),
                        pool);
                parallelTimes[i] =
                        milliseconds(System.nanoTime() - start);

                start = System.nanoTime();
                matrix.multiplyInto(input, sequentialOutput);
                sequentialTimes[i] =
                        milliseconds(System.nanoTime() - start);
            }
        }

        double sequentialMean = mean(sequentialTimes);
        double parallelMean = mean(parallelTimes);

        double sequentialMedian = median(sequentialTimes);
        double parallelMedian = median(parallelTimes);

        double sequentialStdDev =
                populationStdDev(sequentialTimes);
        double parallelStdDev =
                populationStdDev(parallelTimes);

        // Compare each implementation with the independent analytical oracle.
        double sequentialError =
                maxAbsoluteError(sequentialOutput, oracle);
        double parallelError =
                maxAbsoluteError(parallelOutput, oracle);
        double difference =
                maxAbsoluteError(sequentialOutput, parallelOutput);

        if (sequentialError > EPSILON
                || parallelError > EPSILON
                || difference > EPSILON) {
            throw new IllegalStateException(
                    "Independent numerical validation failed: "
                            + "sequential=" + sequentialError
                            + ", parallel=" + parallelError
                            + ", difference=" + difference);
        }

        Runtime runtime = Runtime.getRuntime();

        double speedup = sequentialMean / parallelMean;

        double sequentialThroughput =
                config.n() / (sequentialMean / 1000.0);

        double parallelThroughput =
                config.n() / (parallelMean / 1000.0);

        BenchmarkResult result = new BenchmarkResult(
                Instant.now().toString(),
                runId,
                benchmarkId(config.n()),
                config.n(),
                matrix.getNnz(),
                config.parallelism(),
                config.threshold(),
                config.warmup(),
                config.iterations(),
                sequentialMean,
                sequentialMedian,
                sequentialStdDev,
                parallelMean,
                parallelMedian,
                parallelStdDev,
                speedup,
                sequentialThroughput,
                parallelThroughput,
                sequentialError,
                parallelError,
                difference,
                setupMs,
                System.getProperty("os.arch", "unknown")
                        + "; processors="
                        + runtime.availableProcessors(),
                runtime.maxMemory(),
                runtime.freeMemory(),
                System.getProperty("java.version", "unknown"),
                System.getProperty("os.name", "unknown")
                        + " "
                        + System.getProperty("os.version", "unknown"),
                "V2; population standard deviation; "
                        + "independent analytical oracle y[i]=1.5; "
                        + "alternating measurement order");

        try {
            BenchmarkResultWriter.append(result);
            writeReports(
                    result,
                    Path.of("results", "raw", runId));
        } catch (IOException exception) {
            throw new IllegalStateException(
                    "Unable to persist benchmark evidence",
                    exception);
        }

        print(result);
    }

    static double mean(double[] samples) {
        validateSamples(samples);

        double sum = 0.0;

        for (double sample : samples) {
            requirePositiveFinite(sample);
            sum += sample;
        }

        double result = sum / samples.length;

        if (!Double.isFinite(result) || result <= 0.0) {
            throw new IllegalArgumentException(
                    "Invalid arithmetic mean");
        }

        return result;
    }

    static double median(double[] samples) {
        validateSamples(samples);

        double[] sorted = samples.clone();

        for (double sample : sorted) {
            requirePositiveFinite(sample);
        }

        Arrays.sort(sorted);

        int middle = sorted.length / 2;

        if ((sorted.length & 1) == 0) {
            return (sorted[middle - 1] + sorted[middle]) / 2.0;
        }

        return sorted[middle];
    }

    static double populationStdDev(double[] samples) {
        double average = mean(samples);
        double sumSquares = 0.0;

        for (double sample : samples) {
            double difference = sample - average;
            sumSquares += difference * difference;
        }

        double result = Math.sqrt(sumSquares / samples.length);

        if (!Double.isFinite(result)) {
            throw new IllegalArgumentException(
                    "Standard deviation is not finite");
        }

        return result;
    }

    static double maxAbsoluteError(
            double[] first,
            double[] second) {

        if (first == null || second == null) {
            throw new IllegalArgumentException(
                    "Vectors must not be null");
        }

        if (first.length != second.length) {
            throw new IllegalArgumentException(
                    "Vectors must have equal lengths");
        }

        double maximum = 0.0;

        for (int i = 0; i < first.length; i++) {
            if (!Double.isFinite(first[i])
                    || !Double.isFinite(second[i])) {
                throw new IllegalStateException(
                        "Non-finite vector value at index " + i);
            }

            double error = Math.abs(first[i] - second[i]);

            if (!Double.isFinite(error)) {
                throw new IllegalStateException(
                        "Non-finite absolute error at index " + i);
            }

            maximum = Math.max(maximum, error);
        }

        return maximum;
    }

    /**
     * Returns the maximum absolute deviation of the output vector
     * from a scalar analytical reference value.
     *
     * @param values output vector to validate
     * @param expected expected value for every vector element
     * @return maximum absolute error
     * @throws IllegalArgumentException if the vector is null
     * @throws IllegalStateException if the expected value, an output
     *         value, or a computed error is non-finite
     */
    static double maxExpectedError(double[] values, double expected) {
        if (values == null) {
            throw new IllegalArgumentException(
                    "Values must not be null.");
        }

        if (!Double.isFinite(expected)) {
            throw new IllegalStateException(
                    "Expected value must be finite.");
        }

        double maximum = 0.0;
        for (int i = 0; i < values.length; i++) {
            if (!Double.isFinite(values[i])) {
                throw new IllegalStateException(
                        "Non-finite output at index " + i);
            }

            double error = Math.abs(values[i] - expected);
            if (!Double.isFinite(error)) {
                throw new IllegalStateException(
                        "Non-finite error at index " + i);
            }
            maximum = Math.max(maximum, error);
        }
        return maximum;
    }

    private static void validateSamples(double[] samples) {
        if (samples == null || samples.length == 0) {
            throw new IllegalArgumentException(
                    "At least one measurement is required");
        }
    }

    private static void requirePositiveFinite(double value) {
        if (!Double.isFinite(value) || value <= 0.0) {
            throw new IllegalArgumentException(
                    "Measurements must be finite and positive");
        }
    }

    private static double milliseconds(long nanoseconds) {
        return nanoseconds / 1_000_000.0;
    }

    private static String createRunId() {
        String supplied = System.getenv("RUN_ID");
        String runId = supplied;

        if (runId == null || runId.isBlank()) {
            runId = DateTimeFormatter
                    .ofPattern("yyyyMMdd'T'HHmmss'Z'")
                    .withZone(ZoneOffset.UTC)
                    .format(Instant.now())
                    + "-" + UUID.randomUUID();
        }

        if (!runId.matches("[A-Za-z0-9._-]+")) {
            throw new IllegalArgumentException(
                    "RUN_ID contains unsupported characters");
        }

        return runId;
    }

    private static String benchmarkId(int n) {
        if (n == 12) {
            return "QFLPN-12";
        }
        if (n == 1_000_000) {
            return "QFLPN-1M";
        }
        if (n == 30_000_000) {
            return "QFLPN-30M";
        }
        return "QFLPN-" + n;
    }

    private static SparseMatrixCSR createMatrix(int n) {
        if (n <= 0) {
            throw new IllegalArgumentException(
                    "Matrix dimension must be positive");
        }

        long nonzeroCount = 2L * n;

        if (nonzeroCount > Integer.MAX_VALUE
                || n == Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "Matrix exceeds Java array index limits");
        }

        double[] values = new double[(int) nonzeroCount];
        int[] columns = new int[(int) nonzeroCount];
        int[] rowPointers = new int[n + 1];

        for (int row = 0; row < n; row++) {
            int index = 2 * row;

            values[index] = 1.0;
            values[index + 1] = 0.5;

            columns[index] = row;
            columns[index + 1] =
                    row + 1 < n ? row + 1 : 0;

            rowPointers[row + 1] = index + 2;
        }

        return new SparseMatrixCSR(
                values,
                columns,
                rowPointers,
                n,
                n);
    }

    private static void writeReports(
            BenchmarkResult r,
            Path directory) throws IOException {

        Files.createDirectories(directory);

        String json = """
                {
                  "schema": "qflpn-benchmark-v2",
                  "validation": "PASS",
                  "run_id": "%s",
                  "timestamp": "%s",
                  "dimension": %d,
                  "nnz": %d,
                  "warmup": %d,
                  "iterations": %d,
                  "sequential_mean_ms": %.12e,
                  "sequential_median_ms": %.12e,
                  "sequential_stddev_ms": %.12e,
                  "parallel_mean_ms": %.12e,
                  "parallel_median_ms": %.12e,
                  "parallel_stddev_ms": %.12e,
                  "speedup": %.12e,
                  "sequential_throughput_states_per_s": %.12e,
                  "parallel_throughput_states_per_s": %.12e,
                  "sequential_oracle_error": %.12e,
                  "parallel_oracle_error": %.12e,
                  "max_absolute_error": %.12e
                }
                """.formatted(
                jsonEscape(r.runId()),
                jsonEscape(r.timestamp()),
                r.dimension(),
                r.nonZeroCount(),
                r.warmupIterations(),
                r.measuredIterations(),
                r.sequentialMs(),
                r.sequentialMedianMs(),
                r.sequentialStdDevMs(),
                r.parallelMs(),
                r.parallelMedianMs(),
                r.parallelStdDevMs(),
                r.speedup(),
                r.sequentialThroughput(),
                r.parallelThroughput(),
                r.sequentialExpectedError(),
                r.parallelExpectedError(),
                r.maxAbsoluteError());

        String text = """
                QFLPN P3 BENCHMARK V2
                RUN_ID=%s
                VALIDATION=PASS
                DIMENSION=%d
                NNZ=%d
                WARMUP=%d
                ITERATIONS=%d
                SEQUENTIAL_MEAN_MS=%.12e
                SEQUENTIAL_MEDIAN_MS=%.12e
                SEQUENTIAL_STDDEV_MS=%.12e
                PARALLEL_MEAN_MS=%.12e
                PARALLEL_MEDIAN_MS=%.12e
                PARALLEL_STDDEV_MS=%.12e
                SPEEDUP=%.12e
                SEQUENTIAL_ORACLE_ERROR=%.12e
                PARALLEL_ORACLE_ERROR=%.12e
                MAX_ABSOLUTE_ERROR=%.12e
                """.formatted(
                r.runId(),
                r.dimension(),
                r.nonZeroCount(),
                r.warmupIterations(),
                r.measuredIterations(),
                r.sequentialMs(),
                r.sequentialMedianMs(),
                r.sequentialStdDevMs(),
                r.parallelMs(),
                r.parallelMedianMs(),
                r.parallelStdDevMs(),
                r.speedup(),
                r.sequentialExpectedError(),
                r.parallelExpectedError(),
                r.maxAbsoluteError());

        Files.writeString(
                directory.resolve("benchmark-report.json"),
                json,
                StandardCharsets.UTF_8);

        Files.writeString(
                directory.resolve("benchmark-report.txt"),
                text,
                StandardCharsets.UTF_8);
    }

    private static String jsonEscape(String value) {
        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private static void print(BenchmarkResult r) {
        System.out.printf(
                Locale.ROOT,
                """
                RUN_ID=%s
                VALIDATION=PASS
                Sequential mean/median/stddev: %.6f / %.6f / %.6f ms
                Parallel mean/median/stddev: %.6f / %.6f / %.6f ms
                Speedup: %.6f
                Sequential oracle error: %.3e
                Parallel oracle error: %.3e
                CSV: %s
                """,
                r.runId(),
                r.sequentialMs(),
                r.sequentialMedianMs(),
                r.sequentialStdDevMs(),
                r.parallelMs(),
                r.parallelMedianMs(),
                r.parallelStdDevMs(),
                r.speedup(),
                r.sequentialExpectedError(),
                r.parallelExpectedError(),
                BenchmarkResultWriter.defaultOutputPath());
    }

    private record Config(
            int n,
            int warmup,
            int iterations,
            int threshold,
            int parallelism) {

        private static Config parse(String[] args) {
            int n = DEFAULT_N;
            int warmup = DEFAULT_WARMUP;
            int iterations = DEFAULT_ITERATIONS;
            int threshold = DEFAULT_THRESHOLD;
            int parallelism = Math.max(
                    1,
                    Runtime.getRuntime().availableProcessors());

            for (String argument : args) {
                if (argument.startsWith("--n=")) {
                    n = parseValue(argument, true);
                } else if (argument.startsWith("--warmup=")) {
                    warmup = parseValue(argument, false);
                } else if (argument.startsWith("--iterations=")) {
                    iterations = parseValue(argument, true);
                } else if (argument.startsWith("--threshold=")) {
                    threshold = parseValue(argument, true);
                } else if (argument.startsWith("--parallelism=")) {
                    parallelism = parseValue(argument, true);
                } else {
                    throw new IllegalArgumentException(
                            "Unknown argument: " + argument);
                }
            }

            return new Config(
                    n,
                    warmup,
                    iterations,
                    threshold,
                    parallelism);
        }

        private static int parseValue(
                String argument,
                boolean strictlyPositive) {

            int separator = argument.indexOf('=');
            int value = Integer.parseInt(
                    argument.substring(separator + 1));

            if (strictlyPositive ? value <= 0 : value < 0) {
                throw new IllegalArgumentException(
                        "Invalid argument value: " + argument);
            }

            return value;
        }
    }
}
