package hpc.csr;

import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class MultiplyTaskTest {

    private static final double TOLERANCE = 1.0e-12;

    private static double[] values() {
        return new double[] {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };
    }

    private static int[] columns() {
        return new int[] {
                0, 2, 1, 3, 0, 2, 1, 3
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

    private static double[] execute(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            int rows,
            int threshold,
            MultiplyTask.SplitPolicy splitPolicy,
            MultiplyTask.ThresholdMode thresholdMode,
            int parallelism) {

        double[] output = new double[rows];

        MultiplyTask task = new MultiplyTask(
                values,
                columns,
                rowPointers,
                input,
                output,
                0,
                rows,
                threshold,
                splitPolicy,
                thresholdMode);

        try (ForkJoinPool pool = new ForkJoinPool(parallelism)) {
            pool.invoke(task);
        }

        return output;
    }

    private static double[] execute(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            int rows,
            int threshold,
            MultiplyTask.SplitPolicy splitPolicy,
            MultiplyTask.ThresholdMode thresholdMode) {

        return execute(
                values,
                columns,
                rowPointers,
                input,
                rows,
                threshold,
                splitPolicy,
                thresholdMode,
                4);
    }

    private static double[] sequentialOracle(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            int rows) {

        double[] result = new double[rows];

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            for (int index = rowPointers[row];
                 index < rowPointers[row + 1];
                 index++) {

                sum += values[index] * input[columns[index]];
            }

            result[row] = sum;
        }

        return result;
    }

    @Test
    void shouldExposeTaskMetadata() {
        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                new double[4], 0, 4, 2);

        assertEquals(0, task.getStartRow());
        assertEquals(4, task.getEndRow());
        assertEquals(2, task.getThreshold());
        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                task.getSplitPolicy());
        assertEquals(
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                task.getThresholdMode());
    }

    @Test
    void shouldExposeExplicitThresholdMode() {
        MultiplyTask task = new MultiplyTask(
                values(),
                columns(),
                rowPointers(),
                input(),
                new double[4],
                0,
                4,
                3,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        assertEquals(
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD,
                task.getThresholdMode());

        assertEquals(
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                task.getSplitPolicy());
    }

    @Test
    void shouldComputeEntireMatrixWithLargeThreshold() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 100);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeEntireMatrixWithRecursiveSplitting() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeOnlySelectedRowInterval() {
        double[] output = {-1.0, -1.0, -1.0, -1.0};

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 1, 3, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertEquals(-1.0, output[0], TOLERANCE);
        assertEquals(22.0, output[1], TOLERANCE);
        assertEquals(23.0, output[2], TOLERANCE);
        assertEquals(-1.0, output[3], TOLERANCE);
    }

    @Test
    void shouldComputeSingleRowInterval() {
        double[] output = {-1.0, -1.0, -1.0, -1.0};

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 2, 3, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertEquals(-1.0, output[0], TOLERANCE);
        assertEquals(-1.0, output[1], TOLERANCE);
        assertEquals(23.0, output[2], TOLERANCE);
        assertEquals(-1.0, output[3], TOLERANCE);
    }

    @Test
    void shouldSupportEmptyRowInterval() {
        double[] output = {11.0, 22.0, 33.0, 44.0};

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 2, 2, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertArrayEquals(
                new double[] {11.0, 22.0, 33.0, 44.0},
                output,
                TOLERANCE);
    }

    @Test
    void shouldRejectNullValues() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        null, columns(), rowPointers(), input(),
                        new double[4], 0, 4, 1));
    }

    @Test
    void shouldRejectNullColumns() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(), null, rowPointers(), input(),
                        new double[4], 0, 4, 1));
    }

    @Test
    void shouldRejectNullRowPointers() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(), columns(), null, input(),
                        new double[4], 0, 4, 1));
    }

    @Test
    void shouldRejectNullInput() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), null,
                        new double[4], 0, 4, 1));
    }

    @Test
    void shouldRejectNullOutput() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        null, 0, 4, 1));
    }

    @Test
    void shouldRejectNullSplitPolicy() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        4,
                        1,
                        null,
                        MultiplyTask.ThresholdMode.ROW_THRESHOLD));
    }

    @Test
    void shouldRejectNullThresholdMode() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        4,
                        1,
                        MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                        null));
    }

    @Test
    void shouldRejectNegativeStartRow() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[4], -1, 4, 1));
    }

    @Test
    void shouldRejectEndRowSmallerThanStartRow() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[4], 3, 2, 1));
    }

    @Test
    void shouldRejectEndRowOutsideCSRRange() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[4], 0, 5, 1));
    }

    @Test
    void shouldRejectNonPositiveThreshold() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[4], 0, 4, 0));

        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[4], 0, 4, -1));
    }

    @Test
    void shouldRejectMismatchedValuesAndColumns() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0, 2.0},
                        new int[] {0},
                        new int[] {0, 1, 1},
                        new double[] {1.0, 2.0},
                        new double[] {0.0, 0.0},
                        0, 2, 1));
    }

    @Test
    void shouldRejectEmptyRowPointerArray() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[0],
                        new int[0],
                        new int[0],
                        new double[0],
                        new double[0],
                        0, 0, 1));
    }

    /**
     * Regression test for a rectangular 100 x 2 matrix.
     * Row indices are independent of input-vector column indices.
     */
    @Test
    void shouldComputeRectangularMatrixWithMoreRowsThanColumns() {
        int rows = 100;
        int columnCount = 2;

        double[] rectangularValues = new double[rows * columnCount];
        int[] rectangularColumns = new int[rows * columnCount];
        int[] rectangularRowPointers = new int[rows + 1];

        double[] rectangularInput = {2.0, 3.0};
        double[] rectangularOutput = new double[rows];
        double[] expectedOutput = new double[rows];

        for (int row = 0; row < rows; row++) {
            int offset = row * columnCount;

            rectangularValues[offset] = 1.0;
            rectangularValues[offset + 1] = 1.0;

            rectangularColumns[offset] = 0;
            rectangularColumns[offset + 1] = 1;

            rectangularRowPointers[row] = offset;
            expectedOutput[row] =
                    rectangularInput[0] + rectangularInput[1];
        }

        rectangularRowPointers[rows] = rows * columnCount;

        MultiplyTask task = new MultiplyTask(
                rectangularValues,
                rectangularColumns,
                rectangularRowPointers,
                rectangularInput,
                rectangularOutput,
                0,
                rows,
                1);

        try (ForkJoinPool pool = new ForkJoinPool(4)) {
            pool.invoke(task);
        }

        assertArrayEquals(
                expectedOutput,
                rectangularOutput,
                TOLERANCE);
    }

    @Test
    void shouldRejectEndRowBeyondOutputVector() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[2], 0, 4, 1));
    }

    @Test
    void recursiveAndDirectExecutionShouldProduceIdenticalResults() {
        double[] directOutput = new double[4];
        double[] recursiveOutput = new double[4];

        MultiplyTask directTask = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                directOutput, 0, 4, 100);

        MultiplyTask recursiveTask = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                recursiveOutput, 0, 4, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(directTask);
            pool.invoke(recursiveTask);
        }

        assertArrayEquals(directOutput, recursiveOutput, TOLERANCE);
    }

    @Test
    void shouldHandleEmptyRowsCorrectly() {
        double[] output = new double[3];

        MultiplyTask task = new MultiplyTask(
                new double[] {1.0, 2.0},
                new int[] {0, 2},
                new int[] {0, 1, 1, 2},
                new double[] {5.0, 7.0, 11.0},
                output,
                0, 3, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertArrayEquals(
                new double[] {5.0, 0.0, 22.0},
                output,
                TOLERANCE);
    }

    /**
     * ROW_THRESHOLD is based on row count, not NNZ count.
     *
     * This matrix has 100 rows but only 4 nonzero elements.
     */
    @Test
    void rowThresholdShouldHandleManyRowsWithFewNonzeros() {
        int rows = 100;

        double[] sparseValues = {2.0, 3.0, 5.0, 7.0};
        int[] sparseColumns = {0, 1, 0, 1};
        int[] sparseRowPointers = new int[rows + 1];

        for (int row = 0; row <= rows; row++) {
            if (row < 25) {
                sparseRowPointers[row] = 0;
            } else if (row < 50) {
                sparseRowPointers[row] = 1;
            } else if (row < 75) {
                sparseRowPointers[row] = 2;
            } else if (row < 100) {
                sparseRowPointers[row] = 3;
            } else {
                sparseRowPointers[row] = 4;
            }
        }

        double[] vector = {2.0, 3.0};

        double[] actual = execute(
                sparseValues,
                sparseColumns,
                sparseRowPointers,
                vector,
                rows,
                10,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        double[] expected = sequentialOracle(
                sparseValues,
                sparseColumns,
                sparseRowPointers,
                vector,
                rows);

        assertArrayEquals(expected, actual, TOLERANCE);
    }

    /**
     * NNZ_THRESHOLD is based on the number of nonzeros in the interval,
     * not on its row count.
     *
     * The 100-row interval contains only 4 nonzeros.
     */
    @Test
    void nnzThresholdShouldHandleManyRowsWithFewNonzeros() {
        int rows = 100;

        double[] sparseValues = {2.0, 3.0, 5.0, 7.0};
        int[] sparseColumns = {0, 1, 0, 1};
        int[] sparseRowPointers = new int[rows + 1];

        for (int row = 0; row <= rows; row++) {
            if (row < 25) {
                sparseRowPointers[row] = 0;
            } else if (row < 50) {
                sparseRowPointers[row] = 1;
            } else if (row < 75) {
                sparseRowPointers[row] = 2;
            } else if (row < 100) {
                sparseRowPointers[row] = 3;
            } else {
                sparseRowPointers[row] = 4;
            }
        }

        double[] vector = {2.0, 3.0};

        double[] actual = execute(
                sparseValues,
                sparseColumns,
                sparseRowPointers,
                vector,
                rows,
                10,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        double[] expected = sequentialOracle(
                sparseValues,
                sparseColumns,
                sparseRowPointers,
                vector,
                rows);

        assertArrayEquals(expected, actual, TOLERANCE);
    }

    /**
     * Four rows contain 40 nonzeros. This distinguishes a row-count
     * threshold from an NNZ threshold in the opposite direction.
     */
    @Test
    void nnzThresholdShouldHandleFewRowsWithManyNonzeros() {
        int rows = 4;
        int entriesPerRow = 10;
        int nnz = rows * entriesPerRow;

        double[] sparseValues = new double[nnz];
        int[] sparseColumns = new int[nnz];
        int[] sparseRowPointers = new int[rows + 1];
        double[] vector = new double[entriesPerRow];

        for (int column = 0; column < entriesPerRow; column++) {
            vector[column] = column + 1.0;
        }

        for (int index = 0; index < nnz; index++) {
            sparseValues[index] = 1.0;
            sparseColumns[index] = index % entriesPerRow;
        }

        for (int row = 0; row <= rows; row++) {
            sparseRowPointers[row] = row * entriesPerRow;
        }

        double[] actual = execute(
                sparseValues,
                sparseColumns,
                sparseRowPointers,
                vector,
                rows,
                5,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        double[] expected = sequentialOracle(
                sparseValues,
                sparseColumns,
                sparseRowPointers,
                vector,
                rows);

        assertArrayEquals(expected, actual, TOLERANCE);
    }

    @Test
    void rowThresholdShouldSupportThresholdEqualToRowCount() {
        double[] actual = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                4,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        assertArrayEquals(expected(), actual, TOLERANCE);
    }

    @Test
    void nnzThresholdShouldSupportThresholdEqualToNnzCount() {
        double[] actual = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                8,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        assertArrayEquals(expected(), actual, TOLERANCE);
    }

    @Test
    void nnzThresholdShouldSupportThresholdGreaterThanNnzCount() {
        double[] actual = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                100,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        assertArrayEquals(expected(), actual, TOLERANCE);
    }

    @Test
    void shouldHandleAnEntirelyEmptyMatrixWithNnzThreshold() {
        int rows = 16;

        double[] emptyValues = new double[0];
        int[] emptyColumns = new int[0];
        int[] emptyRowPointers = new int[rows + 1];
        double[] vector = {1.0, 2.0, 3.0};

        double[] actual = execute(
                emptyValues,
                emptyColumns,
                emptyRowPointers,
                vector,
                rows,
                1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        assertArrayEquals(new double[rows], actual, TOLERANCE);
    }

    @Test
    void shouldHandleAnEntirelyEmptyMatrixWithRowThreshold() {
        int rows = 16;

        double[] emptyValues = new double[0];
        int[] emptyColumns = new int[0];
        int[] emptyRowPointers = new int[rows + 1];
        double[] vector = {1.0, 2.0, 3.0};

        double[] actual = execute(
                emptyValues,
                emptyColumns,
                emptyRowPointers,
                vector,
                rows,
                2,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        assertArrayEquals(new double[rows], actual, TOLERANCE);
    }

    @Test
    void bothSplitPoliciesShouldProduceEquivalentResultsWithRowThreshold() {
        double[] binary = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        double[] scan = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                1,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        assertArrayEquals(binary, scan, TOLERANCE);
        assertArrayEquals(expected(), binary, TOLERANCE);
    }

    @Test
    void bothSplitPoliciesShouldProduceEquivalentResultsWithNnzThreshold() {
        double[] binary = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        double[] scan = execute(
                values(),
                columns(),
                rowPointers(),
                input(),
                4,
                1,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        assertArrayEquals(binary, scan, TOLERANCE);
        assertArrayEquals(expected(), binary, TOLERANCE);
    }

    @Test
    void bothThresholdModesShouldMatchSequentialOracleForBothPolicies() {
        double[] oracle = sequentialOracle(
                values(),
                columns(),
                rowPointers(),
                input(),
                4);

        for (MultiplyTask.SplitPolicy policy
                : MultiplyTask.SplitPolicy.values()) {

            for (MultiplyTask.ThresholdMode mode
                    : MultiplyTask.ThresholdMode.values()) {

                double[] actual = execute(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        4,
                        1,
                        policy,
                        mode);

                assertArrayEquals(
                        oracle,
                        actual,
                        TOLERANCE,
                        "Mismatch for policy=" + policy + ", mode=" + mode);
            }
        }
    }

    @Test
    void bothPoliciesShouldHandleConsecutiveEmptyRows() {
        double[] matrixValues = {2.0, 3.0};
        int[] matrixColumns = {0, 1};

        /*
         * Rows 1, 2 and 3 are empty.
         * The nonzero elements belong to rows 0 and 4.
         */
        int[] matrixRowPointers = {0, 1, 1, 1, 1, 2};
        double[] vector = {5.0, 7.0};

        double[] expected = {10.0, 0.0, 0.0, 0.0, 21.0};

        for (MultiplyTask.SplitPolicy policy
                : MultiplyTask.SplitPolicy.values()) {

            double[] actual = execute(
                    matrixValues,
                    matrixColumns,
                    matrixRowPointers,
                    vector,
                    5,
                    1,
                    policy,
                    MultiplyTask.ThresholdMode.ROW_THRESHOLD);

            assertArrayEquals(
                    expected,
                    actual,
                    TOLERANCE,
                    "Incorrect result for split policy " + policy);
        }
    }

    @Test
    void recursiveAndDirectExecutionShouldProduceIdenticalResults() {
        double[] directOutput = new double[4];
        double[] recursiveOutput = new double[4];

        MultiplyTask directTask = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                directOutput, 0, 4, 100);

        MultiplyTask recursiveTask = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                recursiveOutput, 0, 4, 1);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(directTask);
            pool.invoke(recursiveTask);
        }

        assertArrayEquals(directOutput, recursiveOutput, TOLERANCE);
    }

    @Test
    void publicConstructorShouldDefensivelyCopyCsrAndInputArrays() {
        double[] sourceValues = values();
        int[] sourceColumns = columns();
        int[] sourceRowPointers = rowPointers();
        double[] sourceInput = input();

        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                sourceValues,
                sourceColumns,
                sourceRowPointers,
                sourceInput,
                output,
                0,
                4,
                100);

        sourceValues[0] = 999.0;
        sourceColumns[0] = 3;
        sourceRowPointers[1] = 0;
        sourceInput[0] = 999.0;

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldPreserveInputWhenInputAndOutputAreTheSameArray() {
        double[] matrixValues = {2.0, 3.0, 4.0, 5.0};
        int[] matrixColumns = {0, 1, 0, 1};
        int[] matrixRowPointers = {0, 2, 4};

        double[] inPlace = {7.0, 11.0};
        double[] expected = {
                2.0 * 7.0 + 3.0 * 11.0,
                4.0 * 7.0 + 5.0 * 11.0
        };

        MultiplyTask task = new MultiplyTask(
                matrixValues,
                matrixColumns,
                matrixRowPointers,
                inPlace,
                inPlace,
                0,
                2,
                1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            pool.invoke(task);
        }

        assertArrayEquals(expected, inPlace, TOLERANCE);
    }

    @Test
    void shouldReturnNonNullThresholdModeForLegacyConstructor() {
        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                new double[4], 0, 4, 2);

        assertNotNull(task.getThresholdMode());
        assertEquals(
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                task.getThresholdMode());
    }

    @Test
    void shouldHandleSingleNonzeroElement() {
        double[] matrixValues = {4.0};
        int[] matrixColumns = {0};
        int[] matrixRowPointers = {0, 1, 1, 1};
        double[] vector = {3.0, 5.0};
        double[] expected = {12.0, 0.0, 0.0};

        for (MultiplyTask.SplitPolicy policy
                : MultiplyTask.SplitPolicy.values()) {

            for (MultiplyTask.ThresholdMode mode
                    : MultiplyTask.ThresholdMode.values()) {

                double[] actual = execute(
                        matrixValues,
                        matrixColumns,
                        matrixRowPointers,
                        vector,
                        3,
                        1,
                        policy,
                        mode);

                assertArrayEquals(
                        expected,
                        actual,
                        TOLERANCE);
            }
        }
    }
}
