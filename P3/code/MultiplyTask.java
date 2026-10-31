package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * Fork/Join implementation of CSR sparse matrix-vector multiplication.
 *
 * Each task owns a contiguous interval of rows. Rows are indivisible,
 * preserving the exact accumulation order of the sequential CSR kernel.
 *
 * Split policies:
 * - ROW_BOUNDARY_SCAN: scans internal row boundaries for an NNZ-balanced
 *   split. This policy has O(number of rows in the interval) split cost.
 * - BINARY_NNZ_SPLIT: binary-searches the cumulative NNZ midpoint.
 *
 * Threshold modes:
 * - ROW_THRESHOLD: stop when the interval contains at most threshold rows.
 * - NNZ_THRESHOLD: stop when the interval contains at most threshold NNZ.
 *
 * The public constructors defensively copy caller-provided arrays.
 * The package-private factory is reserved for validated matrix-owned CSR
 * arrays and avoids copying immutable matrix storage on every multiplication.
 */
public final class MultiplyTask extends RecursiveAction {

    private static final long serialVersionUID = 1L;

    public enum SplitPolicy {
        ROW_BOUNDARY_SCAN,
        BINARY_NNZ_SPLIT
    }

    public enum ThresholdMode {
        ROW_THRESHOLD,
        NNZ_THRESHOLD
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
    private final ThresholdMode thresholdMode;

    /** Backward-compatible constructor: binary split and row threshold. */
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
                SplitPolicy.BINARY_NNZ_SPLIT,
                ThresholdMode.ROW_THRESHOLD);
    }

    /** Backward-compatible constructor retaining row-threshold semantics. */
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

        this(
                values,
                columns,
                rowPointers,
                input,
                output,
                startRow,
                endRow,
                threshold,
                splitPolicy,
                ThresholdMode.ROW_THRESHOLD);
    }

    /** Public constructor with explicit splitting and threshold semantics. */
    public MultiplyTask(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold,
            SplitPolicy splitPolicy,
            ThresholdMode thresholdMode) {

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columns, "columns must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(input, "input must not be null");
        Objects.requireNonNull(output, "output must not be null");
        Objects.requireNonNull(splitPolicy, "splitPolicy must not be null");
        Objects.requireNonNull(thresholdMode, "thresholdMode must not be null");

        validateCsr(values, columns, rowPointers, input.length);

        int rows = rowPointers.length - 1;
        validateOutputLength(output, rows);
        validateRange(startRow, endRow, rows);
        validateThreshold(threshold);

        this.values = values.clone();
        this.columns = columns.clone();
        this.rowPointers = rowPointers.clone();
        this.input = input == output ? input.clone() : input.clone();
        this.output = output;

        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
        this.splitPolicy = splitPolicy;
        this.thresholdMode = thresholdMode;
    }

    /** Backward-compatible factory for validated matrix-owned CSR arrays. */
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
                SplitPolicy.BINARY_NNZ_SPLIT,
                ThresholdMode.ROW_THRESHOLD);
    }

    /** Factory retaining historical row-threshold semantics. */
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

        return forValidatedCsr(
                values,
                columns,
                rowPointers,
                input,
                output,
                startRow,
                endRow,
                threshold,
                splitPolicy,
                ThresholdMode.ROW_THRESHOLD);
    }

    /**
     * Factory for validated matrix-owned CSR arrays.
     *
     * CSR arrays are reused without cloning. Input is reused unless it aliases
     * output. The caller must not mutate input or CSR storage during execution.
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
            SplitPolicy splitPolicy,
            ThresholdMode thresholdMode) {

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columns, "columns must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(input, "input must not be null");
        Objects.requireNonNull(output, "output must not be null");
        Objects.requireNonNull(splitPolicy, "splitPolicy must not be null");
        Objects.requireNonNull(thresholdMode, "thresholdMode must not be null");

        validateTrustedCsrStructure(values, columns, rowPointers);

        int rows = rowPointers.length - 1;

        validateOutputLength(output, rows);
        validateRange(startRow, endRow, rows);
        validateThreshold(threshold);

        /*
         * The matrix constructor has already validated column bounds against
         * the matrix column count. Here input length is checked explicitly
         * because this factory is also used by package-level execution paths.
         */
        for (int index = 0; index < columns.length; index++) {
            if (columns[index] < 0 || columns[index] >= input.length) {
                throw new IllegalArgumentException(
                        "column index outside input vector bounds");
            }
        }

        double[] safeInput = input == output ? input.clone() : input;

        return new MultiplyTask(
                values,
                columns,
                rowPointers,
                safeInput,
                output,
                startRow,
                endRow,
                threshold,
                splitPolicy,
                thresholdMode,
                TrustedData.INSTANCE);
    }

    /** Internal constructor for trusted arrays and recursive child tasks. */
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
            ThresholdMode thresholdMode,
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
        this.thresholdMode = thresholdMode;
    }

    private enum TrustedData {
        INSTANCE
    }

    private static void validateCsr(
            double[] values,
            int[] columns,
            int[] rowPointers,
            int inputLength) {

        validateTrustedCsrStructure(values, columns, rowPointers);

        for (int index = 0; index < values.length; index++) {
            if (!Double.isFinite(values[index])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite");
            }

            if (columns[index] < 0 || columns[index] >= inputLength) {
                throw new IllegalArgumentException(
                        "column index outside input vector bounds");
            }
        }
    }

    private static void validateTrustedCsrStructure(
            double[] values,
            int[] columns,
            int[] rowPointers) {

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

        int previous = 0;
        int nnz = values.length;

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

    private boolean isBelowThreshold() {
        if (thresholdMode == ThresholdMode.ROW_THRESHOLD) {
            return endRow - startRow <= threshold;
        }

        long intervalNnz =
                (long) rowPointers[endRow] - rowPointers[startRow];

        return intervalNnz <= (long) threshold;
    }

    @Override
    protected void compute() {
        int rowCount = endRow - startRow;

        if (rowCount == 0) {
            return;
        }

        if (isBelowThreshold()) {
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
         * A CSR row is indivisible. If NNZ balancing cannot find a useful
         * boundary, use a row-count midpoint to guarantee progress.
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
                thresholdMode,
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
                thresholdMode,
                TrustedData.INSTANCE);

        /*
         * Fork one branch and compute the other locally. This reduces
         * scheduling overhead versus invokeAll(left, right), which submits
         * both children at every internal node.
         */
        left.fork();

        try {
            right.compute();
        } finally {
            left.join();
        }
    }

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

        return bestSplit < 0
                ? rangeStart + rowCount / 2
                : bestSplit;
    }

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

        int low = rangeStart + 1;
        int high = rangeEnd;

        /*
         * Find the first row boundary whose left side contains at least
         * half of the interval NNZ.
         */
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

        long leftImbalance =
                Math.abs(totalNnz - 2L * leftNnzAtLeft);

        long rightImbalance =
                Math.abs(totalNnz - 2L * leftNnzAtRight);

        return leftImbalance <= rightImbalance
                ? leftCandidate
                : rightCandidate;
    }

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

    public SplitPolicy getSplitPolicy() {
        return splitPolicy;
    }

    public ThresholdMode getThresholdMode() {
        return thresholdMode;
    }
}
