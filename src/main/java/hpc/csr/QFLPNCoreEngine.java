package hpc.csr;

import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * QFLPNCoreEngine
 *
 * Nucleul computational al motorului QFLPN pentru operații
 * matrice-vector pe structuri rare CSR.
 *
 * Responsabilități:
 *
 * 1. încărcarea reprezentării CSR;
 * 2. validarea dimensiunilor;
 * 3. execuția multiplicării secvențiale;
 * 4. execuția multiplicării paralele;
 * 5. reutilizarea unui ForkJoinPool persistent pentru operațiile
 *    paralele implicite;
 * 6. expunerea metadatelor structurii computaționale;
 * 7. gestionarea explicită a ciclului de viață al resurselor.
 *
 * Design HPC:
 *
 * Motorul păstrează un ForkJoinPool persistent pentru apelurile
 * multiplyParallel(x), astfel încât pool-ul nu este recreat la
 * fiecare operație.
 *
 * Pentru un apel care solicită un nivel de parallelism diferit
 * de cel configurat în motor, se utilizează un pool temporar.
 *
 * Acest mecanism permite păstrarea API-ului actual și pregătește
 * nucleul pentru benchmark-uri repetate și execuție la scară mare.
 */
public final class QFLPNCoreEngine {

    private final int dimension;
    private final int parallelism;

    private final ForkJoinPool forkJoinPool;

    private SparseMatrixCSR matrix;

    private boolean shutdown;

    /**
     * Construiește motorul utilizând numărul de procesoare
     * disponibile raportat de JVM.
     *
     * @param n dimensiunea matricei pătratice
     */
    public QFLPNCoreEngine(int n) {

        this(
                n,
                Math.max(
                        1,
                        Runtime.getRuntime()
                                .availableProcessors()));
    }

