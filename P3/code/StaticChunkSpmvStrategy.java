package hpc.csr;

import java.util.Objects;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.RecursiveAction;

/**
 * Static NNZ-balanced chunk strategy.
 *
 * At construction the rows are split once into contiguous chunks holding
 * (approximately) equal numbers of stored entries; the worker pool is also
 * created once. A multiplication then performs no partitioning, builds no
 * task list and allocates no per-call object other than the small binary
 * range tasks over chunk indices (depth log2(chunks)).
 *
 * Reproducibility: chunks are disjoint row intervals and each row is summed
 * in the same order as SparseMatrixCSR.multiplyInto, so the output is bitwise
 * identical to the sequential product for every parallelism and chunk count.
 * A single very long row is never split.
 *
 * Alignment: interior chunk boundaries are rounded to multiples of
 * ROW_ALIGNMENT rows (8 doubles = 64 bytes) to reduce false sharing on the
 * output vector. This is best effort: the JVM does not guarantee the
 * alignment of array bases.
 *
 * Memory: the strategy keeps a private copy of the CSR arrays (public
 * getters only, no change to SparseMatrixCSR is required), i.e. one extra
 * CSR payload while the strategy is open.
 *
 * NUMA / first touch: the JVM zeroes a new array in the allocating thread,
 * so first-touch placement cannot be controlled from Java code; no claim is
 * made about it.
 */
public final class StaticChunkSpmvStrategy implements SpmvStrategy {

    public static final String NAME = "STATIC";

    /** Interior chunk boundaries are multiples of this many rows. */
    public static final int ROW_ALIGNMENT = 8;

    /** Default chunks per worker; more chunks give dynamic balancing. */
    public static final int DEFAULT_CHUNKS_PER_THREAD = 4;

    private final double[] values;
    private final int[] columns;
    private final int[] rowPointers;
    private final int rows;
    private final int columnCount;

    private final int parallelism;
    private final int[] chunkBounds;
    private final ForkJoinPool pool;
    private final boolean ownsPool;

    private volatile boolean closed;

