package hpc.csr;

import java.util.Objects;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * QFLPN computational engine for CSR sparse matrix-vector multiplication.
 *
 * The engine owns one persistent ForkJoinPool and one SpmvPlan associated
 * with the currently loaded matrix.
 *
 * Lifecycle guarantees:
 * - concurrent read operations are permitted;
 * - matrix replacement is exclusive;
 * - shutdown is exclusive and waits for active operations;
 * - the persistent pool is never shut down by multiplication methods;
 * - the plan is rebuilt atomically whenever the matrix is replaced.
 *
 * The matrix and its CSR representation are immutable after construction.
 */
public final class QFLPNCoreEngine implements AutoCloseable {

    private static final int DEFAULT_THRESHOLD = 4096;

    private static final MultiplyTask.SplitPolicy DEFAULT_SPLIT_POLICY =
            MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT;

    private final int dimension;
    private final int parallelism;
    private final ForkJoinPool forkJoinPool;

    private final ReentrantReadWriteLock lifecycleLock =
            new ReentrantReadWriteLock();

    private SparseMatrixCSR matrix;
    private SpmvPlan spmvPlan;

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

        this.matrix = null;
        this.spmvPlan = null;
        this.shutdown = false;
    }

    /**
     * Loads a new CSR matrix.
     *
     * Matrix construction and plan construction are completed before
     * publishing either object to the engine.
     */
    public void loadCSR(
            double[] values,
            int[] columns,
            int[] rowPointers) {

        lifecycleLock.writeLock().lock();

        try {
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

            SparseMatrixCSR candidate = new SparseMatrixCSR(
                    values,
                    columns,
                    rowPointers,
                    dimension,
                    dimension);

            SpmvPlan candidatePlan = createPlan(candidate);

            /*
             * Publish the matrix and its corresponding plan while holding
             * the write lock. Readers cannot observe an inconsistent pair.
             */
            this.matrix = candidate;
            this.spmvPlan = candidatePlan;

        } finally {
            lifecycleLock.writeLock().unlock();
        }
    }

    /**
     * Loads an existing immutable CSR matrix.
     */
    public void loadMatrix(SparseMatrixCSR matrix) {

        lifecycleLock.writeLock().lock();

        try {
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

            SpmvPlan candidatePlan = createPlan(matrix);

            this.matrix = matrix;
            this.spmvPlan = candidatePlan;

        } finally {
            lifecycleLock.writeLock().unlock();
        }
    }

    /**
     * Creates a plan bound to the exact row-pointer structure of a matrix.
     */
    private SpmvPlan createPlan(SparseMatrixCSR matrix) {

        Objects.requireNonNull(
                matrix,
                "matrix cannot be null");

        return SpmvPlan.create(
                matrix.getRowPointers(),
                DEFAULT_THRESHOLD,
                parallelism,
                DEFAULT_SPLIT_POLICY);
    }

    /**
     * Sequential multiplication:
     *
     *     y = A * x
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
     * Parallel multiplication using the engine's persistent SpmvPlan
     * and persistent ForkJoinPool.
     */
    public double[] multiplyParallel(double[] x) {

        lifecycleLock.readLock().lock();

        try {
            ensureActive();

            SparseMatrixCSR current = requireMatrix();
            SpmvPlan currentPlan = requirePlan();

            validateVector(x);

            return current.multiplyParallel(
                    x,
                    currentPlan,
                    forkJoinPool);

        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    /**
     * Parallel multiplication using an explicit threshold and
     * requested parallelism.
     *
     * When requestedParallelism equals the engine parallelism, the
     * persistent plan and persistent pool are reused.
     *
     * When a different parallelism is explicitly requested, a temporary
     * pool and a plan configured for that parallelism are created for
     * backward compatibility. The temporary pool is always shut down.
     *
     * Repeated production execution should use multiplyParallel(x).
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

            if (requestedParallelism == parallelism
                    && threshold == DEFAULT_THRESHOLD) {

                SpmvPlan currentPlan = requirePlan();

                return current.multiplyParallel(
                        x,
                        currentPlan,
                        forkJoinPool);
            }

            /*
             * Explicit non-default configuration.
             * The matrix remains immutable; only the execution plan
             * and pool are specific to this invocation.
             */
            SpmvPlan requestedPlan = SpmvPlan.create(
                    current.getRowPointers(),
                    threshold,
                    requestedParallelism,
                    DEFAULT_SPLIT_POLICY);

            ForkJoinPool temporaryPool =
                    new ForkJoinPool(requestedParallelism);

            try {
                return current.multiplyParallel(
                        x,
                        requestedPlan,
                        temporaryPool);

            } finally {
                temporaryPool.shutdown();
            }

        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    /**
     * Returns the currently loaded matrix.
     *
     * The returned matrix is immutable and exposes defensive copies
     * of its internal CSR arrays.
     */
    public SparseMatrixCSR getMatrix() {

        lifecycleLock.readLock().lock();

        try {
            ensureActive();
            return requireMatrix();

        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    /**
     * Returns the immutable execution plan associated with the
     * currently loaded matrix.
     */
    public SpmvPlan getSpmvPlan() {

        lifecycleLock.readLock().lock();

        try {
            ensureActive();
            return requirePlan();

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

    private SpmvPlan requirePlan() {

        if (spmvPlan == null) {
            throw new IllegalStateException(
                    "SpMV execution plan has not been initialized.");
        }

        return spmvPlan;
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
     * Shuts down the engine.
     *
     * The write lock ensures that all active read operations have
     * completed before the persistent pool is shut down.
     *
     * The operation is idempotent.
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

    /**
     * AutoCloseable integration.
     */
    @Override
    public void close() {
        shutdown();
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
                        + ", plan=not-initialized"
                        + '}';
            }

            return "QFLPNCoreEngine{"
                    + "dimension=" + dimension
                    + ", parallelism=" + parallelism
                    + ", nonZeroCount=" + matrix.getNonZeroCount()
                    + ", density=" + matrix.getDensity()
                    + ", planPartitions="
                    + requirePlan().getPartitionCount()
                    + '}';

        } finally {
            lifecycleLock.readLock().unlock();
        }
    }
}
