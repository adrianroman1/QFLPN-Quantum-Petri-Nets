package hpc.csr;

/**
 * Execution strategy for y = A x on one fixed CSR matrix.
 *
 * A strategy is created once per matrix and reused for every multiplication
 * (iterative state evolution). Implementations MUST:
 *  - create threads and pools only at construction, never per call;
 *  - overwrite y completely;
 *  - accept x == y (in-place) and then behave as if x had been copied;
 *  - produce output bitwise identical to SparseMatrixCSR.multiplyInto,
 *    because every row is summed in the same order.
 *
 * close() releases only resources the strategy owns. A caller-owned pool is
 * never shut down by a strategy.
 */
public interface SpmvStrategy extends AutoCloseable {

    /** Stable identifier used in benchmark artifacts. */
    String name();

    /** Requested number of worker threads (1 for sequential execution). */
    int parallelism();

    /** y = A x. */
    void multiplyInto(double[] x, double[] y);

    /** Allocating convenience variant. */
    double[] multiply(double[] x);

    /** True after close(). */
    boolean isClosed();

    @Override
    void close();
}
