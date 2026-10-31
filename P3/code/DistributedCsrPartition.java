package hpc.csr;

import java.util.Arrays;
import java.util.Objects;

/**
 * Row-wise distribution of a square CSR matrix over R ranks, together with
 * the data-flow plan a distributed SpMV needs. MPI-independent.
 *
 * Distribution:
 *  - rank r owns the contiguous rows [rowStart(r), rowEnd(r)), chosen so
 *    that ranks hold (approximately) equal numbers of stored entries;
 *  - for a square matrix, rank r also owns the entries x[i] of the input
 *    vector for the same index range (the usual 1-D row distribution);
 *  - each rank keeps a LOCAL CSR whose column indices are remapped to a
 *    compact numbering of the distinct global columns it references
 *    (neededColumns), so the local kernel reads a compact vector.
 *
 * Communication plan: before the local product each rank must obtain the
 * entries x[j] for every needed column j it does not own (the "halo").
 * remoteColumnCount(r) is exactly that number, haloBytes(r) = 8 * count is
 * the volume of a point-to-point (Alltoallv-style) exchange, and
 * allgatherBytes(r) is the volume of the naive all-gather alternative.
 * These are exact counts of the plan, not measurements of any network.
 *
 * Numerical contract: every row keeps its original entry order and the same
 * operands, so the distributed product is bitwise identical to the
 * sequential one for every rank count.
 *
 * Relation to MPI: an MPI program would call create(...) on every rank (or
 * scatter the pieces), use neededColumns(r) to derive the Alltoallv counts
 * and displacements, call localMultiply(...) on the received compact
 * vector, and gather the row ranges. This class contains no MPI call and
 * no timing claim; see DistributedSpmvSimulation for the in-process check.
 */
public final class DistributedCsrPartition {

    private final int rows;
    private final int ranks;
    private final int[] bounds;

    private final double[][] localValues;
    private final int[][] localColumns;
    private final int[][] localRowPointers;
    private final int[][] needed;
    private final int[] remoteCounts;

    private DistributedCsrPartition(
            int rows,
            int ranks,
            int[] bounds,
            double[][] localValues,
            int[][] localColumns,
            int[][] localRowPointers,
            int[][] needed,
            int[] remoteCounts) {

        this.rows = rows;
        this.ranks = ranks;
        this.bounds = bounds;
        this.localValues = localValues;
        this.localColumns = localColumns;
        this.localRowPointers = localRowPointers;
        this.needed = needed;
        this.remoteCounts = remoteCounts;
    }

    /**
     * Builds the partition. Uses only the public API of SparseMatrixCSR
     * (the getters return copies, taken once here).
     *
     * @throws IllegalArgumentException if the matrix is not square or
     *                                  ranks is not positive
     */
    public static DistributedCsrPartition create(
            SparseMatrixCSR matrix,
            int ranks) {

        Objects.requireNonNull(matrix, "matrix cannot be null");

        if (ranks <= 0) {
            throw new IllegalArgumentException(
                    "ranks must be greater than zero.");
        }

        if (matrix.getRows() != matrix.getColumns()) {
            throw new IllegalArgumentException(
                    "A 1-D distributed SpMV requires a square matrix: "
                            + matrix.getRows() + " x " + matrix.getColumns());
        }

        int n = matrix.getRows();
        double[] values = matrix.getValues();
        int[] columns = matrix.getColumnIndices();
        int[] pointers = matrix.getRowPointers();

        int[] bounds = balancedBounds(pointers, n, ranks);

        double[][] localValues = new double[ranks][];
        int[][] localColumns = new int[ranks][];
        int[][] localRowPointers = new int[ranks][];
        int[][] needed = new int[ranks][];
        int[] remote = new int[ranks];

        for (int r = 0; r < ranks; r++) {
            int rowStart = bounds[r];
            int rowEnd = bounds[r + 1];
            int begin = pointers[rowStart];
            int end = pointers[rowEnd];
            int count = end - begin;

            // distinct needed columns: bitmap over the global column range
            long[] seen = new long[(n + 63) >>> 6];
            int distinct = 0;

            for (int k = begin; k < end; k++) {
                int column = columns[k];
                long mask = 1L << (column & 63);
                int word = column >>> 6;

                if ((seen[word] & mask) == 0L) {
                    seen[word] |= mask;
                    distinct++;
                }
            }

            int[] neededColumns = new int[distinct];
            int fill = 0;

            for (int word = 0; word < seen.length; word++) {
                long bits = seen[word];

                while (bits != 0L) {
                    int bit = Long.numberOfTrailingZeros(bits);
                    neededColumns[fill++] = (word << 6) + bit;
                    bits &= bits - 1;
                }
            }

            int owned = 0;

            for (int column : neededColumns) {
                if (column >= rowStart && column < rowEnd) {
                    owned++;
                }
            }

            remote[r] = distinct - owned;
            needed[r] = neededColumns;

            int[] cols = new int[count];

            for (int k = 0; k < count; k++) {
                cols[k] = Arrays.binarySearch(
                        neededColumns, columns[begin + k]);
            }

            int[] rowPtr = new int[rowEnd - rowStart + 1];

            for (int i = rowStart; i <= rowEnd; i++) {
                rowPtr[i - rowStart] = pointers[i] - begin;
            }

            localValues[r] = Arrays.copyOfRange(values, begin, end);
            localColumns[r] = cols;
            localRowPointers[r] = rowPtr;
        }

        return new DistributedCsrPartition(
                n, ranks, bounds, localValues, localColumns,
                localRowPointers, needed, remote);
    }

