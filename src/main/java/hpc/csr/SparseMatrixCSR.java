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
 * rowPointers    - delimitarea fiecărui rând.
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

    /**
     * Prag implicit pentru multiplicarea paralelă.
     */
    private static final int DEFAULT_PARALLEL_THRESHOLD = 4096;

    /**
     * Constructor compatibil cu QFLPNCoreEngine.
     *
     * @param values valorile elementelor nenule
     * @param columnIndices indicii coloanelor
     * @param rowPointers pointerii CSR
     * @param rows numărul de rânduri
     * @param columns numărul de coloane
     */
    public SparseMatrixCSR(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        validateDimensions(rows, columns);

        Objects.requireNonNull(
                values,
                "values cannot be null");

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

        /*
         * Copiere defensivă pentru integritatea structurii.
         */
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

    /**
     * Validează dimensiunile matricei.
     */
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

    /**
     * Validează întreaga structură CSR.
     */
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

    /**
     * Multiplicare secvențială:
     *
     * y = A * x
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiply(double[] x) {

        validateInputVector(x);

        double[] y = new double[rows];

        multiplyInto(x, y);

        return y;
    }

    /**
     * Multiplicare secvențială fără alocarea rezultatului.
     *
     * @param x vectorul de intrare
     * @param y vectorul rezultat
     */
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

    /**
     * Multiplicare paralelă cu configurația implicită.
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(
            double[] x) {

        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Runtime.getRuntime()
                        .availableProcessors());
    }

    /**
     * Multiplicare paralelă configurabilă.
     *
     * @param x vectorul de intrare
     * @param threshold pragul ForkJoin
     * @param parallelism numărul de fire
     * @return vectorul rezultat
     */
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

    /**
     * Multiplicare paralelă fără alocarea vectorului rezultat.
     *
     * @param x vectorul de intrare
     * @param y vectorul rezultat
     * @param threshold pragul ForkJoin
     * @param parallelism numărul de fire
     */
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

    /**
     * Validează vectorul de intrare.
     */
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

    /**
     * @return numărul de rânduri
     */
    public int getRows() {
        return rows;
    }

    /**
     * @return numărul de coloane
     */
    public int getColumns() {
        return columns;
    }

    /**
     * @return numărul de elemente nenule
     */
    public int getNonZeroCount() {
        return values.length;
    }

    /**
     * Alias pentru NNZ.
     */
    public int getNnz() {
        return values.length;
    }

    /**
     * Returnează o copie a valorilor CSR.
     */
    public double[] getValues() {

        return Arrays.copyOf(
                values,
                values.length);
    }

    /**
     * Returnează o copie a indicilor de coloană.
     */
    public int[] getColumnIndices() {

        return Arrays.copyOf(
                columnIndices,
                columnIndices.length);
    }

    /**
     * Returnează o copie a pointerilor de rând.
     */
    public int[] getRowPointers() {

        return Arrays.copyOf(
                rowPointers,
                rowPointers.length);
    }

    /**
     * Densitatea matricei:
     *
     * density = NNZ / (rows * columns)
     *
     * @return densitatea matricei
     */
    public double getDensity() {

        long totalElements =
                (long) rows * columns;

        if (totalElements == 0L) {
            return 0.0;
        }

        return (double) values.length
                / (double) totalElements;
    }

    /**
     * Returnează valoarea A[row][column].
     *
     * Pentru un element absent din structura CSR
     * se returnează 0.0.
     *
     * @param row indicele rândului
     * @param column indicele coloanei
     * @return valoarea elementului
     */
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

    /**
     * @return true dacă structura CSR este validă
     */
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
