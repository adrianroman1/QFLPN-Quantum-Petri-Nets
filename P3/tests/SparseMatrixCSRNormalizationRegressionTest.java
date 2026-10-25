package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSRNormalizationRegressionTest {

    private static final double EPS = 1.0e-12;

    @Test
    void sortsColumnIndicesWithinEachRow() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0, 5.0},
                new int[] {3, 0, 2, 1},
                new int[] {0, 2, 4},
                2,
                4);

        assertArrayEquals(
                new int[] {0, 3, 1, 2},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {3.0, 2.0, 5.0, 4.0},
                matrix.getValues(),
                EPS);

        assertArrayEquals(
                new int[] {0, 2, 4},
                matrix.getRowPointers());
    }

    @Test
    void combinesDuplicateColumnsWithinSameRow() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0, 5.0},
                new int[] {1, 1, 0, 1},
                new int[] {0, 3, 4},
                2,
                2);

        assertArrayEquals(
                new int[] {0, 1, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {4.0, 5.0, 5.0},
                matrix.getValues(),
                EPS);

        assertArrayEquals(
                new int[] {0, 2, 3},
                matrix.getRowPointers());

        assertEquals(5.0, matrix.get(0, 1), EPS);
        assertEquals(4.0, matrix.get(0, 0), EPS);
        assertEquals(5.0, matrix.get(1, 1), EPS);
        assertEquals(3, matrix.getNonZeroCount());
    }

    @Test
    void duplicateEntriesWithOppositeValuesPreserveZeroSum() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {7.0, -7.0, 2.0},
                new int[] {0, 0, 1},
                new int[] {0, 3},
                1,
                2);

        assertEquals(0.0, matrix.get(0, 0), EPS);
        assertEquals(2.0, matrix.get(0, 1), EPS);

        assertArrayEquals(
                new double[] {6.0},
                matrix.multiply(new double[] {100.0, 3.0}),
                EPS);

        assertEquals(2, matrix.getNnz());
    }

    @Test
    void normalizationDoesNotMergeEntriesAcrossRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 0},
                new int[] {0, 1, 2},
                2,
                1);

        assertArrayEquals(
                new int[] {0, 0},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {2.0, 3.0},
                matrix.getValues(),
                EPS);

        assertArrayEquals(
                new int[] {0, 1, 2},
                matrix.getRowPointers());

        assertArrayEquals(
                new double[] {8.0, 12.0},
                matrix.multiply(new double[] {4.0}),
                EPS);
    }

    @Test
    void normalizationPreservesEmptyRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {1, 0},
                new int[] {0, 1, 1, 2, 2},
                4,
                2);

        assertArrayEquals(
                new int[] {1, 0},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 1, 1, 2, 2},
                matrix.getRowPointers());

        assertArrayEquals(
                new double[] {6.0, 0.0, 8.0, 0.0},
                matrix.multiply(new double[] {4.0, 3.0}),
                EPS);
    }

    @Test
    void normalizedArraysAreIndependentOfConstructorArrays() {
        double[] values = {2.0, 3.0, 4.0};
        int[] columns = {2, 0, 1};
        int[] pointers = {0, 3};

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columns, pointers, 1, 3);

        values[0] = 100.0;
        columns[0] = 0;
        pointers[1] = 0;

        assertArrayEquals(
                new double[] {3.0, 4.0, 2.0},
                matrix.getValues(),
                EPS);

        assertArrayEquals(
                new int[] {0, 1, 2},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 3},
                matrix.getRowPointers());

        assertTrue(matrix.isValid());
    }
}
