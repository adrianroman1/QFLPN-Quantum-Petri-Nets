package hpc.csr;

import java.util.Arrays;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.RecursiveAction;

/**
 * SparseMatrixCSR
 *
 * Reprezentare a unei matrice rare în format
 * Compressed Sparse Row (CSR).
 *
 * Structura utilizează trei tablouri primitive:
 *
 * values           - valorile elementelor nenule
 * columnIndices    - indicii de coloană ai elementelor nenule
 * rowPointers      - delimitarea fiecărui rând în tablourile CSR
 *
 * Clasa oferă:
 *   1. înmulțire secvențială matrice-vector;
 *   2. înmulțire paralelă matrice-vector;
 *   3. validarea structurii CSR;
 *   4. acces la dimensiunile matricei și numărul de elemente nenule.
 */
public final class SparseMatrixCSR {

    private final int rows;
    private final int columns;

    private final double[] values;
    private final int[] columnIndices;
    private final int[] rowPointers;

    /**
     * Prag implicit pentru divizarea task-urilor Fork/Join.
     *
     * Valoarea este ajustabilă ulterior prin benchmark.
     */
    private static final int DEFAULT_PARALLEL_THRESHOLD = 4_096;

    /**
     * Construiește o matrice CSR.
     *
     * @param values valorile nenule
     * @param columnIndices indicii coloanelor
     * @param rowPointers pointerii de început/sfârșit pentru fiecare rând
     * @param rows numărul de rânduri
     * @param columns numărul de coloane
     */
    public SparseMatrixCSR(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        if (rows < 0) {
            throw new IllegalArgumentException("Number of rows cannot be negative.");
        }

        if (columns < 0) {
            throw new IllegalArgumentException("Number of columns cannot be negative.");
        }

        Objects.requireNonNull(values, "values cannot be null");
        Objects.requireNonNull(columnIndices, "columnIndices cannot be null");
        Objects.requireNonNull(rowPointers, "rowPointers cannot be null");

        if (values.length != columnIndices.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length.");
        }

        if (rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1.");
        }

        validateCSRStructure(
                values,
                columnIndices,
                rowPointers,
                rows,
                columns);

        /*
         * Copiem tablourile pentru a păstra integritatea internă
         * a obiectului și pentru a evita modificări externe necontrolate.
         */
        this.values = Arrays.copyOf(values, values.length);
        this.columnIndices = Arrays.copyOf(columnIndices, columnIndices.length);
        this.rowPointers = Arrays.copyOf(rowPointers, rowPointers.length);

        this.rows = rows;
        this.columns = columns;
    }

    /**
     * Validează structura internă CSR.
     */
    private static void validateCSRStructure(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0.");
        }

        for (int r = 0; r < rows; r++) {
            if (rowPointers[r] > rowPointers[r + 1]) {
                throw new IllegalArgumentException(
                        "rowPointers must be monotonically non-decreasing.");
            }
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
     * Înmulțire secvențială:
     *
     *      y = A * x
     *
     * unde A este matricea CSR.
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiply(double[] x) {
        Objects.requireNonNull(x, "Input vector cannot be null");

        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Input vector length (" + x.length
                            + ") must equal matrix column count ("
                            + columns + ").");
        }

        double[] y = new double[rows];

        for (int row = 0; row < rows; row++) {

            double sum = 0.0;

            int start = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = start; index < end; index++) {

                sum += values[index]
                        * x[columnIndices[index]];
            }

            y[row] = sum;
        }

        return y;
    }

    /**
     * Înmulțire paralelă matrice-vector utilizând ForkJoinPool.
     *
     * Rezultatul matematic este identic cu metoda secvențială,
     * cu posibile diferențe de ordin numeric asociate execuției
     * în virgulă mobilă.
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(double[] x) {
        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Runtime.getRuntime().availableProcessors());
    }

    /**
     * Variantă configurabilă a multiplicării paralele.
     *
     * @param x vectorul de intrare
     * @param threshold numărul maxim de rânduri procesate într-un task
     *                  înainte de execuția secvențială
     * @param parallelism numărul de fire din ForkJoinPool
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism) {

        Objects.requireNonNull(x, "Input vector cannot be null");

        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Input vector length (" + x.length
                            + ") must equal matrix column count ("
                            + columns + ").");
        }

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        double[] y = new double[rows];

        ForkJoinPool pool = new ForkJoinPool(parallelism);

        try {
            pool.invoke(
                    new MultiplyTask(
                            0,
                            rows,
                            x,
                            y,
                            threshold));
        } finally {
            pool.shutdown();
        }

        return y;
    }

    /**
     * Task Fork/Join pentru procesarea unui interval de rânduri.
     */
    private final class MultiplyTask extends RecursiveAction {

        private final int startRow;
        private final int endRow;

        private final double[] x;
        private final double[] y;

        private final int threshold;

        private MultiplyTask(
                int startRow,
                int endRow,
                double[] x,
                double[] y,
                int threshold) {

            this.startRow = startRow;
            this.endRow = endRow;
            this.x = x;
            this.y = y;
            this.threshold = threshold;
        }

        @Override
        protected void compute() {

            int rowCount = endRow - startRow;

            if (rowCount <= threshold) {

                for (int row = startRow; row < endRow; row++) {

                    double sum = 0.0;

                    int start = rowPointers[row];
                    int end = rowPointers[row + 1];

                    for (int index = start; index < end; index++) {

                        sum += values[index]
                                * x[columnIndices[index]];
                    }

                    y[row] = sum;
                }

                return;
            }

            int middle = startRow + ((endRow - startRow) >>> 1);

            MultiplyTask left =
                    new MultiplyTask(
                            startRow,
                            middle,
                            x,
                            y,
                            threshold);

            MultiplyTask right =
                    new MultiplyTask(
                            middle,
                            endRow,
                            x,
                            y,
                            threshold);

            invokeAll(left, right);
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

    public double[] getValues() {
        return Arrays.copyOf(values, values.length);
    }

    public int[] getColumnIndices() {
        return Arrays.copyOf(columnIndices, columnIndices.length);
    }

    public int[] getRowPointers() {
        return Arrays.copyOf(rowPointers, rowPointers.length);
    }

    /**
     * Densitatea matricei:
     *
     *              NNZ
     * density = -------------
     *             rows * cols
     */
    public double getDensity() {

        long totalElements = (long) rows * columns;

        if (totalElements == 0L) {
            return 0.0;
        }

        return (double) values.length / (double) totalElements;
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
