package hpc.csr;

import java.util.Arrays;
import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSRTest {

    private static final double EPSILON = 1.0e-12;

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

    private static double[] inputVector() {
        return new double[] {1.0, 2.0, 3.0, 4.0};
    }

    private static double[] expectedVector() {
        return new double[] {7.0, 22.0, 23.0, 46.0};
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
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        new int[] {0, 2, 1},
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void invalidRowPointerLengthIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        new int[] {0, 2, 4, 6},
                        4,
                        4));
    }

    @Test
    void firstRowPointerMustBeZero() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        new int[] {1, 2, 4, 6, 8},
                        4,
                        4));
    }

    @Test
    void rowPointersMustBeMonotonicallyNonDecreasing() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        new int[] {0, 3, 2, 6, 8},
                        4,
                        4));
    }

    @Test
    void rowPointerCannotExceedNnz() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        new int[] {0, 2, 4, 6, 9},
                        4,
                        4));
    }

    @Test
    void lastRowPointerMustEqualNnz() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        new int[] {0, 2, 4, 6, 7},
                        4,
                        4));
    }

    @Test
    void negativeRowPointerIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        columns(),
                        new int[] {0, 2, -1, 6, 8},
                        4,
                        4));
    }

    @Test
    void negativeColumnIndexIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        new int[] {0, -1, 1, 3, 0, 2, 1, 3},
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void columnIndexOutsideMatrixIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(),
                        new int[] {0, 4, 1, 3, 0, 2, 1, 3},
                        rowPointers(),
                        4,
                        4));
    }

    @Test
    void negativeDimensionsAreRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(), columns(), rowPointers(), -1, 4));

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        values(), columns(), rowPointers(), 4, -1));
    }

    @Test
    void nullArraysAreRejected() {
        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        null, columns(), rowPointers(), 4, 4));

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        values(), null, rowPointers(), 4, 4));

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        values(), columns(), null, 4, 4));
    }

    @Test
    void nanValuesAreRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {Double.NaN},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void positiveInfinityIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {Double.POSITIVE_INFINITY},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void negativeInfinityIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {Double.NEGATIVE_INFINITY},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void finiteNegativeAndZeroValuesAreAccepted() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {-2.5, 0.0},
                new int[] {0, 1},
                new int[] {0, 2},
                1,
                2);

        assertTrue(matrix.isValid());
        assertArrayEquals(
                new double[] {-5.0},
                matrix.multiply(new double[] {2.0, 10.0}),
                EPSILON);
    }

    @Test
    void constructorMakesDefensiveCopies() {
        double[] sourceValues = {2.0, 3.0};
        int[] sourceColumns = {0, 1};
        int[] sourcePointers = {0, 2};

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                sourceValues,
                sourceColumns,
                sourcePointers,
                1,
                2);

        sourceValues[0] = 999.0;
        sourceColumns[0] = 1;
        sourcePointers[1] = 0;

        assertArrayEquals(
                new double[] {2.0, 3.0},
                matrix.getValues(),
                EPSILON);
        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());
        assertArrayEquals(
                new int[] {0, 2},
                matrix.getRowPointers());

        assertTrue(matrix.isValid());
    }

    @Test
    void sequentialMultiplicationProducesExpectedResult() {
        assertArrayEquals(
                expectedVector(),
                createMatrix().multiply(inputVector()),
                EPSILON);
    }

    @Test
    void parallelMultiplicationProducesExpectedResult() {
        assertArrayEquals(
                expectedVector(),
                createMatrix().multiplyParallel(
                        inputVector(),
                        1,
                        2),
                EPSILON);
    }

    @Test
    void sequentialAndParallelResultsMatch() {
        SparseMatrixCSR matrix = createMatrix();

        assertArrayEquals(
                matrix.multiply(inputVector()),
                matrix.multiplyParallel(inputVector(), 1, 2),
                EPSILON);
    }

    @Test
    void multiplyIntoProducesExpectedResult() {
        double[] output = new double[4];

        createMatrix().multiplyInto(inputVector(), output);

        assertArrayEquals(
                expectedVector(),
                output,
                EPSILON);
    }

    @Test
    void parallelIntoProducesExpectedResult() {
        double[] output = new double[4];

        createMatrix().multiplyParallelInto(
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
    void parallelIntoWorksWithCallerOwnedPool() {
        double[] output = new double[4];
        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            createMatrix().multiplyParallelInto(
                    inputVector(),
                    output,
                    1,
                    pool);

            assertArrayEquals(
                    expectedVector(),
                    output,
                    EPSILON);

            assertFalse(pool.isShutdown());
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void sequentialIntoSupportsAliasedInputAndOutput() {
        SparseMatrixCSR matrix = createMatrix();
        double[] aliased = inputVector();

        matrix.multiplyInto(aliased, aliased);

        assertArrayEquals(
                expectedVector(),
                aliased,
                EPSILON);
    }

    @Test
    void parallelIntoSupportsAliasedInputAndOutput() {
        SparseMatrixCSR matrix = createMatrix();
        double[] aliased = inputVector();

        matrix.multiplyParallelInto(
                aliased,
                aliased,
                1,
                2);

        assertArrayEquals(
                expectedVector(),
                aliased,
                EPSILON);
    }

    @Test
    void parallelIntoWithExternalPoolSupportsAliasing() {
        SparseMatrixCSR matrix = createMatrix();
        double[] aliased = inputVector();
        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            matrix.multiplyParallelInto(
                    aliased,
                    aliased,
                    1,
                    pool);
        } finally {
            pool.shutdown();
        }

        assertArrayEquals(
                expectedVector(),
                aliased,
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
                () -> matrix.multiplyParallel(null, 1, 2));

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyInto(null, new double[4]));
    }

    @Test
    void wrongInputVectorDimensionIsRejected() {
        SparseMatrixCSR matrix = createMatrix();
        double[] invalid = {1.0, 2.0, 3.0};

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiply(invalid));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(invalid, 1, 2));
    }

    @Test
    void nullOutputVectorIsRejected() {
        SparseMatrixCSR matrix = createMatrix();

        assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyInto(inputVector(), null));

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

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyInto(
                        inputVector(),
                        new double[3]));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        inputVector(),
                        new double[3],
                        1,
                        2));
    }

    @Test
    void invalidThresholdIsRejected() {
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
                        -1,
                        2));
    }

    @Test
    void invalidParallelismIsRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> createMatrix().multiplyParallel(
                        inputVector(),
                        1,
                        0));
    }

    @Test
    void nullExternalPoolIsRejected() {
        assertThrows(
                NullPointerException.class,
                () -> createMatrix().multiplyParallelInto(
                        inputVector(),
                        new double[4],
                        1,
                        (ForkJoinPool) null));
    }

    @Test
    void shutdownExternalPoolIsRejected() {
        ForkJoinPool pool = new ForkJoinPool(1);
        pool.shutdown();

        assertThrows(
                IllegalStateException.class,
                () -> createMatrix().multiplyParallelInto(
                        inputVector(),
                        new double[4],
                        1,
                        pool));
    }

    @Test
    void gettersReturnDefensiveCopies() {
        SparseMatrixCSR matrix = createMatrix();

        double[] returnedValues = matrix.getValues();
        int[] returnedColumns = matrix.getColumnIndices();
        int[] returnedPointers = matrix.getRowPointers();

        returnedValues[0] = 999.0;
        returnedColumns[0] = 999;
        returnedPointers[0] = 999;

        assertEquals(1.0, matrix.getValues()[0], EPSILON);
        assertEquals(0, matrix.getColumnIndices()[0]);
        assertEquals(0, matrix.getRowPointers()[0]);
        assertTrue(matrix.isValid());
    }

    @Test
    void metadataAndDensityAreCorrect() {
        SparseMatrixCSR matrix = createMatrix();

        assertEquals(4, matrix.getRows());
        assertEquals(4, matrix.getColumns());
        assertEquals(8, matrix.getNonZeroCount());
        assertEquals(8, matrix.getNnz());
        assertEquals(0.5, matrix.getDensity(), EPSILON);
    }

    @Test
    void matrixElementAccessIsCorrect() {
        SparseMatrixCSR matrix = createMatrix();

        assertEquals(1.0, matrix.get(0, 0), EPSILON);
        assertEquals(2.0, matrix.get(0, 2), EPSILON);
        assertEquals(4.0, matrix.get(1, 3), EPSILON);
        assertEquals(6.0, matrix.get(2, 2), EPSILON);
        assertEquals(8.0, matrix.get(3, 3), EPSILON);
        assertEquals(0.0, matrix.get(0, 1), EPSILON);
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
    void zeroByZeroMatrixIsSupported() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                0);

        assertTrue(matrix.isValid());
        assertEquals(0.0, matrix.getDensity(), EPSILON);
        assertArrayEquals(new double[0], matrix.multiply(new double[0]));
        assertArrayEquals(
                new double[0],
                matrix.multiplyParallel(new double[0], 1, 2));
    }

    @Test
    void zeroRowMatrixWithColumnsIsSupported() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                5);

        assertArrayEquals(
                new double[0],
                matrix.multiply(new double[5]));
    }

    @Test
    void positiveRowsWithZeroColumnsAreSupported() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0, 0, 0, 0},
                3,
                0);

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0},
                matrix.multiply(new double[0]));

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0},
                matrix.multiplyParallel(new double[0], 1, 2));
    }

    @Test
    void emptyRowsAreHandledCorrectly() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.0, 2.0},
                new int[] {0, 2},
                new int[] {0, 1, 1, 2},
                3,
                3);

        assertArrayEquals(
                new double[] {5.0, 0.0, 22.0},
                matrix.multiply(new double[] {5.0, 7.0, 11.0}),
                EPSILON);
    }

    @Test
    void rectangularMatrixWithMoreRowsThanColumnsIsSupported() {
        int rows = 100;
        double[] data = new double[rows * 2];
        int[] columnIndices = new int[rows * 2];
        int[] pointers = new int[rows + 1];

        for (int row = 0; row < rows; row++) {
            int offset = row * 2;

            data[offset] = 1.0;
            data[offset + 1] = 1.0;

            columnIndices[offset] = 0;
            columnIndices[offset + 1] = 1;

            pointers[row] = offset;
        }

        pointers[rows] = rows * 2;

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                data,
                columnIndices,
                pointers,
                rows,
                2);

        double[] expected = new double[rows];
        Arrays.fill(expected, 5.0);

        assertArrayEquals(
                expected,
                matrix.multiplyParallel(
                        new double[] {2.0, 3.0},
                        1,
                        4),
                EPSILON);
    }

    @Test
    void rectangularMatrixWithMoreColumnsThanRowsIsSupported() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {1, 4},
                new int[] {0, 2, 2},
                2,
                5);

        assertArrayEquals(
                new double[] {16.0, 0.0},
                matrix.multiply(new double[] {1, 2, 3, 4, 4}),
                EPSILON);
    }

    @Test
    void unsortedColumnIndicesAreAccepted() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {1, 0},
                new int[] {0, 2},
                1,
                2);

        assertArrayEquals(
                new double[] {13.0},
                matrix.multiply(new double[] {5.0, 1.0}),
                EPSILON);
    }

    @Test
    void duplicateColumnIndicesAreSummedCorrectly() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 0},
                new int[] {0, 2},
                1,
                1);

        assertArrayEquals(
                new double[] {25.0},
                matrix.multiply(new double[] {5.0}),
                EPSILON);
    }

    @Test
    void toStringContainsRelevantMetadata() {
        String description = createMatrix().toString();

        assertTrue(description.contains("rows=4"));
        assertTrue(description.contains("columns=4"));
        assertTrue(description.contains("nonZeroCount=8"));
        assertTrue(description.contains("density="));
    }
}
