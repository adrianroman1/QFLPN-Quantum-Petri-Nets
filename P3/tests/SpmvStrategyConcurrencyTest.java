package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.Future;

import org.junit.jupiter.api.Test;

/**
 * Concurrency and lifecycle regression tests for the parallel SpMV strategies.
 *
 * The tests verify:
 * 1. bitwise equality with SparseMatrixCSR.multiplyInto();
 * 2. concurrent calls on one strategy with independent output arrays;
 * 3. caller-owned pool ownership is preserved after strategy.close();
 * 4. internally owned pools are shut down by strategy.close();
 * 5. calls after close() are rejected.
 *
 * No global JVM thread counter is used. Such a counter cannot attribute
 * thread creation to a particular strategy or ForkJoinPool.
 */
class SpmvStrategyConcurrencyTest {

    private static final int ROWS = 24_000;
    private static final int PARALLELISM = 4;
    private static final int CALL_COUNT = 12;

    private static final String[] PARALLEL_STRATEGIES = {
            PlannedForkJoinSpmvStrategy.NAME,
            StaticChunkSpmvStrategy.NAME
    };

    private static SparseMatrixCSR createMatrix(
            int rows,
            int entriesPerRow,
            long seed) {

        Random random = new Random(seed);

        double[] values = new double[rows * entriesPerRow];
        int[] columns = new int[rows * entriesPerRow];
        int[] rowPointers = new int[rows + 1];

        for (int row = 0; row < rows; row++) {

            for (int k = 0; k < entriesPerRow; k++) {

                int index = row * entriesPerRow + k;

                values[index] = random.nextDouble() * 2.0 - 1.0;

                columns[index] = (row + k * 97) % rows;
            }

            rowPointers[row + 1] =
                    (row + 1) * entriesPerRow;
        }

        return new SparseMatrixCSR(
                values,
                columns,
                rowPointers,
                rows,
                rows);
    }

    private static double[] createVector(int size, long seed) {

        Random random = new Random(seed);
        double[] vector = new double[size];

        for (int i = 0; i < size; i++) {
            vector[i] = random.nextDouble() * 4.0 - 2.0;
        }

        return vector;
    }

    private static void assertBitwiseEqual(
            double[] expected,
            double[] actual) {

        assertNotNull(expected);
        assertNotNull(actual);
        assertEquals(expected.length, actual.length);

        for (int i = 0; i < expected.length; i++) {

            assertEquals(
                    Double.doubleToLongBits(expected[i]),
                    Double.doubleToLongBits(actual[i]),
                    "Bitwise mismatch at row " + i);
        }
    }

    private static SpmvStrategy createParallelStrategy(
            String name,
            SparseMatrixCSR matrix) {

        switch (name) {

            case PlannedForkJoinSpmvStrategy.NAME:
                return new PlannedForkJoinSpmvStrategy(
                        matrix,
                        PARALLELISM);

            case StaticChunkSpmvStrategy.NAME:
                return new StaticChunkSpmvStrategy(
                        matrix,
                        PARALLELISM);

            default:
                throw new IllegalArgumentException(
                        "Unsupported parallel strategy: " + name);
        }
    }

    /**
     * Reads the private pool reference solely to verify resource ownership.
     *
     * Both parallel implementations currently store their pool in a
     * private field named "pool". This test intentionally fails if that
     * implementation contract changes, requiring the lifecycle test
     * to be reviewed rather than silently skipping pool verification.
     */
    private static ForkJoinPool getInternalPool(
            SpmvStrategy strategy) throws ReflectiveOperationException {

        Field field = strategy.getClass().getDeclaredField("pool");

        field.setAccessible(true);

        return (ForkJoinPool) field.get(strategy);
    }

    @Test
    void parallelStrategiesAreBitwiseIdenticalToSequentialKernel() {

        SparseMatrixCSR matrix =
                createMatrix(ROWS, 5, 1001L);

        double[] input =
                createVector(ROWS, 1002L);

        double[] expected =
                matrix.multiply(input);

        for (String name : PARALLEL_STRATEGIES) {

            try (SpmvStrategy strategy =
                         createParallelStrategy(name, matrix)) {

                double[] actual =
                        strategy.multiply(input);

                assertBitwiseEqual(expected, actual);
            }
        }
    }

    @Test
    void concurrentCallsOnOneStrategyUseIndependentOutputs()
            throws Exception {

        SparseMatrixCSR matrix =
                createMatrix(ROWS, 5, 2001L);

        double[] input =
                createVector(ROWS, 2002L);

        double[] expected =
                matrix.multiply(input);

        ExecutorService callers =
                Executors.newFixedThreadPool(CALL_COUNT);

        try {

            for (String name : PARALLEL_STRATEGIES) {

                try (SpmvStrategy strategy =
                             createParallelStrategy(name, matrix)) {

                    List<Future<double[]>> futures =
                            new ArrayList<>(CALL_COUNT);

                    for (int call = 0; call < CALL_COUNT; call++) {

                        Callable<double[]> operation = () -> {

                            double[] output =
                                    new double[matrix.getRows()];

                            strategy.multiplyInto(input, output);

                            return output;
                        };

                        futures.add(callers.submit(operation));
                    }

                    for (int call = 0; call < CALL_COUNT; call++) {

                        double[] actual;

                        try {
                            actual = futures.get(call).get();
                        } catch (ExecutionException exception) {

                            Throwable cause = exception.getCause();

                            if (cause instanceof AssertionError) {
                                throw (AssertionError) cause;
                            }

                            throw new AssertionError(
                                    "Concurrent multiplication failed for "
                                            + name,
                                    cause);
                        }

                        assertBitwiseEqual(expected, actual);
                    }
                }
            }

        } finally {
            callers.shutdown();

            assertTrue(
                    callers.awaitTermination(
                            30,
                            java.util.concurrent.TimeUnit.SECONDS),
                    "Caller executor did not terminate.");
        }
    }

