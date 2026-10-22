package hpc.csr;

import java.util.Arrays;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class MultiplyTaskConcurrencyTest {

    private static final double EPS = 1.0e-12;

    private static double[] makeValues(int rows, int entriesPerRow) {
        double[] values = new double[rows * entriesPerRow];

        for (int row = 0; row < rows; row++) {
            for (int j = 0; j < entriesPerRow; j++) {
                values[row * entriesPerRow + j] =
                        1.0 + ((row + j) % 7);
            }
        }

        return values;
    }

    private static int[] makeColumns(int rows, int entriesPerRow, int cols) {
        int[] columns = new int[rows * entriesPerRow];

        for (int row = 0; row < rows; row++) {
            for (int j = 0; j < entriesPerRow; j++) {
                columns[row * entriesPerRow + j] =
                        (row + j) % cols;
            }
        }

        return columns;
    }

    private static int[] makePointers(int rows, int entriesPerRow) {
        int[] pointers = new int[rows + 1];

        for (int row = 0; row <= rows; row++) {
            pointers[row] = row * entriesPerRow;
        }

        return pointers;
    }

    private static double[] denseOracle(
            double[] values,
            int[] columns,
            int[] pointers,
            double[] input,
            int rows) {

        double[] result = new double[rows];

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            for (int p = pointers[row]; p < pointers[row + 1]; p++) {
                sum += values[p] * input[columns[p]];
            }

            result[row] = sum;
        }

        return result;
    }

    @Test
    void concurrentExecutionMatchesIndependentOracle() {
        int rows = 1000;
        int cols = 31;
        int entries = 5;

        double[] values = makeValues(rows, entries);
        int[] columns = makeColumns(rows, entries, cols);
        int[] pointers = makePointers(rows, entries);

        double[] input = new double[cols];

        for (int i = 0; i < cols; i++) {
            input[i] = (i - 11) * 0.25;
        }

        double[] expected = denseOracle(
                values, columns, pointers, input, rows);

        double[] output = new double[rows];

        MultiplyTask task = new MultiplyTask(
                values, columns, pointers, input,
                output, 0, rows, 4);

        ForkJoinPool pool = new ForkJoinPool(4);

        try {
            pool.invoke(task);
        } finally {
            pool.shutdown();
        }

        assertArrayEquals(expected, output, EPS);
    }

    @Test
    void simultaneousIndependentTasksDoNotInterfere() {
        int rows = 256;
        int cols = 16;
        int entries = 4;

        double[] values = makeValues(rows, entries);
        int[] columns = makeColumns(rows, entries, cols);
        int[] pointers = makePointers(rows, entries);

        double[] inputA = new double[cols];
        double[] inputB = new double[cols];

        Arrays.fill(inputA, 2.0);
        Arrays.fill(inputB, -3.0);

        double[] outputA = new double[rows];
        double[] outputB = new double[rows];

        double[] expectedA = denseOracle(
                values, columns, pointers, inputA, rows);

        double[] expectedB = denseOracle(
                values, columns, pointers, inputB, rows);

        ForkJoinPool pool = new ForkJoinPool(4);

        try {
            MultiplyTask taskA = new MultiplyTask(
                    values, columns, pointers, inputA,
                    outputA, 0, rows, 2);

            MultiplyTask taskB = new MultiplyTask(
                    values, columns, pointers, inputB,
                    outputB, 0, rows, 2);

            pool.submit(() -> {
                pool.invoke(taskA);
                pool.invoke(taskB);
            }).join();
        } finally {
            pool.shutdown();
        }

        assertArrayEquals(expectedA, outputA, EPS);
        assertArrayEquals(expectedB, outputB, EPS);
    }

    @Test
    void callerOwnedPoolIsNotShutdownByTask() {
        int rows = 128;
        int cols = 8;
        int entries = 3;

        double[] values = makeValues(rows, entries);
        int[] columns = makeColumns(rows, entries, cols);
        int[] pointers = makePointers(rows, entries);

        double[] input = new double[cols];
        Arrays.fill(input, 1.0);

        double[] output = new double[rows];

        ForkJoinPool pool = new ForkJoinPool(3);

        try {
            pool.invoke(new MultiplyTask(
                    values, columns, pointers, input,
                    output, 0, rows, 1));

            assertFalse(pool.isShutdown());
            assertFalse(pool.isTerminated());
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void repeatedConcurrentRunsProduceCompleteOutputs() {
        int rows = 512;
        int cols = 19;
        int entries = 4;

        double[] values = makeValues(rows, entries);
        int[] columns = makeColumns(rows, entries, cols);
        int[] pointers = makePointers(rows, entries);

        double[] input = new double[cols];

        for (int i = 0; i < cols; i++) {
            input[i] = i * 0.5 - 2.0;
        }

        double[] expected = denseOracle(
                values, columns, pointers, input, rows);

        ForkJoinPool pool = new ForkJoinPool(4);

        try {
            for (int repetition = 0; repetition < 25; repetition++) {
                double[] output = new double[rows];

                pool.invoke(new MultiplyTask(
                        values, columns, pointers, input,
                        output, 0, rows, 3));

                assertArrayEquals(
                        expected,
                        output,
                        EPS,
                        "Mismatch in repetition " + repetition);
            }
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void taskWritesOnlyItsAssignedInterval() {
        double[] values = {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };

        int[] columns = {
                0, 1,
                0, 1,
                0, 1,
                0, 1
        };

        int[] pointers = {0, 2, 4, 6, 8};

        double[] input = {2.0, 3.0};
        double[] output = {-99.0, -99.0, -99.0, -99.0};

        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            pool.invoke(new MultiplyTask(
                    values, columns, pointers, input,
                    output, 1, 3, 1));
        } finally {
            pool.shutdown();
        }

        // Row 0 is outside [1, 3) and must remain unchanged.
        assertEquals(-99.0, output[0], EPS);

        // Row 1: 3*2 + 4*3 = 18.
        assertEquals(18.0, output[1], EPS);

        // Row 2: 5*2 + 6*3 = 28.
        assertEquals(28.0, output[2], EPS);

        // Row 3 is outside [1, 3) and must remain unchanged.
        assertEquals(-99.0, output[3], EPS);
    }

    @Test
    void shutdownPoolRejectsNewWork() throws InterruptedException {
        ForkJoinPool pool = new ForkJoinPool(1);
        pool.shutdown();

        assertTrue(pool.awaitTermination(2, TimeUnit.SECONDS));
        assertThrows(
                java.util.concurrent.RejectedExecutionException.class,
                () -> pool.execute(() -> { }));
    }
}
