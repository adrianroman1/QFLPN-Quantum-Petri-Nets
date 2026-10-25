package hpc.csr;

import java.io.IOException;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ForkJoinPool;

/**
 * Executes the complete additive V3 workload/configuration matrix.
 *
 * V2 classes and output files are not modified.
 */
public final class BenchmarkV3Runner {

    static final int DIMENSION = 4096;
    static final int DEFAULT_WARMUP = 2;
    static final int DEFAULT_ITERATIONS = 5;

    static final String[] WORKLOADS = {
        "UNIFORM_2", "UNIFORM_20", "UNIFORM_100",
        "BANDED", "BLOCK", "POWERLAW"
    };

    static final int[] PARALLELISMS = {1, 2, 4, 8};
    static final int[] THRESHOLDS = {1024, 2048, 4096, 8192};

    private static final double ERROR_TOLERANCE = 1.0e-12;
    private static final String STRATEGY = "FORK_JOIN";
    private static final String SPLIT_POLICY =
            "NNZ_BALANCED_ROW_BOUNDARY";

    private BenchmarkV3Runner() {
    }

    public static void main(String[] args) {
        int dimension = positiveEnvironmentInt(
                "P3_V3_DIMENSION", DIMENSION);
        int warmup = nonnegativeEnvironmentInt(
                "P3_V3_WARMUP", DEFAULT_WARMUP);
        int iterations = positiveEnvironmentInt(
                "P3_V3_ITERATIONS", DEFAULT_ITERATIONS);

        String runId = environmentOrDefault(
                "RUN_ID", createRunId());
        String workflowRunId = environmentOrDefault(
                "GITHUB_RUN_ID", "0");
        String commitSha = environmentOrDefault(
                "GITHUB_SHA",
                "0000000000000000000000000000000000000000");

        if (!workflowRunId.matches("[0-9]+")) {
            throw new IllegalArgumentException(
                    "GITHUB_RUN_ID must contain decimal digits only");
        }
        if (!commitSha.matches("[0-9a-f]{40}")) {
            throw new IllegalArgumentException(
                    "GITHUB_SHA must be a 40-character lowercase SHA-1");
        }
        if (!runId.matches("[A-Za-z0-9._-]+")) {
            throw new IllegalArgumentException(
                    "RUN_ID contains unsupported characters");
        }

        int completed = 0;
        List<String> failures = new ArrayList<>();

        for (String workload : WORKLOADS) {
            Workload generated = generateWorkload(workload, dimension);

            for (int parallelism : PARALLELISMS) {
                for (int threshold : THRESHOLDS) {
                    try {
                        String[] row = executeOne(
                                generated,
                                parallelism,
                                threshold,
                                warmup,
                                iterations,
                                runId,
                                workflowRunId,
                                commitSha);

                        BenchmarkV3ResultWriter.append(row);
                        completed++;
                    } catch (Exception exception) {
                        failures.add(
                                workload + "/p=" + parallelism
                                        + "/threshold=" + threshold
                                        + ": " + exception.getMessage());
                    }
                }
            }
        }

        System.out.println("P3_V3_EXPECTED_CONFIGURATIONS="
                + configurationCount());
        System.out.println("P3_V3_COMPLETED_CONFIGURATIONS=" + completed);
        System.out.println("P3_V3_FAILED_CONFIGURATIONS=" + failures.size());

        for (String failure : failures) {
            System.err.println("P3_V3_FAILURE=" + failure);
        }

        if (completed != configurationCount() || !failures.isEmpty()) {
            throw new IllegalStateException(
                    "V3 benchmark incomplete: " + completed + "/"
                            + configurationCount() + " configurations");
        }
    }

    static int configurationCount() {
        return WORKLOADS.length
                * PARALLELISMS.length
                * THRESHOLDS.length;
    }