    @Test
    void callerOwnedPoolRemainsActiveAfterStrategyClose()
            throws Exception {

        SparseMatrixCSR matrix =
                createMatrix(ROWS, 5, 3001L);

        double[] input =
                createVector(ROWS, 3002L);

        double[] expected =
                matrix.multiply(input);

        for (String name : PARALLEL_STRATEGIES) {

            ForkJoinPool callerPool =
                    new ForkJoinPool(PARALLELISM);

            try {

                SpmvStrategy strategy;

                if (PlannedForkJoinSpmvStrategy.NAME.equals(name)) {

                    strategy = new PlannedForkJoinSpmvStrategy(
                            matrix,
                            PARALLELISM,
                            PlannedForkJoinSpmvStrategy.DEFAULT_THRESHOLD,
                            callerPool);

                } else {

                    strategy = new StaticChunkSpmvStrategy(
                            matrix,
                            PARALLELISM,
                            StaticChunkSpmvStrategy.DEFAULT_CHUNKS_PER_THREAD,
                            callerPool);
                }

                try {

                    assertBitwiseEqual(
                            expected,
                            strategy.multiply(input));

                } finally {
                    strategy.close();
                }

                assertTrue(
                        strategy.isClosed(),
                        name + " did not enter the closed state.");

                assertFalse(
                        callerPool.isShutdown(),
                        name + " shut down a caller-owned pool.");

                assertFalse(
                        callerPool.isTerminated(),
                        name + " terminated a caller-owned pool.");

                /*
                 * Prove that the caller-owned pool remains usable after
                 * strategy.close(), not merely that isShutdown() is false.
                 */
                int result = callerPool.submit(() -> 40 + 2).get();

                assertEquals(42, result);

            } finally {
                callerPool.shutdown();

                assertTrue(
                        callerPool.awaitTermination(
                                30,
                                java.util.concurrent.TimeUnit.SECONDS),
                        "Caller-owned pool did not terminate after caller shutdown.");
            }
        }
    }

    @Test
    void closeShutsDownInternallyOwnedPools()
            throws Exception {

        SparseMatrixCSR matrix =
                createMatrix(ROWS, 5, 4001L);

        for (String name : PARALLEL_STRATEGIES) {

            SpmvStrategy strategy =
                    createParallelStrategy(name, matrix);

            ForkJoinPool internalPool =
                    getInternalPool(strategy);

            assertNotNull(
                    internalPool,
                    name + " should own a pool for this configuration.");

            assertFalse(
                    internalPool.isShutdown(),
                    name + " pool was already shut down before close().");

            strategy.close();

            assertTrue(
                    strategy.isClosed(),
                    name + " did not enter the closed state.");

            assertTrue(
                    internalPool.isShutdown(),
                    name + " did not shut down its internally owned pool.");

            assertThrows(
                    IllegalStateException.class,
                    () -> strategy.multiplyInto(
                            new double[ROWS],
                            new double[ROWS]),
                    name + " accepted a multiplication after close().");

            /*
             * close() is idempotent and must not fail on repeated calls.
             */
            assertDoesNotThrow(strategy::close);
        }
    }

    @Test
    void callsAfterCloseAreRejectedForBothParallelStrategies() {

        SparseMatrixCSR matrix =
                createMatrix(ROWS, 5, 5001L);

        double[] input =
                createVector(ROWS, 5002L);

        double[] output =
                new double[ROWS];

        for (String name : PARALLEL_STRATEGIES) {

            SpmvStrategy strategy =
                    createParallelStrategy(name, matrix);

            strategy.close();

            assertTrue(strategy.isClosed());

            assertThrows(
                    IllegalStateException.class,
                    () -> strategy.multiplyInto(input, output),
                    name + " accepted multiplyInto() after close().");

            assertThrows(
                    IllegalStateException.class,
                    () -> strategy.multiply(input),
                    name + " accepted multiply() after close().");

            assertDoesNotThrow(strategy::close);
        }
    }

    @Test
    void sequentialStrategyAlsoRejectsCallsAfterClose() {

        SparseMatrixCSR matrix =
                createMatrix(2_000, 3, 6001L);

        SpmvStrategy strategy =
                new SequentialSpmvStrategy(matrix);

        strategy.close();

        assertTrue(strategy.isClosed());

        assertThrows(
                IllegalStateException.class,
                () -> strategy.multiplyInto(
                        new double[2_000],
                        new double[2_000]));

        assertThrows(
                IllegalStateException.class,
                () -> strategy.multiply(new double[2_000]));

        assertDoesNotThrow(strategy::close);
    }
}
