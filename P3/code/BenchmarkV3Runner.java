package hpc.csr;

import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Executes the QFLPN Benchmark V3 A/B matrix.
 *
 * Responsibilities:
 * - validate benchmark dimensions;
 * - estimate workload-specific memory requirements before allocation;
 * - generate deterministic canonical CSR workloads;
 * - transfer ownership through the trusted CSR factory;
 * - execute sequential/parallel comparisons;
 * - sample JVM heap usage;
 * - preserve the existing 46-column V3 CSV contract.
 *
 * This runner does not replace the JMH methodology planned
 * for the separate methodology lot.
 */
public final class BenchmarkV3Runner {

    static final int DIMENSION = 4096;
    static final int MINIMUM_DIMENSION = 100;
    static final int DEFAULT_WARMUP = 2;
    static final int DEFAULT_ITERATIONS = 5;

    static final String[] WORKLOADS = {
        "UNIFORM_2",
        "UNIFORM_20",
        "UNIFORM_100",
        "BANDED",
        "BLOCK",
        "POWERLAW"
    };

    static final int[] PARALLELISMS = {1, 2, 4, 8};
    static final int[] THRESHOLDS = {1024, 2048, 4096, 8192};

    static final MultiplyTask.SplitPolicy[] SPLIT_POLICIES = {
        MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
        MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT
    };

    private static final double ERROR_TOLERANCE = 1.0e-12;
    private static final String STRATEGY = "FORK_JOIN";

    private static final double MEMORY_HEADROOM_RATIO = 0.30;
    private static final double CONSTRUCTION_OVERHEAD_FACTOR = 2.5;
    private static final long HEAP_SAMPLE_INTERVAL_MILLIS = 5L;

    private static final long MAX_SUPPORTED_ARRAY_ELEMENTS =
            (long) Integer.MAX_VALUE - 8L;

    private BenchmarkV3Runner() {
    }

