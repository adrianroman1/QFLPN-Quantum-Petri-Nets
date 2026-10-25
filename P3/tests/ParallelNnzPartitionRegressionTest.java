package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class ParallelNnzPartitionRegressionTest {

    private static final double TOLERANCE = 1.0e-12;

    @Test
    void nnzBalancedParallelMultiplicationMatchesSequentialForSkewedRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0, 3.0, 4.0, 5.0, 6.0,
                        7.0, 8.0, 9.0, 10.0, 11.0
                },
                new int[] {
                        0, 1, 2, 3, 4, 5,
                        6, 7, 0, 1, 2
                },
                new int[] {
                        0, 8, 8, 8, 8, 8, 8, 11
                },
                7,
                8);

        double[] input = {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };

        double[] expected = matrix.multiply(input);

        double[] actual = matrix.multiplyParallel(
                input,
                1,
                4);

        assertArrayEquals(expected, actual, TOLERANCE);
    }

    @Test
    void nnzBalancedParallelMultiplicationPreservesEmptyRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0},
                new int[] {0, 1, 2},
                new int[] {0, 1, 1, 1, 2, 2, 3, 3},
                7,
                3);

        double[] input = {5.0, 6.0, 7.0};

        assertArrayEquals(
                matrix.multiply(input),
                matrix.multiplyParallel(input, 1, 3),
                TOLERANCE);
    }

    @Test
    void nnzBalancedParallelMultiplicationHandlesOneGiantRow() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0, 3.0, 4.0, 5.0,
                        6.0, 7.0, 8.0, 9.0, 10.0
                },
                new int[] {
                        0, 1, 2, 3, 4,
                        5, 6, 7, 8, 9
                },
                new int[] {0, 10, 10, 10, 10, 10},
                5,
                10);

        double[] input = {
                1.0, 1.0, 1.0, 1.0, 1.0,
                1.0, 1.0, 1.0, 1.0, 1.0
        };

        assertArrayEquals(
                matrix.multiply(input),
                matrix.multiplyParallel(input, 1, 4),
                TOLERANCE);
    }

    @Test
    void nnzBalancedParallelMultiplicationHandlesAllEmptyRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {},
                new int[] {},
                new int[] {0, 0, 0, 0, 0, 0, 0},
                6,
                4);

        double[] input = {1.0, 2.0, 3.0, 4.0};

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0, 0.0, 0.0, 0.0},
                matrix.multiplyParallel(input, 1, 4),
                TOLERANCE);
    }

    @Test
    void parallelMultiplicationPreservesInputOutputAliasing() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        2.0, 1.0,
                        3.0, 4.0,
                        5.0, 6.0,
                        7.0, 8.0
                },
                new int[] {
                        0, 1,
                        1, 2,
                        2, 3,
                        0, 3
                },
                new int[] {0, 2, 4, 6, 8},
                4,
                4);

        double[] initial = {1.0, 2.0, 3.0, 4.0};
        double[] expected = matrix.multiply(initial);

        double[] aliased = initial.clone();

        matrix.multiplyParallelInto(
                aliased,
                aliased,
                1,
                3);

        assertArrayEquals(expected, aliased, TOLERANCE);
    }

    @Test
    void parallelMultiplicationMatchesSequentialAcrossThresholds() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0,
                        3.0, 4.0,
                        5.0, 6.0,
                        7.0, 8.0,
                        9.0, 10.0,
                        11.0, 12.0
                },
                new int[] {
                        0, 1,
                        1, 2,
                        2, 3,
                        3, 4,
                        4, 5,
                        0, 5
                },
                new int[] {0, 2, 4, 6, 8, 10, 12},
                6,
                6);

        double[] input = {
                1.0, 2.0, 3.0, 4.0, 5.0, 6.0
        };

        double[] expected = matrix.multiply(input);

        for (int threshold : new int[] {1, 2, 3, 6, 20}) {
            double[] actual = matrix.multiplyParallel(
                    input,
                    threshold,
                    4);

            assertArrayEquals(
                    expected,
                    actual,
                    TOLERANCE,
                    "Mismatch for threshold=" + threshold);
        }
    }

    @Test
    void parallelMultiplicationHandlesZeroRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {},
                new int[] {},
                new int[] {0},
                0,
                3);

        double[] result = matrix.multiplyParallel(
                new double[] {1.0, 2.0, 3.0},
                1,
                2);

        assertEquals(0, result.length);
    }
}
