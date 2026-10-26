package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * Fork/Join implementation of CSR sparse matrix-vector multiplication.
 *
 * Rows are indivisible: every task owns a contiguous row interval.
 *
 * Two NNZ partition strategies are supported:
 *  - ROW_BOUNDARY_SCAN: scans every internal row boundary.
 *  - BINARY_NNZ_SPLIT: uses binary search over monotonic CSR row pointers.
 *
 * The default strategy is BINARY_NNZ_SPLIT. ROW_BOUNDARY_SCAN remains
 * available as an explicit baseline for A/B benchmarking.
 */
public final class MultiplyTask extends RecursiveAction {

    private static final long serialVersionUID = 1L;

    /**
     * Strategy used to select the row boundary between two child tasks.
     */
    public enum SplitPolicy {
        /**
         * Baseline strategy: inspect all internal row boundaries.
         */
        ROW_BOUNDARY_SCAN,

        /**
         * Binary-search strategy for the NNZ midpoint.
         */
        BINARY_NNZ_SPLIT
    }

    private final double[] values;
    private final int[] columns;
    private final int[] rowPointers;
    private final double[] input;
    private final double[] output;

    private final int startRow;
    private final int endRow;
    private final int threshold;
    private final SplitPolicy splitPolicy;

    /**
     * Backward-compatible public constructor.
     *
     * The default partition strategy is BINARY_NNZ_SPLIT.
     * Caller-owned arrays are defensively copied.
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

        this(
                values,
                columns,
                rowPointers,
                input,
                output,
                startRow,
                endRow,
                threshold,
                SplitPolicy.BINARY_NNZ_SPLIT);
    }

    /**
     * Public constructor with an explicit split policy.
     *
     * Caller-owned arrays are defensively copied.
     */
    public MultiplyTask(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold,
            SplitPolicy splitPolicy) {

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columns, "columns must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(input, "input must not be null");
        Objects.requireNonNull(output, "output must not be null");
        Objects.requireNonNull(splitPolicy, "splitPolicy must not be null");

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
        this.splitPolicy = splitPolicy;
    }

    /**
     * Backward-compatible factory for SparseMatrixCSR.
     *
     * CSR arrays are already validated and privately owned by the matrix.
     * The input vector is reused unless it aliases output.
     *
     * The default partition strategy is BINARY_NNZ_SPLIT.
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

        return forValidatedCsr(
                values,
                columns,
                rowPointers,
                input,
                output,
                startRow,
                endRow,
                threshold,
                SplitPolicy.BINARY_NNZ_SPLIT);
    }

    /**
     * Factory for SparseMatrixCSR with an explicit partition strategy.
     *
     * Matrix-owned CSR arrays are reused without cloning.
     * The input vector is reused when it does not alias output; when
     * input == output, it is snapshotted to preserve in-place semantics.
     *
     * Callers must not mutate a non-aliased input vector concurrently
     * with the invocation.
     */
    static MultiplyTask forValidatedCsr(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold,
            SplitPolicy splitPolicy) {

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columns, "columns must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(input, "input must not be null");
        Objects.requireNonNull(output, "output must not be null");
        Objects.requireNonNull(splitPolicy, "splitPolicy must not be null");

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
         * ownership of its CSR arrays. The input vector is copied only when
         * it aliases output.
         */
        return new MultiplyTask(
                values,
                columns,
                rowPointers,
                input == output ? input.clone() : input,
                output,
                startRow,
                endRow,
                threshold,
                splitPolicy,
                TrustedData.INSTANCE);
    }

