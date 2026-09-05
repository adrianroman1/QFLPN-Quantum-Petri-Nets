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
 * values         - valorile elementelor nenule;
 * columnIndices  - indicii de coloană ai elementelor nenule;
 * rowPointers    - delimitarea elementelor fiecărui rând.
 *
 * Clasa este responsabilă de:
 * 1. stocarea structurii CSR;
 * 2. validarea structurii CSR;
 * 3. multiplicarea secvențială matrice-vector;
 * 4. multiplicarea paralelă matrice-vector;
 * 5. expunerea metadatelor matricei.
 *
 * Task-ul Fork/Join este implementat separat în MultiplyTask.java.
 */
public final class SparseMatrixCSR {

    private final int rows;
    private final int columns;

    private final double[] values;
    private final int[] columnIndices;
    private final int[] rowPointers;

    /**
     * Prag implicit pentru multiplicarea paralelă.
     *
     * Reprezintă numărul maxim de rânduri procesate
     * de un singur task înainte de calculul direct.
     *
     * Valoarea poate fi ajustată ulterior prin benchmark.
     */
    private static final int DEFAULT_PARALLEL_THRESHOLD = 4_096;

    /**
     * Construiește o matrice CSR.
     *
     * @param values valorile elementelor nenule
     * @param columnIndices indicii coloanelor elementelor nenule
     * @param rowPointers pointerii de delimitare ai rândurilor
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
            throw new IllegalArgumentException(
                    "Number of rows cannot be negative.");
        }

        if (columns < 0) {
            throw new IllegalArgumentException(
                    "Number of columns cannot be negative.");
        }

        Objects.requireNonNull(
                values,
                "values cannot be null.");

        Objects.requireNonNull(
                columnIndices,
                "columnIndices cannot be null.");

        Objects.requireNonNull(
                rowPointers,
                "rowPointers cannot be null.");

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
         * Copiere defensivă:
         * obiectul își păstrează propria reprezentare CSR
         * și nu poate fi modificat accidental prin tablourile
         * furnizate de apelant.
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
     * Validează structura CSR.
     *
     * Condițiile verificate:
     *
     * rowPointers[0] == 0;
     * rowPointers este monoton crescător;
     * rowPointers[rows] == NNZ;
     * indicii de coloană sunt în intervalul valid.
     */
    private static void validateCSRStructure(
            double[] values,
            int[] columnIndices,
            int[] rowPointers,
            int rows,
            int columns) {

        if (rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "Invalid rowPointers length.");
        }

        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be 0.");
        }

        for (int row = 0; row < rows; row++) {

            int current = rowPointers[row];
            int next = rowPointers[row + 1];

            if (current < 0 || next < 0) {
                throw new IllegalArgumentException(
                        "rowPointers cannot contain negative values.");
            }

            if (current > next) {
                throw new IllegalArgumentException(
                        "rowPointers must be monotonically non-decreasing.");
            }
        }

        if (rowPointers[rows] != values.length) {
            throw new IllegalArgumentException(
                    "rowPointers[last] must equal number of non-zero elements.");
        }

        for (int index = 0;
             index < columnIndices.length;
             index++) {

            int column = columnIndices[index];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Column index out of bounds at position "
                                + index + ": " + column);
            }
        }
    }

    /**
     * Înmulțire secvențială:
     *
     *      y = A * x
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
     * Calculează y = A * x și scrie rezultatul
     * într-un vector existent.
     *
     * Această metodă evită alocarea repetată a vectorului rezultat
     * și este utilă pentru benchmark-uri și execuții HPC.
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
     * Înmulțire paralelă matrice-vector utilizând ForkJoinPool.
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
     * @param threshold pragul de divizare a task-urilor
     * @param parallelism numărul de fire din ForkJoinPool
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

        multiplyParallelInto(
                x,
                y,
                threshold,
                parallelism);

        return y;
    }

    /**
     * Variantă paralelă fără alocarea vectorului rezultat.
     *
     * Această variantă este utilă pentru benchmark-uri repetate,
     * deoarece permite reutilizarea bufferului de ieșire.
     *
     * @param x vectorul de intrare
     * @param y vectorul rezultat
     * @param threshold pragul de divizare
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
     * @return numărul de elemente nenule (NNZ)
     */
    public int getNonZeroCount() {
        return values.length;
    }

    /**
     * Returnează o copie a valorilor CSR.
     *
     * @return valorile elementelor nenule
     */
    public double[] getValues() {
        return Arrays.copyOf(
                values,
                values.length);
    }

    /**
     * Returnează o copie a indicilor de coloană.
     *
     * @return indicii coloanelor
     */
    public int[] getColumnIndices() {
        return Arrays.copyOf(
                columnIndices,
                columnIndices.length);
    }

    /**
     * Returnează o copie a pointerilor de rând.
     *
     * @return pointerii CSR
     */
    public int[] getRowPointers() {
        return Arrays.copyOf(
                rowPointers,
                rowPointers.length);
    }

    /**
     * Calculează densitatea matricei:
     *
     *                 NNZ
     * density = -------------
     *             rows * cols
     *
     * Pentru o matrice goală, densitatea este 0.
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
     * Reprezentare textuală a structurii CSR.
     */
    @Override
    public String toString() {

        return "SparseMatrixCSR{"
                + "rows=" + rows
                + ", columns=" + columns
                + ", nonZeroCount=" + values.length
                + ", density=" + getDensity()
                + '}';
    }
}     *
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
