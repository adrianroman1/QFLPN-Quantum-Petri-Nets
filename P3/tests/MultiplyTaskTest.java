package hpc.csr;

import java.util.Arrays;
import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

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

    private static void invoke(MultiplyTask task, int parallelism) {
        try (ForkJoinPool pool = new ForkJoinPool(parallelism)) {
            pool.invoke(task);
        }
    }

    private static double[] sequentialOracle(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input) {

        double[] result = new double[rowPointers.length - 1];

        for (int row = 0; row < result.length; row++) {
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
    void shouldExposeBackwardCompatibleTaskMetadata() {
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
                values(), columns(), rowPointers(), input(),
                new double[4],
                0, 4, 2,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        assertEquals(
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD,
                task.getThresholdMode());
    }

    @Test
    void shouldComputeEntireMatrixWithLargeRowThreshold() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 100);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeEntireMatrixWithRecursiveRowThreshold() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 1);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeEntireMatrixWithNnzThreshold() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 2,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeWithNnzThresholdLargerThanIntervalNnz() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 100,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeWithRowThresholdAndRowBoundaryScan() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 1,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeWithNnzThresholdAndRowBoundaryScan() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 0, 4, 1,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputeOnlySelectedRowInterval() {
        double[] output = {-1.0, -1.0, -1.0, -1.0};

        MultiplyTask task = new MultiplyTask(
                values(), columns(), rowPointers(), input(),
                output, 1, 3, 1);

        invoke(task, 2);

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

        invoke(task, 2);

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

        invoke(task, 2);

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
                        values(), columns(), rowPointers(), input(),
                        new double[4], 0, 4, 1,
                        null,
                        MultiplyTask.ThresholdMode.ROW_THRESHOLD));
    }

    @Test
    void shouldRejectNullThresholdMode() {
        assertThrows(NullPointerException.class,
                () -> new MultiplyTask(
                        values(), columns(), rowPointers(), input(),
                        new double[4], 0, 4, 1,
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
    void shouldRejectEndRowOutsideCsrRange() {
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

    @Test
    void shouldRejectDecreasingRowPointers() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 1, 0},
                        new double[] {2.0},
                        new double[2],
                        0, 2, 1));
    }

    @Test
    void shouldRejectFinalRowPointerDifferentFromNnz() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 0},
                        new double[] {2.0},
                        new double[1],
                        0, 1, 1));
    }

    @Test
    void shouldRejectColumnOutsideInputVector() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0},
                        new int[] {1},
                        new int[] {0, 1},
                        new double[] {2.0},
                        new double[1],
                        0, 1, 1));
    }

    @Test
    void shouldRejectNonFiniteCsrValues() {
        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {Double.NaN},
                        new int[] {0},
                        new int[] {0, 1},
                        new double[] {2.0},
                        new double[1],
                        0, 1, 1));

        assertThrows(IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {Double.POSITIVE_INFINITY},
                        new int[] {0},
                        new int[] {0, 1},
                        new double[] {2.0},
                        new double[1],
                        0, 1, 1));
    }

    /**
     * Regression for a rectangular matrix with 100 rows and 2 columns.
     * A row index is not a column index.
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
                1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        invoke(task, 4);

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

        invoke(task, 2);

        assertArrayEquals(
                new double[] {5.0, 0.0, 22.0},
                output,
                TOLERANCE);
    }

    @Test
    void shouldHandleAllEmptyRowsWithNnzThreshold() {
        double[] output = {9.0, 9.0, 9.0, 9.0};

        MultiplyTask task = new MultiplyTask(
                new double[0],
                new int[0],
                new int[] {0, 0, 0, 0, 0},
                new double[] {1.0},
                output,
                0, 4, 1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 4);

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0, 0.0},
                output,
                TOLERANCE);
    }

    @Test
    void shouldHandleNnzConcentratedInOneRow() {
        double[] concentratedValues = {
                1.0, 2.0, 3.0, 4.0, 5.0, 6.0
        };

        int[] concentratedColumns = {
                0, 1, 0, 1, 0, 1
        };

        int[] concentratedRowPointers = {
                0, 0, 0, 6, 6, 6
        };

        double[] vector = {2.0, 3.0};
        double[] output = new double[5];

        MultiplyTask task = new MultiplyTask(
                concentratedValues,
                concentratedColumns,
                concentratedRowPointers,
                vector,
                output,
                0, 5, 1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 4);

        assertArrayEquals(
                sequentialOracle(
                        concentratedValues,
                        concentratedColumns,
                        concentratedRowPointers,
                        vector),
                output,
                TOLERANCE);
    }

    @Test
    void shouldPreserveInputWhenInputAndOutputAlias() {
        double[] aliasedVector = {1.0, 2.0, 3.0, 4.0};

        MultiplyTask task = new MultiplyTask(
                values(),
                columns(),
                rowPointers(),
                aliasedVector,
                aliasedVector,
                0, 4, 1);

        invoke(task, 2);

        assertArrayEquals(expected(), aliasedVector, TOLERANCE);
    }

    @Test
    void shouldDefensivelyCopyCallerOwnedInputAndCsrArrays() {
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
                0, 4, 1);

        Arrays.fill(sourceValues, 100.0);
        Arrays.fill(sourceColumns, 0);
        Arrays.fill(sourceRowPointers, 0);
        Arrays.fill(sourceInput, 100.0);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
        assertNotSame(sourceValues, output);
    }

    @Test
    void bothSplitPoliciesShouldMatchIndependentSequentialOracle() {
        double[] oracle = sequentialOracle(
                values(), columns(), rowPointers(), input());

        for (MultiplyTask.SplitPolicy policy
                : MultiplyTask.SplitPolicy.values()) {

            for (MultiplyTask.ThresholdMode mode
                    : MultiplyTask.ThresholdMode.values()) {

                double[] output = new double[4];

                MultiplyTask task = new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        0,
                        4,
                        1,
                        policy,
                        mode);

                invoke(task, 4);

                assertArrayEquals(
                        oracle,
                        output,
                        TOLERANCE,
                        "Mismatch for " + policy + " / " + mode);
            }
        }
    }

    @Test
    void shouldComputeLargeRowCountWithSmallInputDimension() {
        int rows = 100;
        int nnzPerRow = 2;

        double[] largeValues = new double[rows * nnzPerRow];
        int[] largeColumns = new int[rows * nnzPerRow];
        int[] largeRowPointers = new int[rows + 1];

        double[] smallInput = {2.0, 3.0};
        double[] output = new double[rows];

        for (int row = 0; row < rows; row++) {
            int offset = row * nnzPerRow;

            largeValues[offset] = 1.0;
            largeValues[offset + 1] = 1.0;

            largeColumns[offset] = 0;
            largeColumns[offset + 1] = 1;

            largeRowPointers[row] = offset;
        }

        largeRowPointers[rows] = rows * nnzPerRow;

        MultiplyTask task = new MultiplyTask(
                largeValues,
                largeColumns,
                largeRowPointers,
                smallInput,
                output,
                0,
                rows,
                10,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        invoke(task, 4);

        for (double value : output) {
            assertEquals(5.0, value, TOLERANCE);
        }
    }

    @Test
    void shouldAcceptThresholdEqualToIntervalNnz() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(),
                columns(),
                rowPointers(),
                input(),
                output,
                0,
                4,
                8,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldAcceptThresholdEqualToIntervalRowCount() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(),
                columns(),
                rowPointers(),
                input(),
                output,
                0,
                4,
                4,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(expected(), output, TOLERANCE);
    }

    @Test
    void shouldComputePartialIntervalWithNnzThreshold() {
        double[] output = {-1.0, -1.0, -1.0, -1.0};

        MultiplyTask task = new MultiplyTask(
                values(),
                columns(),
                rowPointers(),
                input(),
                output,
                1,
                3,
                1,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 2);

        assertArrayEquals(
                new double[] {-1.0, 22.0, 23.0, -1.0},
                output,
                TOLERANCE);
    }

    @Test
    void shouldProduceFiniteResultsForFiniteInputsAndValues() {
        double[] output = new double[4];

        MultiplyTask task = new MultiplyTask(
                values(),
                columns(),
                rowPointers(),
                input(),
                output,
                0,
                4,
                1,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD);

        invoke(task, 4);

        for (double value : output) {
            assertTrue(Double.isFinite(value));
        }
    }
}
