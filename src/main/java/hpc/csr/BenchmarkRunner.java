package hpc.csr;

import java.util.Locale;
import java.util.concurrent.ForkJoinPool;

/**
 * BenchmarkRunner
 *
 * Benchmark controlat pentru multiplicarea sparse matrix-vector:
 *
 *                         y = A * x
 *
 * Acest program este separat de CI și de testele JUnit.
 *
 * Obiectiv:
 *
 * 1. măsurarea execuției secvențiale;
 * 2. măsurarea execuției paralele;
 * 3. calculul speedup-ului;
 * 4. calculul throughput-ului;
 * 5. verificarea numerică a rezultatului;
 * 6. estimarea memoriei;
 * 7. testarea unor dimensiuni mari, inclusiv N=30_000_000.
 *
 * IMPORTANT:
 *
 * ForkJoinPool-ul este creat O SINGURĂ DATĂ înaintea secțiunii
 * măsurate și reutilizat pentru toate iterațiile paralele.
 *
 * Astfel, timpul raportat pentru multiplicarea paralelă reprezintă
 * operația CSR propriu-zisă și nu include crearea/închiderea
 * pool-ului la fiecare iterație.
 *
 * Exemple:
 *
 * N = 1.000.000:
 *
 * java -cp target/classes \
 *      hpc.csr.BenchmarkRunner \
 *      --n=1000000
 *
 * N = 30.000.000:
 *
 * java -cp target/classes \
 *      hpc.csr.BenchmarkRunner \
 *      --n=30000000 \
 *      --warmup=2 \
 *      --iterations=3 \
 *      --threshold=4096 \
 *      --parallelism=8
 */
public final class BenchmarkRunner {

    private static final int DEFAULT_N = 1_000_000;

    private static final int DEFAULT_WARMUP = 2;

    private static final int DEFAULT_ITERATIONS = 3;

    private static final int DEFAULT_THRESHOLD = 4096;

    private BenchmarkRunner() {
        // Utility class.
    }

    public static void main(String[] args) {

        BenchmarkConfig config =
                BenchmarkConfig.fromArgs(args);

        printConfiguration(config);

        long setupStart =
                System.nanoTime();

        SparseMatrixCSR matrix =
                createBenchmarkMatrix(config.n());

        double[] input =
                createInputVector(config.n());

        double[] sequentialOutput =
                new double[config.n()];

        double[] parallelOutput =
                new double[config.n()];

        long setupEnd =
                System.nanoTime();

        double setupTimeMs =
                nanosToMillis(
                        setupEnd - setupStart);

        System.out.println();

        System.out.printf(
                Locale.ROOT,
                "Setup time      : %.3f ms%n",
                setupTimeMs);

        printMemoryEstimate(
                config.n());

        /*
         * Pool persistent:
         *
         * NU este inclus în timpul măsurat.
         */
        ForkJoinPool pool =
                new ForkJoinPool(
                        config.parallelism());

        try {

            warmupSequential(
                    matrix,
                    input,
                    sequentialOutput,
                    config.warmup());

            warmupParallel(
                    matrix,
                    input,
                    parallelOutput,
                    config.warmup(),
                    config.threshold(),
                    pool);

            long sequentialTotalNs =
                    measureSequential(
                            matrix,
                            input,
                            sequentialOutput,
                            config.iterations());

            long parallelTotalNs =
                    measureParallel(
                            matrix,
                            input,
                            parallelOutput,
                            config.iterations(),
                            config.threshold(),
                            pool);

            double sequentialAverageMs =
                    nanosToMillis(
                            sequentialTotalNs
                                    / config.iterations());

            double parallelAverageMs =
                    nanosToMillis(
                            parallelTotalNs
                                    / config.iterations());

            double speedup =
                    sequentialAverageMs
                            / parallelAverageMs;

            double sequentialThroughput =
                    calculateThroughput(
                            config.n(),
                            sequentialAverageMs);

            double parallelThroughput =
                    calculateThroughput(
                            config.n(),
                            parallelAverageMs);

            double maxAbsoluteError =
                    maxAbsoluteError(
                            sequentialOutput,
                            parallelOutput);

            double expectedValue =
                    1.5;

            double sequentialExpectedError =
                    maxExpectedError(
                            sequentialOutput,
                            expectedValue);

            double parallelExpectedError =
                    maxExpectedError(
                            parallelOutput,
                            expectedValue);

            boolean sequentialCorrect =
                    sequentialExpectedError
                            <= 1.0e-12;

            boolean parallelCorrect =
                    parallelExpectedError
                            <= 1.0e-12;

            boolean resultsMatch =
                    maxAbsoluteError
                            <= 1.0e-12;

            printResults(
                    config,
                    matrix,
                    setupTimeMs,
                    sequentialAverageMs,
                    parallelAverageMs,
                    speedup,
                    sequentialThroughput,
                    parallelThroughput,
                    sequentialExpectedError,
                    parallelExpectedError,
                    maxAbsoluteError,
                    sequentialCorrect,
                    parallelCorrect,
                    resultsMatch);

            if (!sequentialCorrect
                    || !parallelCorrect
                    || !resultsMatch) {

                throw new IllegalStateException(
                        "Benchmark numerical validation failed.");
            }

        } finally {

            pool.shutdown();
        }
    }