    public StaticChunkSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism) {

        this(matrix, parallelism, DEFAULT_CHUNKS_PER_THREAD, null);
    }

    public StaticChunkSpmvStrategy(
            SparseMatrixCSR matrix,
            int parallelism,
            int chunksPerThread,
            ForkJoinPool callerOwnedPool) {

        Objects.requireNonNull(matrix, "matrix cannot be null");

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "Parallelism must be greater than zero.");
        }

        if (chunksPerThread <= 0) {
            throw new IllegalArgumentException(
                    "chunksPerThread must be greater than zero.");
        }

        // Public API only. The getters return defensive copies, taken once
        // at construction: the strategy therefore holds one extra copy of
        // the CSR payload (12 bytes per entry + 4 bytes per row) for its
        // lifetime. Account for it in memory budgets (the harness preflight
        // model already assumes two copies of the CSR payload).
        this.values = matrix.getValues();
        this.columns = matrix.getColumnIndices();
        this.rowPointers = matrix.getRowPointers();
        this.rows = matrix.getRows();
        this.columnCount = matrix.getColumns();
        this.parallelism = parallelism;

        long requested = (long) parallelism * chunksPerThread;
        int target = (int) Math.min(Math.max(1L, requested), Integer.MAX_VALUE);

        this.chunkBounds = computeChunkBounds(
                rowPointers, rows, parallelism == 1 ? 1 : target);

        if (parallelism == 1 || chunkBounds.length <= 2) {
            this.pool = null;
            this.ownsPool = false;
        } else if (callerOwnedPool != null) {
            this.pool = callerOwnedPool;
            this.ownsPool = false;
        } else {
            this.pool = new ForkJoinPool(parallelism);
            this.ownsPool = true;
        }
    }

    /**
     * bounds[0] = 0, bounds[last] = rows, strictly increasing (no empty
     * chunks). Each interior boundary is the NNZ-balanced row found by
     * binary search over the monotone row pointers, rounded to a multiple
     * of ROW_ALIGNMENT.
     */
    static int[] computeChunkBounds(
            int[] rowPointers,
            int rows,
            int chunkTarget) {

        if (rows == 0) {
            return new int[] {0, 0};
        }

        int chunks = Math.min(chunkTarget, rows);
        long nnz = rowPointers[rows];

        int[] raw = new int[chunks + 1];
        raw[chunks] = rows;

        for (int k = 1; k < chunks; k++) {
            long targetNnz = nnz * k / chunks;

            int low = 0;
            int high = rows;

            while (low < high) {
                int middle = (low + high) >>> 1;

                if (rowPointers[middle] < targetNnz) {
                    low = middle + 1;
                } else {
                    high = middle;
                }
            }

            int aligned =
                    ((low + ROW_ALIGNMENT / 2) / ROW_ALIGNMENT) * ROW_ALIGNMENT;

            if (aligned > rows) {
                aligned = rows;
            }

            if (aligned < raw[k - 1]) {
                aligned = raw[k - 1];
            }

            raw[k] = aligned;
        }

        int count = 1;
        int[] compact = new int[chunks + 1];

        for (int k = 1; k <= chunks; k++) {
            if (raw[k] > compact[count - 1]) {
                compact[count++] = raw[k];
            }
        }

        if (count == 1) {
            return new int[] {0, rows};
        }

        int[] result = new int[count];
        System.arraycopy(compact, 0, result, 0, count);
        return result;
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
        Objects.requireNonNull(x, "Input vector cannot be null.");
        Objects.requireNonNull(y, "Output vector cannot be null.");

        if (closed) {
            throw new IllegalStateException("SpmvStrategy is closed.");
        }

        if (x.length != columnCount) {
            throw new IllegalArgumentException(
                    "Input vector length (" + x.length
                            + ") must equal matrix column count ("
                            + columnCount + ").");
        }

        if (y.length != rows) {
            throw new IllegalArgumentException(
                    "Output vector length (" + y.length
                            + ") must equal matrix row count ("
                            + rows + ").");
        }

        double[] input = (x == y) ? x.clone() : x;
        int chunks = chunkBounds.length - 1;

        if (pool == null || chunks == 1) {
            computeRows(input, y, 0, rows);
            return;
        }

        pool.invoke(new ChunkRange(this, input, y, 0, chunks));
    }

    @Override
    public double[] multiply(double[] x) {
        double[] y = new double[rows];
        multiplyInto(x, y);
        return y;
    }

    /** Number of non-empty chunks. */
    public int getChunkCount() {
        return chunkBounds.length - 1;
    }

    /** Defensive copy of the chunk boundaries (length = chunks + 1). */
    public int[] getChunkBounds() {
        return chunkBounds.clone();
    }

    @Override
    public boolean isClosed() {
        return closed;
    }

    @Override
    public void close() {
        closed = true;

        if (ownsPool && pool != null) {
            pool.shutdown();
        }
    }

    private void computeRows(
            double[] input,
            double[] output,
            int startRow,
            int endRow) {

        for (int row = startRow; row < endRow; row++) {
            double sum = 0.0;

            int begin = rowPointers[row];
            int end = rowPointers[row + 1];

            for (int index = begin; index < end; index++) {
                sum += values[index] * input[columns[index]];
            }

            output[row] = sum;
        }
    }

    private static final class ChunkRange extends RecursiveAction {

        private static final long serialVersionUID = 1L;

        private final transient StaticChunkSpmvStrategy owner;
        private final transient double[] input;
        private final transient double[] output;
        private final int firstChunk;
        private final int lastChunkExclusive;

        ChunkRange(
                StaticChunkSpmvStrategy owner,
                double[] input,
                double[] output,
                int firstChunk,
                int lastChunkExclusive) {

            this.owner = owner;
            this.input = input;
            this.output = output;
            this.firstChunk = firstChunk;
            this.lastChunkExclusive = lastChunkExclusive;
        }

        @Override
        protected void compute() {
            int count = lastChunkExclusive - firstChunk;

            if (count == 1) {
                owner.computeRows(
                        input,
                        output,
                        owner.chunkBounds[firstChunk],
                        owner.chunkBounds[firstChunk + 1]);
                return;
            }

            int middle = firstChunk + count / 2;

            invokeAll(
                    new ChunkRange(owner, input, output,
                            firstChunk, middle),
                    new ChunkRange(owner, input, output,
                            middle, lastChunkExclusive));
        }
    }
}