    static Workload generateWorkload(String workloadId, int n) {
        if (n <= 0) {
            throw new IllegalArgumentException(
                    "Dimension must be positive");
        }

        if (!Arrays.asList(WORKLOADS).contains(workloadId)) {
            throw new IllegalArgumentException(
                    "Unsupported workload: " + workloadId);
        }

        int[] rowCounts = new int[n];
        int totalNnz = 0;

        for (int row = 0; row < n; row++) {
            int count = switch (workloadId) {
                case "UNIFORM_2" -> 2;
                case "UNIFORM_20" -> 20;
                case "UNIFORM_100" -> 100;
                case "BANDED" -> Math.min(5, n);
                case "BLOCK" -> Math.min(8, n);
                case "POWERLAW" ->
                        Math.min(n, 1 + (int) (32.0 / Math.sqrt(row + 1.0)));
                default -> throw new IllegalArgumentException(
                        "Unsupported workload: " + workloadId);
            };

            rowCounts[row] = count;
            totalNnz = Math.addExact(totalNnz, count);
        }

        double[] values = new double[totalNnz];
        int[] columns = new int[totalNnz];
        int[] rowPointers = new int[n + 1];

        int cursor = 0;
        int blockWidth = Math.max(1, n / 16);

        for (int row = 0; row < n; row++) {
            int count = rowCounts[row];
            int blockStart = (row / blockWidth) * blockWidth;
            int blockEnd = Math.min(n, blockStart + blockWidth);
            int blockSize = blockEnd - blockStart;

            for (int j = 0; j < count; j++) {
                int column;

                switch (workloadId) {
                    case "BANDED" -> {
                        int offset = j - count / 2;
                        column = Math.floorMod(row + offset, n);
                    }
                    case "BLOCK" -> {
                        column = blockStart
                                + Math.floorMod(j, blockSize);
                    }
                    case "POWERLAW" -> {
                        column = Math.floorMod(
                                row + j * 37 + j * j * 13, n);
                    }
                    default -> {
                        column = Math.floorMod(
                                row + j * Math.max(1, n / count), n);
                    }
                }

                // All generated columns within a row must be unique.
                while (containsColumn(
                        columns, rowPointers[row], cursor, column)) {
                    column = (column + 1) % n;
                }

                columns[cursor] = column;
                values[cursor] = 0.5 + ((row + j) % 11) / 10.0;
                cursor++;
            }

            rowPointers[row + 1] = cursor;
        }

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columns, rowPointers, n, n);

        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        long sum = 0L;

        for (int count : rowCounts) {
            min = Math.min(min, count);
            max = Math.max(max, count);
            sum += count;
        }

        String family = switch (workloadId) {
            case "UNIFORM_2", "UNIFORM_20", "UNIFORM_100" -> "UNIFORM";
            case "BANDED" -> "BANDED";
            case "BLOCK" -> "BLOCK_DIAGONAL";
            case "POWERLAW" -> "POWER_LAW";
            default -> throw new IllegalStateException();
        };

        String distribution = switch (workloadId) {
            case "UNIFORM_2" -> "FIXED_2_PER_ROW";
            case "UNIFORM_20" -> "FIXED_20_PER_ROW";
            case "UNIFORM_100" -> "FIXED_100_PER_ROW";
            case "BANDED" -> "LOCAL_BAND_5";
            case "BLOCK" -> "BLOCK_LOCAL_8";
            case "POWERLAW" -> "DETERMINISTIC_INVERSE_SQRT";
            default -> throw new IllegalStateException();
        };

