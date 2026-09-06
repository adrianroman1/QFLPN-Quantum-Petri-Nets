package hpc.csr;

import java.util.Objects;

/**
 * QFLPNCoreEngine
 *
 * Nucleul computational al motorului QFLPN pentru operații
 * matrice-vector pe structuri rare CSR.
 *
 * Responsabilități:
 * 1. încărcarea reprezentării CSR;
 * 2. validarea dimensiunilor;
 * 3. execuția multiplicării secvențiale;
 * 4. execuția multiplicării paralele;
 * 5. expunerea metadatelor structurii computaționale.
 */
public final class QFLPNCoreEngine {

    private final int dimension;

    private SparseMatrixCSR matrix;

    public QFLPNCoreEngine(int n) {

        if (n <= 0) {
            throw new IllegalArgumentException(
                    "Dimension must be greater than zero.");
        }

        this.dimension = n;
    }

    public void loadCSR(
            double[] values,
            int[] columns,
            int[] rowPointers) {

        Objects.requireNonNull(
                values,
                "values cannot be null");

        Objects.requireNonNull(
                columns,
                "columns cannot be null");

        Objects.requireNonNull(
                rowPointers,
                "rowPointers cannot be null");

        this.matrix = new SparseMatrixCSR(
                values,
                columns,
                rowPointers,
                dimension,
                dimension);
    }

    public void loadMatrix(
            SparseMatrixCSR matrix) {

        Objects.requireNonNull(
                matrix,
                "matrix cannot be null");

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

    public double[] multiply(
            double[] x) {

        ensureMatrixLoaded();
        validateVector(x);

        return matrix.multiply(x);
    }

    public double[] multiplyParallel(
            double[] x) {

        ensureMatrixLoaded();
        validateVector(x);

        return matrix.multiplyParallel(x);
    }

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

    private void ensureMatrixLoaded() {

        if (matrix == null) {
            throw new IllegalStateException(
                    "CSR matrix has not been loaded.");
        }
    }

    private void validateVector(
            double[] x) {

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

    public int getDimension() {
        return dimension;
    }

    public SparseMatrixCSR getMatrix() {

        ensureMatrixLoaded();

        return matrix;
    }

    public int getNonZeroCount() {

        ensureMatrixLoaded();

        return matrix.getNonZeroCount();
    }

    public double getMatrixDensity() {

        ensureMatrixLoaded();

        return matrix.getDensity();
    }

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
                + ", nonZeroCount="
                + matrix.getNonZeroCount()
                + ", density="
                + matrix.getDensity()
                + '}';
    }
}