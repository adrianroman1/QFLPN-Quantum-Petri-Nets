package hpc.csr;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.ForkJoinTask;
import java.util.concurrent.RecursiveAction;

/**
 * Immutable Compressed Sparse Row matrix.
 *
 * Duplicate column indices are aggregated additively during construction.
 * The normalized representation has strictly increasing column indices
 * within each row.
 *
 * Parallel execution supports:
 * - legacy threshold-based recursive splitting;
 * - reusable SpmvPlan instances;
 * - caller-owned ForkJoinPool instances.
 *
 * The plan-based API never creates or shuts down a ForkJoinPool.
 */
public final class SparseMatrixCSR {

    private static final int DEFAULT_PARALLEL_THRESHOLD = 4096;

    private static final MultiplyTask.SplitPolicy DEFAULT_SPLIT_POLICY =
            MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT;

    private final int rows;
    private final int columns;
    private final double[] values;
    private final int[] columnIndices;
    private final int[] rowPointers;

    public SparseMatrixCSR(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        validateDimensions(rows, columns);

        Objects.requireNonNull(values, "values cannot be null");
        Objects.requireNonNull(columnIndices, "columnIndices cannot be null");
        Objects.requireNonNull(rowPointers, "rowPointers cannot be null");

        NormalizedCSR normalized = normalizeAndValidate(
                values,
                columnIndices,
                rowPointers,
                rows,
                columns);

        this.values = normalized.values();
        this.columnIndices = normalized.columns();
        this.rowPointers = normalized.rowPointers();
        this.rows = rows;
        this.columns = columns;
    }

    private record NormalizedCSR(
            int[] columns,
            double[] values,
            int[] rowPointers) {
    }

