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

        NormalizedCSR normalized = normalizeAndValidate(values, columnIndices, rowPointers, rows, columns);

        this.values = normalized.values();
        this.columnIndices = normalized.columns();
        this.rowPointers = normalized.rowPointers();
        this.rows = rows;
        this.columns = columns;
    }

    private record NormalizedCSR(int[] columns, double[] values, int[] rowPointers) {
    }

    private static void validateDimensions(int rows, int columns) {
        if (rows < 0) {
            throw new IllegalArgumentException("Number of rows cannot be negative.");
        }
        if (columns < 0) {
            throw new IllegalArgumentException("Number of columns cannot be negative.");
        }
    }

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

            Integer[] order = new Integer[count];
            for (int i = 0; i < count; i++) {
                order[i] = rowStart + i;
            }

            Arrays.sort(order, Comparator.comparingInt(index -> columnIndices[index]));

            int rowWrite = 0;
            for (int pos = 0; pos < order.length; pos++) {
                int index = order[pos];
                int currentColumn = columnIndices[index];
                double currentValue = values[index];

                if (rowWrite > 0 && compactColumns[writeIndex + rowWrite - 1] == currentColumn) {
                    compactValues[writeIndex + rowWrite - 1] += currentValue;
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
        int[] normalizedColumns = Arrays.copyOf(compactColumns, finalNnz);
        double[] normalizedValues = Arrays.copyOf(compactValues, finalNnz);
        int[] normalizedRowPointers = Arrays.copyOf(compactRowPointers, rows + 1);

        return new NormalizedCSR(normalizedColumns, normalizedValues, normalizedRowPointers);
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
