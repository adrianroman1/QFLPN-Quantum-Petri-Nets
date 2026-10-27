package hpc.csr;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

class QFLPNCoreEngineTest {

    private static final int N = 4;
    private static final double TOLERANCE = 1.0e-12;

    private static final double[] VALUES = {
            1.0, 2.0, 3.0, 4.0,
            5.0, 6.0, 7.0, 8.0
    };

    private static final int[] COLUMN_INDICES = {
            0, 2,
            1, 3,
            0, 2,
            1, 3
    };

    private static final int[] ROW_POINTERS = {
            0, 2, 4, 6, 8
    };

    private static final double[] INPUT = {
            1.0, 2.0, 3.0, 4.0
    };

    private static final double[] EXPECTED = {
            7.0, 22.0, 23.0, 46.0
    };

    private static final class TrackingForkJoinPool
            extends ForkJoinPool {

        private int shutdownCalls;

        TrackingForkJoinPool(int parallelism) {
            super(parallelism);
        }

        @Override
        public synchronized void shutdown() {
            shutdownCalls++;
            super.shutdown();
        }

        synchronized int getShutdownCalls() {
            return shutdownCalls;
        }
    }

    private static final class PoolRecorder {

        private final List<TrackingForkJoinPool> pools =
                Collections.synchronizedList(new ArrayList<>());

        ForkJoinPool create(int parallelism) {
            TrackingForkJoinPool pool =
                    new TrackingForkJoinPool(parallelism);

            pools.add(pool);
            return pool;
        }

        int size() {
            return pools.size();
        }

        TrackingForkJoinPool get(int index) {
            return pools.get(index);
        }
    }

    private static double[] values() {
        return VALUES.clone();
    }

    private static int[] columns() {
        return COLUMN_INDICES.clone();
    }

    private static int[] rowPointers() {
        return ROW_POINTERS.clone();
    }

    private static double[] input() {
        return INPUT.clone();
    }

    private static double[] expected() {
        return EXPECTED.clone();
    }

    private static QFLPNCoreEngine.CsrMatrix createMatrix() {
        return new QFLPNCoreEngine.CsrMatrix(
                N,
                N,
                values(),
                columns(),
                rowPointers()
        );
    }

    private static QFLPNCoreEngine.CsrMatrix
    createDifferentCsrDistribution() {

        return new QFLPNCoreEngine.CsrMatrix(
                N,
                N,
                values(),
                columns(),
                new int[]{0, 1, 3, 6, 8}
        );
    }

