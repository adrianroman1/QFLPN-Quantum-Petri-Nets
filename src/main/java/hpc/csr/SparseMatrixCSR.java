package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Teste unitare pentru SparseMatrixCSR.
 *
 * Verifică:
 * 1. validarea structurii CSR;
 * 2. multiplicarea secvențială;
 * 3. multiplicarea paralelă;
 * 4. variantele Into fără alocarea rezultatului;
 * 5. validarea vectorilor;
 * 6. metadatele matricei;
 * 7. accesul la elemente;
 * 8. consistența rezultatelor secvențial/paralel.
 */
class SparseMatrixCSRTest {

    private static final double TOLERANCE = 1.0e-12;

    /**
     * Matricea de referință:
     *
     * A =
     *
     * [ 1  0  2  0 ]
     * [ 0  3  0  4 ]
     * [ 5  0  6  0 ]
     * [ 0  7  0  8 ]
     *
     * x = [1, 2, 3, 4]^T
     *
     * A*x = [7, 22, 23, 46]^T
     */
    private SparseMatrixCSR createReferenceMatrix() {

        double[] values = {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };

        int[] columns = {
                0, 2,
                1, 3,
                0, 2,
                1, 3
        };

        int[] rowPointers = {
                0, 2, 4, 6, 8
        };

        return new SparseMatrixCSR(
                values,
                columns,
                rowPointers,
                4,
                4);
    }

