package hpc.csr;

import java.util.Objects;

/**
 * QFLPNCoreEngine
 *
 * Nucleul computational al motorului QFLPN pentru operații
 * matrice-vector pe structuri rare CSR.
 *
 * Responsabilități:
 *  1. încărcarea reprezentării CSR;
 *  2. validarea dimensiunilor;
 *  3. execuția multiplicării secvențiale;
 *  4. execuția multiplicării paralele;
 *  5. expunerea metadatelor structurii computaționale.
 *
 * Separarea dintre engine și SparseMatrixCSR permite ca:
 *  - reprezentarea datelor să rămână izolată în SparseMatrixCSR;
 *  - benchmark-ul să fie separat de calcul;
 *  - algoritmii paraleli să poată fi modificați fără schimbarea API-ului engine-ului.
 */
public final class QFLPNCoreEngine {

    private final int dimension;

    private SparseMatrixCSR matrix;

    /**
     * Creează un engine QFLPN pentru o matrice pătratică
     * de dimensiune n x n.
     *
     * @param n dimensiunea matricei
     */
    public QFLPNCoreEngine(int n) {
        if (n <= 0) {
            throw new IllegalArgumentException(
                    "Dimension must be greater than zero.");
        }

        this.dimension = n;
    }

    /**
     * Încarcă o matrice CSR pătratică.
     *
     * @param values valorile nenule
     * @param columns indicii de coloană
     * @param rowPointers pointerii de început/sfârșit ai rândurilor
     */
    public void loadCSR(
            double[] values,
            int[] columns,
            int[] rowPointers) {

        Objects.requireNonNull(values, "values cannot be null");
        Objects.requireNonNull(columns, "columns cannot be null");
        Objects.requireNonNull(rowPointers, "rowPointers cannot be null");

        this.matrix = new SparseMatrixCSR(
                values,
                columns,
                rowPointers,
                dimension,
                dimension);
    }

    /**
     * Încarcă direct o structură SparseMatrixCSR.
     *
     * @param matrix matricea CSR
     */
    public void loadMatrix(SparseMatrixCSR matrix) {
        Objects.requireNonNull(matrix, "matrix cannot be null");

        if (matrix.getRows() != dimension
                || matrix.getColumns() != dimension) {

            throw new IllegalArgumentException(
                    "Matrix dimensions must be "
                            + dimension + " x " + dimension
                            + ", but received "
                            + matrix.getRows() + " x "
                            + matrix.getColumns() + ".");
        }

        this.matrix = matrix;
    }

    /**
     * Multiplicare matrice-vector secvențială.
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiply(double[] x) {
        ensureMatrixLoaded();
        validateVector(x);

        return matrix.multiply(x);
    }

    /**
     * Multiplicare matrice-vector paralelă.
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(double[] x) {
        ensureMatrixLoaded();
        validateVector(x);

        return matrix.multiplyParallel(x);
    }

    /**
     * Multiplicare matrice-vector paralelă cu parametri expliciți
     * pentru granularitatea task-urilor și nivelul de paralelism.
     *
     * @param x vectorul de intrare
     * @param threshold numărul de rânduri procesate direct de un task
     * @param parallelism numărul de worker threads
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int parallelism) {

        ensureMatrixLoaded();
        validateVector(x);

        return matrix.multiplyParallel(
                x,
                threshold,
                parallelism);
    }

    /**
     * Verifică dacă matricea CSR a fost încărcată.
     */
    private void ensureMatrixLoaded() {
        if (matrix == null) {
            throw new IllegalStateException(
                    "CSR matrix has not been loaded.");
        }
    }

    /**
     * Validează vectorul de intrare.
     *
     * @param x vectorul care urmează să fie multiplicat
     */
    private void validateVector(double[] x) {
        Objects.requireNonNull(
                x,
                "Input vector cannot be null.");

        if (x.length != dimension) {
            throw new IllegalArgumentException(
                    "Input vector length (" + x.length
                            + ") must equal engine dimension ("
                            + dimension + ").");
        }
    }

    /**
     * Returnează dimensiunea matricei.
     *
     * @return dimensiunea matricei
     */
    public int getDimension() {
        return dimension;
    }

    /**
     * Returnează matricea CSR încărcată.
     *
     * @return matricea CSR
     */
    public SparseMatrixCSR getMatrix() {
        ensureMatrixLoaded();

        return matrix;
    }

    /**
     * Returnează numărul de elemente nenule.
     *
     * @return numărul de elemente nenule
     */
    public int getNonZeroCount() {
        ensureMatrixLoaded();

        return matrix.getNonZeroCount();
    }

    /**
     * Returnează densitatea matricei.
     *
     * @return densitatea matricei
     */
    public double getMatrixDensity() {
        ensureMatrixLoaded();

        return matrix.getDensity();
    }

    /**
     * În versiunea actuală engine-ul nu deține resurse persistente
     * care necesită eliberare explicită.
     */
    public void shutdown() {
        // No persistent resources to release in the current design.
    }

    @Override
    public String toString() {
        if (matrix == null) {
            return "QFLPNCoreEngine{"
                    + "dimension=" + dimension
                    + ", matrix=not-loaded"
                    + '}';
        }

        return "QFLPNCoreEngine{"
                + "dimension=" + dimension
                + ", nonZeroCount=" + matrix.getNonZeroCount()
                + ", density=" + matrix.getDensity()
                + '}';
    }
}