    private static QFLPNCoreEngine createLoadedEngine() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);
        engine.loadCSR(createMatrix());
        return engine;
    }

    @Test
    void shouldStoreConfiguration() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertEquals(N, engine.getDimension());
            assertEquals(2, engine.getParallelism());
            assertFalse(engine.isShutdown());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidConstructorArguments() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(0)
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(-1)
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(N, 0)
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(N, -1)
        );
    }

    @Test
    void shouldRejectOperationsBeforeMatrixLoad() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertThrows(
                    IllegalStateException.class,
                    engine::multiplySequential
            );

            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiplySequential(input())
            );

            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiplyParallel(input())
            );

            assertThrows(
                    IllegalStateException.class,
                    engine::getSpmvPlan
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadCSRAndExposeMetadata() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            engine.loadCSR(
                    N,
                    N,
                    values(),
                    columns(),
                    rowPointers()
            );

            assertEquals(N, engine.getDimension());
            assertEquals(8, engine.getNnz());
            assertNotNull(engine.getSpmvPlan());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadExistingMatrix() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            engine.loadCSR(createMatrix());

            assertEquals(N, engine.getDimension());
            assertEquals(8, engine.getNnz());
            assertArrayEquals(
                    expected(),
                    engine.multiplySequential(input()),
                    TOLERANCE
            );
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
                    () -> engine.loadCSR((QFLPNCoreEngine.CsrMatrix) null)
            );

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            null,
                            columns(),
                            rowPointers()
                    )
            );

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            values(),
                            null,
                            rowPointers()
                    )
            );

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            values(),
                            columns(),
                            null
                    )
            );
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
                            N,
                            N,
                            new double[]{1.0},
                            new int[]{0, 1},
                            new int[]{0, 1, 1, 1, 1}
                    )
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            new double[]{1.0},
                            new int[]{N},
                            new int[]{0, 1, 1, 1, 1}
                    )
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            new double[]{1.0},
                            new int[]{0},
                            new int[]{0, 1, 1, 1}
                    )
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            new double[]{1.0},
                            new int[]{0},
                            new int[]{0, 1, 0, 1, 1}
                    )
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            N,
                            N - 1,
                            values(),
                            columns(),
                            rowPointers()
                    )
            );
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
                    engine.multiplySequential(input()),
                    TOLERANCE
            );
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
                    TOLERANCE
            );
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
                    TOLERANCE
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void sequentialAndParallelResultsShouldMatch() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            double[] sequential =
                    engine.multiplySequential(input());

            double[] parallel =
                    engine.multiplyParallel(input());

            assertArrayEquals(
                    sequential,
                    parallel,
                    TOLERANCE
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldCreatePlanWhenLoadingCsrMatrix() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);

        try {
            assertThrows(
                    IllegalStateException.class,
                    engine::getSpmvPlan
            );

            engine.loadCSR(createMatrix());

            assertNotNull(engine.getSpmvPlan());
            assertEquals(4, engine.getSpmvPlan().getRows());
            assertEquals(8, engine.getSpmvPlan().getNnz());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReuseSamePlanAcrossRepeatedMultiplications() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan originalPlan = engine.getSpmvPlan();

            engine.multiplyParallel(input());
            engine.multiplyParallel(input());
            engine.multiplyParallel(input());

            assertSame(originalPlan, engine.getSpmvPlan());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRebuildPlanWhenMatrixIsReplaced() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan originalPlan = engine.getSpmvPlan();

            engine.loadCSR(createDifferentCsrDistribution());

            SpmvPlan replacementPlan = engine.getSpmvPlan();

            assertNotSame(originalPlan, replacementPlan);
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldUseExactCsrStructureForLoadedPlan() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan plan = engine.getSpmvPlan();

            assertTrue(
                    plan.isCompatible(
                            N,
                            8,
                            rowPointers()
                    )
            );

            assertFalse(
                    plan.isCompatible(
                            N,
                            8,
                            new int[]{0, 1, 3, 6, 8}
                    )
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldKeepPlanSnapshotIndependentFromInputRowPointers() {
        QFLPNCoreEngine engine = new QFLPNCoreEngine(N, 2);
        int[] sourceRowPointers = rowPointers();

        try {
            engine.loadCSR(
                    N,
                    N,
                    values(),
                    columns(),
                    sourceRowPointers
            );

            sourceRowPointers[1] = 0;

            assertTrue(
                    engine.getSpmvPlan().isCompatible(
                            N,
                            8,
                            rowPointers()
                    )
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReturnDefensiveCopiesOfPlanPartitionBoundaries() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan plan = engine.getSpmvPlan();

            int[] starts = plan.getStartRows();
            int[] ends = plan.getEndRows();

            int[] originalStarts = starts.clone();
            int[] originalEnds = ends.clone();

            if (starts.length > 0) {
                starts[0] = -100;
            }

            if (ends.length > 0) {
                ends[0] = -100;
            }

            assertArrayEquals(
                    originalStarts,
                    plan.getStartRows()
            );

            assertArrayEquals(
                    originalEnds,
                    plan.getEndRows()
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReuseSamePersistentPoolAcrossRepeatedMultiplications() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        TrackingForkJoinPool persistentPool;

        try {
            assertEquals(1, recorder.size());

            persistentPool = recorder.get(0);

            engine.loadCSR(createMatrix());

            for (int i = 0; i < 5; i++) {
                assertArrayEquals(
                        expected(),
                        engine.multiplyParallel(input()),
                        TOLERANCE
                );
            }

            assertEquals(1, recorder.size());
            assertSame(persistentPool, recorder.get(0));
            assertFalse(persistentPool.isShutdown());
            assertEquals(0, persistentPool.getShutdownCalls());
        } finally {
            engine.shutdown();
        }

        assertTrue(persistentPool.isShutdown());
        assertEquals(1, persistentPool.getShutdownCalls());
    }

    @Test
    void shouldKeepPersistentPoolActiveAfterRepeatedMultiplications() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        try {
            engine.loadCSR(createMatrix());

            TrackingForkJoinPool persistentPool =
                    recorder.get(0);

            engine.multiplyParallel(input());
            engine.multiplyParallel(input());

            assertFalse(persistentPool.isShutdown());
            assertEquals(0, persistentPool.getShutdownCalls());
            assertEquals(1, recorder.size());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldKeepPersistentPoolWhenMatrixAndPlanAreReplaced() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        try {
            engine.loadCSR(createMatrix());

            TrackingForkJoinPool persistentPool =
                    recorder.get(0);

            SpmvPlan originalPlan = engine.getSpmvPlan();

            engine.loadCSR(createDifferentCsrDistribution());

            SpmvPlan replacementPlan = engine.getSpmvPlan();

            assertNotSame(originalPlan, replacementPlan);
            assertEquals(1, recorder.size());
            assertSame(persistentPool, recorder.get(0));
            assertFalse(persistentPool.isShutdown());
            assertEquals(0, persistentPool.getShutdownCalls());

            assertArrayEquals(
                    engine.multiplySequential(input()),
                    engine.multiplyParallel(input()),
                    TOLERANCE
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldCreateAndCloseTemporaryPoolForExplicitDifferentParallelism() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        try {
            engine.loadCSR(createMatrix());

            TrackingForkJoinPool persistentPool =
                    recorder.get(0);

            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input(), 1, 3),
                    TOLERANCE
            );

            assertEquals(2, recorder.size());

            TrackingForkJoinPool temporaryPool =
                    recorder.get(1);

            assertEquals(3, temporaryPool.getParallelism());
            assertTrue(temporaryPool.isShutdown());
            assertEquals(1, temporaryPool.getShutdownCalls());

            assertFalse(persistentPool.isShutdown());
            assertEquals(0, persistentPool.getShutdownCalls());

            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input()),
                    TOLERANCE
            );

            assertEquals(2, recorder.size());
            assertFalse(persistentPool.isShutdown());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldCreateAndCloseTemporaryPoolForExplicitNonDefaultThreshold() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        try {
            engine.loadCSR(createMatrix());

            TrackingForkJoinPool persistentPool =
                    recorder.get(0);

            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input(), 1, 2),
                    TOLERANCE
            );

            assertEquals(2, recorder.size());

            TrackingForkJoinPool temporaryPool =
                    recorder.get(1);

            assertEquals(2, temporaryPool.getParallelism());
            assertTrue(temporaryPool.isShutdown());
            assertEquals(1, temporaryPool.getShutdownCalls());

            assertFalse(persistentPool.isShutdown());
            assertEquals(0, persistentPool.getShutdownCalls());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReusePersistentPoolForDefaultExplicitConfiguration() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        try {
            engine.loadCSR(createMatrix());

            TrackingForkJoinPool persistentPool =
                    recorder.get(0);

            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(input(), 4096, 2),
                    TOLERANCE
            );

            assertEquals(1, recorder.size());
            assertSame(persistentPool, recorder.get(0));
            assertFalse(persistentPool.isShutdown());
            assertEquals(0, persistentPool.getShutdownCalls());
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidVectorAndParallelConfiguration() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplySequential(new double[]{1.0})
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(new double[]{1.0})
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(input(), 0, 2)
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(input(), -1, 2)
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(input(), 1, 0)
            );

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(input(), 1, -1)
            );

            assertThrows(
                    NullPointerException.class,
                    () -> engine.multiplySequential(null)
            );

            assertThrows(
                    NullPointerException.class,
                    () -> engine.multiplyParallel(null)
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldPreservePreviousMatrixAndPlanAfterFailedReplacement() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            SpmvPlan originalPlan = engine.getSpmvPlan();

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            N,
                            N,
                            new double[]{1.0},
                            new int[]{0},
                            new int[]{0, 2, 1, 1, 1}
                    )
            );

            assertSame(originalPlan, engine.getSpmvPlan());

            assertArrayEquals(
                    expected(),
                    engine.multiplySequential(input()),
                    TOLERANCE
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReplaceMatrixBetweenOperations() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            double[] originalResult =
                    engine.multiplySequential(input());

            engine.loadCSR(createDifferentCsrDistribution());

            double[] replacementResult =
                    engine.multiplySequential(input());

            assertArrayEquals(
                    originalResult,
                    replacementResult,
                    TOLERANCE
            );
        } finally {
            engine.shutdown();
        }
    }

    @Test
    void concurrentMultiplicationsShouldReturnCorrectResults()
            throws Exception {

        QFLPNCoreEngine engine = createLoadedEngine();

        ExecutorService executor =
                Executors.newFixedThreadPool(4);

        try {
            List<Future<double[]>> futures = new ArrayList<>();

            for (int i = 0; i < 8; i++) {
                futures.add(
                        executor.submit(
                                () -> engine.multiplyParallel(input())
                        )
                );
            }

            for (Future<double[]> future : futures) {
                assertArrayEquals(
                        expected(),
                        future.get(10, TimeUnit.SECONDS),
                        TOLERANCE
                );
            }
        } finally {
            executor.shutdownNow();
            assertTrue(
                    executor.awaitTermination(10, TimeUnit.SECONDS)
            );
            engine.shutdown();
        }
    }

    @Test
    void shutdownShouldBeIdempotent() {
        PoolRecorder recorder = new PoolRecorder();

        QFLPNCoreEngine engine = new QFLPNCoreEngine(
                N,
                2,
                recorder::create
        );

        TrackingForkJoinPool persistentPool =
                recorder.get(0);

        engine.shutdown();
        engine.shutdown();
        engine.close();
        engine.close();

        assertTrue(engine.isShutdown());
        assertTrue(persistentPool.isShutdown());
        assertEquals(1, persistentPool.getShutdownCalls());
        assertEquals(1, recorder.size());
    }

    @Test
    void operationsAfterShutdownShouldBeRejected() {
        QFLPNCoreEngine engine = createLoadedEngine();

        engine.shutdown();

        assertTrue(engine.isShutdown());

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiplySequential(input())
        );

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiplyParallel(input())
        );

        assertThrows(
                IllegalStateException.class,
                () -> engine.loadCSR(createMatrix())
        );
    }

    @Test
    void toStringShouldDescribeEngineState() {
        QFLPNCoreEngine engine = createLoadedEngine();

        try {
            String description = engine.toString();

            assertNotNull(description);
            assertFalse(description.isBlank());
            assertTrue(description.contains("4"));
            assertTrue(description.contains("2"));
        } finally {
            engine.shutdown();
        }
    }
}
