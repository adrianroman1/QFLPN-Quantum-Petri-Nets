package hpc.csr;

import java.util.Objects;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Planned Fork/Join strategy for repeated CSR sparse matrix-vector products.
 *
 * The SpmvPlan is constructed once and reused for every multiplication.
 * The ForkJoinPool is also constructed once, unless supplied by the caller.
 *
 * Lifecycle:
 * - an internally created pool is owned and shut down by this strategy;
 * - a caller-supplied pool is never shut down by this strategy;
 * - close() waits for active multiplyInto() calls to finish;
 * - calls started after close() are rejected;
 * - concurrent multiplyInto() calls are permitted.
 *
 * Numerical reproducibility:
 * every row is evaluated in the same CSR entry order as the sequential
 * SparseMatrixCSR kernel. Planned partitions are disjoint row intervals.
 */
public final class PlannedForkJoinSpmvStrategy implements SpmvStrategy {

    public static final String NAME = "FJ_PLAN";

    public static final int DEFAULT_THRESHOLD = 4096;

    private final SparseMatrixCSR matrix;
    private final SpmvPlan plan;
    private final ForkJoinPool pool;
    private final boolean ownsPool;
    private final int parallelism;

    /*
     * Multiple readers may execute multiplications concurrently.
     * close() obtains the write lock and therefore waits for all active
     * multiplications before shutting down an owned pool.
     */
    private final ReentrantReadWriteLock lifecycleLock =
            new ReentrantReadWriteLock();

    private volatile boolean closed;

    public PlannedForkJoinSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism) {

        this(
                matrix,
                parallelism,
                DEFAULT_THRESHOLD,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                null);
    }

    public PlannedForkJoinSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism,
            int threshold,
            ForkJoinPool callerOwnedPool) {

        this(
                matrix,
                parallelism,
                threshold,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                callerOwnedPool);
    }

    public PlannedForkJoinSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism,
            int threshold,
            MultiplyTask.ThresholdMode thresholdMode,
            ForkJoinPool callerOwnedPool) {

        this.matrix = Objects.requireNonNull(
                matrix,
                "matrix cannot be null");

        Objects.requireNonNull(
                thresholdMode,
                "thresholdMode cannot be null");

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "Threshold must be greater than zero.");
        }

        if (callerOwnedPool != null) {
            if (callerOwnedPool.isShutdown()
                    || callerOwnedPool.isTerminated()) {
                throw new IllegalArgumentException(
                        "Caller-owned ForkJoinPool must be active.");
            }

            if (callerOwnedPool.getParallelism() < parallelism) {
                throw new IllegalArgumentException(
                        "Caller-owned ForkJoinPool parallelism is smaller "
                                + "than the requested strategy parallelism.");
            }
        }

        this.parallelism = parallelism;

        /*
         * getRowPointers() returns a defensive copy. The plan retains its
         * own immutable snapshot and is built only once per strategy.
         */
        this.plan = SpmvPlan.create(
                matrix.getRowPointers(),
                threshold,
                parallelism,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                thresholdMode);

        if (callerOwnedPool != null) {
            this.pool = callerOwnedPool;
            this.ownsPool = false;
        } else {
            this.pool = new ForkJoinPool(parallelism);
            this.ownsPool = true;
        }
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public int parallelism() {
        return parallelism;
    }

    @Override
    public void multiplyInto(double[] x, double[] y) {
        lifecycleLock.readLock().lock();

        try {
            ensureOpen();

            matrix.multiplyParallelInto(
                    x,
                    y,
                    plan,
                    pool);
        } finally {
            lifecycleLock.readLock().unlock();
        }
    }

    @Override
    public double[] multiply(double[] x) {
        Objects.requireNonNull(
                x,
                "Input vector cannot be null.");

        double[] y = new double[matrix.getRows()];
        multiplyInto(x, y);
        return y;
    }

    @Override
    public boolean isClosed() {
        return closed;
    }

    @Override
    public void close() {
        lifecycleLock.writeLock().lock();

        try {
            if (closed) {
                return;
            }

            closed = true;

            if (ownsPool) {
                pool.shutdown();
            }
        } finally {
            lifecycleLock.writeLock().unlock();
        }
    }

    private void ensureOpen() {
        if (closed) {
            throw new IllegalStateException(
                    "SpmvStrategy is closed.");
        }
    }
}
