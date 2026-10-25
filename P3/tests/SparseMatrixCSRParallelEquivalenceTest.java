package hpc.csr;

import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSRParallelEquivalenceTest {

    private static final double EPS = 1.0e-10;

    private static SparseMatrixCSR createMatrix(
            int rows,
            int columns,
            int entriesPerRow) {

        int nnz = rows * entriesPerRow;

        double[] values = new double[nnz];
        int[] columnIndices = new int[nnz];
        int[] rowPointers = new int[rows + 1];

        int position = 0;

        for (int row = 0; row < rows; row++) {
            rowPointers[row] = position;

            for (int j = 0; j < entriesPerRow; j++) {
                values[position] = 0.5 + ((row + j) % 11);
                columnIndices[position] = (row + j) % columns;
                position++;
            }
        }

        rowPointers[rows] = position;

        return new SparseMatrixCSR(
                values,
                columnIndices,
                rowPointers,
                rows,
                columns);
    }

    private static double[] createInput(int columns) {
        double[] input = new double[columns];

        for (int i = 0; i < columns; i++) {
            input[i] = (i - 7) * 0.125;
        }

        return input;
    }

    @Test
    void parallelMultiplicationMatchesSequentialForSeveralThresholds() {
        SparseMatrixCSR matrix = createMatrix(257, 31, 5);
        double[] input = createInput(31);

        double[] expected = matrix.multiply(input);

        int[] thresholds = {1, 2, 4, 8, 16, 64, 512};

        for (int threshold : thresholds) {
            double[] actual = matrix.multiplyParallel(
                    input, threshold, 4);

            assertArrayEquals(
                    expected,
                    actual,
                    EPS,
                    "Mismatch for threshold " + threshold);
        }
    }

    @Test
    void parallelMultiplicationMatchesSequentialForDifferentParallelism() {
        SparseMatrixCSR matrix = createMatrix(300, 29, 4);
        double[] input = createInput(29);

        double[] expected = matrix.multiply(input);

        for (int parallelism : new int[] {1, 2, 3, 4}) {
            double[] actual = matrix.multiplyParallel(
                    input, 3, parallelism);

            assertArrayEquals(
                    expected,
                    actual,
                    EPS,
                    "Mismatch for parallelism " + parallelism);
        }
    }

    @Test
    void parallelIntoOverwritesEntireOutput() {
        SparseMatrixCSR matrix = createMatrix(64, 17, 3);
        double[] input = createInput(17);

        double[] expected = matrix.multiply(input);
        double[] output = new double[64];

        java.util.Arrays.fill(output, 999.0);

        matrix.multiplyParallelInto(
                input, output, 2, 4);

        assertArrayEquals(expected, output, EPS);
    }

    @Test
    void parallelMultiplicationSupportsEmptyRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 1},
                new int[] {0, 1, 1, 2, 2},
                4,
                2);

        double[] input = {5.0, 7.0};

        assertArrayEquals(
                matrix.multiply(input),
                matrix.multiplyParallel(input, 1, 3),
                EPS);

        assertArrayEquals(
                new double[] {10.0, 0.0, 21.0, 0.0},
                matrix.multiplyParallel(input, 1, 3),
                EPS);
    }

    @Test
    void parallelInPlaceMultiplicationIsSafe() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0,
                        3.0, 4.0
                },
                new int[] {
                        0, 1,
                        0, 1
                },
                new int[] {0, 2, 4},
                2,
                2);

        double[] expected = matrix.multiply(new double[] {5.0, 7.0});

        double[] vector = {5.0, 7.0};

        matrix.multiplyParallelInto(
                vector, vector, 1, 2);

        assertArrayEquals(expected, vector, EPS);
    }

    @Test
    void callerOwnedForkJoinPoolRemainsOpen() {
        SparseMatrixCSR matrix = createMatrix(128, 19, 4);
        double[] input = createInput(19);
        double[] output = new double[128];

        ForkJoinPool pool = new ForkJoinPool(3);

        try {
            matrix.multiplyParallelInto(
                    input, output, 2, pool);

            assertFalse(pool.isShutdown());
            assertFalse(pool.isTerminated());

            assertArrayEquals(
                    matrix.multiply(input),
                    output,
                    EPS);
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void repeatedParallelExecutionsAreDeterministic() {
        SparseMatrixCSR matrix = createMatrix(200, 23, 6);
        double[] input = createInput(23);

        double[] expected = matrix.multiply(input);

        for (int repetition = 0; repetition < 30; repetition++) {
            assertArrayEquals(
                    expected,
                    matrix.multiplyParallel(input, 2, 4),
                    EPS,
                    "Mismatch at repetition " + repetition);
        }
    }
}
