package hpc.csr;

import java.util.Locale;

/**
 * BenchmarkRunner
 *
 * Instrument separat pentru măsurarea performanței nucleului CSR QFLPN.
 *
 * IMPORTANT:
 * Acest program NU este un test JUnit și NU trebuie executat automat
 * în CI. Este destinat măsurătorilor controlate de performanță.
 *
 * Configurație:
 *
 * --n=<N>
 *     dimensiunea matricei pătratice.
 *
 * --warmup=<W>
 *     numărul de rulări de încălzire.
 *
 * --iterations=<I>
 *     numărul de rulări măsurate.
 *
 * --threshold=<T>
 *     pragul Fork/Join.
 *
 * --parallelism=<P>
 *     nivelul de paralelism.
 *
 * Exemple:
 *
 * java ... BenchmarkRunner --n=1000000
 *
 * java ... BenchmarkRunner --n=30000000 \
 *      --warmup=2 \
 *      --iterations=3 \
 *      --threshold=4096 \
 *      --parallelism=8
 *
 * Structura de test utilizează două elemente nenule pe rând:
 *
 * A[i,i]   = 1.0
 * A[i,i+1] = 0.5
 *
 * pentru ultimul rând, a doua coloană se întoarce circular la 0.
 *
 * Astfel:
 *
 * NNZ = 2 * N
 *
 * iar matricea rămâne rară și reprezentativă pentru un test CSR
 * de tip sparse matrix-vector multiplication.
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

        long allocationStart =
                System.nanoTime();

        SparseMatrixCSR matrix =
                createBenchmarkMatrix(config.n());

        double[] input =
                createInputVector(config.n());

        double[] sequentialOutput =
                new double[config.n()];

        double[] parallelOutput =
                new double[config.n()];

        long allocationEnd =
                System.nanoTime();

        double allocationTimeMs =
                nanosToMillis(
                        allocationEnd - allocationStart);

        System.out.println();
        System.out.printf(
                Locale.ROOT,
                "Setup time      : %.3f ms%n",
                allocationTimeMs);

        printMemoryEstimate(config.n());

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
                config.parallelism());

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
                        config.parallelism());

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
                config.n()
                        / (sequentialAverageMs / 1000.0);

        double parallelThroughput =
                config.n()
                        / (parallelAverageMs / 1000.0);

        double maxAbsoluteError =
                maxAbsoluteError(
                        sequentialOutput,
                        parallelOutput);

        boolean numericalMatch =
                maxAbsoluteError <= 1.0e-12;

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
                "Max abs error   : %.12e%n",
                maxAbsoluteError);

        System.out.println(
                "Numerical match : "
                        + (numericalMatch
                        ? "PASS"
                        : "FAIL"));

        System.out.println(
                "==============================================");

        if (!numericalMatch) {
            throw new IllegalStateException(
                    "Sequential and parallel results differ "
                            + "beyond tolerance.");
        }
    }

    private static SparseMatrixCSR createBenchmarkMatrix(
            int n) {

        long nnzLong =
                2L * n;

        if (nnzLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "NNZ exceeds Java array limits: "
                            + nnzLong);
        }

        int nnz =
                (int) nnzLong;

        double[] values =
                new double[nnz];

        int[] columns =
                new int[nnz];

        int[] rowPointers =
                new int[n + 1];

        for (int row = 0; row < n; row++) {

            int base =
                    2 * row;

            values[base] = 1.0;
            values[base + 1] = 0.5;

            columns[base] = row;

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

    private static double[] createInputVector(
            int n) {

        double[] input =
                new double[n];

        for (int i = 0; i < n; i++) {
            input[i] = 1.0;
        }

        return input;
    }

    private static void warmupSequential(
            SparseMatrixCSR matrix,
            double[] input,
            double[] output,
            int warmup) {

        for (int i = 0; i < warmup; i++) {

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
            int parallelism) {

        for (int i = 0; i < warmup; i++) {

            matrix.multiplyParallelInto(
                    input,
                    output,
                    threshold,
                    parallelism);
        }
    }

    private static long measureSequential(
            SparseMatrixCSR matrix,
            double[] input,
            double[] output,
            int iterations) {

        long totalNs = 0L;

        for (int i = 0; i < iterations; i++) {

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
            int parallelism) {

        long totalNs = 0L;

        for (int i = 0; i < iterations; i++) {

            long start =
                    System.nanoTime();

            matrix.multiplyParallelInto(
                    input,
                    output,
                    threshold,
                    parallelism);

            long end =
                    System.nanoTime();

            totalNs +=
                    end - start;
        }

        return totalNs;
    }

    private static double maxAbsoluteError(
            double[] first,
            double[] second) {

        if (first.length != second.length) {
            return Double.POSITIVE_INFINITY;
        }

        double maxError = 0.0;

        for (int i = 0; i < first.length; i++) {

            double error =
                    Math.abs(
                            first[i] - second[i]);

            if (error > maxError) {
                maxError = error;
            }
        }

        return maxError;
    }

    private static double nanosToMillis(
            long nanos) {

        return nanos / 1_000_000.0;
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
    }

    private static void printMemoryEstimate(
            int n) {

        long nnz =
                2L * n;

        long valuesBytes =
                nnz * Double.BYTES;

        long columnBytes =
                nnz * Integer.BYTES;

        long rowPointerBytes =
                (n + 1L) * Integer.BYTES;

        long inputBytes =
                n * (long) Double.BYTES;

        long outputBytes =
                n * (long) Double.BYTES;

        long rawWorkingSetBytes =
                valuesBytes
                        + columnBytes
                        + rowPointerBytes
                        + inputBytes
                        + outputBytes;

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
                toMiB(columnBytes));

        System.out.printf(
                Locale.ROOT,
                "CSR rowPointers : %.3f MiB%n",
                toMiB(rowPointerBytes));

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
                "Raw working set : %.3f MiB%n",
                toMiB(rawWorkingSetBytes));

        System.out.println(
                "Note: JVM/object overhead and defensive"
                        + " CSR copies are not included.");
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
