package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.jupiter.api.Test;

/**
 * Regression tests for the SpmvStrategy implementations.
 *
 * Central properties:
 *  1. every strategy is BITWISE identical to the sequential kernel;
 *  2. no worker thread is created per multiplication after pool warmup;
 *  3. caller-owned pools are never shut down;
 *  4. chunk partitions are valid, aligned and NNZ-balanced.
 */
class SpmvStrategyTest {

    private static final int[] PARALLELISMS = {1, 2, 3, 4};

    // ---- deterministic generators -------------------------------------

    static SparseMatrixCSR uniform(int n, int perRow, long seed) {
        Random random = new Random(seed);
        double[] values = new double[n * perRow];
        int[] columns = new int[n * perRow];
        int[] pointers = new int[n + 1];

        for (int row = 0; row < n; row++) {
            for (int k = 0; k < perRow; k++) {
                values[row * perRow + k] = random.nextDouble() * 2.0 - 1.0;
                columns[row * perRow + k] = (row + k) % n;
            }
            pointers[row + 1] = (row + 1) * perRow;
        }

        return new SparseMatrixCSR(values, columns, pointers, n, n);
    }

    static SparseMatrixCSR skewed(int n, long seed) {
        Random random = new Random(seed);
        int[] pointers = new int[n + 1];
        int[] counts = new int[n];
        int total = 0;

        for (int row = 0; row < n; row++) {
            double u = random.nextDouble();
            int count;

            if (u < 0.25) {
                count = 0;
            } else if (u < 0.97) {
                count = 1 + random.nextInt(4);
            } else {
                count = Math.min(n, 50 + random.nextInt(300));
            }

            counts[row] = count;
            total += count;
            pointers[row + 1] = total;
        }

        double[] values = new double[total];
        int[] columns = new int[total];

        for (int row = 0; row < n; row++) {
            int step = Math.max(1, n / Math.max(1, counts[row]));

            for (int k = 0; k < counts[row]; k++) {
                int index = pointers[row] + k;
                columns[index] = (int) (((long) k * step + row) % n);
                values[index] = random.nextGaussian();
            }
        }

        return new SparseMatrixCSR(values, columns, pointers, n, n);
    }

    static SparseMatrixCSR singleHugeRow(int n, long seed) {
        Random random = new Random(seed);
        int hugeRow = n / 2;
        double[] values = new double[(n - 1) + n];
        int[] columns = new int[(n - 1) + n];
        int[] pointers = new int[n + 1];
        int position = 0;

        for (int row = 0; row < n; row++) {
            if (row == hugeRow) {
                for (int c = 0; c < n; c++) {
                    values[position] = random.nextGaussian();
                    columns[position++] = c;
                }
            } else {
                values[position] = random.nextGaussian();
                columns[position++] = row;
            }
            pointers[row + 1] = position;
        }

        return new SparseMatrixCSR(values, columns, pointers, n, n);
    }

    static double[] vector(int n, long seed) {
        Random random = new Random(seed);
        double[] x = new double[n];

        for (int i = 0; i < n; i++) {
            x[i] = random.nextDouble() * 4.0 - 2.0;
        }

        return x;
    }

    static void assertBitwiseEqual(double[] expected, double[] actual) {
        assertEquals(expected.length, actual.length);

        for (int i = 0; i < expected.length; i++) {
            assertEquals(
                    Double.doubleToLongBits(expected[i]),
                    Double.doubleToLongBits(actual[i]),
                    "bitwise mismatch at row " + i);
        }
    }

    // ---- bitwise equality ---------------------------------------------

    @Test
    void everyStrategyIsBitwiseIdenticalOnEveryStructure() {
        List<SparseMatrixCSR> matrices = List.of(
                uniform(30_000, 2, 1L),
                skewed(15_000, 2L),
                singleHugeRow(3_000, 3L),
                uniform(1, 1, 4L),
                uniform(7, 2, 5L),
                uniform(17, 3, 6L));

        for (SparseMatrixCSR matrix : matrices) {
            double[] x = vector(matrix.getColumns(), 99L);
            double[] expected = matrix.multiply(x);

            for (String name : SpmvStrategies.names()) {
                for (int p : PARALLELISMS) {
                    try (SpmvStrategy strategy =
                                 SpmvStrategies.create(name, matrix, p)) {
                        assertEquals(name, strategy.name());
                        assertBitwiseEqual(expected, strategy.multiply(x));
                    }
                }
            }
        }
    }

