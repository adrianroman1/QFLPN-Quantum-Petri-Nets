package hpc.csr;

import java.util.Arrays;
import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Contract tests for SparseMatrixCSR.
 *
 * These tests verify constructor invariants, immutability,
 * dimensional contracts, numerical edge cases and consistency
 * between sequential and parallel multiplication.
 */
class SparseMatrixCSRContractTest {

    private static final double EPS = 1.0e-12;

    @Test
    void constructorRejectsNullArguments() {
        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        null, new int[0], new int[] {0}, 0, 0));

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        new double[0], null, new int[] {0}, 0, 0));

        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        new double[0], new int[0], null, 0, 0));
    }

    @Test
    void constructorRejectsNegativeDimensions() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[0], new int[0], new int[] {0}, -1, 0));

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[0], new int[0], new int[] {0}, 0, -1));
    }

    @Test
    void constructorRejectsInconsistentNonzeroArrays() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[0],
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void constructorRejectsInvalidRowPointerLength() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[0],
                        new int[0],
                        new int[] {0, 0},
                        2,
                        2));
    }

    @Test
    void constructorRejectsNonzeroFirstPointer() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {1, 1},
                        1,
                        1));
    }

    @Test
    void constructorRejectsDecreasingPointers() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0, 2.0},
                        new int[] {0, 1},
                        new int[] {0, 2, 1},
                        2,
                        2));
    }

    @Test
    void constructorRejectsPointerBeyondNnz() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 2},
                        1,
                        1));
    }

    @Test
    void constructorRequiresLastPointerToEqualNnz() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0, 2.0},
                        new int[] {0, 1},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void constructorRejectsOutOfRangeColumnIndices() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {2},
                        new int[] {0, 1},
                        1,
                        2));

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {-1},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void constructorRejectsNonFiniteValues() {
        double[] invalid = {
                Double.NaN,
                Double.POSITIVE_INFINITY,
                Double.NEGATIVE_INFINITY
        };

        for (double value : invalid) {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> new SparseMatrixCSR(
                            new double[] {value},
                            new int[] {0},
                            new int[] {0, 1},
                            1,
                            1));
        }
    }

    @Test
    void emptyRowsAreValidAndProduceZero() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 1},
                new int[] {0, 1, 1, 2},
                3,
                2);

        assertArrayEquals(
                new double[] {8.0, 0.0, 21.0},
                matrix.multiply(new double[] {4.0, 7.0}),
                EPS);
    }

    @Test
    void duplicateEntriesHaveAdditiveMathematicalMeaning() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, -1.0},
                new int[] {0, 0, 1},
                new int[] {0, 3},
                1,
                2);

        assertEquals(5.0, matrix.get(0, 0), EPS);
        assertEquals(-1.0, matrix.get(0, 1), EPS);

        assertArrayEquals(
                new double[] {13.0},
                matrix.multiply(new double[] {4.0, 7.0}),
                EPS);
    }

    @Test
    void unsortedColumnIndicesAreAccepted() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0},
                new int[] {2, 0, 1},
                new int[] {0, 3},
                1,
                3);

        assertArrayEquals(
                new double[] {41.0},
                matrix.multiply(new double[] {5.0, 3.0, 7.0}),
                EPS);
    }

    @Test
    void constructorAndGettersPreserveImmutability() {
        double[] values = {2.0, 3.0};
        int[] columns = {0, 1};
        int[] pointers = {0, 2};

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columns, pointers, 1, 2);

        values[0] = 100.0;
        columns[0] = 1;
        pointers[1] = 0;

        assertArrayEquals(
                new double[] {2.0, 3.0},
                matrix.getValues(),
                EPS);

        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2},
                matrix.getRowPointers());

        double[] returnedValues = matrix.getValues();
        int[] returnedColumns = matrix.getColumnIndices();
        int[] returnedPointers = matrix.getRowPointers();

        returnedValues[0] = -500.0;
        returnedColumns[0] = 99;
        returnedPointers[0] = 99;

        assertEquals(2.0, matrix.getValues()[0], EPS);
        assertEquals(0, matrix.getColumnIndices()[0]);
        assertEquals(0, matrix.getRowPointers()[0]);
        assertTrue(matrix.isValid());
    }

    @Test
    void matrixVectorDimensionContractIsEnforced() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0},
                new int[] {0},
                new int[] {0, 1},
                1,
                2);

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiply(new double[] {1.0}));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyInto(
                        new double[] {1.0},
                        new double[1]));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyInto(
                        new double[] {1.0, 2.0},
                        new double[2]));
    }

    @Test
    void outputVectorIsCompletelyOverwritten() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0},
                new int[] {0},
                new int[] {0, 1, 1},
                2,
                1);

        double[] output = {999.0, 999.0};

        matrix.multiplyInto(new double[] {3.0}, output);

        assertArrayEquals(
                new double[] {6.0, 0.0},
                output,
                EPS);
    }

    @Test
    void inPlaceMultiplicationIsSafeForSquareMatrix() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.0, 2.0, 3.0, 4.0},
                new int[] {0, 1, 0, 1},
                new int[] {0, 2, 4},
                2,
                2);

        double[] vector = {5.0, 7.0};

        matrix.multiplyInto(vector, vector);

        assertArrayEquals(
                new double[] {19.0, 43.0},
                vector,
                EPS);
    }

    @Test
    void parallelAndSequentialResultsAreEquivalent() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0,
                        3.0, 4.0,
                        5.0, 6.0
                },
                new int[] {
                        0, 2,
                        1, 3,
                        0, 2
                },
                new int[] {0, 2, 4, 6},
                3,
                4);

        double[] vector = {2.0, 3.0, 5.0, 7.0};

        assertArrayEquals(
                matrix.multiply(vector),
                matrix.multiplyParallel(vector, 1, 3),
                EPS);
    }

    @Test
    void callerOwnedPoolRemainsOpenAfterMultiplication() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 1},
                new int[] {0, 1, 2},
                2,
                2);

        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            double[] output = new double[2];

            matrix.multiplyParallelInto(
                    new double[] {4.0, 5.0},
                    output,
                    1,
                    pool);

            assertArrayEquals(
                    new double[] {8.0, 15.0},
                    output,
                    EPS);

            assertFalse(pool.isShutdown());
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void parallelConfigurationMustBePositive() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.0},
                new int[] {0},
                new int[] {0, 1},
                1,
                1);

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        new double[] {1.0}, 0, 1));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallel(
                        new double[] {1.0}, 1, 0));

        assertThrows(
                IllegalArgumentException.class,
                () -> matrix.multiplyParallelInto(
                        new double[] {1.0},
                        new double[1],
                        -1,
                        1));
    }

    @Test
    void zeroDimensionContractsAreSupported() {
        SparseMatrixCSR zeroByZero = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                0);

        assertArrayEquals(
                new double[0],
                zeroByZero.multiply(new double[0]));

        SparseMatrixCSR zeroRows = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                4);

        assertArrayEquals(
                new double[0],
                zeroRows.multiply(new double[4]));

        SparseMatrixCSR zeroColumns = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0, 0, 0},
                2,
                0);

        assertArrayEquals(
                new double[] {0.0, 0.0},
                zeroColumns.multiply(new double[0]),
                EPS);
    }

    @Test
    void densityUsesMatrixDimensionsAndNnz() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.0, 2.0, 3.0},
                new int[] {0, 1, 2},
                new int[] {0, 2, 3},
                2,
                3);

        assertEquals(0.5, matrix.getDensity(), EPS);
        assertEquals(3, matrix.getNnz());
        assertEquals(3, matrix.getNonZeroCount());
    }

    @Test
    void getRejectsInvalidCoordinates() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.0},
                new int[] {0},
                new int[] {0, 1},
                1,
                1);

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(-1, 0));

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(1, 0));

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(0, -1));

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> matrix.get(0, 1));
    }

    @Test
    void deterministicInputProducesDeterministicOutput() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {1.25, -2.0, 3.5, 4.0, -1.5},
                new int[] {0, 2, 1, 0, 2},
                new int[] {0, 2, 3, 5},
                3,
                3);

        double[] input = {2.0, -3.0, 4.0};
        double[] first = matrix.multiply(input);

        for (int repetition = 0; repetition < 20; repetition++) {
            assertArrayEquals(
                    first,
                    matrix.multiply(input),
                    EPS);

            assertArrayEquals(
                    first,
                    matrix.multiplyParallel(input, 1, 3),
                    EPS);
        }
    }
}
