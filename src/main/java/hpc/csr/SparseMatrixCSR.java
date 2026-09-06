package hpc.csr;

/**
 * SparseMatrixCSR
 *
 * Reprezentare a unei matrice rare (sparse) în format
 * Compressed Sparse Row (CSR).
 *
 * Structura CSR:
 *   values       - valorile elementelor nenule
 *   columnIndices - indicii de coloană pentru fiecare valoare
 *   rowPointers  - delimitarea fiecărui rând în values/columnIndices
 *
 * Implementarea este optimizată pentru acces secvențial pe rânduri
 * și pentru operații matrice-vector.
 *
 * Observație:
 * Această implementare folosește tablouri Java pe heap.
 * Nu pretinde că folosește memorie off-heap.
 */
public final class SparseMatrixCSR {

    private final int rows;
    private final int columns;

    private final double[] values;
    private final int[] columnIndices;
    private final int[] rowPointers;

    /**
     * Construiește o matrice CSR.
     *
     * Tablourile sunt copiate pentru a proteja integritatea
     * internă a structurii.
     *
     * @param rows numărul de rânduri
     * @param columns numărul de coloane
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
