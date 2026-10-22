package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * Fork/Join implementation of CSR sparse matrix-vector multiplication.
 *
 * Computes y = A*x by partitioning the matrix into disjoint row ranges.
 * Every task writes only to its own output interval.
 *
 * Public construction validates and defensively copies the input data.
 * Recursive child tasks share the already validated immutable snapshots.
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
     * Creates a validated multiplication task.
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

        if (output.length != rows) {
            throw new IllegalArgumentException(
                    "output length must equal the matrix row count");
        }

        validateRange(startRow, endRow, rows);

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be greater than zero");
        }

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
     * Private constructor used by recursive children.
     * Arrays are already validated snapshots and are safe to share
     * between child tasks. The output array is intentionally shared.
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
            boolean trusted) {

        this.values = values;
        this.columns = columns;
        this.rowPointers = rowPointers;
        this.input = input;
        this.output = output;
        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
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
                true);

        MultiplyTask right = new MultiplyTask(
                values,
                columns,
                rowPointers,
                input,
                output,
                middle,
                endRow,
                threshold,
                true);

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
