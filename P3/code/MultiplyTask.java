package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * Fork/Join implementation of CSR sparse matrix-vector multiplication.
 *
 * Computes y = A*x by partitioning the matrix into disjoint row ranges.
 * Every task writes only to its own output interval.
 *
 * The public constructor validates and defensively copies all input arrays.
 * The package-private factory is reserved for SparseMatrixCSR, whose CSR
 * arrays have already been validated, normalized and made immutable through
 * private ownership. It still snapshots the input vector once per operation.
 *
 * Recursive child tasks share the validated snapshots of their parent.
 */
public final class MultiplyTask extends RecursiveAction {

    private static final long serialVersionUID = 1L;

    private final double[] values;
    private final int[] columns;
    private final int[] rowPointers;
    private final double[] input;
    private final double[] output;

    private final int startRow;
    private final int endRow;
    private final int threshold;

    /**
     * Creates a task from caller-owned CSR arrays.
     *
     * All input arrays are validated and defensively copied. The output
     * vector is intentionally not copied because the task must write into it.
     *
     * @param values CSR nonzero values
     * @param columns CSR column indices
     * @param rowPointers CSR row pointers
     * @param input input vector
     * @param output output vector
     * @param startRow first row, inclusive
     * @param endRow last row, exclusive
     * @param threshold maximum number of rows computed by one leaf task
     */
    public MultiplyTask(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold) {

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columns, "columns must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(input, "input must not be null");
        Objects.requireNonNull(output, "output must not be null");

        validateCsr(values, columns, rowPointers, input.length);

        int rows = rowPointers.length - 1;

        validateOutputLength(output, rows);
        validateRange(startRow, endRow, rows);
        validateThreshold(threshold);

        this.values = values.clone();
        this.columns = columns.clone();
        this.rowPointers = rowPointers.clone();
        this.input = input.clone();
        this.output = output;

        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
    }

    /**
     * Creates a task using CSR arrays already validated and privately owned
     * by SparseMatrixCSR.
     *
     * This method must remain package-private. It deliberately avoids
     * revalidating and cloning the matrix's CSR arrays on every multiplication.
     * The input vector is always copied once, preserving snapshot semantics
     * and making x == output safe.
     *
     * @param values validated matrix values owned by SparseMatrixCSR
     * @param columns validated column indices owned by SparseMatrixCSR
     * @param rowPointers validated row pointers owned by SparseMatrixCSR
     * @param input caller input vector; copied by this method
     * @param output caller output vector
     * @param startRow first row, inclusive
     * @param endRow last row, exclusive
     * @param threshold maximum number of rows computed by one leaf task
     * @return a task using the trusted matrix arrays and a private input snapshot
     */
    static MultiplyTask forValidatedCsr(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold) {

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columns, "columns must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(input, "input must not be null");
        Objects.requireNonNull(output, "output must not be null");

        if (values.length != columns.length) {
            throw new IllegalArgumentException(
                    "values and columns must have equal lengths");
        }

        if (rowPointers.length == 0) {
            throw new IllegalArgumentException(
                    "rowPointers must contain at least one element");
        }

        int rows = rowPointers.length - 1;

        validateOutputLength(output, rows);
        validateRange(startRow, endRow, rows);
        validateThreshold(threshold);

        if (rowPointers[0] != 0
                || rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "trusted CSR arrays have inconsistent boundary pointers");
        }

        /*
         * SparseMatrixCSR owns the CSR arrays and never exposes their
         * references. Its constructor validates their full structure.
         * The vector is copied here exactly once for this operation.
         */
        return new MultiplyTask(
                values,
                columns,
                rowPointers,
                input.clone(),
                output,
                startRow,
                endRow,
                threshold,
                TrustedData.INSTANCE);
    }

    /**
     * Private constructor for trusted, immutable CSR arrays and an already
     * snapshotted input vector. Recursive tasks use this constructor too.
     */
    private MultiplyTask(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold,
            TrustedData trustedData) {

        this.values = values;
        this.columns = columns;
        this.rowPointers = rowPointers;
        this.input = input;
        this.output = output;
        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
    }

    /**
     * Marker used to distinguish the private trusted-data constructor.
     */
    private enum TrustedData {
        INSTANCE
    }

    private static void validateCsr(
            double[] values,
            int[] columns,
            int[] rowPointers,
            int inputLength) {

        if (values.length != columns.length) {
            throw new IllegalArgumentException(
                    "values and columns must have equal lengths");
        }

        if (rowPointers.length == 0) {
            throw new IllegalArgumentException(
                    "rowPointers must contain at least one element");
        }

        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "the first row pointer must be zero");
        }

        int nnz = values.length;
        int previous = 0;

        for (int row = 1; row < rowPointers.length; row++) {
            int current = rowPointers[row];

            if (current < previous) {
                throw new IllegalArgumentException(
                        "row pointers must be monotonically non-decreasing");
            }

            if (current < 0 || current > nnz) {
                throw new IllegalArgumentException(
                        "row pointer outside the nonzero array");
            }

            previous = current;
        }

        if (rowPointers[rowPointers.length - 1] != nnz) {
            throw new IllegalArgumentException(
                    "the final row pointer must equal nnz");
        }

        for (int i = 0; i < nnz; i++) {
            if (!Double.isFinite(values[i])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite");
            }

            if (columns[i] < 0 || columns[i] >= inputLength) {
                throw new IllegalArgumentException(
                        "column index outside input vector bounds");
            }
        }
    }

    private static void validateOutputLength(
            double[] output,
            int rows) {

        if (output.length != rows) {
            throw new IllegalArgumentException(
                    "output length must equal the matrix row count");
        }
    }

    private static void validateRange(
            int startRow,
            int endRow,
            int rows) {

        if (startRow < 0) {
            throw new IllegalArgumentException(
                    "startRow must not be negative");
        }

        if (endRow < startRow) {
            throw new IllegalArgumentException(
                    "endRow must not be smaller than startRow");
        }

        if (endRow > rows) {
            throw new IllegalArgumentException(
                    "endRow exceeds the matrix row count");
        }
    }

    private static void validateThreshold(int threshold) {
        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be greater than zero");
        }
    }

    @Override
    protected void compute() {
        int rowCount = endRow - startRow;

        if (rowCount == 0) {
            return;
        }

        if (rowCount <= threshold) {
            computeSequentially();
            return;
        }

        int middle = startRow + rowCount / 2;

        MultiplyTask left = new MultiplyTask(
                values,
                columns,
                rowPointers,
                input,
                output,
                startRow,
                middle,
                threshold,
                TrustedData.INSTANCE);

        MultiplyTask right = new MultiplyTask(
                values,
                columns,
                rowPointers,
                input,
                output,
                middle,
                endRow,
                threshold,
                TrustedData.INSTANCE);

        invokeAll(left, right);
    }

    /**
     * Computes the assigned rows in ascending row order.
     * Each row is written exactly once.
     */
    private void computeSequentially() {
        for (int row = startRow; row < endRow; row++) {
            double sum = 0.0;

            int begin = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = begin; index < end; index++) {
                sum += values[index] * input[columns[index]];
            }

            output[row] = sum;
        }
    }

    public int getStartRow() {
        return startRow;
    }

    public int getEndRow() {
        return endRow;
    }

    public int getThreshold() {
        return threshold;
    }
}