    @Test
    void shouldValidateReferenceCSRStructure() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertTrue(matrix.isValid());
    }

    @Test
    void shouldRejectDifferentValuesAndColumnLengths() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0, 2.0},
                        new int[]{0},
                        new int[]{0, 1},
                        1,
                        1));
    }

    @Test
    void shouldRejectInvalidRowPointerLength() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{0},
                        new int[]{0},
                        1,
                        1));
    }

    @Test
    void shouldRejectFirstRowPointerDifferentFromZero() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{0},
                        new int[]{1, 1},
                        1,
                        1));
    }

    @Test
    void shouldRejectNonMonotonicRowPointers() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0, 2.0},
                        new int[]{0, 1},
                        new int[]{0, 2, 1},
                        2,
                        2));
    }

    @Test
    void shouldRejectRowPointerGreaterThanNNZ() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{0},
                        new int[]{0, 2},
                        1,
                        1));
    }

    @Test
    void shouldRejectLastRowPointerDifferentFromNNZ() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{0},
                        new int[]{0, 0},
                        1,
                        1));
    }

    @Test
    void shouldRejectNegativeRowPointer() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{0},
                        new int[]{0, -1},
                        1,
                        1));
    }

    @Test
    void shouldRejectColumnIndexOutOfBounds() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{4},
                        new int[]{0, 1},
                        1,
                        4));
    }

    @Test
    void shouldRejectNegativeColumnIndex() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{1.0},
                        new int[]{-1},
                        new int[]{0, 1},
                        1,
                        1));
    }

    @Test
    void shouldRejectNegativeDimensions() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{},
                        new int[]{},
                        new int[]{0},
                        -1,
                        0));

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[]{},
                        new int[]{},
                        new int[]{0},
                        0,
                        -1));
    }

    @Test
    void shouldRejectNullArrays() {

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        null,
                        new int[]{},
                        new int[]{0},
                        0,
                        0));

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        new double[]{},
                        null,
                        new int[]{0},
                        0,
                        0));

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        new double[]{},
                        new int[]{},
                        null,
                        0,
                        0));
    }

    @Test
    void shouldComputeCorrectSequentialMultiplication() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0
        };

        double[] expected = {
                7.0, 22.0, 23.0, 46.0
        };

        double[] actual =
                matrix.multiply(input);

        assertArrayEquals(
                expected,
                actual,
                TOLERANCE);
    }

    @Test
    void shouldComputeCorrectParallelMultiplication() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0
        };

        double[] expected = {
                7.0, 22.0, 23.0, 46.0
        };

        double[] actual =
                matrix.multiplyParallel(
                        input,
                        1,
                        2);

        assertArrayEquals(
                expected,
                actual,
                TOLERANCE);
    }

    @Test
    void sequentialAndParallelResultsShouldMatch() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0
        };

        double[] sequential =
                matrix.multiply(input);

        double[] parallel =
                matrix.multiplyParallel(
                        input,
                        1,
                        2);

        assertArrayEquals(
                sequential,
                parallel,
                TOLERANCE);
    }

    @Test
    void shouldComputeCorrectMultiplyInto() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0
        };

        double[] output =
                new double[4];

        matrix.multiplyInto(
                input,
                output);

        assertArrayEquals(
                new double[]{
                        7.0, 22.0, 23.0, 46.0
                },
                output,
                TOLERANCE);
    }

    @Test
    void shouldComputeCorrectParallelMultiplyInto() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0
        };

        double[] output =
                new double[4];

        matrix.multiplyParallelInto(
                input,
                output,
                1,
                2);

        assertArrayEquals(
                new double[]{
                        7.0, 22.0, 23.0, 46.0
                },
                output,
                TOLERANCE);
    }

    @Test
    void shouldRejectNullInputVector() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiply(null));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyInto(
                        null,
                        new double[4]));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyParallel(
                        null,
                        1,
                        2));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyParallelInto(
                        null,
                        new double[4],
                        1,
                        2));
    }

    @Test
    void shouldRejectWrongInputVectorLength() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiply(
                        new double[3]));
    }

    @Test
    void shouldRejectWrongOutputVectorLength() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyInto(
                        new double[4],
                        new double[3]));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        new double[4],
                        new double[3],
                        1,
                        2));
    }

    @Test
    void shouldRejectNullOutputVector() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyInto(
                        new double[4],
                        null));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyParallelInto(
                        new double[4],
                        null,
                        1,
                        2));
    }

    @Test
    void shouldRejectInvalidParallelThreshold() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        new double[4],
                        0,
                        2));
    }

    @Test
    void shouldRejectInvalidParallelism() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        new double[4],
                        1,
                        0));
    }

    @Test
    void shouldRejectInvalidParallelIntoConfiguration() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        new double[4],
                        new double[4],
                        0,
                        2));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        new double[4],
                        new double[4],
                        1,
                        0));
    }

    @Test
    void shouldExposeCorrectMetadata() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertEquals(4, matrix.getRows());
        assertEquals(4, matrix.getColumns());
        assertEquals(8, matrix.getNonZeroCount());
        assertEquals(8, matrix.getNnz());

        assertEquals(
                0.5,
                matrix.getDensity(),
                TOLERANCE);
    }

    @Test
    void shouldReturnDefensiveCopiesOfCSRArrays() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        double[] values =
                matrix.getValues();

        int[] columns =
                matrix.getColumnIndices();

        int[] rowPointers =
                matrix.getRowPointers();

        values[0] = 999.0;
        columns[0] = 999;
        rowPointers[0] = 999;

        assertEquals(
                1.0,
                matrix.get(0, 0),
                TOLERANCE);

        assertEquals(
                0,
                matrix.getRowPointers()[0]);

        assertEquals(
                0,
                matrix.getColumnIndices()[0]);
    }

    @Test
    void shouldReturnCorrectElementValues() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertEquals(
                1.0,
                matrix.get(0, 0),
                TOLERANCE);

        assertEquals(
                2.0,
                matrix.get(0, 2),
                TOLERANCE);

        assertEquals(
                0.0,
                matrix.get(0, 1),
                TOLERANCE);

        assertEquals(
                8.0,
                matrix.get(3, 3),
                TOLERANCE);
    }

    @Test
    void shouldRejectOutOfBoundsElementAccess() {

        SparseMatrixCSR matrix =
                createReferenceMatrix();

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(-1, 0));

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(4, 0));

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(0, -1));

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(0, 4));
    }

    @Test
    void shouldSupportZeroSizeMatrix() {

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(
                        new double[]{},
                        new int[]{},
                        new int[]{0},
                        0,
                        0);

        assertTrue(matrix.isValid());
        assertEquals(0, matrix.getRows());
        assertEquals(0, matrix.getColumns());
        assertEquals(0, matrix.getNonZeroCount());
        assertFalse(matrix.getDensity() > 0.0);

        assertArrayEquals(
                new double[]{},
                matrix.multiply(new double[]{}),
                TOLERANCE);
    }
}