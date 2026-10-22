package hpc.csr;

import java.util.Random;
import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSROracleTest {

    private static final double EPSILON = 1.0e-10;

    /**
     * Independent dense oracle.
     * Duplicate CSR entries are accumulated into the dense matrix.
     */
    private static double[][] denseOracle(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        double[][] dense = new double[rows][columns];

        for (int row = 0; row < rows; row++) {
            for (int p = rowPointers[row]; p < rowPointers[row + 1]; p++) {
                dense[row][columnIndices[p]] += values[p];
            }
        }
        return dense;
    }

    /**
     * Dense matrix-vector multiplication independent of SparseMatrixCSR.
     */
    private static double[] denseMultiply(double[][] matrix, double[] vector) {
        double[] result = new double[matrix.length];

        for (int row = 0; row < matrix.length; row++) {
            double sum = 0.0;
            for (int column = 0; column < vector.length; column++) {
                sum += matrix[row][column] * vector[column];
            }
            result[row] = sum;
        }
        return result;
    }

    private static void assertClose(
            double[] expected,
            double[] actual) {

        assertEquals(expected.length, actual.length);

        for (int i = 0; i < expected.length; i++) {
            assertEquals(
                    expected[i],
                    actual[i],
                    EPSILON,
                    "Mismatch at output index " + i);
        }
    }

    @Test
    void getSumsDuplicateColumnEntries() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, -1.0},
                new int[] {0, 0, 1},
                new int[] {0, 3},
                1,
                2);

        assertEquals(5.0, matrix.get(0, 0), EPSILON);
        assertEquals(-1.0, matrix.get(0, 1), EPSILON);

        double[] expected = {5.0 * 4.0 + (-1.0) * 7.0};
        assertClose(expected, matrix.multiply(new double[] {4.0, 7.0}));
    }

    @Test
    void getAndSpmvHaveConsistentSemanticsForDuplicates() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0, -1.0},
                new int[] {1, 1, 0, 1},
                new int[] {0, 3, 4},
                2,
                2);

        double[] x = {5.0, 2.0};
        double[] y = matrix.multiply(x);

        for (int row = 0; row < matrix.getRows(); row++) {
            double reconstructed = 0.0;
            for (int column = 0; column < matrix.getColumns(); column++) {
                reconstructed += matrix.get(row, column) * x[column];
            }
            assertEquals(reconstructed, y[row], EPSILON);
        }
    }

    @Test
    void rectangularMatrixTallMatchesIndependentDenseOracle() {
        int rows = 17;
        int columns = 3;

        double[] values = {
                1, 2, 3, 4, 5, 6,
                -2, 1, 4, 3, 7, 2
        };
        int[] columnIndices = {
                0, 1, 1, 2, 0, 2,
                2, 0, 0, 1, 2, 1
        };

        int[] rowPointers = new int[rows + 1];
        rowPointers[0] = 0;
        rowPointers[1] = 2;
        rowPointers[2] = 2;
        rowPointers[3] = 4;
        rowPointers[4] = 6;
        rowPointers[5] = 6;
        rowPointers[6] = 8;
        rowPointers[7] = 8;
        rowPointers[8] = 10;
        rowPointers[9] = 12;
        rowPointers[10] = 12;
        rowPointers[11] = 12;
        rowPointers[12] = 12;
        rowPointers[13] = 12;
        rowPointers[14] = 12;
        rowPointers[15] = 12;
        rowPointers[16] = 12;
        rowPointers[17] = 12;

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columnIndices, rowPointers, rows, columns);

        double[] x = {1.25, -2.0, 0.5};
        double[] expected = denseMultiply(
                denseOracle(values, columnIndices, rowPointers, rows, columns),
                x);

        assertClose(expected, matrix.multiply(x));
        assertClose(expected, matrix.multiplyParallel(x, 1, 4));
    }

    @Test
    void rectangularMatrixWideMatchesIndependentDenseOracle() {
        int rows = 3;
        int columns = 19;

        double[] values = {2.0, -3.0, 4.0, 5.0, 1.5};
        int[] columnIndices = {0, 18, 3, 3, 12};
        int[] rowPointers = {0, 2, 2, 5};

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columnIndices, rowPointers, rows, columns);

        double[] x = new double[columns];
        for (int i = 0; i < columns; i++) {
            x[i] = (i - 7) * 0.25;
        }

        double[] expected = denseMultiply(
                denseOracle(values, columnIndices, rowPointers, rows, columns),
                x);

        assertClose(expected, matrix.multiply(x));
        assertClose(expected, matrix.multiplyParallel(x, 1, 3));
    }

    @Test
    void deterministicGeneratedMatricesMatchDenseOracle() {
        Random random = new Random(20261022L);

        for (int sample = 0; sample < 100; sample++) {
            int rows = 1 + random.nextInt(20);
            int columns = 1 + random.nextInt(20);

            int[] rowPointers = new int[rows + 1];
            int nnz = 0;

            for (int row = 0; row < rows; row++) {
                rowPointers[row] = nnz;
                nnz += random.nextInt(7);
            }
            rowPointers[rows] = nnz;

            double[] values = new double[nnz];
            int[] columnIndices = new int[nnz];

            for (int p = 0; p < nnz; p++) {
                values[p] = (random.nextInt(2001) - 1000) / 100.0;
                columnIndices[p] = random.nextInt(columns);
            }

            double[] x = new double[columns];
            for (int column = 0; column < columns; column++) {
                x[column] = (random.nextInt(2001) - 1000) / 100.0;
            }

            SparseMatrixCSR matrix = new SparseMatrixCSR(
                    values, columnIndices, rowPointers, rows, columns);

            double[] expected = denseMultiply(
                    denseOracle(values, columnIndices, rowPointers, rows, columns),
                    x);

            assertClose(expected, matrix.multiply(x));
            assertClose(expected, matrix.multiplyParallel(x, 2, 3));
        }
    }

    @Test
    void sequentialAndParallelIntoMatchDenseOracleWithExternalPool() {
        double[] values = {1.0, 2.0, -3.0, 4.0, 5.0};
        int[] columns = {0, 0, 2, 1, 2};
        int[] pointers = {0, 2, 2, 5};

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columns, pointers, 3, 3);

        double[] x = {2.0, 3.0, -1.0};
        double[][] dense = denseOracle(values, columns, pointers, 3, 3);
        double[] expected = denseMultiply(dense, x);

        double[] sequentialOutput = new double[3];
        matrix.multiplyInto(x, sequentialOutput);
        assertClose(expected, sequentialOutput);

        double[] parallelOutput = new double[3];
        ForkJoinPool pool = new ForkJoinPool(2);
        try {
            matrix.multiplyParallelInto(x, parallelOutput, 1, pool);
            assertClose(expected, parallelOutput);
            assertFalse(pool.isShutdown());
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void zeroDimensionCasesRemainSupported() {
        SparseMatrixCSR zeroByZero = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                0);

        assertArrayEquals(new double[0], zeroByZero.multiply(new double[0]));
        assertArrayEquals(
                new double[0],
                zeroByZero.multiplyParallel(new double[0], 1, 2));

        SparseMatrixCSR zeroRows = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                5);

        assertArrayEquals(new double[0], zeroRows.multiply(new double[5]));

        SparseMatrixCSR zeroColumns = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0, 0, 0, 0},
                3,
                0);

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0},
                zeroColumns.multiply(new double[0]));
        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0},
                zeroColumns.multiplyParallel(new double[0], 1, 2));
    }
}
