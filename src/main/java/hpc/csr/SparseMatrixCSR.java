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
}     * @param columns numărul de coloane
     * @param values valorile elementelor nenule
     * @param columnIndices indicii coloanelor
     * @param rowPointers pointerii de început/sfârșit ai rândurilor
     */
    public SparseMatrixCSR(
            int rows,
            int columns,
            double[] values,
            int[] columnIndices,
            int[] rowPointers) {

        validateDimensions(rows, columns);
        validateArrays(
                rows,
                columns,
                values,
                columnIndices,
                rowPointers
        );

        this.rows = rows;
        this.columns = columns;

        this.values = values.clone();
        this.columnIndices = columnIndices.clone();
        this.rowPointers = rowPointers.clone();
    }

    /**
     * Construiește o matrice CSR fără copierea tablourilor.
     *
     * Această variantă este destinată scenariilor HPC în care
     * reducerea operațiilor de copiere este importantă.
     *
     * Apelantul trebuie să trateze tablourile ca fiind proprietatea
     * structurii după construcție și să nu le modifice.
     */
    public static SparseMatrixCSR wrap(
            int rows,
            int columns,
            double[] values,
            int[] columnIndices,
            int[] rowPointers) {

        validateDimensions(rows, columns);
        validateArrays(
                rows,
                columns,
                values,
                columnIndices,
                rowPointers
        );

        return new SparseMatrixCSR(
                rows,
                columns,
                values,
                columnIndices,
                rowPointers,
                false
        );
    }

    /**
     * Constructor intern folosit de wrap().
     */
    private SparseMatrixCSR(
            int rows,
            int columns,
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            boolean copyArrays) {

        this.rows = rows;
        this.columns = columns;

        if (copyArrays) {
            this.values = values.clone();
            this.columnIndices = columnIndices.clone();
            this.rowPointers = rowPointers.clone();
        } else {
            this.values = values;
            this.columnIndices = columnIndices;
            this.rowPointers = rowPointers;
        }
    }

    /**
     * Numărul de rânduri.
     */
    public int getRows() {
        return rows;
    }

    /**
     * Numărul de coloane.
     */
    public int getColumns() {
        return columns;
    }

    /**
     * Numărul de elemente nenule.
     */
    public int getNnz() {
        return values.length;
    }

    /**
     * Returnează o copie a vectorului de valori.
     */
    public double[] getValues() {
        return values.clone();
    }

    /**
     * Returnează o copie a indicilor de coloană.
     */
    public int[] getColumnIndices() {
        return columnIndices.clone();
    }

    /**
     * Returnează o copie a pointerilor de rând.
     */
    public int[] getRowPointers() {
        return rowPointers.clone();
    }

    /**
     * Acces intern rapid pentru clasele din același package.
     *
     * Nu se face copiere pentru a evita overhead-ul în nucleul HPC.
     */
    double[] valuesArray() {
        return values;
    }

    /**
     * Acces intern rapid pentru indicii de coloană.
     */
    int[] columnIndicesArray() {
        return columnIndices;
    }

    /**
     * Acces intern rapid pentru pointerii de rând.
     */
    int[] rowPointersArray() {
        return rowPointers;
    }

    /**
     * Înmulțire CSR × vector, implementată secvențial.
     *
     * y = A × x
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiply(double[] x) {

        if (x == null) {
            throw new IllegalArgumentException(
                    "Input vector must not be null"
            );
        }

        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Vector length mismatch: expected "
                    + columns
                    + ", got "
                    + x.length
            );
        }

        double[] y = new double[rows];

        multiplyInto(x, y);

        return y;
    }

    /**
     * Înmulțire CSR × vector fără alocarea vectorului rezultat.
     *
     * Această metodă este utilă pentru benchmark-uri și execuții HPC
     * repetate, deoarece reduce presiunea asupra Garbage Collector-ului.
     *
     * @param x vectorul de intrare
     * @param y vectorul rezultat
     */
    public void multiplyInto(double[] x, double[] y) {

        if (x == null) {
            throw new IllegalArgumentException(
                    "Input vector must not be null"
            );
        }

        if (y == null) {
            throw new IllegalArgumentException(
                    "Output vector must not be null"
            );
        }

        if (x.length != columns) {
            throw new IllegalArgumentException(
                    "Input vector length mismatch: expected "
                    + columns
                    + ", got "
                    + x.length
            );
        }

        if (y.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length mismatch: expected "
                    + rows
                    + ", got "
                    + y.length
            );
        }

        for (int row = 0; row < rows; row++) {

            double sum = 0.0;

            int start = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = start; index < end; index++) {

                int column = columnIndices[index];

                sum += values[index] * x[column];
            }

            y[row] = sum;
        }
    }

    /**
     * Returnează valoarea elementului A[row][column].
     *
     * Dacă elementul nu este prezent în matricea rară,
     * valoarea returnată este 0.0.
     */
    public double get(int row, int column) {

        checkRowIndex(row);
        checkColumnIndex(column);

        int start = rowPointers[row];
        int end = rowPointers[row + 1];

        for (int index = start; index < end; index++) {

            if (columnIndices[index] == column) {
                return values[index];
            }
        }

        return 0.0;
    }

    /**
     * Verifică dacă matricea conține structura CSR validă.
     *
     * @return true dacă structura este validă
     */
    public boolean isValid() {

        try {
            validateArrays(
                    rows,
                    columns,
                    values,
                    columnIndices,
                    rowPointers
            );

            return true;

        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    /**
     * Validează dimensiunile matricei.
     */
    private static void validateDimensions(
            int rows,
            int columns) {

        if (rows < 0) {
            throw new IllegalArgumentException(
                    "Number of rows must be >= 0"
            );
        }

        if (columns < 0) {
            throw new IllegalArgumentException(
                    "Number of columns must be >= 0"
            );
        }
    }

    /**
     * Validează toate componentele CSR.
     */
    private static void validateArrays(
            int rows,
            int columns,
            double[] values,
            int[] columnIndices,
            int[] rowPointers) {

        if (values == null) {
            throw new IllegalArgumentException(
                    "values must not be null"
            );
        }

        if (columnIndices == null) {
            throw new IllegalArgumentException(
                    "columnIndices must not be null"
            );
        }

        if (rowPointers == null) {
            throw new IllegalArgumentException(
                    "rowPointers must not be null"
            );
        }

        if (values.length != columnIndices.length) {
            throw new IllegalArgumentException(
                    "values and columnIndices must have the same length"
            );
        }

        if (rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1"
            );
        }

        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0"
            );
        }

        int previous = rowPointers[0];

        for (int row = 1; row < rowPointers.length; row++) {

            int current = rowPointers[row];

            if (current < previous) {
                throw new IllegalArgumentException(
                        "rowPointers must be non-decreasing"
                );
            }

            if (current < 0 || current > values.length) {
                throw new IllegalArgumentException(
                        "Invalid rowPointers value at index "
                        + row
                );
            }

            previous = current;
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "Last rowPointers value must equal NNZ"
            );
        }

        for (int index = 0; index < columnIndices.length; index++) {

            int column = columnIndices[index];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Invalid column index "
                        + column
                        + " at position "
                        + index
                );
            }
        }
    }

    /**
     * Verifică indexul unui rând.
     */
    private void checkRowIndex(int row) {

        if (row < 0 || row >= rows) {
            throw new IndexOutOfBoundsException(
                    "Row index out of range: " + row
            );
        }
    }

    /**
     * Verifică indexul unei coloane.
     */
    private void checkColumnIndex(int column) {

        if (column < 0 || column >= columns) {
            throw new IndexOutOfBoundsException(
                    "Column index out of range: " + column
            );
        }
    }

    @Override
    public String toString() {

        return "SparseMatrixCSR{"
                + "rows=" + rows
                + ", columns=" + columns
                + ", nnz=" + values.length
                + '}';
    }
}
