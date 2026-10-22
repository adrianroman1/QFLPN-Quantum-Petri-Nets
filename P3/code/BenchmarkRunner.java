package hpc.csr;

import java.io.IOException;
import java.time.Instant;
import java.util.Locale;
import java.util.concurrent.ForkJoinPool;

/**
 * Reproducible CSR matrix-vector benchmark.
 *
 * Sequential and parallel measurements are alternated to reduce
 * systematic order bias. The same ForkJoinPool is reused throughout
 * the parallel measurements.
 */
public final class BenchmarkRunner {

    private static final int DEFAULT_N = 1_000_000;
    private static final int DEFAULT_WARMUP = 3;
    private static final int DEFAULT_ITERATIONS = 10;
    private static final int DEFAULT_THRESHOLD = 4096;

    private BenchmarkRunner() {
    }

    public static void main(String[] args) {
        BenchmarkConfig config = BenchmarkConfig.fromArgs(args);
        printConfiguration(config);

        long setupStart = System.nanoTime();

        SparseMatrixCSR matrix = createBenchmarkMatrix(config.n());
        double[] input = createInputVector(config.n());
        double[] sequentialOutput = new double[config.n()];
        double[] parallelOutput = new double[config.n()];

        double setupTimeMs = nanosToMillis(
                System.nanoTime() - setupStart);

        Runtime runtime = Runtime.getRuntime();
        long maxJvmMemoryBytes = runtime.maxMemory();

        ForkJoinPool pool = new ForkJoinPool(config.parallelism());

        try {
            warmup(
                    matrix, input, sequentialOutput, parallelOutput,
                    config, pool);

            Measurement measurement = measureAlternating(
                    matrix, input, sequentialOutput, parallelOutput,
                    config, pool);

            double sequentialAverageMs =
                    nanosToMillis(measurement.sequentialTotalNs()
                            / config.iterations());

            double parallelAverageMs =
                    nanosToMillis(measurement.parallelTotalNs()
                            / config.iterations());

            if (sequentialAverageMs <= 0.0 || parallelAverageMs <= 0.0) {
                throw new IllegalStateException(
                        "Measured duration is zero; benchmark result rejected.");
            }

            double speedup = sequentialAverageMs / parallelAverageMs;
            double sequentialThroughput =
                    config.n() / (sequentialAverageMs / 1000.0);
            double parallelThroughput =
                    config.n() / (parallelAverageMs / 1000.0);

            double maxAbsoluteError =
                    maxAbsoluteError(sequentialOutput, parallelOutput);
            double sequentialExpectedError =
                    maxExpectedError(sequentialOutput, 1.5);
            double parallelExpectedError =
                    maxExpectedError(parallelOutput, 1.5);

            boolean valid =
                    maxAbsoluteError <= 1.0e-12
                    && sequentialExpectedError <= 1.0e-12
                    && parallelExpectedError <= 1.0e-12;

            printResults(
                    matrix, config, setupTimeMs,
                    sequentialAverageMs, parallelAverageMs,
                    speedup, sequentialThroughput, parallelThroughput,
                    maxAbsoluteError, sequentialExpectedError,
                    parallelExpectedError, valid);

            if (!valid) {
                throw new IllegalStateException(
                        "Numerical validation failed; result not persisted.");
            }

            // Capture free heap after measurements and before persistence.
            long freeJvmHeapBytes = runtime.freeMemory();

            BenchmarkResult result = new BenchmarkResult(
                    Instant.now().toString(),
                    benchmarkId(config.n()),
                    config.n(),
                    matrix.getNnz(),
                    config.parallelism(),
                    config.threshold(),
                    config.warmup(),
                    config.iterations(),
                    sequentialAverageMs,
                    parallelAverageMs,
                    speedup,
                    sequentialThroughput,
                    parallelThroughput,
                    sequentialExpectedError,
                    parallelExpectedError,
                    maxAbsoluteError,
                    setupTimeMs,
                    System.getProperty("os.arch", "unknown")
                            + "; processors=" + runtime.availableProcessors(),
                    maxJvmMemoryBytes,
                    freeJvmHeapBytes,
                    System.getProperty("java.version", "unknown"),
                    System.getProperty("os.name", "unknown")
                            + " " + System.getProperty("os.version", "unknown"),
                    "Alternating sequential/parallel measurements; "
                            + "freeJvmHeapBytes is free heap at capture time.");

            try {
                BenchmarkResultWriter.append(result);
                System.out.println("Result persisted to: "
                        + BenchmarkResultWriter.defaultOutputPath());
            } catch (IOException exception) {
                throw new IllegalStateException(
                        "Unable to persist benchmark result.", exception);
            }
        } finally {
            pool.shutdown();
        }
    }