        return new Workload(
                workloadId,
                family,
                distribution,
                matrix,
                min,
                (double) sum / n,
                max);
    }

    private static boolean containsColumn(
            int[] columns,
            int start,
            int end,
            int candidate) {

        for (int i = start; i < end; i++) {
            if (columns[i] == candidate) {
                return true;
            }
        }
        return false;
    }

    private static String[] executeOne(
            Workload workload,
            int parallelism,
            int threshold,
            int warmup,
            int iterations,
            String runId,
            String workflowRunId,
            String commitSha) {

        if (parallelism <= 0 || threshold <= 0
                || warmup < 0 || iterations <= 0) {
            throw new IllegalArgumentException(
                    "Invalid benchmark configuration");
        }

        SparseMatrixCSR matrix = workload.matrix();
        int n = matrix.getRows();

        double[] input = new double[n];
        double[] sequentialOutput = new double[n];
        double[] parallelOutput = new double[n];

        for (int i = 0; i < n; i++) {
            input[i] = 0.25 + (i % 17) / 13.0;
        }

        long setupStart = System.nanoTime();

        // Independent reference: direct CSR traversal, not either multiply API.
        double[] oracle = independentOracle(matrix, input);

        double setupMs = (System.nanoTime() - setupStart) / 1_000_000.0;

        ForkJoinPool pool = new ForkJoinPool(parallelism);

        try {
            for (int i = 0; i < warmup; i++) {
                matrix.multiplyInto(input, sequentialOutput);
                matrix.multiplyParallelInto(
                        input, parallelOutput, threshold, pool);
            }

            double[] seqSamples = new double[iterations];
            double[] parSamples = new double[iterations];

            for (int i = 0; i < iterations; i++) {
                long start;

                if ((i & 1) == 0) {
                    start = System.nanoTime();
                    matrix.multiplyInto(input, sequentialOutput);
                    seqSamples[i] = elapsedMs(start);

                    start = System.nanoTime();
                    matrix.multiplyParallelInto(
                            input, parallelOutput, threshold, pool);
                    parSamples[i] = elapsedMs(start);
                } else {
                    start = System.nanoTime();
                    matrix.multiplyParallelInto(
                            input, parallelOutput, threshold, pool);
                    parSamples[i] = elapsedMs(start);

                    start = System.nanoTime();
                    matrix.multiplyInto(input, sequentialOutput);
                    seqSamples[i] = elapsedMs(start);
                }
            }

            double seqError = maxAbsoluteError(sequentialOutput, oracle);
            double parError = maxAbsoluteError(parallelOutput, oracle);
            double crossError = maxAbsoluteError(
                    sequentialOutput, parallelOutput);
            double maxError = Math.max(
                    Math.max(seqError, parError), crossError);

            String status = maxError <= ERROR_TOLERANCE ? "PASS" : "FAIL";

            double seqMean = mean(seqSamples);
            double parMean = mean(parSamples);
            double speedup = seqMean / parMean;

            Runtime runtime = Runtime.getRuntime();
            long maxHeap = runtime.maxMemory();
            long freeHeap = Math.min(runtime.freeMemory(), maxHeap);

            String verdict;
            if (speedup < 0.80) {
                verdict = "REGRESSION";
            } else if (speedup < 1.05) {
                verdict = "NEUTRAL";
            } else {
                verdict = "IMPROVEMENT";
            }

            String timestamp = Instant.now().toString();
            String benchmarkId = "QFLPN-V3-" + workload.id();

            return new String[] {
                timestamp,
                runId,
                workflowRunId,
                commitSha,
                benchmarkId,
                workload.id(),
                workload.family(),
                workload.distribution(),
                Integer.toString(n),
                Integer.toString(matrix.getNnz()),
                decimal(workload.minNnz()),
                decimal(workload.averageNnz()),
                decimal(workload.maxNnz()),
                Integer.toString(parallelism),
                Integer.toString(threshold),
                STRATEGY,
                SPLIT_POLICY,
                Integer.toString(warmup),
                Integer.toString(iterations),
                decimal(seqMean),
                decimal(median(seqSamples)),
                decimal(populationStdDev(seqSamples)),
                decimal(min(seqSamples)),
                decimal(max(seqSamples)),
                decimal(parMean),
                decimal(median(parSamples)),
                decimal(populationStdDev(parSamples)),
                decimal(min(parSamples)),
                decimal(max(parSamples)),
                decimal(speedup),
                decimal(n / (seqMean / 1000.0)),
                decimal(n / (parMean / 1000.0)),
                decimal(matrix.getNnz() / (seqMean / 1000.0)),
                decimal(matrix.getNnz() / (parMean / 1000.0)),
                decimal(seqError),
                decimal(parError),
                decimal(maxError),
                decimal(setupMs),
                System.getProperty("os.arch", "unknown")
                        + ";processors=" + runtime.availableProcessors(),
                Long.toString(maxHeap),
                Long.toString(freeHeap),
                System.getProperty("java.version", "unknown"),
                System.getProperty("os.name", "unknown")
                        + " " + System.getProperty("os.version", "unknown"),
                status,
                verdict,
                "pool_reused;alternating_order;independent_csr_oracle"
            };
        } finally {
            pool.shutdown();
        }
    }

    private static double[] independentOracle(
            SparseMatrixCSR matrix,
            double[] input) {

        double[] values = matrix.getValues();
        int[] columns = matrix.getColumnIndices();
        int[] pointers = matrix.getRowPointers();

        double[] output = new double[matrix.getRows()];

        for (int row = 0; row < output.length; row++) {
            double sum = 0.0;
            for (int k = pointers[row]; k < pointers[row + 1]; k++) {
                sum += values[k] * input[columns[k]];
            }
            output[row] = sum;
        }

        return output;
    }

    static double maxAbsoluteError(double[] a, double[] b) {
        if (a.length != b.length) {
            throw new IllegalArgumentException("Vector lengths differ");
        }

        double result = 0.0;
        for (int i = 0; i < a.length; i++) {
            if (!Double.isFinite(a[i]) || !Double.isFinite(b[i])) {
                return Double.POSITIVE_INFINITY;
            }
            result = Math.max(result, Math.abs(a[i] - b[i]));
        }
        return result;
    }

    static double mean(double[] values) {
        requireSamples(values);
        double sum = 0.0;
        for (double value : values) {
            requirePositiveFinite(value);
            sum += value;
        }
        return sum / values.length;
    }

    static double median(double[] values) {
        requireSamples(values);
        double[] sorted = values.clone();
        for (double value : sorted) {
            requirePositiveFinite(value);
        }
        Arrays.sort(sorted);
        int middle = sorted.length / 2;
        return sorted.length % 2 == 0
                ? (sorted[middle - 1] + sorted[middle]) / 2.0
                : sorted[middle];
    }

    static double populationStdDev(double[] values) {
        double average = mean(values);
        double sum = 0.0;
        for (double value : values) {
            double delta = value - average;
            sum += delta * delta;
        }
        return Math.sqrt(sum / values.length);
    }

    private static double min(double[] values) {
        return Arrays.stream(values).min().orElseThrow();
    }

    private static double max(double[] values) {
        return Arrays.stream(values).max().orElseThrow();
    }

    private static void requireSamples(double[] values) {
        if (values == null || values.length == 0) {
            throw new IllegalArgumentException("No measurement samples");
        }
    }

    private static void requirePositiveFinite(double value) {
        if (!Double.isFinite(value) || value <= 0.0) {
            throw new IllegalArgumentException(
                    "Measurement must be finite and positive");
        }
    }

    private static double elapsedMs(long start) {
        return (System.nanoTime() - start) / 1_000_000.0;
    }

    private static String decimal(double value) {
        if (!Double.isFinite(value)) {
            throw new IllegalArgumentException(
                    "Cannot serialize non-finite number");
        }
        return String.format(Locale.ROOT, "%.12e", value);
    }

    private static int positiveEnvironmentInt(
            String name, int fallback) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            return fallback;
        }
        int parsed = Integer.parseInt(value);
        if (parsed <= 0) {
            throw new IllegalArgumentException(name + " must be positive");
        }
        return parsed;
    }

    private static int nonnegativeEnvironmentInt(
            String name, int fallback) {
        String value = System.getenv(name);
        if (value == null || value.isBlank()) {
            return fallback;
        }
        int parsed = Integer.parseInt(value);
        if (parsed < 0) {
            throw new IllegalArgumentException(
                    name + " must be nonnegative");
        }
        return parsed;
    }

    private static String environmentOrDefault(
            String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }

    private static String createRunId() {
        return DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'")
                .withZone(java.time.ZoneOffset.UTC)
                .format(Instant.now()) + "-" + UUID.randomUUID();
    }

    record Workload(
            String id,
            String family,
            String distribution,
            SparseMatrixCSR matrix,
            int minNnz,
            double averageNnz,
            int maxNnz) {
    }
}
