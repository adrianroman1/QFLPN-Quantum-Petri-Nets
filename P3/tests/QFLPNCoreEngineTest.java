package hpc.csr;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

class QFLPNCoreEngineTest {

    private static final int N = 4;
    private static final double TOLERANCE = 1.0e-12;

    private static double[] values() {
        return new double[] {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };
    }

    private static int[] columns() {
        return new int[] {
                0, 2,
                1, 3,
                0, 2,
                1, 3
        };
    }

    private static int[] rowPointers() {
        return new int[] {0, 2, 4, 6, 8};
    }

    private static double[] input() {
        return new double[] {1.0, 2.0, 3.0, 4.0};
    }

    private static double[] expected() {
        return new double[] {7.0, 22.0, 23.0, 46.0};
    }

    private static SparseMatrixCSR createMatrix() {
        return new SparseMatrixCSR(
                values(), columns(), rowPointers(), N, N);
    }

    private static SparseMatrixCSR createDifferentCsrDistribution() {
        /*
         * Same dimensions and NNZ as createMatrix(), but a different
         * distribution of non-zero elements among rows.
         *
         * Original rowPointers:  [0, 2, 4, 6, 8]
         * Replacement rowPointers: [0, 1, 3, 6, 8]
         */
        return new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0, 3.0, 4.0,
                        5.0, 6.0, 7.0, 8.0
                },
                new int[] {
                        0, 0, 2, 1, 3, 0, 2, 1
                },
                new int[] {0, 1, 3, 6, 8},
                N,
                N);
    }

    private static QFLPNCoreEngine createLoadedEngine() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);
        engine.loadCSR(values(), columns(), rowPointers());
        return engine;
    }

    @Test
    void shouldStoreConfiguration() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);
        try {
            assertEquals(N, engine.getDimension());
            assertEquals(2, engine.getParallelism());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidConstructorArguments() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(0, 2));

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(-1, 2));

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(N, 0));

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(N, -1));
    }

    @Test
    void shouldRejectOperationsBeforeMatrixLoad() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiply(input()));

            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiplyParallel(input()));

            assertThrows(
                    IllegalStateException.class,
                    engine::getMatrix);

            assertThrows(
                    IllegalStateException.class,
                    engine::getSpmvPlan);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadCSRAndExposeMetadata() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertEquals(8, engine.getNonZeroCount());
            assertEquals(0.5, engine.getMatrixDensity(), TOLERANCE);
            assertTrue(engine.getMatrix().isValid());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadExistingMatrix() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);
        SparseMatrixCSR matrix = createMatrix();

        try {
            engine.loadMatrix(matrix);

            assertSame(matrix, engine.getMatrix());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullMatrixAndCsrArguments() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadMatrix(null));

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            null,
                            columns(),
                            rowPointers()));

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            values(),
                            null,
                            rowPointers()));

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            values(),
                            columns(),
                            null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidCsrAndDimensionMismatch() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            values(),
                            columns(),
                            new int[] {0, 2, 4, 6, 7}));

            SparseMatrixCSR wrongSize = new SparseMatrixCSR(
                    new double[] {1.0},
                    new int[] {0},
                    new int[] {0, 1},
                    1,
                    1);

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadMatrix(wrongSize));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeSequentialResult() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiply(input()),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeParallelResult() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input()),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeWithExplicitParallelConfiguration() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input(), 1, 3),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void sequentialAndParallelResultsShouldMatch() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertArrayEquals(
                    engine.multiply(input()),
                    engine.multiplyParallel(input()),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldCreatePlanWhenLoadingCsrMatrix() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan plan = engine.getSpmvPlan();

            assertNotNull(plan);
            assertEquals(N, plan.getRows());
            assertEquals(8, plan.getNnz());
            assertEquals(2, plan.getParallelism());
            assertEquals(
                    MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                    plan.getSplitPolicy());

            assertTrue(
                    plan.isCompatibleWith(
                            engine.getMatrix().getRowPointers()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReuseSamePlanAcrossRepeatedMultiplications() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan originalPlan = engine.getSpmvPlan();

            for (int i = 0; i < 10; i++) {
                assertArrayEquals(
                        expected(),
                        engine.multiplyParallel(input()),
                        TOLERANCE);

                assertSame(
                        originalPlan,
                        engine.getSpmvPlan());
            }

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRebuildPlanWhenMatrixIsReplaced() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan originalPlan = engine.getSpmvPlan();

            SparseMatrixCSR replacement =
                    createDifferentCsrDistribution();

            engine.loadMatrix(replacement);

            SpmvPlan replacementPlan = engine.getSpmvPlan();

            assertNotSame(originalPlan, replacementPlan);

            assertTrue(
                    replacementPlan.isCompatibleWith(
                            replacement.getRowPointers()));

            assertFalse(
                    originalPlan.isCompatibleWith(
                            replacement.getRowPointers()));

            assertEquals(
                    replacement.getNnz(),
                    replacementPlan.getNnz());

            assertEquals(
                    replacement.getRows(),
                    replacementPlan.getRows());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldUseExactCsrStructureForLoadedPlan() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan plan = engine.getSpmvPlan();

            int[] differentDistribution =
                    new int[] {0, 1, 3, 6, 8};

            /*
             * Same number of rows and same total NNZ do not establish
             * structural compatibility.
             */
            assertEquals(N + 1, differentDistribution.length);
            assertEquals(8, differentDistribution[N]);

            assertFalse(
                    plan.isCompatibleWith(differentDistribution));

            assertTrue(
                    plan.isCompatibleWith(rowPointers()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldKeepPlanSnapshotIndependentFromInputRowPointers() {
        int[] sourceRowPointers = rowPointers();

        SpmvPlan plan = SpmvPlan.create(
                sourceRowPointers,
                1,
                2,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT);

        sourceRowPointers[1] = 1;
        sourceRowPointers[2] = 3;

        assertTrue(
                plan.isCompatibleWith(
                        new int[] {0, 2, 4, 6, 8}));

        assertFalse(
                plan.isCompatibleWith(sourceRowPointers));
    }

    @Test
    void shouldReturnDefensiveCopiesOfPlanPartitionBoundaries() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan plan = engine.getSpmvPlan();

            int[] starts = plan.getStartRows();
            int[] ends = plan.getEndRows();

            int originalStart = plan.getStartRow(0);
            int originalEnd = plan.getEndRow(0);

            starts[0] = 1000;
            ends[0] = 1000;

            assertEquals(originalStart, plan.getStartRow(0));
            assertEquals(originalEnd, plan.getEndRow(0));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReusePersistentPool() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            double[] first = engine.multiplyParallel(input());
            double[] second = engine.multiplyParallel(input());

            assertArrayEquals(first, second, TOLERANCE);
            assertFalse(engine.isShutdown());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldKeepPersistentPoolActiveAfterRepeatedMultiplications() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            for (int i = 0; i < 20; i++) {
                assertArrayEquals(
                        expected(),
                        engine.multiplyParallel(input()),
                        TOLERANCE);

                assertFalse(engine.isShutdown());
            }

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidVectorAndParallelConfiguration() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.multiply(null));

            assertThrows(
                    NullPointerException.class,
                    () -> engine.multiplyParallel(null));

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiply(
                            new double[] {1.0, 2.0}));

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            input(), 0, 2));

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            input(), 1, 0));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldPreservePreviousMatrixAndPlanAfterFailedReplacement() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SparseMatrixCSR originalMatrix = engine.getMatrix();
            SpmvPlan originalPlan = engine.getSpmvPlan();

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            values(),
                            columns(),
                            new int[] {0, 2, 4, 6, 7}));

            assertSame(originalMatrix, engine.getMatrix());
            assertSame(originalPlan, engine.getSpmvPlan());

            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input()),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReplaceMatrixBetweenOperations() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiply(input()),
                    TOLERANCE);

            SparseMatrixCSR replacement = new SparseMatrixCSR(
                    new double[] {2.0},
                    new int[] {0},
                    new int[] {0, 1, 1, 1, 1},
                    N,
                    N);

            engine.loadMatrix(replacement);

            assertArrayEquals(
                    new double[] {2.0, 0.0, 0.0, 0.0},
                    engine.multiply(input()),
                    TOLERANCE);

            assertTrue(
                    engine.getSpmvPlan().isCompatibleWith(
                            replacement.getRowPointers()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void concurrentMultiplicationsShouldReturnCorrectResults()
            throws Exception {

        QFLPNCoreEngine engine = createLoadedEngine();
        ExecutorService executor = Executors.newFixedThreadPool(4);

        try {
            List<Future<double[]>> futures = new ArrayList<>();

            for (int i = 0; i < 16; i++) {
                futures.add(executor.submit(
                        () -> engine.multiplyParallel(input())));
            }

            for (Future<double[]> future : futures) {
                assertArrayEquals(
                        expected(),
                        future.get(10, TimeUnit.SECONDS),
                        TOLERANCE);
            }

        } finally {
            executor.shutdownNow();
            engine.shutdown();
        }
    }

    @Test
    void shutdownShouldBeIdempotent() {
        QFLPNCoreEngine engine = createLoadedEngine();

        engine.shutdown();
        engine.shutdown();

        assertTrue(engine.isShutdown());
    }

    @Test
    void operationsAfterShutdownShouldBeRejected() {
        QFLPNCoreEngine engine = createLoadedEngine();

        engine.shutdown();

        assertTrue(engine.isShutdown());

        assertThrows(
                IllegalStateException.class,
                engine::getMatrix);

        assertThrows(
                IllegalStateException.class,
                engine::getSpmvPlan);

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiply(input()));

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiplyParallel(input()));

        assertThrows(
                IllegalStateException.class,
                () -> engine.loadCSR(
                        values(),
                        columns(),
                        rowPointers()));
    }

    @Test
    void toStringShouldDescribeEngineState() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertTrue(
                    engine.toString().contains("matrix=not-loaded"));

            engine.loadCSR(values(), columns(), rowPointers());

            assertTrue(
                    engine.toString().contains("nonZeroCount=8"));

            assertTrue(
                    engine.toString().contains("planPartitions="));

        } finally {
            engine.shutdown();
        }

        assertTrue(
                engine.toString().contains("shutdown=true"));
    }
}