    /**
     * Construiește motorul cu un nivel explicit de paralelism.
     *
     * @param n dimensiunea matricei pătratice
     * @param parallelism numărul de worker threads
     */
    public QFLPNCoreEngine(
            int n,
            int parallelism) {

        if (n <= 0) {
            throw new IllegalArgumentException(
                    "Dimension must be greater than zero.");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        this.dimension = n;
        this.parallelism = parallelism;

        this.forkJoinPool =
                new ForkJoinPool(parallelism);

        this.shutdown = false;
    }

    /**
     * Încarcă structura CSR.
     *
     * @param values valorile CSR
     * @param columns indicii coloanelor
     * @param rowPointers pointerii CSR
     */
    public void loadCSR(
            double[] values,
            int[] columns,
            int[] rowPointers) {

        ensureActive();

        Objects.requireNonNull(
                values,
                "values cannot be null");

        Objects.requireNonNull(
                columns,
                "columns cannot be null");

        Objects.requireNonNull(
                rowPointers,
                "rowPointers cannot be null");

        this.matrix =
                new SparseMatrixCSR(
                        values,
                        columns,
                        rowPointers,
                        dimension,
                        dimension);
    }

    /**
     * Încarcă o matrice SparseMatrixCSR existentă.
     *
     * @param matrix matricea CSR
     */
    public void loadMatrix(
            SparseMatrixCSR matrix) {

        ensureActive();

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

    /**
     * Multiplicare secvențială:
     *
     * y = A * x
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiply(
            double[] x) {

        ensureActive();
        ensureMatrixLoaded();
        validateVector(x);

        return matrix.multiply(x);
    }

    /**
     * Multiplicare paralelă folosind pool-ul persistent
     * al motorului.
     *
     * @param x vectorul de intrare
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(
            double[] x) {

        ensureActive();
        ensureMatrixLoaded();
        validateVector(x);

        return multiplyParallelInternal(
                x,
                4096);
    }

    /**
     * Multiplicare paralelă cu threshold și parallelism explicit.
     *
     * Dacă parallelism-ul solicitat coincide cu cel al motorului,
     * este reutilizat pool-ul persistent.
     *
     * În caz contrar, este creat un pool temporar numai pentru
     * apelul respectiv.
     *
     * @param x vectorul de intrare
     * @param threshold pragul de divizare
     * @param requestedParallelism nivelul de paralelism solicitat
     * @return vectorul rezultat
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int requestedParallelism) {

        ensureActive();
        ensureMatrixLoaded();
        validateVector(x);

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Parallel threshold must be greater than zero.");
        }

        if (requestedParallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        double[] output =
                new double[dimension];

        executeParallel(
                x,
                output,
                threshold,
                requestedParallelism);

        return output;
    }

    /**
     * Execută multiplicarea paralelă utilizând buffer intern nou.
     */
    private double[] multiplyParallelInternal(
            double[] x,
            int threshold) {

        double[] output =
                new double[dimension];

        executeParallel(
                x,
                output,
                threshold,
                parallelism);

        return output;
    }

    /**
     * Execută task-ul Fork/Join.
     */
    private void executeParallel(
            double[] x,
            double[] output,
            int threshold,
            int requestedParallelism) {

        MultiplyTask task =
                new MultiplyTask(
                        matrix.getValues(),
                        matrix.getColumnIndices(),
                        matrix.getRowPointers(),
                        x,
                        output,
                        0,
                        dimension,
                        threshold);

        if (requestedParallelism == parallelism) {

            forkJoinPool.invoke(task);
            return;
        }

        ForkJoinPool temporaryPool =
                new ForkJoinPool(
                        requestedParallelism);

        try {

            temporaryPool.invoke(task);

        } finally {

            temporaryPool.shutdown();
        }
    }

    /**
     * Validează vectorul de intrare.
     */
    private void validateVector(
            double[] x) {

        Objects.requireNonNull(
                x,
                "Input vector cannot be null.");

        if (x.length != dimension) {
            throw new IllegalArgumentException(
                    "Input vector length ("
                            + x.length
                            + ") must equal engine dimension ("
                            + dimension
                            + ").");
        }
    }

    /**
     * Verifică dacă motorul nu a fost închis.
     */
    private void ensureActive() {

        if (shutdown) {
            throw new IllegalStateException(
                    "QFLPNCoreEngine has been shut down.");
        }
    }

    /**
     * Verifică existența matricei încărcate.
     */
    private void ensureMatrixLoaded() {

        if (matrix == null) {
            throw new IllegalStateException(
                    "CSR matrix has not been loaded.");
        }
    }

    /**
     * @return dimensiunea motorului
     */
    public int getDimension() {
        return dimension;
    }

    /**
     * @return nivelul de paralelism configurat
     */
    public int getParallelism() {
        return parallelism;
    }

    /**
     * @return matricea CSR încărcată
     */
    public SparseMatrixCSR getMatrix() {

        ensureActive();
        ensureMatrixLoaded();

        return matrix;
    }

    /**
     * @return numărul de elemente nenule
     */
    public int getNonZeroCount() {

        ensureActive();
        ensureMatrixLoaded();

        return matrix.getNonZeroCount();
    }

    /**
     * @return densitatea matricei
     */
    public double getMatrixDensity() {

        ensureActive();
        ensureMatrixLoaded();

        return matrix.getDensity();
    }

    /**
     * Închide resursele persistente ale motorului.
     */
    public void shutdown() {

        if (!shutdown) {

            forkJoinPool.shutdown();
            shutdown = true;
        }
    }

    /**
     * @return true dacă motorul a fost închis
     */
    public boolean isShutdown() {
        return shutdown;
    }

    /**
     * Reprezentare textuală.
     */
    @Override
    public String toString() {

        if (shutdown) {
            return "QFLPNCoreEngine{"
                    + "dimension=" + dimension
                    + ", parallelism=" + parallelism
                    + ", shutdown=true"
                    + '}';
        }

        if (matrix == null) {
            return "QFLPNCoreEngine{"
                    + "dimension=" + dimension
                    + ", parallelism=" + parallelism
                    + ", matrix=not-loaded"
                    + '}';
        }

        return "QFLPNCoreEngine{"
                + "dimension=" + dimension
                + ", parallelism=" + parallelism
                + ", nonZeroCount="
                + matrix.getNonZeroCount()
                + ", density="
                + matrix.getDensity()
                + '}';
    }
}