package hpc.csr;

import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SpmvPlanExecutionTest {

    private static final double TOLERANCE = 1.0e-12;
    private static final int PARALLELISM = 4;
    private static final int THRESHOLD = 2;

    private static SparseMatrixCSR createMatrix() {
        return new SparseMatrixCSR(
                new double[] {
                        2.0, 3.0,
                        4.0,
                        5.0, 6.0,
                        7.0,
                        8.0, 9.0
                },
                new int[] {
                        0, 2,
                        1,
                        0, 3,
                        2,
                        1, 4
                },
                new int[] {
                        0, 2, 3, 5, 6, 8
                },
                5,
                5
        );
    }

    private static double[] createInput() {
        return new double[] {
                1.0, 2.0, 3.0, 4.0, 5.0
        };
    }

    private static double[] sequentialOracle(
            SparseMatrixCSR matrix,
            double[] input) {

        return matrix.multiply(input);
    }

    private static SpmvPlan createPlan(
            SparseMatrixCSR matrix,
            MultiplyTask.SplitPolicy splitPolicy,
            MultiplyTask.ThresholdMode thresholdMode) {

        return SpmvPlan.create(
                matrix.getRowPointers(),
                THRESHOLD,
                PARALLELISM,
                splitPolicy,
                thresholdMode
        );
    }

    @Test
    void plannedExecutionMustMatchSequentialOracleForEveryPolicyAndMode() {
        SparseMatrixCSR matrix = createMatrix();
        double[] input = createInput();

        double[] expected = sequentialOracle(matrix, input);

        for (MultiplyTask.SplitPolicy policy
                : MultiplyTask.SplitPolicy.values()) {

            for (MultiplyTask.ThresholdMode mode
                    : MultiplyTask.ThresholdMode.values()) {

                SpmvPlan plan = createPlan(matrix, policy, mode);
                double[] actual = new double[matrix.getRows()];

                try (ForkJoinPool pool =
                             new ForkJoinPool(PARALLELISM)) {

                    matrix.multiplyParallelInto(
                            input,
                            actual,
                            plan,
                            pool
                    );

                    assertFalse(pool.isShutdown());
                }

                assertArrayEquals(
                        expected,
                        actual,
                        TOLERANCE,
                        "Mismatch for policy=" + policy
                                + ", thresholdMode=" + mode
                );
            }
        }
    }

    @Test
    void samePlanAndPoolMustBeReusableAcrossRepeatedExecutions() {
        SparseMatrixCSR matrix = createMatrix();
        double[] input = createInput();

        double[] expected = sequentialOracle(matrix, input);

        SpmvPlan plan = createPlan(
                matrix,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        try (ForkJoinPool pool = new ForkJoinPool(PARALLELISM)) {

            for (int iteration = 0; iteration < 20; iteration++) {
                double[] actual = new double[matrix.getRows()];

                matrix.multiplyParallelInto(
                        input,
                        actual,
                        plan,
                        pool
                );

                assertArrayEquals(
                        expected,
                        actual,
                        TOLERANCE,
                        "Execution mismatch at iteration " + iteration
                );

                assertFalse(
                        pool.isShutdown(),
                        "The matrix operation must not shut down the caller-owned pool"
                );
            }
        }
    }

    @Test
    void plannedExecutionMustSupportInputOutputAliasing() {
        SparseMatrixCSR matrix = createMatrix();

        double[] original = createInput();
        double[] expected = sequentialOracle(matrix, original);

        /*
         * This matrix is square, so the same array can be used as input
         * and output. The implementation must snapshot the input before
         * writing the output rows.
         */
        double[] inPlace = original.clone();

        SpmvPlan plan = createPlan(
                matrix,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        try (ForkJoinPool pool = new ForkJoinPool(PARALLELISM)) {
            matrix.multiplyParallelInto(
                    inPlace,
                    inPlace,
                    plan,
                    pool
            );

            assertFalse(pool.isShutdown());
        }

        assertArrayEquals(
                expected,
                inPlace,
                TOLERANCE
        );
    }

    @Test
    void plannedExecutionMustRejectDifferentCsrStructure() {
        SparseMatrixCSR first = new SparseMatrixCSR(
                new double[] {1.0, 2.0, 3.0, 4.0},
                new int[] {0, 1, 0, 1},
                new int[] {0, 1, 2, 3, 4},
                4,
                2
        );

        /*
         * Same dimensions and NNZ, but different row-pointer structure.
         */
        SparseMatrixCSR second = new SparseMatrixCSR(
                new double[] {1.0, 2.0, 3.0, 4.0},
                new int[] {0, 1, 0, 1},
                new int[] {0, 2, 2, 3, 4},
                4,
                2
        );

        SpmvPlan plan = SpmvPlan.create(
                first.getRowPointers(),
                1,
                2
        );

        assertFalse(
                plan.isCompatibleWith(second.getRowPointers())
        );

        try (ForkJoinPool pool = new ForkJoinPool(2)) {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> second.multiplyParallelInto(
                            new double[] {2.0, 3.0},
                            new double[4],
                            plan,
                            pool
                    )
            );

            assertFalse(pool.isShutdown());
        }
    }

    @Test
    void plannedExecutionMustRejectShutdownPool() {
        SparseMatrixCSR matrix = createMatrix();

        SpmvPlan plan = createPlan(
                matrix,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        ForkJoinPool pool = new ForkJoinPool(PARALLELISM);
        pool.shutdown();

        assertThrows(
                IllegalStateException.class,
                () -> matrix.multiplyParallelInto(
                        createInput(),
                        new double[matrix.getRows()],
                        plan,
                        pool
                )
        );
    }

    @Test
    void emptyNnzMatrixMustExecuteThroughAnEmptyNnzPlan() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0],
                new int[0],
                new int[] {0, 0, 0, 0, 0},
                4,
                3
        );

        SpmvPlan plan = SpmvPlan.create(
                matrix.getRowPointers(),
                1,
                PARALLELISM,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        double[] input = {1.0, 2.0, 3.0};
        double[] output = {-1.0, -1.0, -1.0, -1.0};

        try (ForkJoinPool pool = new ForkJoinPool(PARALLELISM)) {
            matrix.multiplyParallelInto(
                    input,
                    output,
                    plan,
                    pool
            );

            assertFalse(pool.isShutdown());
        }

        assertArrayEquals(
                new double[] {0.0, 0.0, 0.0, 0.0},
                output,
                TOLERANCE
        );
    }

    @Test
    void planExecutionMustCoverRowsWithEmptyIntervalsOfNnz() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {2.0, 3.0},
                new int[] {0, 2},
                new int[] {0, 1, 1, 1, 2, 2},
                5,
                3
        );

        double[] input = {5.0, 7.0, 11.0};
        double[] expected = matrix.multiply(input);

        SpmvPlan plan = SpmvPlan.create(
                matrix.getRowPointers(),
                1,
                4,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD
        );

        double[] actual = new double[matrix.getRows()];

        try (ForkJoinPool pool = new ForkJoinPool(PARALLELISM)) {
            matrix.multiplyParallelInto(
                    input,
                    actual,
                    plan,
                    pool
            );
        }

        assertArrayEquals(
                expected,
                actual,
                TOLERANCE
        );
    }
}
