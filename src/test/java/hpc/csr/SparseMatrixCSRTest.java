package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SparseMatrixCSRTest {

    private static final double EPSILON = 1.0e-12;

    /*
     * Matrix:
     *
     * [1  0  2  0]
     * [0  3  0  4]
     * [5  0  6  0]
     * [0  7  0  8]
     *
     * x = [1, 2, 3, 4]
     *
     * A*x = [7, 22, 23, 46]
     */

    private static double[] values() {
        return new double[] {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };
    }

    private static int[] columns() {
        return new int[] {
                0, 2,
                1, 3,
                0, 2,
                1, 3
        };
    }

    private static int[] rowPointers() {
        return new int[] {
                0, 2, 4, 6, 8
        };
    }

    private static double[] inputVector() {
        return new double[] {
                1.0, 2.0, 3.0, 4.0
        };
    }

    private static double[] expectedVector() {
        return new double[] {
                7.0, 22.0, 23.0, 46.0
        };
    }

    private static SparseMatrixCSR createMatrix() {
        return new SparseMatrixCSR(
                values(),
                columns(),
                rowPointers(),
                4,
                4);
    }

    @Test
    void validCsrStructureIsAccepted() {

        SparseMatrixCSR matrix = createMatrix();

        assertTrue(matrix.isValid());
        assertEquals(4, matrix.getRows());
        assertEquals(4, matrix.getColumns());
        assertEquals(8, matrix.getNonZeroCount());
        assertEquals(8, matrix.getNnz());
    }

    @Test
    void mismatchedValuesAndColumnsAreRejected() {

        int[] invalidColumns = {
                0, 2, 1, 3, 0, 2, 1
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        invalidColumns,
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void invalidRowPointerLengthIsRejected() {

        int[] invalidRowPointers = {
                0, 2, 4, 6
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        invalidRowPointers,
                        4,
                        4));
    }

    @Test
    void firstRowPointerMustBeZero() {

        int[] invalidRowPointers = {
                1, 2, 4, 6, 8
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        invalidRowPointers,
                        4,
                        4));
    }

    @Test
    void rowPointersMustBeMonotonicallyNonDecreasing() {

        int[] invalidRowPointers = {
                0, 3, 2, 6, 8
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        invalidRowPointers,
                        4,
                        4));
    }

    @Test
    void rowPointerCannotExceedNnz() {

        int[] invalidRowPointers = {
                0, 2, 4, 6, 9
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        invalidRowPointers,
                        4,
                        4));
    }

    @Test
    void lastRowPointerMustEqualNnz() {

        int[] invalidRowPointers = {
                0, 2, 4, 6, 7
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        invalidRowPointers,
                        4,
                        4));
    }

    @Test
    void negativeRowPointerIsRejected() {

        int[] invalidRowPointers = {
                0, 2, -1, 6, 8
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        invalidRowPointers,
                        4,
                        4));
    }

    @Test
    void negativeColumnIndexIsRejected() {

        int[] invalidColumns = {
                0, -1,
                1, 3,
                0, 2,
                1, 3
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        invalidColumns,
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void columnIndexOutsideMatrixIsRejected() {

        int[] invalidColumns = {
                0, 4,
                1, 3,
                0, 2,
                1, 3
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        invalidColumns,
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void negativeDimensionsAreRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        rowPointers(),
                        -1,
                        4));

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        rowPointers(),
                        4,
                        -1));
    }

    @Test
    void nullValuesAreRejected() {

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        null,
                        columns(),
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void nullColumnsAreRejected() {

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        null,
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void nullRowPointersAreRejected() {

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        null,
                        4,
                        4));
    }

    @Test
    void sequentialMultiplicationProducesExpectedResult() {

        SparseMatrixCSR matrix = createMatrix();

        double[] actual = matrix.multiply(inputVector());

        assertArrayEquals(
                expectedVector(),
                actual,
                EPSILON);
    }

    @Test
    void parallelMultiplicationProducesExpectedResult() {

        SparseMatrixCSR matrix = createMatrix();

        double[] actual = matrix.multiplyParallel(
                inputVector(),
                1,
                2);

        assertArrayEquals(
                expectedVector(),
                actual,
                EPSILON);
    }

    @Test
    void sequentialAndParallelResultsMatch() {

        SparseMatrixCSR matrix = createMatrix();

        double[] sequential =
                matrix.multiply(inputVector());

        double[] parallel =
                matrix.multiplyParallel(
                        inputVector(),
                        1,
                        2);

        assertArrayEquals(
                sequential,
                parallel,
                EPSILON);
    }

    @Test
    void multiplyIntoProducesExpectedResult() {

        SparseMatrixCSR matrix = createMatrix();

        double[] output = new double[4];

        matrix.multiplyInto(
                inputVector(),
                output);

        assertArrayEquals(
                expectedVector(),
                output,
                EPSILON);
    }

    @Test
    void multiplyParallelIntoProducesExpectedResult() {

        SparseMatrixCSR matrix = createMatrix();

        double[] output = new double[4];

        matrix.multiplyParallelInto(
                inputVector(),
                output,
                1,
                2);

        assertArrayEquals(
                expectedVector(),
                output,
                EPSILON);
    }

    @Test
    void nullInputVectorIsRejected() {

        SparseMatrixCSR matrix = createMatrix();

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiply(null));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyParallel(
                        null,
                        1,
                        2));
    }

    @Test
    void wrongInputVectorDimensionIsRejected() {

        SparseMatrixCSR matrix = createMatrix();

        double[] invalidInput = {
                1.0, 2.0, 3.0
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiply(invalidInput));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        invalidInput,
                        1,
                        2));
    }

    @Test
    void nullOutputVectorIsRejected() {

        SparseMatrixCSR matrix = createMatrix();

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyInto(
                        inputVector(),
                        null));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyParallelInto(
                        inputVector(),
                        null,
                        1,
                        2));
    }

    @Test
    void wrongOutputVectorDimensionIsRejected() {

        SparseMatrixCSR matrix = createMatrix();

        double[] invalidOutput = {
                0.0, 0.0, 0.0
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyInto(
                        inputVector(),
                        invalidOutput));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        inputVector(),
                        invalidOutput,
                        1,
                        2));
    }

    @Test
    void invalidParallelThresholdIsRejected() {

        SparseMatrixCSR matrix = createMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        inputVector(),
                        0,
                        2));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        inputVector(),
                        new double[4],
                        0,
                        2));
    }

    @Test
    void invalidParallelismIsRejected() {

        SparseMatrixCSR matrix = createMatrix();

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        inputVector(),
                        1,
                        0));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        inputVector(),
                        new double[4],
                        1,
                        0));
    }

    @Test
    void metadataIsCorrect() {

        SparseMatrixCSR matrix = createMatrix();

        assertEquals(4, matrix.getRows());
        assertEquals(4, matrix.getColumns());
        assertEquals(8, matrix.getNonZeroCount());
        assertEquals(8, matrix.getNnz());

        assertEquals(
                0.5,
                matrix.getDensity(),
                EPSILON);
    }

    @Test
    void csrArraysAreReturnedAsDefensiveCopies() {

        SparseMatrixCSR matrix = createMatrix();

        double[] returnedValues =
                matrix.getValues();

        int[] returnedColumns =
                matrix.getColumnIndices();

        int[] returnedRowPointers =
                matrix.getRowPointers();

        returnedValues[0] = 999.0;
        returnedColumns[0] = 999;
        returnedRowPointers[0] = 999;

        assertEquals(
                1.0,
                matrix.getValues()[0],
                EPSILON);

        assertEquals(
                0,
                matrix.getColumnIndices()[0]);

        assertEquals(
                0,
                matrix.getRowPointers()[0]);
    }

    @Test
    void matrixElementAccessIsCorrect() {

        SparseMatrixCSR matrix = createMatrix();

        assertEquals(
                1.0,
                matrix.get(0, 0),
                EPSILON);

        assertEquals(
                2.0,
                matrix.get(0, 2),
                EPSILON);

        assertEquals(
                4.0,
                matrix.get(1, 3),
                EPSILON);

        assertEquals(
                6.0,
                matrix.get(2, 2),
                EPSILON);

        assertEquals(
                8.0,
                matrix.get(3, 3),
                EPSILON);

        assertEquals(
                0.0,
                matrix.get(0, 1),
                EPSILON);
    }

    @Test
    void matrixElementAccessRejectsInvalidIndices() {

        SparseMatrixCSR matrix = createMatrix();

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
    void zeroSizeMatrixCanBeRepresented() {

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        0,
                        0);

        assertTrue(matrix.isValid());
        assertEquals(0, matrix.getRows());
        assertEquals(0, matrix.getColumns());
        assertEquals(0, matrix.getNonZeroCount());
        assertEquals(
                0.0,
                matrix.getDensity(),
                EPSILON);

        double[] result =
                matrix.multiply(new double[0]);

        assertNotNull(result);
        assertEquals(0, result.length);
    }

    @Test
    void emptyRowsAreHandledCorrectly() {

        /*
         * Matrix:
         *
         * [1 0 0]
         * [0 0 0]
         * [0 0 2]
         */

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(
                        new double[] {1.0, 2.0},
                        new int[] {0, 2},
                        new int[] {0, 1, 1, 2},
                        3,
                        3);

        double[] actual =
                matrix.multiply(
                        new double[] {
                                5.0, 7.0, 11.0
                        });

        assertArrayEquals(
                new double[] {
                        5.0, 0.0, 22.0
                },
                actual,
                EPSILON);
    }

    @Test
    void toStringContainsRelevantMetadata() {

        SparseMatrixCSR matrix = createMatrix();

        String text = matrix.toString();

        assertTrue(text.contains("rows=4"));
        assertTrue(text.contains("columns=4"));
        assertTrue(text.contains("nonZeroCount=8"));
        assertTrue(text.contains("density="));
    }
}