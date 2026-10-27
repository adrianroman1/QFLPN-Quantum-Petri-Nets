package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSRScalingTest {

    @Test
    void publicConstructorAggregatesDuplicateColumns() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.5, 2.5, 3.0, 4.0},
                new int[] {2, 1, 2, 0},
                new int[] {0, 3, 4},
                2,
                3);

        assertTrue(matrix.isValid());

        assertArrayEquals(
                new int[] {1, 2, 0},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {2.5, 4.5, 4.0},
                matrix.getValues(),
                1.0e-12);

        assertArrayEquals(
                new int[] {0, 2, 3},
                matrix.getRowPointers());

        assertEquals(3, matrix.getNnz());
    }

    @Test
    void duplicateAggregationPreservesDeterministicInputOrder() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.0e16, -1.0e16, 1.0},
                new int[] {0, 0, 0},
                new int[] {0, 3},
                1,
                1);

        assertEquals(
                1.0,
                matrix.get(0, 0),
                1.0e-12);
    }

    @Test
    void publicConstructorKeepsDefensiveCopyContract() {
        double[] values = {2.0, 3.0};
        int[] columns = {0, 1};
        int[] pointers = {0, 2};

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values,
                columns,
                pointers,
                1,
                2);

        values[0] = 100.0;
        columns[0] = 1;
        pointers[1] = 0;

        assertArrayEquals(
                new double[] {2.0, 3.0},
                matrix.getValues(),
                1.0e-12);

        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2},
                matrix.getRowPointers());
    }

    @Test
    void gettersReturnDefensiveCopies() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 1},
                new int[] {0, 2},
                1,
                2);

        double[] values = matrix.getValues();
        int[] columns = matrix.getColumnIndices();
        int[] pointers = matrix.getRowPointers();

        values[0] = 99.0;
        columns[0] = 1;
        pointers[1] = 0;

        assertArrayEquals(
                new double[] {2.0, 3.0},
                matrix.getValues(),
                1.0e-12);

        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2},
                matrix.getRowPointers());
    }

    @Test
    void trustedFactoryAcceptsCanonicalCsr() {
        double[] values = {2.0, 3.0, 4.0};
        int[] columns = {0, 2, 1};
        int[] pointers = {0, 2, 3};

        SparseMatrixCSR matrix =
                SparseMatrixCSR.fromTrustedCanonical(
                        values,
                        columns,
                        pointers,
                        2,
                        3);

        assertTrue(matrix.isValid());
        assertEquals(3, matrix.getNnz());

        assertArrayEquals(
                new double[] {2.0, 3.0, 4.0},
                matrix.getValues(),
                1.0e-12);

        assertArrayEquals(
                new int[] {0, 2, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2, 3},
                matrix.getRowPointers());
    }

    @Test
    void trustedFactoryRejectsUnsortedColumns() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {1.0, 2.0},
                        new int[] {2, 1},
                        new int[] {0, 2},
                        1,
                        3));
    }

    @Test
    void trustedFactoryRejectsDuplicateColumns() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {1.0, 2.0},
                        new int[] {1, 1},
                        new int[] {0, 2},
                        1,
                        3));
    }

    @Test
    void trustedFactoryRejectsNonFiniteValues() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {1.0, Double.NaN},
                        new int[] {0, 1},
                        new int[] {0, 2},
                        1,
                        2));
    }

    @Test
    void trustedFactoryRejectsInvalidLastPointer() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {1.0, 2.0},
                        new int[] {0, 1},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void trustedFactoryRejectsOutOfRangeColumns() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {1.0},
                        new int[] {2},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void emptyRowsAreAcceptedByTrustedFactory() {
        SparseMatrixCSR matrix =
                SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {3.0},
                        new int[] {1},
                        new int[] {0, 0, 1, 1},
                        3,
                        2);

        assertTrue(matrix.isValid());

        assertArrayEquals(
                new int[] {0, 0, 1, 1},
                matrix.getRowPointers());

        assertArrayEquals(
                new double[] {0.0, 6.0, 0.0},
                matrix.multiply(new double[] {2.0, 2.0}),
                1.0e-12);
    }

    @Test
    void trustedFactoryRejectsNullArrays() {
        assertThrows(
                NullPointerException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        null,
                        new int[0],
                        new int[] {0},
                        0,
                        0));

        assertThrows(
                NullPointerException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[0],
                        null,
                        new int[] {0},
                        0,
                        0));

        assertThrows(
                NullPointerException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[0],
                        new int[0],
                        null,
                        0,
                        0));
    }
}
