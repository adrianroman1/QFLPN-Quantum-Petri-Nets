package hpc.csr;

import java.util.Arrays;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * Immutable sparse matrix stored in Compressed Sparse Row (CSR) format.
 *
 * <p>The matrix owns its CSR arrays. Public accessors return defensive copies.
 * Parallel multiplication uses a trusted internal task factory to avoid
 * repeatedly copying the immutable matrix structure.</p>
 */
public final class SparseMatrixCSR {

    private final int rows;
    private final int columns;

    private final double[] values;
    private final int[] columnIndices;
    private final int[] rowPointers;

    /**
     * Constructs a CSR matrix.
     *
     * @param rows number of rows
     * @param columns number of columns
     * @param values non-zero values
     * @param columnIndices column index for each non-zero value
     * @param rowPointers row offsets
     */
    public SparseMatrixCSR(
            int rows,
            int columns,
            double[] values,
            int[] columnIndices,
            int[] rowPointers) {

        if (rows < 0) {
            throw new IllegalArgumentException("rows must be >= 0");
        }

        if (columns < 0) {
            throw new IllegalArgumentException("columns must be >= 0");
        }

        Objects.requireNonNull(values, "values must not be null");
        Objects.requireNonNull(columnIndices, "columnIndices must not be null");
        Objects.requireNonNull(rowPointers, "rowPointers must not be null");

        if (values.length != columnIndices.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length");
        }

        if (rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must equal rows + 1");
        }

        this.rows = rows;
        this.columns = columns;

        this.values = Arrays.copyOf(values, values.length);
        this.columnIndices = Arrays.copyOf(
                columnIndices, columnIndices.length);
        this.rowPointers = Arrays.copyOf(rowPointers, rowPointers.length);

        normalizeAndValidate();
    }

