package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class SparseMatrixCSRNormalizationRegressionTest {

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
                new double[] {6.0, 0.0, 12.0, 0.0},
                matrix.multiply(new double[] {4.0, 3.0}),
                1.0e-12);
    }

    @Test
    void normalizationPreservesValuesAndNonZeroCount() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0},
                new int[] {2, 0, 1},
                new int[] {0, 2, 3},
                2,
                3);

        assertEquals(3, matrix.getNonZeroCount());
        assertEquals(3, matrix.getNnz());

        assertArrayEquals(
                new double[] {3.0, 2.0, 4.0},
                matrix.getValues(),
                0.0);

        assertArrayEquals(
                new int[] {0, 2, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2, 3},
                matrix.getRowPointers());
    }

    @Test
    void normalizationPreservesMatrixDimensions() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {5.0},
                new int[] {1},
                new int[] {0, 0, 1, 1},
                3,
                2);

        assertEquals(3, matrix.getRows());
        assertEquals(2, matrix.getColumns());
    }

    @Test
    void normalizationPreservesEmptyMatrix() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {},
                new int[] {},
                new int[] {0, 0, 0, 0},
                3,
                2);

        assertEquals(0, matrix.getNonZeroCount());
        assertEquals(0, matrix.getNnz());

        assertArrayEquals(
                new int[] {0, 0, 0, 0},
                matrix.getRowPointers());

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0},
                matrix.multiply(new double[] {7.0, 9.0}),
                1.0e-12);
    }

    @Test
    void normalizationPreservesSingleNonZeroEntry() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {7.0},
                new int[] {1},
                new int[] {0, 0, 1},
                2,
                2);

        assertEquals(1, matrix.getNonZeroCount());

        assertArrayEquals(
                new double[] {0.0, 14.0},
                matrix.multiply(new double[] {2.0, 2.0}),
                1.0e-12);
    }

    @Test
    void duplicateColumnsAreAggregatedWithoutLosingValues() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0},
                new int[] {1, 0, 1},
                new int[] {0, 3},
                1,
                2);

        assertEquals(2, matrix.getNnz());

        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {3.0, 6.0},
                matrix.getValues(),
                0.0);

        assertEquals(6.0, matrix.get(0, 1), 0.0);

        assertArrayEquals(
                new double[] {15.0},
                matrix.multiply(new double[] {1.0, 2.0}),
                1.0e-12);
    }

    @Test
    void duplicateAggregationRejectsPositiveOverflow() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {
                                Double.MAX_VALUE,
                                Double.MAX_VALUE
                        },
                        new int[] {0, 0},
                        new int[] {0, 2},
                        1,
                        1));
    }

    @Test
    void duplicateAggregationRejectsNegativeOverflow() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {
                                -Double.MAX_VALUE,
                                -Double.MAX_VALUE
                        },
                        new int[] {0, 0},
                        new int[] {0, 2},
                        1,
                        1));
    }

    @Test
    void normalizedMatrixRemainsValid() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.5, 2.5},
                new int[] {0, 1},
                new int[] {0, 1, 2},
                2,
                2);

        assertTrue(matrix.isValid());
    }
}