    private static void warmup(
            SparseMatrixCSR matrix,
            double[] input,
            double[] sequentialOutput,
            double[] parallelOutput,
            BenchmarkConfig config,
            ForkJoinPool pool) {

        for (int i = 0; i < config.warmup(); i++) {
            if ((i & 1) == 0) {
                matrix.multiplyInto(input, sequentialOutput);
                matrix.multiplyParallelInto(
                        input, parallelOutput, config.threshold(), pool);
            } else {
                matrix.multiplyParallelInto(
                        input, parallelOutput, config.threshold(), pool);
                matrix.multiplyInto(input, sequentialOutput);
            }
        }
    }

    private static Measurement measureAlternating(
            SparseMatrixCSR matrix,
            double[] input,
            double[] sequentialOutput,
            double[] parallelOutput,
            BenchmarkConfig config,
            ForkJoinPool pool) {

        long sequentialTotal = 0L;
        long parallelTotal = 0L;

        for (int i = 0; i < config.iterations(); i++) {
            long start;
            long elapsed;

            if ((i & 1) == 0) {
                start = System.nanoTime();
                matrix.multiplyInto(input, sequentialOutput);
                elapsed = System.nanoTime() - start;
                sequentialTotal = Math.addExact(sequentialTotal, elapsed);

                start = System.nanoTime();
                matrix.multiplyParallelInto(
                        input, parallelOutput, config.threshold(), pool);
                elapsed = System.nanoTime() - start;
                parallelTotal = Math.addExact(parallelTotal, elapsed);
            } else {
                start = System.nanoTime();
                matrix.multiplyParallelInto(
                        input, parallelOutput, config.threshold(), pool);
                elapsed = System.nanoTime() - start;
                parallelTotal = Math.addExact(parallelTotal, elapsed);

                start = System.nanoTime();
                matrix.multiplyInto(input, sequentialOutput);
                elapsed = System.nanoTime() - start;
                sequentialTotal = Math.addExact(sequentialTotal, elapsed);
            }

            if (elapsed <= 0L) {
                throw new IllegalStateException(
                        "Non-positive measurement duration.");
            }
        }

        if (sequentialTotal <= 0L || parallelTotal <= 0L) {
            throw new IllegalStateException(
                    "Invalid aggregate benchmark duration.");
        }

        return new Measurement(sequentialTotal, parallelTotal);
    }

    private static SparseMatrixCSR createBenchmarkMatrix(int n) {
        if (n <= 0) {
            throw new IllegalArgumentException("N must be positive.");
        }

        long nnzLong = 2L * n;
        if (nnzLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "NNZ exceeds Java array limits: " + nnzLong);
        }

        int nnz = (int) nnzLong;
        double[] values = new double[nnz];
        int[] columns = new int[nnz];
        int[] rowPointers = new int[n + 1];

        for (int row = 0; row < n; row++) {
            int base = 2 * row;
            values[base] = 1.0;
            values[base + 1] = 0.5;
            columns[base] = row;
            columns[base + 1] = (row + 1 < n) ? row + 1 : 0;
            rowPointers[row + 1] = base + 2;
        }

