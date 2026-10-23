package hpc.csr;

import java.util.Arrays;
import java.util.Comparator;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * Immutable Compressed Sparse Row matrix.
 *
 * Duplicate column indices are supported. Their values are
 * interpreted additively by get(), multiply() and multiplyParallel().
 */
public final class SparseMatrixCSR {

    private static final int DEFAULT_PARALLEL_THRESHOLD = 4096;

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

        int[] normalizedColumns = normalizeAndValidate(values, columnIndices, rowPointers, rows, columns);

        this.values = Arrays.copyOf(values, values.length);
        this.columnIndices = Arrays.copyOf(normalizedColumns, normalizedColumns.length);
        this.rowPointers = Arrays.copyOf(rowPointers, rowPointers.length);
        this.rows = rows;
        this.columns = columns;
    }

    private static void validateDimensions(int rows, int columns) {
        if (rows < 0) {
            throw new IllegalArgumentException("Number of rows cannot be negative.");
        }
        if (columns < 0) {
            throw new IllegalArgumentException("Number of columns cannot be negative.");
        }
    }

    private static int[] normalizeAndValidate(
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
            throw new IllegalArgumentException("rowPointers[0] must be 0.");
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
                        "Column index out of bounds at position " + i + ": " + column);
            }
        }

        for (int i = 0; i < values.length; i++) {
            if (!Double.isFinite(values[i])) {
                throw new IllegalArgumentException(
                        "CSR values must be finite. Invalid value at position "
                                + i + ": " + values[i]);
            }
        }

        int[] normalizedColumns = Arrays.copyOf(columnIndices, columnIndices.length);
        double[] normalizedValues = Arrays.copyOf(values, values.length);

        int start = 0;
        for (int row = 0; row < rows; row++) {
            int end = rowPointers[row + 1];
            if (end - start <= 1) {
                start = end;
                continue;
            }

            int[] sliceCols = Arrays.copyOfRange(normalizedColumns, start, end);
            double[] sliceVals = Arrays.copyOfRange(normalizedValues, start, end);
            Integer[] sortedOrder = new Integer[sliceCols.length];
            for (int i = 0; i < sortedOrder.length; i++) {
                sortedOrder[i] = i;
            }
            Arrays.sort(sortedOrder, Comparator.comparingInt(index -> sliceCols[index]));

            int write = 0;
            for (int i = 0; i < sortedOrder.length; i++) {
                int index = sortedOrder[i];
                int col = sliceCols[index];
                double val = sliceVals[index];
                if (write > 0 && sliceCols[sortedOrder[write - 1]] == col) {
                    normalizedValues[start + write - 1] += val;
                    continue;
                }
                normalizedColumns[start + write] = col;
                normalizedValues[start + write] = val;
                write++;
            }

            for (int i = write; i < end - start; i++) {
                normalizedColumns[start + i] = -1;
            }

            int range = end - start;
            int[] compactCols = new int[write];
            double[] compactVals = new double[write];
            System.arraycopy(normalizedColumns, start, compactCols, 0, write);
            System.arraycopy(normalizedValues, start, compactVals, 0, write);
            System.arraycopy(compactCols, 0, normalizedColumns, start, write);
            System.arraycopy(compactVals, 0, normalizedValues, start, write);

            for (int i = start + write; i < end; i++) {
                normalizedColumns[i] = -1;
                normalizedValues[i] = 0.0;
            }

            rowPointers[row + 1] = start + write;
            start = rowPointers[row + 1];
        }

        int total = 0;
        for (int row = 0; row < rows; row++) {
            total += rowPointers[row + 1] - rowPointers[row];
        }
        if (total != values.length) {
            throw new IllegalArgumentException("Duplicate column normalization changed NNZ unexpectedly.");
        }

        return normalizedColumns;
    }

    public double[] multiply(double[] x) {
        validateInputVector(x);
        double[] y = new double[rows];
        multiplyInto(x, y);
        return y;
    }

    public void multiplyInto(double[] x, double[] y) {
        validateInputVector(x);
        validateOutputVector(y);

        double[] input = (x == y) ? Arrays.copyOf(x, x.length) : x;

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;
            for (int index = rowPointers[row];
                 index < rowPointers[row + 1];
                 index++) {
                sum += values[index] * input[columnIndices[index]];
            }
            y[row] = sum;
        }
    }

    public double[] multiplyParallel(double[] x) {
        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Math.max(1, Runtime.getRuntime().availableProcessors()));
    }

    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism) {

        validateInputVector(x);
        validateParallelConfiguration(threshold, parallelism);

        double[] y = new double[rows];
        multiplyParallelInto(x, y, threshold, parallelism);
        return y;
    }

    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            int parallelism) {

        validateInputVector(x);
        validateOutputVector(y);
        validateParallelConfiguration(threshold, parallelism);

        ForkJoinPool pool = new ForkJoinPool(parallelism);
        try {
            multiplyParallelInto(x, y, threshold, pool);
        } finally {
            pool.shutdown();
        }
    }

    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            ForkJoinPool pool) {

        validateInputVector(x);
        validateOutputVector(y);
        Objects.requireNonNull(pool, "ForkJoinPool cannot be null.");

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }
        if (pool.isShutdown()) {
            throw new IllegalStateException("ForkJoinPool is already shut down.");
        }

        double[] input = (x == y) ? Arrays.copyOf(x, x.length) : x;

        pool.invoke(new MultiplyTask(
                values,
                columnIndices,
                rowPointers,
                input,
                y,
                0,
                rows,
                threshold));
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
        Objects.requireNonNull(x, "Input vector cannot be null.");
        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Input vector length (" + x.length
                            + ") must equal matrix column count (" + columns + ").");
        }
    }

    private void validateOutputVector(double[] y) {
        Objects.requireNonNull(y, "Output vector cannot be null.");
        if (y.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length (" + y.length
                            + ") must equal matrix row count (" + rows + ").");
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
                    values, columnIndices, rowPointers, rows, columns);
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
            throw new IllegalArgumentException("rowPointers[0] must be 0.");
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
                        "Column index out of bounds at position " + i + ": " + column);
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
