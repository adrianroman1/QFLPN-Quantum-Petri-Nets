package hpc.csr;

import java.util.Objects;
import java.util.concurrent.ForkJoinPool;

/**
 * Strategy built on the existing SpmvPlan and the persistent-pool overload
 * SparseMatrixCSR.multiplyParallelInto(x, y, plan, pool).
 *
 * Uses the public API of SparseMatrixCSR and SpmvPlan only; it does not
 * require any change to those classes.
 *
 * The plan is created once. The ForkJoinPool is either created once and
 * owned by the strategy, or supplied by the caller and left running on
 * close().
 */
public final class PlannedForkJoinSpmvStrategy implements SpmvStrategy {

    public static final String NAME = "FJ_PLAN";

    /** Default minimum row threshold used by the planned recursion. */
    public static final int DEFAULT_THRESHOLD = 4096;

    private final SparseMatrixCSR matrix;
    private final SpmvPlan plan;
    private final ForkJoinPool pool;
    private final boolean ownsPool;
    private final int parallelism;
    private volatile boolean closed;

    public PlannedForkJoinSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism) {

        this(matrix, parallelism, DEFAULT_THRESHOLD, null);
    }

    public PlannedForkJoinSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism,
            int threshold,
            ForkJoinPool callerOwnedPool) {

        this(matrix, parallelism, threshold,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD, callerOwnedPool);
    }

    /**
     * @param thresholdMode unit of the recursion threshold. ROW_THRESHOLD
     *                      matches the default of SparseMatrixCSR;
     *                      SpmvPlan.create(int[], int, int) alone would use
     *                      NNZ_THRESHOLD, so the mode is always passed
     *                      explicitly here.
     */
    public PlannedForkJoinSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism,
            int threshold,
            MultiplyTask.ThresholdMode thresholdMode,
            ForkJoinPool callerOwnedPool) {

        this.matrix = Objects.requireNonNull(matrix, "matrix cannot be null");
        Objects.requireNonNull(thresholdMode, "thresholdMode cannot be null");

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        this.parallelism = parallelism;
        // Public API only: getRowPointers() returns a copy, taken once here.
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
        ensureOpen();
        matrix.multiplyParallelInto(x, y, plan, pool);
    }

    @Override
    public double[] multiply(double[] x) {
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
        closed = true;

        if (ownsPool) {
            pool.shutdown();
        }
    }

    private void ensureOpen() {
        if (closed) {
            throw new IllegalStateException("SpmvStrategy is closed.");
        }
    }
}
