package hpc.csr;

import java.util.Arrays;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * Immutable Compressed Sparse Row matrix.
 *
 * Duplicate column indices are supported. Their values are
 * interpreted additively by get(), multiply() and multiplyParallel().
 *
 * The default parallel split policy is BINARY_NNZ_SPLIT.
 * ROW_BOUNDARY_SCAN remains available as an explicit baseline.
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

        NormalizedCSR normalized =
                normalizeAndValidate(
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
    }

    /**
     * Validates and normalizes CSR input.
     *
     * Each row is sorted by column index using primitive long keys.
     * The low 32 bits retain the original input position, so equal
     * column indices preserve their original order during aggregation.
     *
     * This avoids allocating one Integer object per nonzero entry.
     */
    private static NormalizedCSR normalizeAndValidate(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        if (values.length != columnIndices.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length.");
        }

        if (rows == Integer.MAX_VALUE || rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1.");
        }

        if (rowPointers.length == 0 || rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0.");
        }

        int previous = 0;

        for (int i = 0; i < rowPointers.length; i++) {
            int current = rowPointers[i];

            if (current < 0 || current < previous) {
                throw new IllegalArgumentException(
                        "rowPointers must be non-negative and monotonically non-decreasing.");
            }

            if (current > values.length) {
                throw new IllegalArgumentException(
                        "rowPointers value exceeds NNZ at index " + i + ".");
            }

            previous = current;
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "The last row pointer must equal NNZ.");
        }

        for (int i = 0; i < columnIndices.length; i++) {
            int column = columnIndices[i];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Column index out of bounds at position "
                                + i + ": " + column);
            }
        }

        for (int i = 0; i < values.length; i++) {
            if (!Double.isFinite(values[i])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite. Invalid value at position "
                                + i + ": " + values[i]);
            }
        }

        int[] compactColumns = new int[values.length];
        double[] compactValues = new double[values.length];
        int[] compactRowPointers = new int[rows + 1];

        compactRowPointers[0] = 0;

        int writeIndex = 0;

        for (int row = 0; row < rows; row++) {
            int rowStart = rowPointers[row];
            int rowEnd = rowPointers[row + 1];
            int count = rowEnd - rowStart;

            if (count == 0) {
                compactRowPointers[row + 1] = writeIndex;
                continue;
            }

            /*
             * Key layout:
             *
             * bits 63..32: column index
             * bits 31..0 : original absolute input index
             *
             * Column indices are non-negative, so signed long sorting
             * preserves ascending column order. The original index
             * provides deterministic ordering for duplicate columns.
             */
            long[] order = new long[count];

            for (int i = 0; i < count; i++) {
                int originalIndex = rowStart + i;
                int column = columnIndices[originalIndex];

                order[i] =
                        ((long) column << 32)
                                | (originalIndex & 0xffffffffL);
            }

            Arrays.sort(order);

            int rowWrite = 0;

            for (int pos = 0; pos < order.length; pos++) {
                int index = (int) order[pos];

                int currentColumn = columnIndices[index];
                double currentValue = values[index];

                if (rowWrite > 0
                        && compactColumns[writeIndex + rowWrite - 1]
                        == currentColumn) {

                    int duplicatePosition =
                            writeIndex + rowWrite - 1;

                    double aggregatedValue =
                            compactValues[duplicatePosition] + currentValue;

                    if (!Double.isFinite(aggregatedValue)) {
                        throw new IllegalArgumentException(
                                "Duplicate CSR aggregation overflow at row "
                                        + row + ", column " + currentColumn
                                        + ": aggregated value is not finite.");
                    }

                    compactValues[duplicatePosition] = aggregatedValue;
                    continue;
                }

                compactColumns[writeIndex + rowWrite] = currentColumn;
                compactValues[writeIndex + rowWrite] = currentValue;
                rowWrite++;
            }

            writeIndex += rowWrite;
            compactRowPointers[row + 1] = writeIndex;
        }

        int finalNnz = compactRowPointers[rows];

        int[] normalizedColumns =
                Arrays.copyOf(compactColumns, finalNnz);

        double[] normalizedValues =
                Arrays.copyOf(compactValues, finalNnz);

        int[] normalizedRowPointers =
                Arrays.copyOf(compactRowPointers, rows + 1);

        return new NormalizedCSR(
                normalizedColumns,
                normalizedValues,
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
     * Sequential CSR matrix-vector multiplication into a caller-owned
     * output array.
     *
     * If x and y are the same array, x is snapshotted before any output
     * element is overwritten.
     */
    public void multiplyInto(double[] x, double[] y) {
        validateInputVector(x);
        validateOutputVector(y);

        double[] input = (x == y)
                ? Arrays.copyOf(x, x.length)
                : x;

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            int begin = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = begin; index < end; index++) {
                sum += values[index] * input[columnIndices[index]];
            }

            y[row] = sum;
        }
    }

    /**
     * Parallel multiplication using the default threshold, available
     * processor count and BINARY_NNZ_SPLIT policy.
     */
    public double[] multiplyParallel(double[] x) {
        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Math.max(1, Runtime.getRuntime().availableProcessors()),
                DEFAULT_SPLIT_POLICY);
    }

    /**
     * Backward-compatible API.
     *
     * The default split policy is BINARY_NNZ_SPLIT.
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
     * Parallel multiplication with an explicitly selected split policy.
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism,
            MultiplyTask.SplitPolicy splitPolicy) {

        validateInputVector(x);
        validateParallelConfiguration(threshold, parallelism);

        Objects.requireNonNull(
                splitPolicy,
                "splitPolicy cannot be null");

        double[] y = new double[rows];

        multiplyParallelInto(
                x,
                y,
                threshold,
                parallelism,
                splitPolicy);

        return y;
    }

    /**
     * Backward-compatible API.
     *
     * The default split policy is BINARY_NNZ_SPLIT.
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
     * Parallel multiplication with an explicitly selected split policy.
     *
     * A new ForkJoinPool is created and shut down by this method.
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

        Objects.requireNonNull(
                splitPolicy,
                "splitPolicy cannot be null");

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
     * Backward-compatible overload using BINARY_NNZ_SPLIT.
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
     * Parallel multiplication using a caller-owned ForkJoinPool and an
     * explicit split policy.
     *
     * The pool is not shut down by this method.
     *
     * MultiplyTask.forValidatedCsr reuses the input vector when it is
     * distinct from the output vector. When x == y, it snapshots the
     * input to preserve in-place multiplication semantics.
     *
     * When x != y, callers must not mutate x concurrently with this call.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            ForkJoinPool pool,
            MultiplyTask.SplitPolicy splitPolicy) {

        validateInputVector(x);
        validateOutputVector(y);

        Objects.requireNonNull(
                pool,
                "ForkJoinPool cannot be null.");

        Objects.requireNonNull(
                splitPolicy,
                "splitPolicy cannot be null.");

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (pool.isShutdown()) {
            throw new IllegalStateException(
                    "ForkJoinPool is already shut down.");
        }

        MultiplyTask task = MultiplyTask.forValidatedCsr(
                values,
                columnIndices,
                rowPointers,
                x,
                y,
                0,
                rows,
                threshold,
                splitPolicy);

        pool.invoke(task);
    }

    private static void validateParallelConfiguration(
            int threshold,
            int parallelism) {

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
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

        if (values.length != columnIndices.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length.");
        }

        if (rows == Integer.MAX_VALUE || rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1.");
        }

        if (rowPointers.length == 0 || rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0.");
        }

        int previous = 0;

        for (int i = 0; i < rowPointers.length; i++) {
            int current = rowPointers[i];

            if (current < 0 || current < previous) {
                throw new IllegalArgumentException(
                        "rowPointers must be non-negative and monotonically non-decreasing.");
            }

            if (current > values.length) {
                throw new IllegalArgumentException(
                        "rowPointers value exceeds NNZ at index " + i + ".");
            }

            previous = current;
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "The last row pointer must equal NNZ.");
        }

        for (int i = 0; i < columnIndices.length; i++) {
            int column = columnIndices[i];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Column index out of bounds at position "
                                + i + ": " + column);
            }
        }

        for (int i = 0; i < values.length; i++) {
            if (!Double.isFinite(values[i])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite. Invalid value at position "
                                + i + ": " + values[i]);
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
