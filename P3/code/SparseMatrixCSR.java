package hpc.csr;

import java.util.Arrays;
import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * Reprezentare structural imutabilă a unei matrice rare CSR.
 *
 * CSR:
 * values        - valorile elementelor nenule;
 * columnIndices - indicii coloanelor;
 * rowPointers   - delimitările rândurilor.
 *
 * Contract:
 * - arrays de intrare sunt validate și copiate defensiv;
 * - getter-ele returnează copii defensive;
 * - structura CSR este validată înainte de construire;
 * - valorile numerice trebuie să fie finite;
 * - multiplicarea secvențială și paralelă acceptă matrice
 *   dreptunghiulare, inclusiv matrice cu dimensiuni zero.
 *
 * Nu se impune ordonarea indicilor de coloană și nu se interzic
 * duplicatele: acestea nu sunt necesare pentru corectitudinea
 * multiplicării implementate aici.
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

        this.values = Arrays.copyOf(values, values.length);
        this.columnIndices =
                Arrays.copyOf(columnIndices, columnIndices.length);
        this.rowPointers =
                Arrays.copyOf(rowPointers, rowPointers.length);

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

    /**
     * Validează invarianta CSR:
     *
     * 1. values.length == columnIndices.length;
     * 2. rowPointers.length == rows + 1;
     * 3. rowPointers[0] == 0;
     * 4. pointerii sunt nenegativi și monoton crescători;
     * 5. niciun pointer nu depășește NNZ;
     * 6. ultimul pointer este egal cu NNZ;
     * 7. indicii de coloană sunt în intervalul [0, columns);
     * 8. toate valorile numerice sunt finite.
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

        if (rows == Integer.MAX_VALUE
                || rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "rowPointers length must be rows + 1.");
        }

        if (rowPointers.length == 0) {
            throw new IllegalArgumentException(
                    "rowPointers cannot be empty.");
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
                        "CSR values must be finite. Invalid value at "
                                + "position " + i + ": " + values[i]);
            }
        }
    }

    /**
     * Calculează y = A*x și returnează un vector nou.
     */
    public double[] multiply(double[] x) {
        validateInputVector(x);

        double[] y = new double[rows];
        multiplyInto(x, y);

        return y;
    }

    /**
     * Calculează y = A*x într-un buffer furnizat de apelant.
     *
     * Dacă x și y sunt același obiect, intrarea este copiată
     * înainte de calcul pentru a evita suprascrierea valorilor
     * necesare rândurilor următoare.
     */
    public void multiplyInto(
            double[] x,
            double[] y) {

        validateInputVector(x);
        validateOutputVector(y);

        double[] input =
                (x == y)
                        ? Arrays.copyOf(x, x.length)
                        : x;

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            int start = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = start; index < end; index++) {
                sum += values[index] * input[columnIndices[index]];
            }

            y[row] = sum;
        }
    }

    /**
     * Multiplicare paralelă cu prag și paralelism implicite.
     */
    public double[] multiplyParallel(double[] x) {
        return multiplyParallel(
                x,
                DEFAULT_PARALLEL_THRESHOLD,
                Math.max(
                        1,
                        Runtime.getRuntime().availableProcessors()));
    }

    /**
     * Multiplicare paralelă cu configurație explicită.
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism) {

        validateInputVector(x);
        validateParallelConfiguration(threshold, parallelism);

        double[] y = new double[rows];

        multiplyParallelInto(
                x,
                y,
                threshold,
                parallelism);

        return y;
    }

    /**
     * Creează și închide un ForkJoinPool dedicat apelului.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            int parallelism) {

        validateInputVector(x);
        validateOutputVector(y);
        validateParallelConfiguration(threshold, parallelism);

        ForkJoinPool pool =
                new ForkJoinPool(parallelism);

        try {
            multiplyParallelInto(
                    x,
                    y,
                    threshold,
                    pool);
        } finally {
            pool.shutdown();
        }
    }

    /**
     * Utilizează un pool administrat de apelant.
     *
     * Această metodă nu închide pool-ul primit.
     * Tablourile CSR interne sunt transmise direct către task,
     * fără copii defensive suplimentare.
     */
    public void multiplyParallelInto(
            double[] x,
            double[] y,
            int threshold,
            ForkJoinPool pool) {

        validateInputVector(x);
        validateOutputVector(y);

        Objects.requireNonNull(
                pool,
                "ForkJoinPool cannot be null.");

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (pool.isShutdown()) {
            throw new IllegalStateException(
                    "ForkJoinPool is already shut down.");
        }

        /*
         * x == y este periculos în execuția paralelă:
         * un subtask ar putea suprascrie o valoare înainte
         * ca alt subtask să o citească.
         */
        double[] input =
                (x == y)
                        ? Arrays.copyOf(x, x.length)
                        : x;

        pool.invoke(
                new MultiplyTask(
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

    /**
     * Returnează o copie defensivă.
     */
    public double[] getValues() {
        return Arrays.copyOf(values, values.length);
    }

    /**
     * Returnează o copie defensivă.
     */
    public int[] getColumnIndices() {
        return Arrays.copyOf(
                columnIndices,
                columnIndices.length);
    }

    /**
     * Returnează o copie defensivă.
     */
    public int[] getRowPointers() {
        return Arrays.copyOf(
                rowPointers,
                rowPointers.length);
    }

    /**
     * Densitatea este NNZ / (rows * columns).
     * Calculul produsului se face în long pentru a evita
     * overflow-ul aritmetic pe int.
     */
    public double getDensity() {
        long totalElements = (long) rows * (long) columns;

        if (totalElements == 0L) {
            return 0.0;
        }

        return (double) values.length / (double) totalElements;
    }

    /**
     * Acces la un element al matricei.
     *
     * Căutarea este liniară în rândul CSR respectiv.
     */
    public double get(int row, int column) {
        if (row < 0 || row >= rows) {
            throw new IndexOutOfBoundsException(
                    "Row index out of bounds: " + row);
        }

        if (column < 0 || column >= columns) {
            throw new IndexOutOfBoundsException(
                    "Column index out of bounds: " + column);
        }

        for (int index = rowPointers[row];
             index < rowPointers[row + 1];
             index++) {

            if (columnIndices[index] == column) {
                return values[index];
            }
        }

        return 0.0;
    }

    /**
     * Verifică invarianta internă a structurii.
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
                + ", nonZeroCount=" + values.length
                + ", density=" + getDensity()
                + '}';
    }
}