    /**
     * Validates the CSR structure and normalizes each row.
     *
     * <p>Column indices are sorted within each row. Duplicate column entries
     * are combined by summing their values.</p>
     */
    private void normalizeAndValidate() {
        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be zero");
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "last row pointer must equal number of non-zero values");
        }

        for (int row = 0; row < rows; row++) {
            int start = rowPointers[row];
            int end = rowPointers[row + 1];

            if (start < 0 || end < start || end > values.length) {
                throw new IllegalArgumentException(
                        "Invalid row pointer range at row " + row);
            }

            normalizeRow(start, end, row);
        }

        if (columns == 0 && values.length != 0) {
            throw new IllegalArgumentException(
                    "A matrix with zero columns cannot contain non-zero entries");
        }
    }

    /**
     * Sorts and combines duplicate column entries in one row.
     */
    private void normalizeRow(int start, int end, int row) {
        int length = end - start;

        if (length <= 1) {
            if (length == 1) {
                validateEntry(start, row);
            }
            return;
        }

        Integer[] order = new Integer[length];

        for (int i = 0; i < length; i++) {
            int index = start + i;
            validateEntry(index, row);
            order[i] = index;
        }

        Arrays.sort(order, (a, b) ->
                Integer.compare(columnIndices[a], columnIndices[b]));

        double[] sortedValues = new double[length];
        int[] sortedColumns = new int[length];

        for (int i = 0; i < length; i++) {
            int originalIndex = order[i];
            sortedValues[i] = values[originalIndex];
            sortedColumns[i] = columnIndices[originalIndex];
        }

        int write = start;

        for (int i = 0; i < length; i++) {
            int column = sortedColumns[i];
            double value = sortedValues[i];

            if (write > start && columnIndices[write - 1] == column) {
                values[write - 1] += value;
            } else {
                values[write] = value;
                columnIndices[write] = column;
                write++;
            }
        }

        int removed = end - write;

        if (removed > 0) {
            removeEntriesFromRow(row, write, end, removed);
        }
    }

    /**
     * Removes duplicate entries and shifts subsequent CSR data.
     */
    private void removeEntriesFromRow(
            int row,
            int write,
            int end,
            int removed) {

        int oldNnz = values.length;
        int newNnz = oldNnz - removed;

        System.arraycopy(
                values,
                end,
                values,
                write,
                oldNnz - end);

        System.arraycopy(
                columnIndices,
                end,
                columnIndices,
                write,
                oldNnz - end);

        for (int i = row + 1; i < rowPointers.length; i++) {
            rowPointers[i] -= removed;
        }

        if (newNnz < 0) {
            throw new IllegalStateException(
                    "Invalid CSR normalization state");
        }

        if (newNnz != oldNnz) {
            compactArrays(newNnz);
        }
    }

    /**
     * Compacts the internal arrays after duplicate removal.
     */
    private void compactArrays(int newLength) {
        if (newLength == values.length) {
            return;
        }

        // The arrays are final references, so normalization is performed
        // in-place. Unused trailing positions are ignored by rowPointers.
    }

    /**
     * Validates a single non-zero entry.
     */
    private void validateEntry(int index, int row) {
        int column = columnIndices[index];
        double value = values[index];

        if (column < 0 || column >= columns) {
            throw new IllegalArgumentException(
                    "Column index out of range at row " + row
                            + ": " + column);
        }

        if (!Double.isFinite(value)) {
            throw new IllegalArgumentException(
                    "Non-finite matrix value at row " + row);
        }
    }

    /**
     * Returns the number of rows.
     */
    public int getRows() {
        return rows;
    }

    /**
     * Returns the number of columns.
     */
    public int getColumns() {
        return columns;
    }

    /**
     * Returns the number of stored non-zero entries.
     */
    public int getNnz() {
        return rowPointers[rows];
    }

    /**
     * Returns a defensive copy of the values array.
     */
    public double[] getValues() {
        return Arrays.copyOf(values, getNnz());
    }

    /**
     * Returns a defensive copy of the column indices.
     */
    public int[] getColumnIndices() {
        return Arrays.copyOf(columnIndices, getNnz());
    }

    /**
     * Returns a defensive copy of the row pointers.
     */
    public int[] getRowPointers() {
        return Arrays.copyOf(rowPointers, rowPointers.length);
    }

    /**
     * Returns the matrix density.
     */
    public double getDensity() {
        long total = (long) rows * columns;

        if (total == 0L) {
            return 0.0;
        }

        return (double) getNnz() / (double) total;
    }

    /**
     * Returns the element at the specified position.
     */
    public double get(int row, int column) {
        checkRow(row);
        checkColumn(column);

        int start = rowPointers[row];
        int end = rowPointers[row + 1];

        for (int i = start; i < end; i++) {
            if (columnIndices[i] == column) {
                return values[i];
            }
        }

        return 0.0;
    }

    /**
     * Performs sequential matrix-vector multiplication.
     *
     * @param x input vector
     * @return resulting vector
     */
    public double[] multiply(double[] x) {
        validateInputVector(x);

        double[] result = new double[rows];

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            for (int i = rowPointers[row];
                 i < rowPointers[row + 1];
                 i++) {

                sum += values[i] * x[columnIndices[i]];
            }

            result[row] = sum;
        }

        return result;
    }

    /**
     * Performs sequential multiplication into a caller-provided output array.
     */
    public void multiplyInto(double[] x, double[] output) {
        validateInputVector(x);
        validateOutputVector(output);

        double[] input = x == output
                ? Arrays.copyOf(x, x.length)
                : x;

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            for (int i = rowPointers[row];
                 i < rowPointers[row + 1];
                 i++) {

                sum += values[i] * input[columnIndices[i]];
            }

            output[row] = sum;
        }
    }

    /**
     * Performs parallel multiplication using a newly created pool.
     *
     * <p>The pool is owned by this method and is shut down before return.</p>
     */
    public double[] multiplyParallel(double[] x, int parallelism) {
        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "parallelism must be greater than zero");
        }

        ForkJoinPool pool = new ForkJoinPool(parallelism);

        try {
            return multiplyParallel(x, pool);
        } finally {
            pool.shutdown();
        }
    }

    /**
     * Performs parallel multiplication using a caller-owned pool.
     *
     * <p>The caller-owned pool is not shut down by this method.</p>
     */
    public double[] multiplyParallel(double[] x, ForkJoinPool pool) {
        validateInputVector(x);
        Objects.requireNonNull(pool, "pool must not be null");

        double[] output = new double[rows];
        multiplyParallelInto(x, output, 4096, pool);
        return output;
    }

    /**
     * Performs parallel multiplication into a caller-provided output array.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] output,
            int threshold,
            ForkJoinPool pool) {

        validateInputVector(x);
        validateOutputVector(output);
        Objects.requireNonNull(pool, "pool must not be null");

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be greater than zero");
        }

        MultiplyTask task = MultiplyTask.forValidatedCsr(
                values,
                columnIndices,
                rowPointers,
                x,
                output,
                0,
                rows,
                threshold);

        pool.invoke(task);
    }

    /**
     * Validates an input vector against the matrix column count.
     */
    private void validateInputVector(double[] x) {
        Objects.requireNonNull(x, "input vector must not be null");

        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Input vector length must equal matrix columns");
        }
    }

    /**
     * Validates an output vector against the matrix row count.
     */
    private void validateOutputVector(double[] output) {
        Objects.requireNonNull(output, "output vector must not be null");

        if (output.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length must equal matrix rows");
        }
    }

    private void checkRow(int row) {
        if (row < 0 || row >= rows) {
            throw new IndexOutOfBoundsException(
                    "Row index out of range: " + row);
        }
    }

    private void checkColumn(int column) {
        if (column < 0 || column >= columns) {
            throw new IndexOutOfBoundsException(
                    "Column index out of range: " + column);
        }
    }

    /**
     * Checks the CSR invariants.
     */
    public boolean isValid() {
        if (rows < 0 || columns < 0) {
            return false;
        }

        if (rowPointers.length != rows + 1) {
            return false;
        }

        if (rowPointers[0] != 0) {
            return false;
        }

        if (rowPointers[rows] != getNnz()) {
            return false;
        }

        for (int row = 0; row < rows; row++) {
            int start = rowPointers[row];
            int end = rowPointers[row + 1];

            if (start < 0 || end < start || end > getNnz()) {
                return false;
            }

            int previousColumn = -1;

            for (int i = start; i < end; i++) {
                int column = columnIndices[i];

                if (column < 0 || column >= columns) {
                    return false;
                }

                if (column <= previousColumn) {
                    return false;
                }

                if (!Double.isFinite(values[i])) {
                    return false;
                }

                previousColumn = column;
            }
        }

        return true;
    }

    @Override
    public String toString() {
        return "SparseMatrixCSR{"
                + "rows=" + rows
                + ", columns=" + columns
                + ", nnz=" + getNnz()
                + ", density=" + getDensity()
                + '}';
    }
}
