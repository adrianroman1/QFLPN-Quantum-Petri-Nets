package hpc.csr;

import java.util.Arrays;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * SparseMatrixCSR
 *
 * Reprezentare a unei matrice rare în format
 * Compressed Sparse Row (CSR).
 *
 * Structura CSR utilizează trei tablouri:
 *
 * values          - valorile elementelor nenule;
 * columnIndices   - indicii coloanelor;
 * rowPointers     - delimitarea fiecărui rând.
 *
 * Clasa oferă:
 * 1. validarea structurii CSR;
 * 2. multiplicare secvențială A*x;
 * 3. multiplicare paralelă A*x cu ForkJoinPool;
 * 4. metadatele matricei;
 * 5. acces controlat la datele CSR.
 *
 * Notă:
 * Implementarea actuală utilizează tablouri Java pe heap.
 * Memoria off-heap va fi tratată într-o etapă separată a proiectului HPC.
 */
public final class SparseMatrixCSR {

    private final int rows;
    private final int columns;

    private final double[] values;
    private final int[] columnIndices;
    private final int[] rowPointers;

    private static final int DEFAULT_PARALLEL_THRESHOLD = 4096;

    public SparseMatrixCSR(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        validateDimensions(rows, columns);

        Objects.requireNonNull(values, "values cannot be null");
        Objects.requireNonNull(
                columnIndices,
                "columnIndices cannot be null");
        Objects.requireNonNull(
                rowPointers,
                "rowPointers cannot be null");

        validateCSRStructure(
                values,
                columnIndices,
                rowPointers,
                rows,
                columns);

        this.values = Arrays.copyOf(
                values,
                values.length);

        this.columnIndices = Arrays.copyOf(
                columnIndices,
                columnIndices.length);

        this.rowPointers = Arrays.copyOf(
                rowPointers,
                rowPointers.length);

        this.rows = rows;
        this.columns = columns;
    }

    private static void validateDimensions(
            int rows,
            int columns) {

        if (rows < 0) {
            throw new IllegalArgumentException(
                    "Number of rows cannot be negative.");
        }

        if (columns < 0) {
            throw new IllegalArgumentException(
                    "Number of columns cannot be negative.");
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

        if (rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1.");
        }

        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0.");
        }

        int previous = 0;

        for (int i = 0; i < rowPointers.length; i++) {

            int current = rowPointers[i];

            if (current < 0) {
                throw new IllegalArgumentException(
                        "rowPointers cannot contain negative values.");
            }

            if (current < previous) {
                throw new IllegalArgumentException(
                        "rowPointers must be monotonically non-decreasing.");
            }

            if (current > values.length) {
                throw new IllegalArgumentException(
                        "rowPointers value exceeds NNZ at index "
                                + i + ".");
            }

            previous = current;
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "rowPointers[last] must equal number of non-zero elements.");
        }

        for (int i = 0; i < columnIndices.length; i++) {

            int column = columnIndices[i];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Column index out of bounds at position "
                                + i + ": " + column);
            }
        }
    }

    public double[] multiply(double[] x) {

        validateInputVector(x);

        double[] y = new double[rows];

        multiplyInto(x, y);

        return y;
    }

    public void multiplyInto(
            double[] x,
            double[] y) {

        validateInputVector(x);

        Objects.requireNonNull(
                y,
                "Output vector cannot be null.");

        if (y.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length (" + y.length
                            + ") must equal matrix row count ("
                            + rows + ").");
        }

        for (int row = 0; row < rows; row++) {

            double sum = 0.0;

            int start = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = start;
                 index < end;
                 index++) {

                sum += values[index]
                        * x[columnIndices[index]];
            }

            y[row] = sum;
        }
    }

    public double[] multiplyParallel(
            double[] x) {

        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Runtime.getRuntime()
                        .availableProcessors());
    }

    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism) {

        validateInputVector(x);

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        double[] y = new double[rows];

        ForkJoinPool pool =
                new ForkJoinPool(parallelism);

        try {

            pool.invoke(
                    new MultiplyTask(
                            values,
                            columnIndices,
                            rowPointers,
                            x,
                            y,
                            0,
                            rows,
                            threshold));

        } finally {

            pool.shutdown();
        }

        return y;
    }

    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            int parallelism) {

        validateInputVector(x);

        Objects.requireNonNull(
                y,
                "Output vector cannot be null.");

        if (y.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length (" + y.length
                            + ") must equal matrix row count ("
                            + rows + ").");
        }

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        ForkJoinPool pool =
                new ForkJoinPool(parallelism);

        try {

            pool.invoke(
                    new MultiplyTask(
                            values,
                            columnIndices,
                            rowPointers,
                            x,
                            y,
                            0,
                            rows,
                            threshold));

        } finally {

            pool.shutdown();
        }
    }

    private void validateInputVector(
            double[] x) {

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

        return Arrays.copyOf(
                values,
                values.length);
    }

    public int[] getColumnIndices() {

        return Arrays.copyOf(
                columnIndices,
                columnIndices.length);
    }

    public int[] getRowPointers() {

        return Arrays.copyOf(
                rowPointers,
                rowPointers.length);
    }

    public double getDensity() {

        long totalElements =
                (long) rows * columns;

        if (totalElements == 0L) {
            return 0.0;
        }

        return (double) values.length
                / (double) totalElements;
    }

    public double get(
            int row,
            int column) {

        if (row < 0 || row >= rows) {
            throw new IndexOutOfBoundsException(
                    "Row index out of bounds: " + row);
        }

        if (column < 0 || column >= columns) {
            throw new IndexOutOfBoundsException(
                    "Column index out of bounds: " + column);
        }

        int start = rowPointers[row];
        int end = rowPointers[row + 1];

        for (int index = start;
             index < end;
             index++) {

            if (columnIndices[index] == column) {
                return values[index];
            }
        }

        return 0.0;
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

    @Override
    public String toString() {

        return "SparseMatrixCSR{"
                + "rows=" + rows
                + ", columns=" + columns
                + ", nonZeroCount="
                + values.length
                + ", density="
                + getDensity()
                + '}';
    }
}