    @Test
    void emptyMatrixWorksForEveryStrategy() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0], new int[0], new int[] {0}, 0, 0);

        for (String name : SpmvStrategies.names()) {
            try (SpmvStrategy strategy =
                         SpmvStrategies.create(name, matrix, 4)) {
                assertEquals(0, strategy.multiply(new double[0]).length);
            }
        }
    }

    @Test
    void rowsWithoutEntriesProduceZerosAndOverwriteTheOutput() {
        int n = 2_000;
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0], new int[0], new int[n + 1], n, n);

        for (String name : SpmvStrategies.names()) {
            try (SpmvStrategy strategy =
                         SpmvStrategies.create(name, matrix, 4)) {
                double[] y = new double[n];
                java.util.Arrays.fill(y, 42.0);
                strategy.multiplyInto(vector(n, 7L), y);

                for (double value : y) {
                    assertEquals(0.0, value, 0.0);
                }
            }
        }
    }

    @Test
    void inPlaceMultiplicationMatchesOutOfPlace() {
        SparseMatrixCSR matrix = skewed(10_000, 8L);
        double[] x = vector(10_000, 9L);
        double[] expected = matrix.multiply(x);

        for (String name : SpmvStrategies.names()) {
            try (SpmvStrategy strategy =
                         SpmvStrategies.create(name, matrix, 3)) {
                double[] aliased = x.clone();
                strategy.multiplyInto(aliased, aliased);
                assertBitwiseEqual(expected, aliased);
            }
        }
    }

    @Test
    void aReusedStrategyStaysCorrectOverManyIterations() {
        SparseMatrixCSR matrix = uniform(20_000, 2, 10L);
        double[] reference = vector(20_000, 11L);

        for (String name : SpmvStrategies.names()) {
            double[] current = reference.clone();
            double[] oracle = reference.clone();

            try (SpmvStrategy strategy =
                         SpmvStrategies.create(name, matrix, 4)) {
                for (int step = 0; step < 50; step++) {
                    oracle = matrix.multiply(oracle);
                    current = strategy.multiply(current);
                    scale(oracle);
                    scale(current);
                }
            }

            assertBitwiseEqual(oracle, current);
        }
    }

    private static void scale(double[] v) {
        double norm = 0.0;

        for (double value : v) {
            norm += value * value;
        }

        norm = Math.sqrt(norm);

        if (norm > 0.0) {
            for (int i = 0; i < v.length; i++) {
                v[i] /= norm;
            }
        }
    }

    // ---- no per-call worker threads or pools ---------------------------

    @Test
    void noWorkerThreadsAreCreatedDuringRepeatedMultiplications() {
        SparseMatrixCSR matrix = uniform(200_000, 2, 12L);
        double[] x = vector(200_000, 13L);
        double[] y = new double[200_000];

        for (String name : List.of(
                PlannedForkJoinSpmvStrategy.NAME,
                StaticChunkSpmvStrategy.NAME)) {

            AtomicInteger createdWorkers = new AtomicInteger();

            ForkJoinPool.ForkJoinWorkerThreadFactory workerFactory =
                    ownerPool -> {
                        createdWorkers.incrementAndGet();
                        return ForkJoinPool
                                .defaultForkJoinWorkerThreadFactory
                                .newThread(ownerPool);
                    };

            ForkJoinPool pool = new ForkJoinPool(
                    2,
                    workerFactory,
                    null,
                    false);

            try {
                SpmvStrategy strategy;

                if (PlannedForkJoinSpmvStrategy.NAME.equals(name)) {
                    strategy = new PlannedForkJoinSpmvStrategy(
                            matrix, 2, 4096, pool);
                } else {
                    strategy = new StaticChunkSpmvStrategy(
                            matrix, 2, 4, pool);
                }

                try (strategy) {
                    // Warmup: worker creation is allowed here.
                    for (int i = 0; i < 100; i++) {
                        strategy.multiplyInto(x, y);
                    }

                    int workersAfterWarmup = createdWorkers.get();

                    assertTrue(
                            workersAfterWarmup > 0,
                            name + " did not create any worker thread");

                    // Hot loop: no additional worker may be created.
                    for (int i = 0; i < 300; i++) {
                        strategy.multiplyInto(x, y);
                    }

                    int workersAfterHotLoop = createdWorkers.get();

                    assertEquals(
                            workersAfterWarmup,
                            workersAfterHotLoop,
                            name + " created additional worker threads "
                                    + "inside the hot loop");

                    assertFalse(
                            pool.isShutdown(),
                            name + " shut down a caller-owned pool");
                }
            } finally {
                pool.shutdown();
            }
        }
    }

    // ---- lifecycle and pools -------------------------------------------

    @Test
    void closedStrategyRejectsMultiplication() {
        SparseMatrixCSR matrix = uniform(1_000, 2, 14L);

        for (String name : SpmvStrategies.names()) {
            SpmvStrategy strategy = SpmvStrategies.create(name, matrix, 2);
            strategy.close();

            assertTrue(strategy.isClosed());
            assertThrows(IllegalStateException.class,
                    () -> strategy.multiply(new double[1_000]));
            strategy.close();
        }
    }

    @Test
    void callerOwnedPoolIsNeverShutDown() {
        SparseMatrixCSR matrix = uniform(100_000, 2, 15L);
        double[] x = vector(100_000, 16L);
        double[] expected = matrix.multiply(x);
        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            try (SpmvStrategy planned = new PlannedForkJoinSpmvStrategy(
                    matrix, 2, 4096, pool)) {
                assertBitwiseEqual(expected, planned.multiply(x));
            }

            try (SpmvStrategy fixed = new StaticChunkSpmvStrategy(
                    matrix, 2, 4, pool)) {
                assertBitwiseEqual(expected, fixed.multiply(x));
            }

            assertFalse(pool.isShutdown());
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void concurrentMultiplicationsOnOneStrategyAreSafe() throws Exception {
        SparseMatrixCSR matrix = skewed(15_000, 17L);
        double[] x = vector(15_000, 18L);
        double[] expected = matrix.multiply(x);
        ExecutorService callers = Executors.newFixedThreadPool(4);

        try {
            for (String name : SpmvStrategies.names()) {
                try (SpmvStrategy strategy =
                             SpmvStrategies.create(name, matrix, 4)) {
                    List<Future<double[]>> futures = new ArrayList<>();

                    for (int i = 0; i < 24; i++) {
                        futures.add(callers.submit(
                                () -> strategy.multiply(x)));
                    }

                    for (Future<double[]> future : futures) {
                        assertBitwiseEqual(expected, future.get());
                    }
                }
            }
        } finally {
            callers.shutdown();
        }
    }

    // ---- validation ----------------------------------------------------

    @Test
    void rejectsInvalidArguments() {
        SparseMatrixCSR matrix = uniform(100, 2, 19L);

        assertThrows(NullPointerException.class,
                () -> SpmvStrategies.create(null, matrix, 2));
        assertThrows(NullPointerException.class,
                () -> SpmvStrategies.create("SEQ", null, 2));
        assertThrows(IllegalArgumentException.class,
                () -> SpmvStrategies.create("NOPE", matrix, 2));
        assertThrows(IllegalArgumentException.class,
                () -> new StaticChunkSpmvStrategy(matrix, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new StaticChunkSpmvStrategy(matrix, 2, 0, null));
        assertThrows(IllegalArgumentException.class,
                () -> new PlannedForkJoinSpmvStrategy(matrix, 0));

        for (String name : SpmvStrategies.names()) {
            try (SpmvStrategy strategy =
                         SpmvStrategies.create(name, matrix, 2)) {
                assertThrows(RuntimeException.class,
                        () -> strategy.multiplyInto(null, new double[100]));
                assertThrows(RuntimeException.class,
                        () -> strategy.multiplyInto(new double[100], null));
                assertThrows(IllegalArgumentException.class,
                        () -> strategy.multiplyInto(
                                new double[99], new double[100]));
                assertThrows(IllegalArgumentException.class,
                        () -> strategy.multiplyInto(
                                new double[100], new double[99]));
            }
        }
    }

    // ---- static partition invariants ----------------------------------

    @Test
    void chunkBoundsAreValidMonotoneAndCoverAllRows() {
        SparseMatrixCSR matrix = skewed(30_000, 20L);

        for (int p : PARALLELISMS) {
            for (int chunksPerThread : new int[] {1, 4, 32}) {
                try (StaticChunkSpmvStrategy strategy =
                             new StaticChunkSpmvStrategy(
                                     matrix, p, chunksPerThread, null)) {
                    int[] bounds = strategy.getChunkBounds();

                    assertEquals(0, bounds[0]);
                    assertEquals(matrix.getRows(), bounds[bounds.length - 1]);
                    assertEquals(strategy.getChunkCount(), bounds.length - 1);

                    for (int k = 1; k < bounds.length; k++) {
                        assertTrue(bounds[k] > bounds[k - 1],
                                "empty or reversed chunk " + k);
                    }
                }
            }
        }
    }

    @Test
    void interiorBoundariesAreAlignedToEightRows() {
        SparseMatrixCSR matrix = uniform(100_000, 2, 21L);

        try (StaticChunkSpmvStrategy strategy =
                     new StaticChunkSpmvStrategy(matrix, 4, 8, null)) {
            int[] bounds = strategy.getChunkBounds();

            for (int k = 1; k < bounds.length - 1; k++) {
                assertEquals(0,
                        bounds[k] % StaticChunkSpmvStrategy.ROW_ALIGNMENT,
                        "unaligned boundary " + bounds[k]);
            }
        }
    }

    @Test
    void uniformMatrixChunksAreNnzBalanced() {
        SparseMatrixCSR matrix = uniform(200_000, 2, 22L);
        int[] pointers = matrix.getRowPointers();

        try (StaticChunkSpmvStrategy strategy =
                     new StaticChunkSpmvStrategy(matrix, 4, 4, null)) {
            int[] bounds = strategy.getChunkBounds();
            double ideal = (double) matrix.getNnz() / strategy.getChunkCount();

            for (int k = 0; k < strategy.getChunkCount(); k++) {
                double chunkNnz =
                        pointers[bounds[k + 1]] - pointers[bounds[k]];
                assertTrue(Math.abs(chunkNnz - ideal) / ideal < 0.01,
                        "chunk " + k + " holds " + chunkNnz
                                + ", ideal " + ideal);
            }
        }
    }

    @Test
    void singleWorkerUsesOneChunkAndNoPool() {
        SparseMatrixCSR matrix = uniform(10_000, 2, 23L);

        try (StaticChunkSpmvStrategy strategy =
                     new StaticChunkSpmvStrategy(matrix, 1)) {
            assertEquals(1, strategy.getChunkCount());
            assertEquals(1, strategy.parallelism());
        }
    }
}
