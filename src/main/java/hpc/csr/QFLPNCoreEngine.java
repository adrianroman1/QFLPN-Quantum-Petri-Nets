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
 *  5. expunerea metadatelor structurii computational;
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
     * Construiește un engine pentru o problemă pătratică de dimensiune n.
     *
     * @param n dimensiunea matricei și a vectorului de stare
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
     * Datele sunt validate și copiate de SparseMatrixCSR,
     * astfel încât engine-ul să nu depindă de modificări externe
     * ale tablourilor primite.
     *
     * @param values valorile elementelor nenule
     * @param columns indicii coloanelor
     * @param rowPointers pointerii CSR
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
     * Încarcă direct o instanță SparseMatrixCSR.
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
     * Execută multiplicarea secvențială:
     *
     *          y = A * x
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
     * Execută multiplicarea paralelă:
     *
     *          y = A * x
     *
     * utilizând implementarea paralelă definită în SparseMatrixCSR.
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
     * Execută multiplicarea paralelă cu parametri experimentali
     * controlați explicit.
     *
     * Această variantă este utilă pentru benchmarking și pentru
     * studiul influenței pragului de divizare și a paralelismului.
     *
     * @param x vectorul de intrare
     * @param threshold pragul de divizare Fork/Join
     * @param parallelism numărul de fire utilizate
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
     * @return dimensiunea problemei
     */
    public int getDimension() {
        return dimension;
    }

    /**
     * @return matricea CSR încărcată
     */
    public SparseMatrixCSR getMatrix() {

        ensureMatrixLoaded();

        return matrix;
    }

    /**
     * @return numărul de elemente nenule
     */
    public int getNonZeroCount() {

        ensureMatrixLoaded();

        return matrix.getNonZeroCount();
    }

    /**
     * @return densitatea matricei
     */
    public double getMatrixDensity() {

        ensureMatrixLoaded();

        return matrix.getDensity();
    }

    /**
     * Nu există resurse native persistente de închis în această
     * versiune a engine-ului.
     *
     * Metoda este păstrată pentru compatibilitate arhitecturală
     * și poate fi extinsă ulterior când managementul pool-ului
     * va fi mutat la nivelul engine-ului.
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
