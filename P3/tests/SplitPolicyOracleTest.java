package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

class SplitPolicyOracleTest {

    private static final double TOLERANCE = 1.0e-12;

    private static final MultiplyTask.SplitPolicy[] POLICIES = {
            MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
            MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT
    };

    @Test
    void bothPoliciesMatchSequentialOracleForSkewedRows() {
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

        assertBothPoliciesMatchOracle(matrix, input, 1, 4);
    }

    @Test
    void bothPoliciesMatchSequentialOracleWithEmptyRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0, 4.0},
                new int[] {0, 1, 2},
                new int[] {0, 1, 1, 1, 2, 2, 3, 3},
                7,
                3);

        double[] input = {5.0, 6.0, 7.0};

        assertBothPoliciesMatchOracle(matrix, input, 1, 3);
    }

    @Test
    void bothPoliciesMatchSequentialOracleForOneGiantRow() {
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

        assertBothPoliciesMatchOracle(matrix, input, 1, 4);
    }

    @Test
    void bothPoliciesMatchSequentialOracleForAllEmptyRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0, 0, 0, 0, 0, 0, 0},
                6,
                4);

        double[] input = {1.0, 2.0, 3.0, 4.0};

        assertBothPoliciesMatchOracle(matrix, input, 1, 4);
    }

    @Test
    void bothPoliciesHandleZeroRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0},
                0,
                3);

        double[] input = {1.0, 2.0, 3.0};

        for (MultiplyTask.SplitPolicy policy : POLICIES) {
            double[] actual = matrix.multiplyParallel(
                    input,
                    1,
                    2,
                    policy);

            assertNotNull(actual);
            assertEquals(0, actual.length);
        }
    }

    @Test
    void bothPoliciesPreserveInputOutputAliasing() {
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

        for (MultiplyTask.SplitPolicy policy : POLICIES) {
            double[] aliased = initial.clone();

            matrix.multiplyParallelInto(
                    aliased,
                    aliased,
                    1,
                    3,
                    policy);

            assertArrayEquals(
                    expected,
                    aliased,
                    TOLERANCE,
                    "Aliasing mismatch for policy=" + policy);
        }
    }

    @Test
    void bothPoliciesMatchOracleAcrossSeveralThresholds() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0,
                        3.0, 4.0,
                        5.0, 6.0,
                        7.0, 8.0,
                        9.0, 10.0,
                        11.0, 12.0,
                        13.0, 14.0,
                        15.0, 16.0
                },
                new int[] {
                        0, 1,
                        1, 2,
                        2, 3,
                        3, 4,
                        4, 5,
                        5, 6,
                        6, 7,
                        0, 7
                },
                new int[] {
                        0, 2, 4, 6, 8, 10, 12, 14, 16
                },
                8,
                8);

        double[] input = {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };

        double[] expected = matrix.multiply(input);

        for (MultiplyTask.SplitPolicy policy : POLICIES) {
            for (int threshold : new int[] {1, 2, 3, 4, 8, 20}) {
                double[] actual = matrix.multiplyParallel(
                        input,
                        threshold,
                        4,
                        policy);

                assertArrayEquals(
                        expected,
                        actual,
                        TOLERANCE,
                        "Mismatch for policy=" + policy
                                + ", threshold=" + threshold);
            }
        }
    }

    @Test
    void explicitPoolOverloadSupportsBothPoliciesAndCanBeReused() {
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

        double[] input = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0};
        double[] expected = matrix.multiply(input);

        ForkJoinPool pool = new ForkJoinPool(3);

        try {
            for (MultiplyTask.SplitPolicy policy : POLICIES) {
                double[] output = new double[matrix.getRows()];

                matrix.multiplyParallelInto(
                        input,
                        output,
                        1,
                        pool,
                        policy);

                assertArrayEquals(
                        expected,
                        output,
                        TOLERANCE,
                        "Pool overload mismatch for policy=" + policy);

                assertFalse(
                        pool.isShutdown(),
                        "The caller-owned pool must remain active.");
            }
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void legacyOverloadsRemainEquivalentToExplicitScanPolicy() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0,
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

        double[] input = {1.0, 2.0, 3.0, 4.0};

        double[] legacy = matrix.multiplyParallel(
                input,
                1,
                3);

        double[] explicitScan = matrix.multiplyParallel(
                input,
                1,
                3,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN);

        assertArrayEquals(
                explicitScan,
                legacy,
                TOLERANCE);
    }

    @Test
    void nullSplitPolicyIsRejected() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0},
                new int[] {0},
                new int[] {0, 1},
                1,
                1);

        double[] input = {3.0};

        org.junit.jupiter.api.Assertions.assertThrows(
                NullPointerException.class,
                () -> matrix.multiplyParallel(input, 1, 1, null));
    }

    private static void assertBothPoliciesMatchOracle(
            SparseMatrixCSR matrix,
            double[] input,
            int threshold,
            int parallelism) {

        double[] expected = matrix.multiply(input);

        for (MultiplyTask.SplitPolicy policy : POLICIES) {
            double[] actual = matrix.multiplyParallel(
                    input,
                    threshold,
                    parallelism,
                    policy);

            assertArrayEquals(
                    expected,
                    actual,
                    TOLERANCE,
                    "Sequential oracle mismatch for policy=" + policy);
        }
    }
}