        return new SparseMatrixCSR(
                values, columns, rowPointers, n, n);
    }

    private static double[] createInputVector(int n) {
        double[] input = new double[n];
        java.util.Arrays.fill(input, 1.0);
        return input;
    }

    static double maxAbsoluteError(double[] first, double[] second) {
        if (first == null || second == null
                || first.length != second.length) {
            throw new IllegalArgumentException(
                    "Vectors must be non-null and have equal lengths.");
        }

        double maximum = 0.0;
        for (int i = 0; i < first.length; i++) {
            if (!Double.isFinite(first[i])
                    || !Double.isFinite(second[i])) {
                throw new IllegalStateException(
                        "Non-finite output at index " + i);
            }

            double error = Math.abs(first[i] - second[i]);
            if (!Double.isFinite(error)) {
                throw new IllegalStateException(
                        "Non-finite error at index " + i);
            }
            maximum = Math.max(maximum, error);
        }
        return maximum;
    }

    static double maxExpectedError(double[] values, double expected) {
        if (values == null || !Double.isFinite(expected)) {
            throw new IllegalArgumentException(
                    "Values must be non-null and expected must be finite.");
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

    private static String benchmarkId(int n) {
        if (n == 12) return "QFLPN-12";
        if (n == 1_000_000) return "QFLPN-1M";
        if (n == 30_000_000) return "QFLPN-30M";
        return "QFLPN-" + n;
    }

    private static double nanosToMillis(long nanos) {
        return nanos / 1_000_000.0;
    }

    private static void printConfiguration(BenchmarkConfig config) {
        System.out.println("========================================");
        System.out.println(" QFLPN CSR BENCHMARK");
        System.out.println("========================================");
        System.out.printf(Locale.ROOT, "N            : %,d%n", config.n());
        System.out.printf(Locale.ROOT, "Warmup       : %d%n", config.warmup());
        System.out.printf(Locale.ROOT, "Iterations   : %d%n", config.iterations());
        System.out.printf(Locale.ROOT, "Threshold    : %d%n", config.threshold());
        System.out.printf(Locale.ROOT, "Parallelism  : %d%n", config.parallelism());
        System.out.printf(Locale.ROOT, "Processors   : %d%n",
                Runtime.getRuntime().availableProcessors());
    }

    private static void printResults(
            SparseMatrixCSR matrix,
            BenchmarkConfig config,
            double setupMs,
            double sequentialMs,
            double parallelMs,
            double speedup,
            double sequentialThroughput,
            double parallelThroughput,
            double maxError,
            double sequentialExpectedError,
            double parallelExpectedError,
            boolean valid) {

        System.out.println();
        System.out.println("Benchmark results");
        System.out.printf(Locale.ROOT, "Dimension             : %,d%n", config.n());
        System.out.printf(Locale.ROOT, "Non-zero values       : %,d%n", matrix.getNnz());
        System.out.printf(Locale.ROOT, "Setup                 : %.6f ms%n", setupMs);
        System.out.printf(Locale.ROOT, "Sequential average    : %.6f ms%n", sequentialMs);
        System.out.printf(Locale.ROOT, "Parallel average      : %.6f ms%n", parallelMs);
        System.out.printf(Locale.ROOT, "Speedup               : %.6f%n", speedup);
        System.out.printf(Locale.ROOT, "Sequential throughput : %.3f states/s%n",
                sequentialThroughput);
        System.out.printf(Locale.ROOT, "Parallel throughput   : %.3f states/s%n",
                parallelThroughput);
        System.out.printf(Locale.ROOT, "Max absolute error    : %.12e%n", maxError);
        System.out.printf(Locale.ROOT, "Sequential expected error: %.12e%n",
                sequentialExpectedError);
        System.out.printf(Locale.ROOT, "Parallel expected error  : %.12e%n",
                parallelExpectedError);
        System.out.println("Numerical validation  : " + (valid ? "PASS" : "FAIL"));
    }

    private record Measurement(
            long sequentialTotalNs,
            long parallelTotalNs) {
    }

    private record BenchmarkConfig(
            int n,
            int warmup,
            int iterations,
            int threshold,
            int parallelism) {

        private static BenchmarkConfig fromArgs(String[] args) {
            int n = DEFAULT_N;
            int warmup = DEFAULT_WARMUP;
            int iterations = DEFAULT_ITERATIONS;
            int threshold = DEFAULT_THRESHOLD;
            int parallelism = Math.max(
                    1, Runtime.getRuntime().availableProcessors());

            for (String arg : args) {
                if (arg.startsWith("--n=")) {
                    n = parse(arg, "--n=", false);
                } else if (arg.startsWith("--warmup=")) {
                    warmup = parse(arg, "--warmup=", true);
                } else if (arg.startsWith("--iterations=")) {
                    iterations = parse(arg, "--iterations=", false);
                } else if (arg.startsWith("--threshold=")) {
                    threshold = parse(arg, "--threshold=", false);
                } else if (arg.startsWith("--parallelism=")) {
                    parallelism = parse(arg, "--parallelism=", false);
                } else {
                    throw new IllegalArgumentException(
                            "Unknown argument: " + arg);
                }
            }

            return new BenchmarkConfig(
                    n, warmup, iterations, threshold, parallelism);
        }

        private static int parse(
                String argument, String prefix, boolean allowZero) {
            int value = Integer.parseInt(
                    argument.substring(prefix.length()));

            if (allowZero ? value < 0 : value <= 0) {
                throw new IllegalArgumentException(
                        prefix + (allowZero
                                ? " must be >= 0."
                                : " must be > 0."));
            }
            return value;
        }
    }
}