    /**
     * bounds[0] = 0, bounds[ranks] = rows, non-decreasing. Empty ranges are
     * allowed (more ranks than rows, or a very long single row).
     */
    static int[] balancedBounds(int[] pointers, int rows, int ranks) {
        int[] bounds = new int[ranks + 1];
        bounds[ranks] = rows;
        long nnz = pointers[rows];

        for (int k = 1; k < ranks; k++) {
            long target = nnz * k / ranks;
            int low = 0;
            int high = rows;

            while (low < high) {
                int middle = (low + high) >>> 1;

                if (pointers[middle] < target) {
                    low = middle + 1;
                } else {
                    high = middle;
                }
            }

            bounds[k] = Math.max(low, bounds[k - 1]);
        }

        return bounds;
    }

    public int ranks() {
        return ranks;
    }

    public int rows() {
        return rows;
    }

    public int rowStart(int rank) {
        checkRank(rank);
        return bounds[rank];
    }

    public int rowEnd(int rank) {
        checkRank(rank);
        return bounds[rank + 1];
    }

    public int localRows(int rank) {
        return rowEnd(rank) - rowStart(rank);
    }

    public int localNnz(int rank) {
        checkRank(rank);
        return localValues[rank].length;
    }

    /** Sorted distinct global columns referenced by the rows of the rank. */
    public int[] neededColumns(int rank) {
        checkRank(rank);
        return needed[rank].clone();
    }

    /** Needed columns that are not owned by the rank (the halo size). */
    public int remoteColumnCount(int rank) {
        checkRank(rank);
        return remoteCounts[rank];
    }

    /** Point-to-point exchange volume for the rank, in bytes. */
    public long haloBytes(int rank) {
        return 8L * remoteColumnCount(rank);
    }

    /** Volume if the rank received all remote entries of x, in bytes. */
    public long allgatherBytes(int rank) {
        return 8L * (rows - localRows(rank));
    }

    public long totalHaloBytes() {
        long total = 0;

        for (int r = 0; r < ranks; r++) {
            total += haloBytes(r);
        }

        return total;
    }

    public long totalAllgatherBytes() {
        long total = 0;

        for (int r = 0; r < ranks; r++) {
            total += allgatherBytes(r);
        }

        return total;
    }

    /** max local NNZ divided by the mean local NNZ (1.0 = perfect). */
    public double nnzImbalance() {
        long total = 0;
        int max = 0;

        for (int r = 0; r < ranks; r++) {
            total += localValues[r].length;
            max = Math.max(max, localValues[r].length);
        }

        if (total == 0) {
            return 1.0;
        }

        return (double) max / ((double) total / ranks);
    }

    /**
     * Fills the compact input vector of the rank from a global vector.
     * In a real run this gather is the halo exchange.
     */
    public void gatherCompact(int rank, double[] globalX, double[] compact) {
        checkRank(rank);
        int[] columns = needed[rank];

        if (compact.length != columns.length) {
            throw new IllegalArgumentException(
                    "compact vector length must be " + columns.length);
        }

        for (int k = 0; k < columns.length; k++) {
            compact[k] = globalX[columns[k]];
        }
    }

    /** Length of the compact input vector of the rank. */
    public int compactLength(int rank) {
        checkRank(rank);
        return needed[rank].length;
    }

    /**
     * Local product: yLocal[i] = sum over the row of the rank, with the same
     * summation order as the sequential kernel.
     */
    public void localMultiply(
            int rank,
            double[] compactX,
            double[] yLocal,
            int yOffset) {

        checkRank(rank);

        double[] vals = localValues[rank];
        int[] cols = localColumns[rank];
        int[] ptr = localRowPointers[rank];
        int localRows = ptr.length - 1;

        for (int i = 0; i < localRows; i++) {
            double sum = 0.0;

            for (int k = ptr[i]; k < ptr[i + 1]; k++) {
                sum += vals[k] * compactX[cols[k]];
            }

            yLocal[yOffset + i] = sum;
        }
    }

    private void checkRank(int rank) {
        if (rank < 0 || rank >= ranks) {
            throw new IllegalArgumentException(
                    "rank " + rank + " is outside [0, " + ranks + ")");
        }
    }
}