    /**
     * Creează matricea CSR de benchmark.
     *
     * Pentru fiecare rând:
     *
     * A[i,i]     = 1.0
     * A[i,i+1]   = 0.5
     *
     * Pentru ultimul rând:
     *
     * A[N-1,0]   = 0.5
     *
     * Astfel:
     *
     * NNZ = 2 * N
     *
     * pentru N > 0.
     */
    private static SparseMatrixCSR createBenchmarkMatrix(
            int n) {

        long nnzLong =
                2L * n;

        if (nnzLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "NNZ exceeds Java array limits: "
                            + nnzLong);
        }

        if (n <= 0) {
            throw new IllegalArgumentException(
                    "N must be greater than zero.");
        }

        int nnz =
                (int) nnzLong;

        double[] values =
                new double[nnz];

        int[] columns =
                new int[nnz];

        int[] rowPointers =
                new int[n + 1];

        for (int row = 0;
             row < n;
             row++) {

            int base =
                    2 * row;

            values[base] =
                    1.0;

            values[base + 1] =
                    0.5;

            columns[base] =
                    row;

            columns[base + 1] =
                    row + 1 < n
                            ? row + 1
                            : 0;

            rowPointers[row + 1] =
                    base + 2;
        }

        return new SparseMatrixCSR(
                values,
                columns,
                rowPointers,
                n,
                n);
    }

    /**
     * Creează vectorul x.
     *
     * x[i] = 1.0
     *
     * Pentru matricea de benchmark rezultatul așteptat este:
     *
     * y[i] = 1.5
     */
    private static double[] createInputVector(
            int n) {

        double[] input =
                new double[n];

        for (int i = 0;
             i < n;
             i++) {

            input[i] =
                    1.0;
        }

        return input;
    }

    private static void warmupSequential(
            SparseMatrixCSR matrix,
            double[] input,
            double[] output,
            int warmup) {

        for (int i = 0;
             i < warmup;
             i++) {

            matrix.multiplyInto(
                    input,
                    output);
        }
    }

    private static void warmupParallel(
            SparseMatrixCSR matrix,
            double[] input,
            double[] output,
            int warmup,
            int threshold,
            ForkJoinPool pool) {

        for (int i = 0;
             i < warmup;
             i++) {

            matrix.multiplyParallelInto(
                    input,
                    output,
                    threshold,
                    pool);
        }
    }

    private static long measureSequential(
            SparseMatrixCSR matrix,
            double[] input,
            double[] output,
            int iterations) {

        long totalNs =
                0L;

        for (int i = 0;
             i < iterations;
             i++) {

            long start =
                    System.nanoTime();

            matrix.multiplyInto(
                    input,
                    output);

            long end =
                    System.nanoTime();

            totalNs +=
                    end - start;
        }

        return totalNs;
    }

    private static long measureParallel(
            SparseMatrixCSR matrix,
            double[] input,
            double[] output,
            int iterations,
            int threshold,
            ForkJoinPool pool) {

        long totalNs =
                0L;

        for (int i = 0;
             i < iterations;
             i++) {

            long start =
                    System.nanoTime();

            matrix.multiplyParallelInto(
                    input,
                    output,
                    threshold,
                    pool);

            long end =
                    System.nanoTime();

            totalNs +=
                    end - start;
        }

        return totalNs;
    }

    private static double calculateThroughput(
            int n,
            double averageMs) {

        if (averageMs <= 0.0) {
            return Double.POSITIVE_INFINITY;
        }

        return n
                / (averageMs / 1000.0);
    }

    private static double maxAbsoluteError(
            double[] first,
            double[] second) {

        if (first.length != second.length) {
            return Double.POSITIVE_INFINITY;
        }

        double maxError =
                0.0;

        for (int i = 0;
             i < first.length;
             i++) {

            double error =
                    Math.abs(
                            first[i]
                                    - second[i]);

            if (error > maxError) {
                maxError =
                        error;
            }
        }

        return maxError;
    }

    private static double maxExpectedError(
            double[] values,
            double expected) {

        double maxError =
                0.0;

        for (double value : values) {

            double error =
                    Math.abs(
                            value
                                    - expected);

            if (error > maxError) {
                maxError =
                        error;
            }
        }

        return maxError;
    }

    private static void printConfiguration(
            BenchmarkConfig config) {

        System.out.println();

        System.out.println(
                "==============================================");

        System.out.println(
                " QFLPN CSR BENCHMARK");

        System.out.println(
                "==============================================");

        System.out.printf(
                Locale.ROOT,
                "N               : %,d%n",
                config.n());

        System.out.printf(
                Locale.ROOT,
                "Warmup          : %d%n",
                config.warmup());

        System.out.printf(
                Locale.ROOT,
                "Iterations      : %d%n",
                config.iterations());

        System.out.printf(
                Locale.ROOT,
                "Threshold       : %d%n",
                config.threshold());

        System.out.printf(
                Locale.ROOT,
                "Parallelism     : %d%n",
                config.parallelism());

        System.out.printf(
                Locale.ROOT,
                "Available CPUs  : %d%n",
                Runtime.getRuntime()
                        .availableProcessors());
    }

    private static void printResults(
            BenchmarkConfig config,
            SparseMatrixCSR matrix,
            double setupTimeMs,
            double sequentialAverageMs,
            double parallelAverageMs,
            double speedup,
            double sequentialThroughput,
            double parallelThroughput,
            double sequentialExpectedError,
            double parallelExpectedError,
            double maxAbsoluteError,
            boolean sequentialCorrect,
            boolean parallelCorrect,
            boolean resultsMatch) {

        System.out.println();

        System.out.println(
                "==============================================");

        System.out.println(
                " QFLPN CSR PERFORMANCE RESULT");

        System.out.println(
                "==============================================");

        System.out.printf(
                Locale.ROOT,
                "N               : %,d%n",
                config.n());

        System.out.printf(
                Locale.ROOT,
                "NNZ             : %,d%n",
                matrix.getNnz());

        System.out.printf(
                Locale.ROOT,
                "Density         : %.12e%n",
                matrix.getDensity());

        System.out.printf(
                Locale.ROOT,
                "Setup time      : %.3f ms%n",
                setupTimeMs);

        System.out.printf(
                Locale.ROOT,
                "Sequential avg  : %.3f ms%n",
                sequentialAverageMs);

        System.out.printf(
                Locale.ROOT,
                "Parallel avg    : %.3f ms%n",
                parallelAverageMs);

        System.out.printf(
                Locale.ROOT,
                "Speedup         : %.4fx%n",
                speedup);

        System.out.printf(
                Locale.ROOT,
                "Seq throughput  : %.3f states/s%n",
                sequentialThroughput);

        System.out.printf(
                Locale.ROOT,
                "Par throughput  : %.3f states/s%n",
                parallelThroughput);

        System.out.printf(
                Locale.ROOT,
                "Seq expected err: %.12e%n",
                sequentialExpectedError);

        System.out.printf(
                Locale.ROOT,
                "Par expected err: %.12e%n",
                parallelExpectedError);

        System.out.printf(
                Locale.ROOT,
                "Seq/Par max err : %.12e%n",
                maxAbsoluteError);

        System.out.println(
                "Sequential      : "
                        + (sequentialCorrect
                        ? "PASS"
                        : "FAIL"));

        System.out.println(
                "Parallel        : "
                        + (parallelCorrect
                        ? "PASS"
                        : "FAIL"));

        System.out.println(
                "Seq/Par match   : "
                        + (resultsMatch
                        ? "PASS"
                        : "FAIL"));

        System.out.println(
                "==============================================");
    }

    private static void printMemoryEstimate(
            int n) {

        long nnz =
                2L * n;

        long valuesBytes =
                nnz * (long) Double.BYTES;

        long columnsBytes =
                nnz * (long) Integer.BYTES;

        long rowPointersBytes =
                (n + 1L)
                        * (long) Integer.BYTES;

        long inputBytes =
                n * (long) Double.BYTES;

        long outputBytes =
                n * (long) Double.BYTES;

        /*
         * Memoria pentru tablourile originale.
         */
        long originalArrays =
                valuesBytes
                        + columnsBytes
                        + rowPointersBytes
                        + inputBytes
                        + outputBytes;

        /*
         * SparseMatrixCSR face copii defensive ale celor
         * trei tablouri CSR în constructor.
         *
         * Prin urmare, în etapa actuală trebuie considerată
         * și această memorie suplimentară.
         */
        long csrDefensiveCopies =
                valuesBytes
                        + columnsBytes
                        + rowPointersBytes;

        long estimatedPeak =
                originalArrays
                        + csrDefensiveCopies;

        System.out.println();

        System.out.println(
                "[MEMORY ESTIMATE]");

        System.out.printf(
                Locale.ROOT,
                "CSR values      : %.3f MiB%n",
                toMiB(valuesBytes));

        System.out.printf(
                Locale.ROOT,
                "CSR columns     : %.3f MiB%n",
                toMiB(columnsBytes));

        System.out.printf(
                Locale.ROOT,
                "CSR rowPointers : %.3f MiB%n",
                toMiB(rowPointersBytes));

        System.out.printf(
                Locale.ROOT,
                "Input vector    : %.3f MiB%n",
                toMiB(inputBytes));

        System.out.printf(
                Locale.ROOT,
                "Output vector   : %.3f MiB%n",
                toMiB(outputBytes));

        System.out.printf(
                Locale.ROOT,
                "Original arrays : %.3f MiB%n",
                toMiB(originalArrays));

        System.out.printf(
                Locale.ROOT,
                "CSR copies      : %.3f MiB%n",
                toMiB(csrDefensiveCopies));

        System.out.printf(
                Locale.ROOT,
                "Estimated peak  : %.3f MiB%n",
                toMiB(estimatedPeak));

        System.out.println(
                "Note: JVM overhead and runtime allocations "
                        + "are not included.");
    }

    private static double toMiB(
            long bytes) {

        return bytes
                / (1024.0 * 1024.0);
    }

    private record BenchmarkConfig(
            int n,
            int warmup,
            int iterations,
            int threshold,
            int parallelism) {

        private static BenchmarkConfig fromArgs(
                String[] args) {

            int n =
                    DEFAULT_N;

            int warmup =
                    DEFAULT_WARMUP;

            int iterations =
                    DEFAULT_ITERATIONS;

            int threshold =
                    DEFAULT_THRESHOLD;

            int parallelism =
                    Math.max(
                            1,
                            Runtime.getRuntime()
                                    .availableProcessors());

            for (String arg : args) {

                if (arg.startsWith("--n=")) {

                    n =
                            parsePositiveInt(
                                    arg,
                                    "--n=");

                } else if (arg.startsWith(
                        "--warmup=")) {

                    warmup =
                            parseNonNegativeInt(
                                    arg,
                                    "--warmup=");

                } else if (arg.startsWith(
                        "--iterations=")) {

                    iterations =
                            parsePositiveInt(
                                    arg,
                                    "--iterations=");

                } else if (arg.startsWith(
                        "--threshold=")) {

                    threshold =
                            parsePositiveInt(
                                    arg,
                                    "--threshold=");

                } else if (arg.startsWith(
                        "--parallelism=")) {

                    parallelism =
                            parsePositiveInt(
                                    arg,
                                    "--parallelism=");

                } else {

                    throw new IllegalArgumentException(
                            "Unknown argument: "
                                    + arg);
                }
            }

            return new BenchmarkConfig(
                    n,
                    warmup,
                    iterations,
                    threshold,
                    parallelism);
        }

        private static int parsePositiveInt(
                String argument,
                String prefix) {

            int value =
                    Integer.parseInt(
                            argument.substring(
                                    prefix.length()));

            if (value <= 0) {
                throw new IllegalArgumentException(
                        prefix
                                + " must be greater than zero.");
            }

            return value;
        }

        private static int parseNonNegativeInt(
                String argument,
                String prefix) {

            int value =
                    Integer.parseInt(
                            argument.substring(
                                    prefix.length()));

            if (value < 0) {
                throw new IllegalArgumentException(
                        prefix
                                + " cannot be negative.");
            }

            return value;
        }
    }
}