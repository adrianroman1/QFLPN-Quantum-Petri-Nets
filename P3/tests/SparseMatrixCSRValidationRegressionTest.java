package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSRValidationRegressionTest {

    private static SparseMatrixCSR create(
            double[] values,
            int[] columns,
            int[] pointers,
            int rows,
            int columnCount) {

        return new SparseMatrixCSR(
                values, columns, pointers, rows, columnCount);
    }

    @Test
    void rejectsNegativeRowCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        -1,
                        2));
    }

    @Test
    void rejectsNegativeColumnCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[0],
                        new int[0],
                        new int[] {0, 0},
                        1,
                        -1));
    }

    @Test
    void rejectsDifferentValuesAndColumnArrayLengths() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0, 2.0},
                        new int[] {0},
                        new int[] {0, 2},
                        1,
                        1));
    }

    @Test
    void rejectsIncorrectRowPointerLength() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        2,
                        2));
    }

    @Test
    void rejectsNonzeroFirstRowPointer() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {1, 1},
                        1,
                        1));
    }

    @Test
    void rejectsDecreasingRowPointers() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 1, 0},
                        2,
                        1));
    }

    @Test
    void rejectsNegativeRowPointers() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[0],
                        new int[0],
                        new int[] {0, -1},
                        1,
                        1));
    }

    @Test
    void rejectsPointersBeyondNonzeroCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 2},
                        1,
                        1));
    }

    @Test
    void rejectsLastPointerDifferentFromNnz() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0, 2.0},
                        new int[] {0, 0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void rejectsNegativeColumnIndex() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0},
                        new int[] {-1},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void rejectsColumnIndexEqualToColumnCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {1.0},
                        new int[] {2},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void rejectsNanValues() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {Double.NaN},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void rejectsPositiveInfinity() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {Double.POSITIVE_INFINITY},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void rejectsNegativeInfinity() {
        assertThrows(
                IllegalArgumentException.class,
                () -> create(
                        new double[] {Double.NEGATIVE_INFINITY},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void rejectsNullConstructorArrays() {
        assertThrows(
                NullPointerException.class,
                () -> create(null, new int[0], new int[] {0}, 0, 0));

        assertThrows(
                NullPointerException.class,
                () -> create(new double[0], null, new int[] {0}, 0, 0));

        assertThrows(
                NullPointerException.class,
                () -> create(new double[0], new int[0], null, 0, 0));
    }

    @Test
    void acceptsZeroByZeroMatrix() {
        SparseMatrixCSR matrix = create(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                0);

        assertTrue(matrix.isValid());
        assertEquals(0, matrix.getNnz());
        assertEquals(0, matrix.getRows());
        assertEquals(0, matrix.getColumns());
    }

    @Test
    void acceptsMatrixWithZeroColumns() {
        SparseMatrixCSR matrix = create(
                new double[0],
                new int[0],
                new int[] {0, 0, 0},
                2,
                0);

        assertTrue(matrix.isValid());

        assertArrayEquals(
                new double[] {0.0, 0.0},
                matrix.multiply(new double[0]));
    }
}
