package hpc.csr;

import java.util.concurrent.RecursiveAction;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.ForkJoinTask;
import java.util.concurrent.TimeUnit;

/**
 * QFLPNCoreEngine - CSR x Vector multiplication engine optimized for low GC pressure
 * and ForkJoin parallelism. Designed to be extended with off-heap buffers (DirectByteBuffer)
 * or JNI native memory for max throughput and minimal GC.
 */
public class QFLPNCoreEngine {
    private final int dimension;
    private double[] csrValues;
    private int[] colIndices;
    private int[] rowPtr;
    private final ForkJoinPool pool;
    private final int threshold;

    public QFLPNCoreEngine(int n) {
        this.dimension = n;
        this.pool = new ForkJoinPool(Runtime.getRuntime().availableProcessors());
        this.threshold = Math.max(64, Math.max(1, n / (pool.getParallelism() * 8)));
    }

    public void loadCSR(double[] values, int[] cols, int[] rowPtr) {
        if (rowPtr.length != dimension + 1) {
            throw new IllegalArgumentException("Invalid rowPtr length");
        }
        this.csrValues = values;
        this.colIndices = cols;
        this.rowPtr = rowPtr;
    }

    public double[] multiply(double[] x) {
        if (x.length != dimension) {
            throw new IllegalArgumentException("Input vector length mismatch");
        }
        final double[] y = new double[dimension];
        if (csrValues == null) throw new IllegalStateException("CSR not loaded");

        ForkJoinTask<?> job = pool.submit(new MultiplyTask(0, dimension, x, y, csrValues, colIndices, rowPtr, threshold));
        job.join();
        return y;
    }

    public void shutdown() {
        pool.shutdown();
        try { pool.awaitTermination(1, TimeUnit.MINUTES); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    private static final class MultiplyTask extends RecursiveAction {
        private final int start, end, threshold;
        private final double[] x, y, values;
        private final int[] cols, rowPtr;

        MultiplyTask(int start, int end, double[] x, double[] y, double[] values, int[] cols, int[] rowPtr, int threshold) {
            this.start = start; this.end = end; this.x = x; this.y = y; this.values = values; this.cols = cols; this.rowPtr = rowPtr; this.threshold = threshold;
        }

        @Override
        protected void compute() {
            int rows = end - start;
            if (rows <= threshold) {
                for (int r = start; r < end; r++) {
                    double acc = 0.0;
                    int s = rowPtr[r], e = rowPtr[r+1];
                    for (int i = s; i < e; i++) {
                        acc += values[i] * x[cols[i]];
                    }
                    y[r] = acc;
                }
            } else {
                int mid = (start + end) >>> 1;
                invokeAll(new MultiplyTask(start, mid, x, y, values, cols, rowPtr, threshold),
                          new MultiplyTask(mid, end, x, y, values, cols, rowPtr, threshold));
            }
        }
    }
}
