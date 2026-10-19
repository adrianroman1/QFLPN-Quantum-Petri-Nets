package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

/**
 * Independent CSR-versus-dense oracle.
 *
 * Reference:
 * P3 manuscript, Section 13, equations (14)-(19).
 *
 * The dense oracle is constructed independently from the
 * CSR arrays. It does not call SparseMatrixCSR.get(),
 * SparseMatrixCSR.multiply(), or reuse CSR storage.
 */
class CSRvsDenseOracleTest {

    private static final double EPSILON = 1.0e-12;

    /*
     * Manuscript equation (14):
     *
     * A = [ 4  0  0  2 ]
     *     [ 0  3  0  0 ]
     *     [ 1  0  5  0 ]
     *     [ 0  0  2  6 ]
     *
     * Manuscript equations (15)-(17):
     *
     * values  = (4, 2, 3, 1, 5, 2, 6)
     * col_idx = (0, 3, 1, 0, 2, 2, 3)
     * row_ptr = (0, 2, 3, 5, 7)
     *
     * The manuscript defines x symbolically.
     * This test explicitly selects x = (1, 2, 3, 4)^T.
     *
     * Expected result:
     *
     * y = A*x = (12, 6, 16, 30)^T
     *
     * Equations (18)-(19) are satisfied:
     *
     * y0 = 4*1 + 2*4 = 12
     * y2 = 1*1 + 5*3 = 16
     */

    private static double[][] denseMatrix() {

        return new double[][] {
                {4.0, 0.0, 0.0, 2.0},
                {0.0, 3.0, 0.0, 0.0},
                {1.0, 0.0, 5.0, 0.0},
                {0.0, 0.0, 2.0, 6.0}
        };
    }

    private static double[] inputVector() {

        return new double[] {
                1.0, 2.0, 3.0, 4.0
        };
    }

    private static double[] expectedVector() {

        return new double[] {
                12.0, 6.0, 16.0, 30.0
        };
    }

    private static SparseMatrixCSR createManuscriptMatrix() {

        double[] values = {
                4.0, 2.0, 3.0, 1.0, 5.0, 2.0, 6.0
        };

        int[] columnIndices = {
                0, 3, 1, 0, 2, 2, 3
        };

        int[] rowPointers = {
                0, 2, 3, 5, 7
        };

        return new SparseMatrixCSR(
                values,
                columnIndices,
                rowPointers,
                4,
                4);
    }

    /**
     * Independent dense matrix-vector multiplication.
     *
     * This implementation uses only the dense matrix
     * and input vector. It does not depend on CSR code.
     */
    private static double[] denseMultiply(
            double[][] matrix,
            double[] vector) {

        if (matrix == null || vector == null) {
            throw new IllegalArgumentException(
                    "Matrix and vector must not be null.");
        }

        if (matrix.length != vector.length) {
            throw new IllegalArgumentException(
                    "Matrix and vector dimensions do not match.");
        }

        double[] result = new double[matrix.length];

        for (int row = 0; row < matrix.length; row++) {

            if (matrix[row] == null
                    || matrix[row].length != vector.length) {

                throw new IllegalArgumentException(
                        "Dense matrix must be square.");
            }

            double sum = 0.0;

            for (int column = 0;
                 column < vector.length;
                 column++) {

                sum += matrix[row][column] * vector[column];
            }

            result[row] = sum;
        }

        return result;
    }

    @Test
    void manuscriptSection13CsrEncodingMustMatchDenseOracle() {

        double[][] dense = denseMatrix();

        double[] x = inputVector();

        double[] expected = expectedVector();

        SparseMatrixCSR csr = createManuscriptMatrix();

        /*
         * Verify that the CSR arrays reproduce exactly
         * the manuscript equations (15)-(17).
         */
        assertArrayEquals(
                new double[] {
                        4.0, 2.0, 3.0, 1.0, 5.0, 2.0, 6.0
                },
                csr.getValues(),
                0.0);

        assertArrayEquals(
                new int[] {
                        0, 3, 1, 0, 2, 2, 3
                },
                csr.getColumnIndices());

        assertArrayEquals(
                new int[] {
                        0, 2, 3, 5, 7
                },
                csr.getRowPointers());

        assertEquals(4, csr.getRows());
        assertEquals(4, csr.getColumns());
        assertEquals(7, csr.getNonZeroCount());

        /*
         * Independent dense oracle.
         */
        double[] denseResult =
                denseMultiply(dense, x);

        /*
         * Check the independently calculated expected vector.
         */
        assertArrayEquals(
                expected,
                denseResult,
                0.0);

        /*
         * Compare CSR sequential multiplication
         * against the independent dense result.
         */
        double[] csrSequential =
                csr.multiply(x);

        assertArrayEquals(
                denseResult,
                csrSequential,
                EPSILON);

        /*
         * Compare CSR parallel multiplication
         * against the same independent dense result.
         */
        double[] csrParallel =
                csr.multiplyParallel(
                        x,
                        1,
                        2);

        assertArrayEquals(
                denseResult,
                csrParallel,
                EPSILON);
    }
}
