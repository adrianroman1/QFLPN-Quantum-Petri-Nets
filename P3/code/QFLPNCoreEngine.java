package hpc.csr;

import java.util.Objects;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Motorul computational QFLPN pentru multiplicare matrice-vector CSR.
 *
 * Ciclul de viață este protejat printr-un read/write lock:
 * - calculele și citirile pot rula concurent;
 * - încărcarea matricei și shutdown sunt operații exclusive;
 * - shutdown nu poate închide pool-ul în timpul unui calcul.
 *
 * Matricea CSR este structural imutabilă. Execuția paralelă utilizează
 * metoda multiplyParallelInto(..., ForkJoinPool), evitând copiile
 * defensive ale tablourilor CSR la fiecare multiplicare.
 */
public final class QFLPNCoreEngine {

    private static final int DEFAULT_THRESHOLD = 4096;

    private final int dimension;
    private final int parallelism;
    private final ForkJoinPool forkJoinPool;

    private final ReentrantReadWriteLock lifecycleLock =
            new ReentrantReadWriteLock();

    private SparseMatrixCSR matrix;
    private volatile boolean shutdown;

    public QFLPNCoreEngine(int n) {
        this(
                n,
                Math.max(1, Runtime.getRuntime().availableProcessors()));
    }

    public QFLPNCoreEngine(int n, int parallelism) {
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
        this.forkJoinPool = new ForkJoinPool(parallelism);
        this.shutdown = false;
    }

    /**
     * Încarcă o matrice CSR nouă.
     * Înlocuirea este atomică față de operațiile motorului.
     */
    public void loadCSR(
            double[] values,
            int[] columns,
            int[] rowPointers) {

        lifecycleLock.writeLock().lock();
        try {
            ensureActive();

            Objects.requireNonNull(values, "values cannot be null");
            Objects.requireNonNull(columns, "columns cannot be null");
            Objects.requireNonNull(rowPointers, "rowPointers cannot be null");

            SparseMatrixCSR candidate = new SparseMatrixCSR(
                    values,
                    columns,
                    rowPointers,
                    dimension,
                    dimension);

            this.matrix = candidate;
        } finally {
            lifecycleLock.writeLock().unlock();
        }
    }

    /**
     * Încarcă o matrice CSR existentă.
     */
    public void loadMatrix(SparseMatrixCSR matrix) {
        lifecycleLock.writeLock().lock();
        try {
            ensureActive();
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
        } finally {
            lifecycleLock.writeLock().unlock();
        }
    }

    /**
     * Multiplicare secvențială y = A*x.
     */
    public double[] multiply(double[] x) {
        lifecycleLock.readLock().lock();
        try {
            ensureActive();
            SparseMatrixCSR current = requireMatrix();
            validateVector(x);
            return current.multiply(x);
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    /**
     * Multiplicare paralelă cu pool-ul persistent al motorului.
     */
    public double[] multiplyParallel(double[] x) {
        return multiplyParallel(x, DEFAULT_THRESHOLD, parallelism);
    }

    /**
     * Multiplicare paralelă cu prag și paralelism explicit.
     *
     * Dacă paralelismul solicitat este cel configurat în motor,
     * se reutilizează pool-ul persistent. Altfel se creează un pool
     * temporar, închis după terminarea operației.
     */
    public double[] multiplyParallel(
            double[] x,
            int threshold,
            int requestedParallelism) {

        lifecycleLock.readLock().lock();
        try {
            ensureActive();
            SparseMatrixCSR current = requireMatrix();
            validateVector(x);

            if (threshold <= 0) {
                throw new IllegalArgumentException(
                        "Parallel threshold must be greater than zero.");
            }

            if (requestedParallelism <= 0) {
                throw new IllegalArgumentException(
                        "Parallelism must be greater than zero.");
            }

            double[] output = new double[dimension];

            if (requestedParallelism == parallelism) {
                current.multiplyParallelInto(
                        x,
                        output,
                        threshold,
                        forkJoinPool);
                return output;
            }

            ForkJoinPool temporaryPool =
                    new ForkJoinPool(requestedParallelism);

            try {
                current.multiplyParallelInto(
                        x,
                        output,
                        threshold,
                        temporaryPool);
            } finally {
                temporaryPool.shutdown();
            }

            return output;
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    private SparseMatrixCSR requireMatrix() {
        if (matrix == null) {
            throw new IllegalStateException(
                    "CSR matrix has not been loaded.");
        }
        return matrix;
    }

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

    private void ensureActive() {
        if (shutdown) {
            throw new IllegalStateException(
                    "QFLPNCoreEngine has been shut down.");
        }
    }

    public int getDimension() {
        return dimension;
    }

    public int getParallelism() {
        return parallelism;
    }

    public SparseMatrixCSR getMatrix() {
        lifecycleLock.readLock().lock();
        try {
            ensureActive();
            return requireMatrix();
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    public int getNonZeroCount() {
        lifecycleLock.readLock().lock();
        try {
            ensureActive();
            return requireMatrix().getNonZeroCount();
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    public double getMatrixDensity() {
        lifecycleLock.readLock().lock();
        try {
            ensureActive();
            return requireMatrix().getDensity();
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    /**
     * Închiderea este exclusivă și idempotentă.
     * Așteaptă terminarea operațiilor care dețin read lock.
     */
    public void shutdown() {
        lifecycleLock.writeLock().lock();
        try {
            if (!shutdown) {
                shutdown = true;
                forkJoinPool.shutdown();
            }
        } finally {
            lifecycleLock.writeLock().unlock();
        }
    }

    public boolean isShutdown() {
        return shutdown;
    }

    @Override
    public String toString() {
        lifecycleLock.readLock().lock();
        try {
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
                    + ", nonZeroCount=" + matrix.getNonZeroCount()
                    + ", density=" + matrix.getDensity()
                    + '}';
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }
}
