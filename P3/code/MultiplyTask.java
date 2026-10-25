package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * Fork/Join implementation of CSR sparse matrix-vector multiplication.
 *
 * Tasks partition the matrix by row boundaries selected to balance NNZ
 * work as closely as possible. A row is never split between tasks.
 *
 * The public constructor validates and defensively copies caller-owned
 * arrays. The package-private factory is reserved for SparseMatrixCSR,
 * which owns validated immutable CSR arrays.
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
     * The matrix arrays are not copied. The input vector is snapshotted once.
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
         * SparseMatrixCSR guarantees full structural validation and private
         * ownership of these arrays. Only the vector needs a per-call copy.
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

        int middle = findNnzBalancedSplit(startRow, endRow);

        /*
         * Defensive fallback: every recursive split must make strict
         * progress and create two non-empty row ranges.
         */
        if (middle <= startRow || middle >= endRow) {
            middle = startRow + rowCount / 2;
        }

        if (middle <= startRow || middle >= endRow) {
            computeSequentially();
            return;
        }

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
     * Finds an internal row boundary that minimizes the difference between
     * the NNZ counts assigned to the left and right task.
     *
     * Rows are indivisible. If the range contains no nonzeros, the method
     * falls back to a row-count midpoint.
     *
     * Long arithmetic is used for totals and imbalance calculations.
     */
    private int findNnzBalancedSplit(
            int rangeStart,
            int rangeEnd) {

        int rowCount = rangeEnd - rangeStart;

        if (rowCount <= 1) {
            return rangeStart;
        }

        long totalNnz =
                (long) rowPointers[rangeEnd]
                        - (long) rowPointers[rangeStart];

        if (totalNnz <= 0L) {
            return rangeStart + rowCount / 2;
        }

        int bestSplit = -1;
        long bestImbalance = Long.MAX_VALUE;

        long basePointer = rowPointers[rangeStart];

        for (int candidate = rangeStart + 1;
             candidate < rangeEnd;
             candidate++) {

            long leftNnz =
                    (long) rowPointers[candidate] - basePointer;

            long rightNnz = totalNnz - leftNnz;

            long imbalance = Math.abs(leftNnz - rightNnz);

            if (imbalance < bestImbalance) {
                bestImbalance = imbalance;
                bestSplit = candidate;
            }
        }

        if (bestSplit < 0) {
            return rangeStart + rowCount / 2;
        }

        return bestSplit;
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