    public static void main(String[] args) {

        int dimension = positiveEnvironmentInt(
                "P3_V3_DIMENSION",
                DIMENSION);

        int warmup = nonnegativeEnvironmentInt(
                "P3_V3_WARMUP",
                DEFAULT_WARMUP);

        int iterations = positiveEnvironmentInt(
                "P3_V3_ITERATIONS",
                DEFAULT_ITERATIONS);

        requireSupportedDimension(dimension);

        String runId = environmentOrDefault(
                "RUN_ID",
                createRunId());

        String workflowRunId = environmentOrDefault(
                "GITHUB_RUN_ID",
                "0");

        String commitSha = environmentOrDefault(
                "GITHUB_SHA",
                "0000000000000000000000000000000000000000");

        validateRunMetadata(runId, workflowRunId, commitSha);

        int completed = 0;
        int rejectedWorkloads = 0;
        int failedConfigurations = 0;

        for (String workloadId : WORKLOADS) {

            final Workload workload;

            try {
                MemoryPreflight preflight =
                        preflightWorkload(workloadId, dimension);

                System.out.println(
                        "P3_V3_PREFLIGHT=PASS"
                                + ";workload=" + workloadId
                                + ";N=" + dimension
                                + ";NNZ=" + preflight.nonZeroCount()
                                + ";estimated_bytes="
                                + preflight.requiredWithHeadroomBytes()
                                + ";available_bytes="
                                + preflight.availableBytes());

                workload = generateTrustedWorkload(
                        workloadId,
                        dimension,
                        preflight);

            } catch (Exception exception) {
                rejectedWorkloads++;

                System.err.println(
                        "P3_V3_WORKLOAD_REJECTED="
                                + workloadId
                                + ";N=" + dimension
                                + ";reason=" + exception);

                continue;
            }

            for (MultiplyTask.SplitPolicy splitPolicy : SPLIT_POLICIES) {
                for (int parallelism : PARALLELISMS) {
                    for (int threshold : THRESHOLDS) {

                        try {
                            String[] row = executeOne(
                                    workload,
                                    splitPolicy,
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
                            failedConfigurations++;

                            System.err.println(
                                    "P3_V3_CONFIGURATION_FAILED="
                                            + workloadId
                                            + ";policy=" + splitPolicy.name()
                                            + ";parallelism=" + parallelism
                                            + ";threshold=" + threshold
                                            + ";reason=" + exception);
                        }
                    }
                }
            }
        }

        int expected = configurationCount();

        System.out.println("P3_V3_EXPECTED_CONFIGURATIONS=" + expected);
        System.out.println("P3_V3_COMPLETED_CONFIGURATIONS=" + completed);
        System.out.println("P3_V3_REJECTED_WORKLOADS=" + rejectedWorkloads);
        System.out.println("P3_V3_FAILED_CONFIGURATIONS=" + failedConfigurations);

        if (completed != expected
                || rejectedWorkloads != 0
                || failedConfigurations != 0) {

            throw new IllegalStateException(
                    "V3 A/B matrix incomplete: completed="
                            + completed + "/" + expected
                            + ", rejected_workloads=" + rejectedWorkloads
                            + ", failed_configurations=" + failedConfigurations
                            + ". Partial results must not be reported as a complete matrix.");
        }

        System.out.println("P3_V3_AB_MATRIX_COMPLETE");
    }

    static int configurationCount() {
        return WORKLOADS.length
                * SPLIT_POLICIES.length
                * PARALLELISMS.length
                * THRESHOLDS.length;
    }

    static int legacyConfigurationCount() {
        return WORKLOADS.length
                * PARALLELISMS.length
                * THRESHOLDS.length;
    }

    static void requireSupportedDimension(int n) {

        if (n < MINIMUM_DIMENSION) {
            throw new IllegalArgumentException(
                    "P3 V3 dimension must be at least "
                            + MINIMUM_DIMENSION + "; got " + n);
        }

        if (n == DIMENSION) {
            return;
        }

        BenchmarkScale scale = BenchmarkScale.fromDimension(n);

        if (!scale.isTimedBenchmark()) {
            throw new IllegalArgumentException(
                    "Dimension " + n
                            + " is not eligible for timed benchmarking. Role: "
                            + scale.role());
        }
    }

    static MemoryPreflight preflightWorkload(String workloadId, int n) {

        requireSupportedDimension(n);
        validateWorkloadId(workloadId);

        long nnz = calculateNonZeroCount(workloadId, n);

        if (nnz > MAX_SUPPORTED_ARRAY_ELEMENTS) {
            throw new IllegalArgumentException(
                    "Workload exceeds int-indexed CSR array capacity: "
                            + "N=" + n
                            + ", workload=" + workloadId
                            + ", NNZ=" + nnz
                            + ", maximum=" + MAX_SUPPORTED_ARRAY_ELEMENTS);
        }

        long csrBytes = estimateCsrPayloadBytes(n, nnz);

        long vectorBytes = Math.multiplyExact(
                24L,
                (long) n);

        long rowMetadataBytes = Math.multiplyExact(4L, (long) n);

        long baseBytes = Math.addExact(
                csrBytes,
                Math.addExact(vectorBytes, rowMetadataBytes));

        long estimatedRequiredBytes = (long) Math.ceil(
                baseBytes * CONSTRUCTION_OVERHEAD_FACTOR);

        long requiredWithHeadroom = (long) Math.ceil(
                estimatedRequiredBytes * (1.0 + MEMORY_HEADROOM_RATIO));

        Runtime runtime = Runtime.getRuntime();

        long maxHeap = runtime.maxMemory();

        long currentlyUsed = Math.max(
                0L,
                runtime.totalMemory() - runtime.freeMemory());

        long available = Math.max(0L, maxHeap - currentlyUsed);

        if (requiredWithHeadroom > available) {
            throw new IllegalStateException(
                    "Memory preflight rejected workload before allocation: "
                            + "workload=" + workloadId
                            + ", N=" + n
                            + ", NNZ=" + nnz
                            + ", required_with_headroom="
                            + requiredWithHeadroom
                            + ", available=" + available
                            + ", max_heap=" + maxHeap);
        }

        return new MemoryPreflight(
                workloadId,
                n,
                nnz,
                csrBytes,
                estimatedRequiredBytes,
                requiredWithHeadroom,
                available,
                maxHeap);
    }

    static long calculateNonZeroCount(String workloadId, int n) {

        validateWorkloadId(workloadId);

        if (n < MINIMUM_DIMENSION) {
            throw new IllegalArgumentException(
                    "Dimension must be at least " + MINIMUM_DIMENSION);
        }

        return switch (workloadId) {
            case "UNIFORM_2" ->
                    Math.multiplyExact(2L, n);

            case "UNIFORM_20" ->
                    Math.multiplyExact(20L, n);

            case "UNIFORM_100" ->
                    Math.multiplyExact(100L, n);

            case "BANDED" ->
                    Math.multiplyExact((long) Math.min(5, n), n);

            case "BLOCK" ->
                    Math.multiplyExact((long) Math.min(8, n), n);

            case "POWERLAW" -> {
                long total = 0L;

                for (int row = 0; row < n; row++) {
                    total = Math.addExact(
                            total,
                            rowCountFor(workloadId, row, n));
                }

                yield total;
            }

            default -> throw new IllegalArgumentException(
                    "Unsupported workload: " + workloadId);
        };
    }

    static long estimateCsrPayloadBytes(int n, long nnz) {

        if (n <= 0 || nnz < 0L) {
            throw new IllegalArgumentException("Invalid CSR dimensions");
        }

        long valuesBytes = Math.multiplyExact(8L, nnz);
        long columnsBytes = Math.multiplyExact(4L, nnz);
        long pointersBytes = Math.multiplyExact(4L, (long) n + 1L);

        return Math.addExact(
                Math.addExact(valuesBytes, columnsBytes),
                pointersBytes);
    }

    static Workload generateTrustedWorkload(
            String workloadId,
            int n,
            MemoryPreflight preflight) {

        validateWorkloadId(workloadId);

        if (preflight == null) {
            throw new IllegalArgumentException(
                    "Memory preflight must not be null");
        }

        if (!preflight.workloadId().equals(workloadId)
                || preflight.dimension() != n) {
            throw new IllegalArgumentException(
                    "Preflight does not match requested workload and dimension");
        }

        MemoryPreflight current = preflightWorkload(workloadId, n);

        if (current.nonZeroCount() != preflight.nonZeroCount()) {
            throw new IllegalStateException(
                    "Preflight NNZ changed before generation");
        }

        return generateWorkloadInternal(
                workloadId,
                n,
                preflight.nonZeroCount());
    }

    static Workload generateWorkload(String workloadId, int n) {

        MemoryPreflight preflight = preflightWorkload(workloadId, n);

        return generateTrustedWorkload(workloadId, n, preflight);
    }

    private static Workload generateWorkloadInternal(
            String workloadId,
            int n,
            long expectedNnz) {

        int totalNnz = Math.toIntExact(expectedNnz);

        double[] values = new double[totalNnz];
        int[] columns = new int[totalNnz];
        int[] rowPointers = new int[Math.addExact(n, 1)];

        int cursor = 0;
        int minimum = Integer.MAX_VALUE;
        int maximum = Integer.MIN_VALUE;
        long sum = 0L;

        int blockWidth = Math.max(8, n / 16);

        for (int row = 0; row < n; row++) {

            int count = rowCountFor(workloadId, row, n);

            minimum = Math.min(minimum, count);
            maximum = Math.max(maximum, count);
            sum = Math.addExact(sum, count);

            int blockStart = 0;
            int blockSize = 0;

            if ("BLOCK".equals(workloadId)) {
                blockStart = Math.min(
                        (row / blockWidth) * blockWidth,
                        n - blockWidth);

                blockSize = Math.min(blockWidth, n - blockStart);

                if (blockSize < count) {
                    throw new IllegalStateException(
                            "BLOCK distribution cannot provide "
                                    + count + " distinct columns");
                }
            }

            int stride = 1;

            if ("UNIFORM_2".equals(workloadId)
                    || "UNIFORM_20".equals(workloadId)
                    || "UNIFORM_100".equals(workloadId)
                    || "POWERLAW".equals(workloadId)) {

                stride = coprimeStride(n, count);
            }

            for (int j = 0; j < count; j++) {

                int column = columnFor(
                        workloadId,
                        row,
                        j,
                        n,
                        stride,
                        blockStart,
                        blockSize);

                columns[cursor] = column;
                values[cursor] = 0.5 + ((row + j) % 11) / 10.0;
                cursor++;
            }

            sortRow(columns, rowPointers[row], cursor);
            rowPointers[row + 1] = cursor;
        }

        if (cursor != totalNnz) {
            throw new IllegalStateException(
                    "Generated NNZ differs from preflight: expected="
                            + totalNnz + ", actual=" + cursor);
        }

        SparseMatrixCSR matrix = SparseMatrixCSR.fromTrustedCanonical(
                values,
                columns,
                rowPointers,
                n,
                n);

        return new Workload(
                workloadId,
                familyFor(workloadId),
                distributionFor(workloadId),
                matrix,
                minimum,
                (double) sum / n,
                maximum);
    }

    private static int rowCountFor(
            String workloadId,
            int row,
            int n) {

        return switch (workloadId) {
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
    }

    private static int columnFor(
            String workloadId,
            int row,
            int j,
            int n,
            int stride,
            int blockStart,
            int blockSize) {

        return switch (workloadId) {
            case "BANDED" ->
                    Math.floorMod(row + j - 2, n);

            case "BLOCK" ->
                    blockStart + j;

            case "UNIFORM_2", "UNIFORM_20", "UNIFORM_100", "POWERLAW" ->
                    (int) Math.floorMod(
                            (long) row + (long) j * stride,
                            (long) n);

            default -> throw new IllegalArgumentException(
                    "Unsupported workload: " + workloadId);
        };
    }

    private static int coprimeStride(int n, int count) {

        if (count < 1 || count > n) {
            throw new IllegalArgumentException(
                    "Invalid row density: " + count + " for N=" + n);
        }

        int candidate = Math.max(1, n / count);

        while (greatestCommonDivisor(candidate, n) != 1) {
            candidate++;

            if (candidate >= n) {
                candidate = 1;
            }
        }

        return candidate;
    }

    private static int greatestCommonDivisor(int a, int b) {

        int x = Math.abs(a);
        int y = Math.abs(b);

        while (y != 0) {
            int remainder = x % y;
            x = y;
            y = remainder;
        }

        return x;
    }

    private static void sortRow(int[] columns, int start, int end) {

        for (int i = start + 1; i < end; i++) {

            int value = columns[i];
            int j = i - 1;

            while (j >= start && columns[j] > value) {
                columns[j + 1] = columns[j];
                j--;
            }

            if (j >= start && columns[j] == value) {
                throw new IllegalStateException(
                        "Generator produced a duplicate column index");
            }

            columns[j + 1] = value;
        }
    }

    private static String familyFor(String workloadId) {

        return switch (workloadId) {
            case "UNIFORM_2", "UNIFORM_20", "UNIFORM_100" -> "UNIFORM";
            case "BANDED" -> "BANDED";
            case "BLOCK" -> "BLOCK_DIAGONAL";
            case "POWERLAW" -> "POWER_LAW";
            default -> throw new IllegalArgumentException(
                    "Unsupported workload: " + workloadId);
        };
    }

    private static String distributionFor(String workloadId) {

        return switch (workloadId) {
            case "UNIFORM_2" -> "FIXED_2_PER_ROW";
            case "UNIFORM_20" -> "FIXED_20_PER_ROW";
            case "UNIFORM_100" -> "FIXED_100_PER_ROW";
            case "BANDED" -> "LOCAL_BAND_5";
            case "BLOCK" -> "BLOCK_LOCAL_8";
            case "POWERLAW" -> "DETERMINISTIC_INVERSE_SQRT";
            default -> throw new IllegalArgumentException(
                    "Unsupported workload: " + workloadId);
        };
    }

    private static void validateWorkloadId(String workloadId) {

        if (workloadId == null) {
            throw new IllegalArgumentException(
                    "Workload identifier must not be null");
        }

        for (String supported : WORKLOADS) {
            if (supported.equals(workloadId)) {
                return;
            }
        }

        throw new IllegalArgumentException(
                "Unsupported workload: " + workloadId);
    }

    static String[] executeOne(
            Workload workload,
            MultiplyTask.SplitPolicy splitPolicy,
            int parallelism,
            int threshold,
            int warmup,
            int iterations,
            String runId,
            String workflowRunId,
            String commitSha) {

        if (workload == null || splitPolicy == null) {
            throw new IllegalArgumentException(
                    "Workload and split policy must not be null");
        }

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

        HeapPeakMonitor heapMonitor = new HeapPeakMonitor();
        ForkJoinPool pool = new ForkJoinPool(parallelism);

        heapMonitor.start();

        try {
            long setupStart = System.nanoTime();
            double[] oracle = independentOracle(matrix, input);
            double setupMs = elapsedMs(setupStart);

            heapMonitor.sampleNow();

            for (int i = 0; i < warmup; i++) {
                matrix.multiplyInto(input, sequentialOutput);

                matrix.multiplyParallelInto(
                        input,
                        parallelOutput,
                        threshold,
                        pool,
                        splitPolicy);

                heapMonitor.sampleNow();
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
                            input, parallelOutput, threshold, pool, splitPolicy);
                    parSamples[i] = elapsedMs(start);

                } else {
                    start = System.nanoTime();
                    matrix.multiplyParallelInto(
                            input, parallelOutput, threshold, pool, splitPolicy);
                    parSamples[i] = elapsedMs(start);

                    start = System.nanoTime();
                    matrix.multiplyInto(input, sequentialOutput);
                    seqSamples[i] = elapsedMs(start);
                }

                heapMonitor.sampleNow();
            }

            double seqError = maxAbsoluteError(sequentialOutput, oracle);
            double parError = maxAbsoluteError(parallelOutput, oracle);
            double crossError = maxAbsoluteError(
                    sequentialOutput, parallelOutput);

            double maxError = Math.max(
                    Math.max(seqError, parError),
                    crossError);

            String status = maxError <= ERROR_TOLERANCE ? "PASS" : "FAIL";

            double seqMean = mean(seqSamples);
            double parMean = mean(parSamples);
            double speedup = seqMean / parMean;

            Runtime runtime = Runtime.getRuntime();

            heapMonitor.sampleNow();

            long maxHeap = runtime.maxMemory();
            long minimumFreeHeap = heapMonitor.minimumFreeHeapBytes();
            long peakHeapUsed = heapMonitor.peakUsedHeapBytes();

            String verdict;

            if (speedup < 0.80) {
                verdict = "REGRESSION";
            } else if (speedup < 1.05) {
                verdict = "NEUTRAL";
            } else {
                verdict = "IMPROVEMENT";
            }

            String notes =
                    "pool_reused"
                            + ";alternating_order"
                            + ";independent_csr_oracle"
                            + ";split_policy=" + splitPolicy.name()
                            + ";heap_sampling_interval_ms="
                            + HEAP_SAMPLE_INTERVAL_MILLIS
                            + ";peak_heap_used_bytes=" + peakHeapUsed
                            + ";minimum_free_heap_bytes=" + minimumFreeHeap;

            return new String[] {
                Instant.now().toString(),
                runId,
                workflowRunId,
                commitSha,
                "QFLPN-V3-" + workload.id() + "-" + splitPolicy.name(),
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
                splitPolicy.name(),
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
                Long.toString(minimumFreeHeap),
                System.getProperty("java.version", "unknown"),
                System.getProperty("os.name", "unknown")
                        + " " + System.getProperty("os.version", "unknown"),
                status,
                verdict,
                notes
            };

        } finally {
            heapMonitor.close();
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

        if (a == null || b == null || a.length != b.length) {
            throw new IllegalArgumentException(
                    "Vector lengths differ or are null");
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
            String name,
            int fallback) {

        String value = System.getenv(name);

        if (value == null || value.isBlank()) {
            return fallback;
        }

        int parsed = Integer.parseInt(value);

        if (parsed <= 0) {
            throw new IllegalArgumentException(
                    name + " must be positive");
        }

        return parsed;
    }

    private static int nonnegativeEnvironmentInt(
            String name,
            int fallback) {

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
            String name,
            String fallback) {

        String value = System.getenv(name);

        return value == null || value.isBlank() ? fallback : value;
    }

    private static void validateRunMetadata(
            String runId,
            String workflowRunId,
            String commitSha) {

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
    }

    private static String createRunId() {

        return DateTimeFormatter
                .ofPattern("yyyyMMdd'T'HHmmss'Z'")
                .withZone(java.time.ZoneOffset.UTC)
                .format(Instant.now())
                + "-" + UUID.randomUUID();
    }

    record MemoryPreflight(
            String workloadId,
            int dimension,
            long nonZeroCount,
            long csrPayloadBytes,
            long estimatedRequiredBytes,
            long requiredWithHeadroomBytes,
            long availableBytes,
            long maximumHeapBytes) {
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

    static final class HeapPeakMonitor implements AutoCloseable {

        private final Runtime runtime = Runtime.getRuntime();

        private final AtomicBoolean running = new AtomicBoolean(false);
        private final AtomicLong peakUsedHeap = new AtomicLong(0L);
        private final AtomicLong minimumFreeHeap =
                new AtomicLong(Long.MAX_VALUE);

        private Thread sampler;

        void start() {

            if (!running.compareAndSet(false, true)) {
                throw new IllegalStateException(
                        "Heap monitor already started");
            }

            sampleNow();

            sampler = new Thread(
                    this::sampleLoop,
                    "p3-v3-heap-monitor");

            sampler.setDaemon(true);
            sampler.start();
        }

        void sampleNow() {

            long total = runtime.totalMemory();
            long free = runtime.freeMemory();
            long used = Math.max(0L, total - free);

            peakUsedHeap.accumulateAndGet(used, Math::max);
            minimumFreeHeap.accumulateAndGet(free, Math::min);
        }

        private void sampleLoop() {

            while (running.get()) {
                sampleNow();

                try {
                    Thread.sleep(HEAP_SAMPLE_INTERVAL_MILLIS);
                } catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }

            sampleNow();
        }

        long peakUsedHeapBytes() {
            sampleNow();
            return peakUsedHeap.get();
        }

        long minimumFreeHeapBytes() {

            sampleNow();

            long value = minimumFreeHeap.get();

            return value == Long.MAX_VALUE
                    ? runtime.freeMemory()
                    : value;
        }

        @Override
        public void close() {

            running.set(false);

            if (sampler != null) {
                sampler.interrupt();

                try {
                    sampler.join(2_000L);
                } catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                }
            }

            sampleNow();
        }
    }
}
