package hpc.csr;

import java.lang.reflect.Field;
import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SparseMatrixCSRPolicyAndNormalizationRegressionTest {

    private static final double EPSILON = 1.0e-12;

    @Test
    void defaultMultiplyTaskUsesBinaryNnzSplit() {
        MultiplyTask task = new MultiplyTask(
                new double[] {2.0, 3.0},
                new int[] {0, 1},
                new int[] {0, 2},
                new double[] {4.0, 5.0},
                new double[1],
                0,
                1,
                1);

        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                task.getSplitPolicy());
    }

    @Test
    void sparseMatrixDefaultPolicyIsBinaryNnzSplit() throws Exception {
        Field field =
                SparseMatrixCSR.class.getDeclaredField(
                        "DEFAULT_SPLIT_POLICY");

        field.setAccessible(true);

        MultiplyTask.SplitPolicy policy =
                (MultiplyTask.SplitPolicy) field.get(null);

        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                policy);
    }

    @Test
    void defaultParallelOverloadsProduceCorrectResults() {
        SparseMatrixCSR matrix = createSkewedMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };

        double[] expected = matrix.multiply(input);

        assertArrayEquals(
                expected,
                matrix.multiplyParallel(input),
                EPSILON);

        assertArrayEquals(
                expected,
                matrix.multiplyParallel(input, 1, 4),
                EPSILON);

        double[] output = new double[matrix.getRows()];

        matrix.multiplyParallelInto(
                input,
                output,
                1,
                4);

        assertArrayEquals(expected, output, EPSILON);
    }

    @Test
    void defaultExternalPoolOverloadProducesCorrectResults() {
        SparseMatrixCSR matrix = createSkewedMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };

        double[] expected = matrix.multiply(input);
        double[] output = new double[matrix.getRows()];

        ForkJoinPool pool = new ForkJoinPool(4);

        try {
            matrix.multiplyParallelInto(
                    input,
                    output,
                    1,
                    pool);

            assertArrayEquals(expected, output, EPSILON);

            assertFalse(
                    pool.isShutdown(),
                    "Caller-owned pool must remain active.");
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void explicitRowBoundaryScanRemainsAvailable() {
        SparseMatrixCSR matrix = createSkewedMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };

        double[] expected = matrix.multiply(input);

        double[] actual = matrix.multiplyParallel(
                input,
                1,
                4,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN);

        assertArrayEquals(expected, actual, EPSILON);
    }

    @Test
    void explicitBinaryNnzSplitRemainsAvailable() {
        SparseMatrixCSR matrix = createSkewedMatrix();

        double[] input = {
                1.0, 2.0, 3.0, 4.0,
                5.0, 6.0, 7.0, 8.0
        };

        double[] expected = matrix.multiply(input);

        double[] actual = matrix.multiplyParallel(
                input,
                1,
                4,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT);

        assertArrayEquals(expected, actual, EPSILON);
    }

    @Test
    void primitiveNormalizationSortsColumnsAndPreservesDuplicateOrder() {
        /*
         * Row 0:
         *
         * Original columns: 2, 2, 2, 0
         * Original values:  1e16, -1e16, 1, 2
         *
         * Stable duplicate aggregation:
         * (1e16 + -1e16) + 1 = 1
         *
         * Expected normalized row:
         * columns = [0, 2]
         * values  = [2, 1]
         *
         * Row 1 is empty.
         *
         * Row 2:
         * columns = [1, 1, 0]
         * values  = [4, 5, 6]
         *
         * Expected normalized row:
         * columns = [0, 1]
         * values  = [6, 9]
         */

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0e16,
                        -1.0e16,
                        1.0,
                        2.0,
                        4.0,
                        5.0,
                        6.0
                },
                new int[] {
                        2, 2, 2, 0,
                        1, 1, 0
                },
                new int[] {
                        0, 4, 4, 7
                },
                3,
                3);

        assertArrayEquals(
                new int[] {
                        0, 2,
                        0, 1
                },
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {
                        2.0, 1.0,
                        6.0, 9.0
                },
                matrix.getValues(),
                EPSILON);

        assertArrayEquals(
                new int[] {0, 2, 2, 4},
                matrix.getRowPointers());

        assertEquals(4, matrix.getNnz());
    }

    @Test
    void primitiveNormalizationProducesCorrectMultiplication() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        1.0e16,
                        -1.0e16,
                        1.0,
                        2.0,
                        4.0,
                        5.0,
                        6.0
                },
                new int[] {
                        2, 2, 2, 0,
                        1, 1, 0
                },
                new int[] {
                        0, 4, 4, 7
                },
                3,
                3);

        double[] input = {
                3.0, 5.0, 7.0
        };

        assertArrayEquals(
                new double[] {
                        13.0,
                        0.0,
                        63.0
                },
                matrix.multiply(input),
                EPSILON);

        assertArrayEquals(
                matrix.multiply(input),
                matrix.multiplyParallel(input, 1, 3),
                EPSILON);
    }

    @Test
    void primitiveNormalizationHandlesAlreadySortedRows() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        2.0, 3.0, 4.0,
                        5.0, 6.0
                },
                new int[] {
                        0, 1, 2,
                        0, 2
                },
                new int[] {
                        0, 3, 5
                },
                2,
                3);

        assertArrayEquals(
                new int[] {0, 1, 2, 0, 2},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {2.0, 3.0, 4.0, 5.0, 6.0},
                matrix.getValues(),
                EPSILON);

        assertArrayEquals(
                new int[] {0, 3, 5},
                matrix.getRowPointers());
    }

    @Test
    void primitiveNormalizationHandlesRepeatedColumns() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        2.0, 3.0, 4.0, 5.0, 6.0
                },
                new int[] {
                        1, 1, 0, 1, 0
                },
                new int[] {
                        0, 5
                },
                1,
                2);

        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {10.0, 10.0},
                matrix.getValues(),
                EPSILON);

        assertArrayEquals(
                new int[] {0, 2},
                matrix.getRowPointers());
    }

    @Test
    void duplicateAggregationOverflowIsRejected() {
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
    void emptyRowsRemainCorrectAfterPrimitiveNormalization() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[] {
                        2.0, 3.0,
                        4.0, 5.0
                },
                new int[] {
                        2, 0,
                        1, 0
                },
                new int[] {
                        0, 2, 2, 4, 4
                },
                4,
                3);

        assertArrayEquals(
                new int[] {
                        0, 2,
                        0, 1
                },
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2, 2, 4, 4},
                matrix.getRowPointers());

        assertArrayEquals(
                new double[] {
                        3.0, 2.0,
                        5.0, 4.0
                },
                matrix.getValues(),
                EPSILON);
    }

    @Test
    void normalizedMatrixRemainsImmutable() {
        double[] sourceValues = {
                3.0, 2.0, 4.0
        };

        int[] sourceColumns = {
                2, 0, 1
        };

        int[] sourcePointers = {
                0, 3
        };

        SparseMatrixCSR matrix = new SparseMatrixCSR(
                sourceValues,
                sourceColumns,
                sourcePointers,
                1,
                3);

        sourceValues[0] = 999.0;
        sourceColumns[0] = 0;
        sourcePointers[1] = 0;

        assertArrayEquals(
                new int[] {0, 1, 2},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {2.0, 4.0, 3.0},
                matrix.getValues(),
                EPSILON);

        assertArrayEquals(
                new int[] {0, 3},
                matrix.getRowPointers());

        assertTrue(matrix.isValid());
    }

    private static SparseMatrixCSR createSkewedMatrix() {
        return new SparseMatrixCSR(
                new double[] {
                        1.0, 2.0, 3.0, 4.0,
                        5.0, 6.0, 7.0, 8.0,
                        9.0, 10.0, 11.0
                },
                new int[] {
                        0, 1, 2, 3,
                        4, 5, 6, 7,
                        0, 1, 2
                },
                new int[] {
                        0, 8, 8, 8, 8, 8, 8, 11
                },
                7,
                8);
    }
}
