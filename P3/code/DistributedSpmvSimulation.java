package hpc.csr;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/**
 * IN-PROCESS SIMULATION of a distributed SpMV. It is NOT MPI and uses no
 * network.
 *
 * What it validates: the row distribution, the halo (needed-column) plan,
 * the compact local numbering, the data flow
 *     gather needed x  ->  local product  ->  assemble y
 * and, above all, that the distributed result is bitwise identical to the
 * sequential product for any number of ranks.
 *
 * What it does NOT provide: communication time, cluster scaling or any
 * statement about MPI performance. Timings taken from this class must never
 * be reported as distributed or cluster measurements. The reported halo
 * volumes are exact counts of the plan, not network measurements.
 *
 * Ranks are tasks, not threads: R ranks run on a fixed pool of
 * min(R, cores) threads created once, so R may exceed the core count.
 */
public final class DistributedSpmvSimulation implements AutoCloseable {

    private final DistributedCsrPartition partition;
    private final ExecutorService pool;
    private volatile boolean closed;
    private volatile long lastHaloBytes;
    private volatile long lastAllgatherBytes;

    public DistributedSpmvSimulation(DistributedCsrPartition partition) {
        this.partition = Objects.requireNonNull(
                partition, "partition cannot be null");

        int threads = Math.max(1, Math.min(
                partition.ranks(),
                Runtime.getRuntime().availableProcessors()));

        this.pool = Executors.newFixedThreadPool(threads, runnable -> {
            Thread thread = new Thread(runnable, "spmv-sim-rank-worker");
            thread.setDaemon(true);
            return thread;
        });
    }

    /** y = A x through the simulated distributed data flow. */
    public double[] multiply(double[] x) {
        double[] y = new double[partition.rows()];
        multiplyInto(x, y);
        return y;
    }

    /** x and y may be the same array. */
    public void multiplyInto(double[] x, double[] y) {
        Objects.requireNonNull(x, "Input vector cannot be null.");
        Objects.requireNonNull(y, "Output vector cannot be null.");

        if (closed) {
            throw new IllegalStateException(
                    "DistributedSpmvSimulation is closed.");
        }

        if (x.length != partition.rows() || y.length != partition.rows()) {
            throw new IllegalArgumentException(
                    "Vectors must have length " + partition.rows());
        }

        double[] input = (x == y) ? x.clone() : x;
        double[] result = new double[partition.rows()];
        List<Future<?>> futures = new ArrayList<>();

        for (int rank = 0; rank < partition.ranks(); rank++) {
            final int r = rank;

            futures.add(pool.submit(() -> {
                double[] compact = new double[partition.compactLength(r)];
                partition.gatherCompact(r, input, compact);
                partition.localMultiply(r, compact, result,
                        partition.rowStart(r));
            }));
        }

        try {
            for (Future<?> future : futures) {
                future.get();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted", e);
        } catch (ExecutionException e) {
            throw new IllegalStateException(
                    "rank task failed: " + e.getCause(), e.getCause());
        }

        System.arraycopy(result, 0, y, 0, result.length);
        lastHaloBytes = partition.totalHaloBytes();
        lastAllgatherBytes = partition.totalAllgatherBytes();
    }

    /** Exact halo volume of the plan used by the last multiplication. */
    public long lastHaloBytes() {
        return lastHaloBytes;
    }

    /** Volume the naive all-gather alternative would have moved. */
    public long lastAllgatherBytes() {
        return lastAllgatherBytes;
    }

    public DistributedCsrPartition partition() {
        return partition;
    }

    public boolean isClosed() {
        return closed;
    }

    @Override
    public void close() {
        closed = true;
        pool.shutdown();
    }
}