    private static void validateDimensions(int rows, int columns) {
        if (rows < 0) {
            throw new IllegalArgumentException(
                    "Number of rows cannot be negative.");
        }

        if (columns < 0) {
            throw new IllegalArgumentException(
                    "Number of columns cannot be negative.");
        }

        if (rows == Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "Number of rows is too large for a CSR row-pointer array.");
        }
    }

    /**
     * Validates and normalizes CSR input.
     *
     * Each row is sorted by primitive long keys. The upper 32 bits contain
     * the column index and the lower 32 bits contain the original absolute
     * input position. Equal columns therefore retain deterministic input
     * order during aggregation.
     *
     * No Integer objects are allocated for sorting.
     */
    private static NormalizedCSR normalizeAndValidate(
            double[] inputValues,
            int[] inputColumns,
            int[] inputRowPointers,
            int rows,
            int columns) {

        if (inputValues.length != inputColumns.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length.");
        }

        if (inputRowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1.");
        }

        if (inputRowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0.");
        }

        int previous = 0;

        for (int i = 0; i < inputRowPointers.length; i++) {
            int current = inputRowPointers[i];

            if (current < 0 || current < previous) {
                throw new IllegalArgumentException(
                        "rowPointers must be non-negative and monotonically non-decreasing.");
            }

            if (current > inputValues.length) {
                throw new IllegalArgumentException(
                        "rowPointers value exceeds NNZ at index " + i + ".");
            }

            previous = current;
        }

        if (inputRowPointers[rows] != inputValues.length) {
            throw new IllegalArgumentException(
                    "The last row pointer must equal NNZ.");
        }

        for (int i = 0; i < inputColumns.length; i++) {
            int column = inputColumns[i];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Column index out of bounds at position "
                                + i + ": " + column);
            }
        }

        for (int i = 0; i < inputValues.length; i++) {
            if (!Double.isFinite(inputValues[i])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite. Invalid value at position "
                                + i + ": " + inputValues[i]);
            }
        }

        int[] normalizedColumns = new int[inputValues.length];
        double[] normalizedValues = new double[inputValues.length];
        int[] normalizedRowPointers = new int[rows + 1];

        int writeIndex = 0;
        normalizedRowPointers[0] = 0;

        for (int row = 0; row < rows; row++) {
            int rowStart = inputRowPointers[row];
            int rowEnd = inputRowPointers[row + 1];
            int count = rowEnd - rowStart;

            if (count == 0) {
                normalizedRowPointers[row + 1] = writeIndex;
                continue;
            }

            long[] order = new long[count];

            for (int i = 0; i < count; i++) {
                int originalIndex = rowStart + i;
                int column = inputColumns[originalIndex];

                order[i] = ((long) column << 32)
                        | (originalIndex & 0xffffffffL);
            }

            Arrays.sort(order);

            int rowWrite = 0;

            for (long key : order) {
                int originalIndex = (int) key;
                int currentColumn = inputColumns[originalIndex];
                double currentValue = inputValues[originalIndex];

                if (rowWrite > 0
                        && normalizedColumns[writeIndex + rowWrite - 1]
                        == currentColumn) {

                    int duplicatePosition =
                            writeIndex + rowWrite - 1;

                    double aggregated =
                            normalizedValues[duplicatePosition]
                                    + currentValue;

                    if (!Double.isFinite(aggregated)) {
                        throw new IllegalArgumentException(
                                "Duplicate CSR aggregation overflow at row "
                                        + row + ", column " + currentColumn
                                        + ": aggregated value is not finite.");
                    }

                    normalizedValues[duplicatePosition] = aggregated;
                } else {
                    normalizedColumns[writeIndex + rowWrite] =
                            currentColumn;

                    normalizedValues[writeIndex + rowWrite] =
                            currentValue;

                    rowWrite++;
                }
            }

            writeIndex += rowWrite;
            normalizedRowPointers[row + 1] = writeIndex;
        }

        return new NormalizedCSR(
                Arrays.copyOf(normalizedColumns, writeIndex),
                Arrays.copyOf(normalizedValues, writeIndex),
                normalizedRowPointers);
    }

    /**
     * Sequential CSR matrix-vector multiplication.
     */
    public double[] multiply(double[] x) {
        validateInputVector(x);

        double[] y = new double[rows];
        multiplyInto(x, y);

        return y;
    }

    /**
     * Sequential multiplication into a caller-owned output array.
     *
     * In-place multiplication is supported by snapshotting the input.
     */
    public void multiplyInto(double[] x, double[] y) {
        validateInputVector(x);
        validateOutputVector(y);

        double[] input = x == y
                ? Arrays.copyOf(x, x.length)
                : x;

        multiplyRows(input, y, 0, rows);
    }

    private void multiplyRows(
            double[] input,
            double[] output,
            int startRow,
            int endRow) {

        for (int row = startRow; row < endRow; row++) {
            double sum = 0.0;

            for (int index = rowPointers[row];
                 index < rowPointers[row + 1];
                 index++) {

                sum += values[index] * input[columnIndices[index]];
            }

            output[row] = sum;
        }
    }

    /**
     * Legacy convenience API.
     *
     * Creates and shuts down a pool for this call. For repeated execution,
     * prefer the SpmvPlan and caller-owned-pool overloads.
     */
    public double[] multiplyParallel(double[] x) {
        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Math.max(1, Runtime.getRuntime().availableProcessors()),
                DEFAULT_SPLIT_POLICY);
    }

    /**
     * Legacy convenience API.
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism) {

        return multiplyParallel(
                x,
                threshold,
                parallelism,
                DEFAULT_SPLIT_POLICY);
    }

    /**
     * Legacy convenience API with an explicit split policy.
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism,
            MultiplyTask.SplitPolicy splitPolicy) {

        validateInputVector(x);
        validateParallelConfiguration(threshold, parallelism);
        Objects.requireNonNull(splitPolicy, "splitPolicy cannot be null");

        double[] output = new double[rows];

        ForkJoinPool pool = new ForkJoinPool(parallelism);

        try {
            multiplyParallelInto(
                    x,
                    output,
                    threshold,
                    pool,
                    splitPolicy);
        } finally {
            pool.shutdown();
        }

        return output;
    }

    /**
     * Legacy convenience API. Creates and shuts down a pool for this call.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            int parallelism) {

        multiplyParallelInto(
                x,
                y,
                threshold,
                parallelism,
                DEFAULT_SPLIT_POLICY);
    }

    /**
     * Legacy convenience API with an explicit split policy.
     *
     * This overload owns the pool lifecycle. Use the ForkJoinPool overload
     * or the SpmvPlan overload for persistent-pool execution.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            int parallelism,
            MultiplyTask.SplitPolicy splitPolicy) {

        validateInputVector(x);
        validateOutputVector(y);
        validateParallelConfiguration(threshold, parallelism);
        Objects.requireNonNull(splitPolicy, "splitPolicy cannot be null");

        ForkJoinPool pool = new ForkJoinPool(parallelism);

        try {
            multiplyParallelInto(
                    x,
                    y,
                    threshold,
                    pool,
                    splitPolicy);
        } finally {
            pool.shutdown();
        }
    }

    /**
     * Backward-compatible overload using the default split policy.
     *
     * The caller owns the pool. This method never shuts it down.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            ForkJoinPool pool) {

        multiplyParallelInto(
                x,
                y,
                threshold,
                pool,
                DEFAULT_SPLIT_POLICY);
    }

    /**
     * Parallel multiplication using a caller-owned ForkJoinPool.
     *
     * The caller owns the pool lifecycle. This method never creates,
     * shuts down, or otherwise changes ownership of the supplied pool.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            ForkJoinPool pool,
            MultiplyTask.SplitPolicy splitPolicy) {

        validateInputVector(x);
        validateOutputVector(y);
        validateThreshold(threshold);

        Objects.requireNonNull(pool, "ForkJoinPool cannot be null.");
        Objects.requireNonNull(splitPolicy, "splitPolicy cannot be null.");

        ensurePoolActive(pool);

        double[] input = x == y
                ? Arrays.copyOf(x, x.length)
                : x;

        MultiplyTask task = MultiplyTask.forValidatedCsr(
                values,
                columnIndices,
                rowPointers,
                input,
                y,
                0,
                rows,
                threshold,
                splitPolicy);

        pool.invoke(task);
    }

    /**
     * Allocates the output vector and executes using an existing plan
     * and caller-owned pool.
     *
     * The plan must have been created for this matrix's exact row-pointer
     * structure.
     */
    public double[] multiplyParallel(
            double[] x,
            SpmvPlan plan,
            ForkJoinPool pool) {

        validateInputVector(x);

        double[] output = new double[rows];

        multiplyParallelInto(x, output, plan, pool);

        return output;
    }

    /**
     * Executes a precomputed SpMV plan.
     *
     * Each planned row interval is submitted as an independent
     * MultiplyTask. The plan determines the top-level partitioning;
     * MultiplyTask retains its existing recursive splitting behaviour
     * inside each interval.
     *
     * The supplied pool is reused and remains owned by the caller.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            SpmvPlan plan,
            ForkJoinPool pool) {

        validateInputVector(x);
        validateOutputVector(y);

        Objects.requireNonNull(plan, "SpmvPlan cannot be null.");
        Objects.requireNonNull(pool, "ForkJoinPool cannot be null.");

        ensurePoolActive(pool);

        if (!plan.isCompatibleWith(rowPointers)) {
            throw new IllegalArgumentException(
                    "SpmvPlan is not compatible with this matrix's CSR row pointers.");
        }

        int threshold = plan.getThreshold();
        validateThreshold(threshold);

        MultiplyTask.SplitPolicy policy = plan.getSplitPolicy();
        Objects.requireNonNull(
                policy,
                "SpmvPlan split policy cannot be null.");

        double[] input = x == y
                ? Arrays.copyOf(x, x.length)
                : x;

        int partitionCount = plan.getPartitionCount();

        if (partitionCount == 0) {
            if (rows != 0) {
                throw new IllegalArgumentException(
                        "SpmvPlan contains no partitions for a non-empty matrix.");
            }
            return;
        }

        List<MultiplyTask> tasks =
                new ArrayList<>(partitionCount);

        int expectedStart = 0;

        for (int partition = 0;
             partition < partitionCount;
             partition++) {

            int startRow = plan.getStartRow(partition);
            int endRow = plan.getEndRow(partition);

            if (startRow != expectedStart
                    || endRow < startRow
                    || endRow > rows) {
                throw new IllegalArgumentException(
                        "SpmvPlan contains invalid or non-contiguous row intervals.");
            }

            if (startRow == endRow) {
                throw new IllegalArgumentException(
                        "SpmvPlan contains an empty partition.");
            }

            tasks.add(MultiplyTask.forValidatedCsr(
                    values,
                    columnIndices,
                    rowPointers,
                    input,
                    y,
                    startRow,
                    endRow,
                    threshold,
                    policy));

            expectedStart = endRow;
        }

        if (expectedStart != rows) {
            throw new IllegalArgumentException(
                    "SpmvPlan does not cover every matrix row.");
        }

        pool.invoke(new PlannedMultiplyAction(tasks));
    }

    /**
     * Root action for a collection of disjoint planned row intervals.
     */
    private static final class PlannedMultiplyAction
            extends RecursiveAction {

        private static final long serialVersionUID = 1L;

        private final List<MultiplyTask> tasks;

        private PlannedMultiplyAction(List<MultiplyTask> tasks) {
            this.tasks = List.copyOf(tasks);
        }

        @Override
        protected void compute() {
            ForkJoinTask.invokeAll(tasks);
        }
    }

    private static void ensurePoolActive(ForkJoinPool pool) {
        if (pool.isShutdown() || pool.isTerminated()) {
            throw new IllegalStateException(
                    "ForkJoinPool is shut down or terminated.");
        }
    }

    private static void validateParallelConfiguration(
            int threshold,
            int parallelism) {

        validateThreshold(threshold);

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }
    }

    private static void validateThreshold(int threshold) {
        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }
    }

    private void validateInputVector(double[] x) {
        Objects.requireNonNull(
                x,
                "Input vector cannot be null.");

        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Input vector length (" + x.length
                            + ") must equal matrix column count ("
                            + columns + ").");
        }
    }

    private void validateOutputVector(double[] y) {
        Objects.requireNonNull(
                y,
                "Output vector cannot be null.");

        if (y.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length (" + y.length
                            + ") must equal matrix row count ("
                            + rows + ").");
        }
    }

    public int getRows() {
        return rows;
    }

    public int getColumns() {
        return columns;
    }

    public int getNonZeroCount() {
        return values.length;
    }

    public int getNnz() {
        return values.length;
    }

    public double[] getValues() {
        return Arrays.copyOf(values, values.length);
    }

    public int[] getColumnIndices() {
        return Arrays.copyOf(columnIndices, columnIndices.length);
    }

    public int[] getRowPointers() {
        return Arrays.copyOf(rowPointers, rowPointers.length);
    }

    public double getDensity() {
        long totalElements = (long) rows * (long) columns;

        if (totalElements == 0L) {
            return 0.0;
        }

        return (double) values.length / (double) totalElements;
    }

    public double get(int row, int column) {
        if (row < 0 || row >= rows) {
            throw new IndexOutOfBoundsException(
                    "Row index out of bounds: " + row);
        }

        if (column < 0 || column >= columns) {
            throw new IndexOutOfBoundsException(
                    "Column index out of bounds: " + column);
        }

        double sum = 0.0;

        for (int index = rowPointers[row];
             index < rowPointers[row + 1];
             index++) {

            if (columnIndices[index] == column) {
                sum += values[index];
            }
        }

        return sum;
    }

    public boolean isValid() {
        try {
            validateCSRStructure(
                    values,
                    columnIndices,
                    rowPointers,
                    rows,
                    columns);

            return true;
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    private static void validateCSRStructure(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        if (rows < 0 || columns < 0 || rows == Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "Invalid CSR dimensions.");
        }

        if (values.length != columnIndices.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length.");
        }

        if (rowPointers.length != rows + 1 || rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "Invalid CSR row-pointer array.");
        }

        int previous = 0;

        for (int i = 0; i < rowPointers.length; i++) {
            int current = rowPointers[i];

            if (current < previous || current < 0
                    || current > values.length) {
                throw new IllegalArgumentException(
                        "Invalid row pointer at index " + i + ".");
            }

            previous = current;
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "The last row pointer must equal NNZ.");
        }

        for (int i = 0; i < columnIndices.length; i++) {
            if (columnIndices[i] < 0 || columnIndices[i] >= columns) {
                throw new IllegalArgumentException(
                        "Column index out of bounds at position " + i + ".");
            }
        }

        for (int i = 0; i < values.length; i++) {
            if (!Double.isFinite(values[i])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite at position " + i + ".");
            }
        }
    }

    @Override
    public String toString() {
        return "SparseMatrixCSR{"
                + "rows=" + rows
                + ", columns=" + columns
                + ", nonZeroCount=" + values.length
                + ", density=" + getDensity()
                + '}';
    }
}
