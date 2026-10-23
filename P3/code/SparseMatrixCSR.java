package hpc.csr;

import java.util.Arrays;
import java.util.Comparator;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * Immutable Compressed Sparse Row matrix.
 *
 * Duplicate column indices are accepted. Their values are interpreted
 * additively in the mathematical sense, and row entries are internally
 * canonicalized to be deterministic across evaluation order.
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

        validateCSRStructure(values, columnIndices, rowPointers, rows, columns);

        CanonicalizedMatrix canonical = canonicalize(values, columnIndices, rowPointers, rows);

        this.values = Arrays.copyOf(canonical.values, canonical.values.length);
        this.columnIndices = Arrays.copyOf(canonical.columnIndices, canonical.columnIndices.length);
        this.rowPointers = Arrays.copyOf(canonical.rowPointers, canonical.rowPointers.length);
        this.rows = rows;
        this.columns = columns;
    }

    private static final class CanonicalizedMatrix {
        final double[] values;
        final int[] columnIndices;
        final int[] rowPointers;

        CanonicalizedMatrix(double[] values, int[] columnIndices, int[] rowPointers) {
            this.values = values;
            this.columnIndices = columnIndices;
            this.rowPointers = rowPointers;
        }
    }

    private static CanonicalizedMatrix canonicalize(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows) {

        int nnz = values.length;
        double[] renamedValues = new double[nnz];
        int[] renamedColumns = new int[nnz];
        int[] normalizedPointers = new int[rowPointers.length];

        int writeIndex = 0;
        normalizedPointers[0] = 0;

        for (int row = 0; row < rows; row++) {
            int start = rowPointers[row];
            int end = rowPointers[row + 1];
            int rowLength = end - start;

            if (rowLength == 0) {
                normalizedPointers[row] = writeIndex;
                if (row + 1 < normalizedPointers.length) {
                    normalizedPointers[row + 1] = writeIndex;
                }
                continue;
            }

            Integer[] order = new Integer[rowLength];
            for (int i = 0; i < rowLength; i++) {
                order[i] = start + i;
            }

            Arrays.sort(order, Comparator.comparingInt(index -> columnIndices[index]));

            int rowWrite = 0;
            for (int index : order) {
                int column = columnIndices[index];
                double value = values[index];

                if (rowWrite > 0 && renamedColumns[writeIndex + rowWrite - 1] == column) {
                    renamedValues[writeIndex + rowWrite - 1] += value;
                } else {
                    renamedColumns[writeIndex + rowWrite] = column;
                    renamedValues[writeIndex + rowWrite] = value;
                    rowWrite++;
                }
            }

            normalizedPointers[row] = writeIndex;
            writeIndex += rowWrite;
            normalizedPointers[row + 1] = writeIndex;
        }

        return new CanonicalizedMatrix(
                Arrays.copyOf(renamedValues, writeIndex),
                Arrays.copyOf(renamedColumns, writeIndex),
                Arrays.copyOf(normalizedPointers, rows + 1));
    }

    private static void validateDimensions(int rows, int columns) {
        if (rows < 0) {
            throw new IllegalArgumentException("Number of rows cannot be negative.");
        }
        if (columns < 0) {
            throw new IllegalArgumentException("Number of columns cannot be negative.");
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
