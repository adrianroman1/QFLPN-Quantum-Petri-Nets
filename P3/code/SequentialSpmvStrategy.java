package hpc.csr;

import java.util.Objects;

/**
 * Reference strategy: delegates to SparseMatrixCSR.multiplyInto.
 * Used as the sequential baseline and as the numerical oracle.
 */
public final class SequentialSpmvStrategy implements SpmvStrategy {

    public static final String NAME = "SEQ";

    private final SparseMatrixCSR matrix;
    private volatile boolean closed;

    public SequentialSpmvStrategy(SparseMatrixCSR matrix) {
        this.matrix = Objects.requireNonNull(matrix, "matrix cannot be null");
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public int parallelism() {
        return 1;
    }

    @Override
    public void multiplyInto(double[] x, double[] y) {
        ensureOpen();
        matrix.multiplyInto(x, y);
    }

    @Override
    public double[] multiply(double[] x) {
        ensureOpen();
        return matrix.multiply(x);
    }

    @Override
    public boolean isClosed() {
        return closed;
    }

    @Override
    public void close() {
        closed = true;
    }

    private void ensureOpen() {
        if (closed) {
            throw new IllegalStateException("SpmvStrategy is closed.");
        }
    }
}