    /**
     * Internal constructor for trusted matrix-owned arrays and recursive
     * child tasks.
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
            SplitPolicy splitPolicy,
            TrustedData trustedData) {

        this.values = values;
        this.columns = columns;
        this.rowPointers = rowPointers;
        this.input = input;
        this.output = output;

        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
        this.splitPolicy = splitPolicy;
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

        int middle;

        switch (splitPolicy) {
            case ROW_BOUNDARY_SCAN:
                middle = findNnzBalancedSplitByScan(
                        startRow,
                        endRow);
                break;

            case BINARY_NNZ_SPLIT:
                middle = findNnzBalancedSplitByBinarySearch(
                        startRow,
                        endRow);
                break;

            default:
                throw new IllegalStateException(
                        "Unsupported split policy: " + splitPolicy);
        }

        /*
         * Defensive fallback. Every recursive split must make strict
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
                splitPolicy,
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
                splitPolicy,
                TrustedData.INSTANCE);

        invokeAll(left, right);
    }

    /**
     * Baseline NNZ partitioning strategy.
     *
     * Inspects every internal row boundary and selects the boundary with
     * the smallest absolute difference between left and right NNZ counts.
     *
     * In case of equal imbalance, the first (lowest) row boundary wins.
     *
     * Complexity: O(number of rows in the task interval).
     */
    private int findNnzBalancedSplitByScan(
            int rangeStart,
            int rangeEnd) {

        int rowCount = rangeEnd - rangeStart;

        if (rowCount <= 1) {
            return rangeStart;
        }

        long basePointer = rowPointers[rangeStart];
        long totalNnz =
                (long) rowPointers[rangeEnd] - basePointer;

        if (totalNnz <= 0L) {
            return rangeStart + rowCount / 2;
        }

        int bestSplit = -1;
        long bestImbalance = Long.MAX_VALUE;

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
     * Binary-search NNZ partitioning strategy.
     *
     * CSR row pointers are monotonically non-decreasing. Therefore, the
     * internal boundary whose left NNZ count is closest to half of the
     * interval's total NNZ can be located with lower-bound binary search.
     *
     * The search is restricted to internal row boundaries:
     *     rangeStart + 1 <= boundary < rangeEnd
     *
     * Repeated row pointers are valid and represent empty rows. The
     * lower-bound search handles them deterministically.
     *
     * If two candidates have equal imbalance, the lower row boundary wins.
     *
     * If the interval contains no nonzeros, a row-count midpoint is used.
     *
     * Complexity: O(log(number of rows in the task interval)).
     */
    private int findNnzBalancedSplitByBinarySearch(
            int rangeStart,
            int rangeEnd) {

        int rowCount = rangeEnd - rangeStart;

        if (rowCount <= 1) {
            return rangeStart;
        }

        long basePointer = rowPointers[rangeStart];
        long totalNnz =
                (long) rowPointers[rangeEnd] - basePointer;

        if (totalNnz <= 0L) {
            return rangeStart + rowCount / 2;
        }

        /*
         * Find the first internal boundary for which:
         *
         *     2 * leftNnz >= totalNnz
         *
         * Long arithmetic avoids overflow in the comparison.
         */
        int low = rangeStart + 1;
        int high = rangeEnd;

        while (low < high) {
            int middle = low + (high - low) / 2;

            long leftNnz =
                    (long) rowPointers[middle] - basePointer;

            if (2L * leftNnz < totalNnz) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }

        /*
         * low is the lower-bound insertion position. It may equal
         * rangeEnd, which is not an admissible internal split boundary.
         */
        int rightCandidate = low;
        int leftCandidate = low - 1;

        boolean leftValid =
                leftCandidate > rangeStart
                        && leftCandidate < rangeEnd;

        boolean rightValid =
                rightCandidate > rangeStart
                        && rightCandidate < rangeEnd;

        if (!leftValid && !rightValid) {
            return rangeStart + rowCount / 2;
        }

        if (!leftValid) {
            return rightCandidate;
        }

        if (!rightValid) {
            return leftCandidate;
        }

        long leftNnzAtLeft =
                (long) rowPointers[leftCandidate] - basePointer;

        long leftNnzAtRight =
                (long) rowPointers[rightCandidate] - basePointer;

        long leftImbalance = Math.abs(
                totalNnz - 2L * leftNnzAtLeft);

        long rightImbalance = Math.abs(
                totalNnz - 2L * leftNnzAtRight);

        /*
         * Deterministic tie-break: choose the lower row boundary.
         */
        if (leftImbalance <= rightImbalance) {
            return leftCandidate;
        }

        return rightCandidate;
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

    /**
     * Returns the partition strategy used by this task.
     */
    public SplitPolicy getSplitPolicy() {
        return splitPolicy;
    }
}
