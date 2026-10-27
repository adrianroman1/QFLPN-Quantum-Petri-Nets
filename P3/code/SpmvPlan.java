import java.util.Arrays;
import java.util.Objects;

/**
 * Immutable execution plan for sparse matrix-vector multiplication (SpMV).
 *
 * <p>The plan partitions the CSR row range into contiguous, non-empty
 * intervals. Partition boundaries are selected using the cumulative number
 * of non-zero elements (NNZ), with a row-count fallback for matrices
 * containing no non-zero elements.</p>
 *
 * <p>A plan is bound to the exact CSR row-pointer structure from which it
 * was created. Compatibility checks compare the complete row-pointer array,
 * not merely the matrix dimensions or total NNZ.</p>
 *
 * <p>The plan does not own a ForkJoinPool and does not create or shut down
 * execution resources. Pool lifecycle remains the responsibility of the
 * caller.</p>
 */
public final class SpmvPlan {

    private final int rows;
    private final int nnz;
    private final int threshold;
    private final int parallelism;
    private final MultiplyTask.SplitPolicy splitPolicy;

    /**
     * Exact immutable snapshot of the CSR row-pointer structure.
     */
    private final int[] rowPointersSnapshot;

    /**
     * Inclusive start row of each partition.
     */
    private final int[] startRows;

    /**
     * Exclusive end row of each partition.
     */
    private final int[] endRows;

    private SpmvPlan(
            int[] rowPointers,
            int threshold,
            int parallelism,
            MultiplyTask.SplitPolicy splitPolicy) {

        validateArguments(rowPointers, threshold, parallelism, splitPolicy);

        this.rows = rowPointers.length - 1;
        this.nnz = rowPointers[rowPointers.length - 1];
        this.threshold = threshold;
        this.parallelism = parallelism;
        this.splitPolicy = splitPolicy;

        this.rowPointersSnapshot = rowPointers.clone();

        int partitionCount = calculatePartitionCount(rows, parallelism);

        this.startRows = new int[partitionCount];
        this.endRows = new int[partitionCount];

        buildPartitions(rowPointersSnapshot, startRows, endRows, nnz);
    }

    /**
     * Creates a plan using the specified split policy.
     *
     * @param rowPointers CSR row-pointer array
     * @param threshold minimum NNZ threshold used by recursive tasks
     * @param parallelism requested maximum partition count
     * @param splitPolicy recursive task splitting policy
     * @return immutable execution plan
     */
    public static SpmvPlan create(
            int[] rowPointers,
            int threshold,
            int parallelism,
            MultiplyTask.SplitPolicy splitPolicy) {

        return new SpmvPlan(
                rowPointers,
                threshold,
                parallelism,
                splitPolicy);
    }

    /**
     * Creates a plan using binary NNZ splitting.
     *
     * @param rowPointers CSR row-pointer array
     * @param threshold minimum NNZ threshold used by recursive tasks
     * @param parallelism requested maximum partition count
     * @return immutable execution plan
     */
    public static SpmvPlan create(
            int[] rowPointers,
            int threshold,
            int parallelism) {

        return create(
                rowPointers,
                threshold,
                parallelism,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT);
    }

    private static void validateArguments(
            int[] rowPointers,
            int threshold,
            int parallelism,
            MultiplyTask.SplitPolicy splitPolicy) {

        Objects.requireNonNull(rowPointers, "rowPointers must not be null");
        Objects.requireNonNull(splitPolicy, "splitPolicy must not be null");

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be greater than zero");
        }

        if (parallelism <= 0) {
            throw new IllegalArgumentException(
                    "parallelism must be greater than zero");
        }

        if (rowPointers.length == 0) {
            throw new IllegalArgumentException(
                    "rowPointers must contain at least the initial zero");
        }

        if (rowPointers[0] != 0) {
            throw new IllegalArgumentException(
                    "rowPointers[0] must be zero");
        }

        int previous = 0;

        for (int i = 0; i < rowPointers.length; i++) {
            int current = rowPointers[i];

            if (current < 0) {
                throw new IllegalArgumentException(
                        "rowPointers must not contain negative values");
            }

            if (current < previous) {
                throw new IllegalArgumentException(
                        "rowPointers must be monotonically non-decreasing");
            }

            previous = current;
        }
    }

    private static int calculatePartitionCount(
            int rows,
            int parallelism) {

        if (rows == 0) {
            return 0;
        }

        return Math.min(rows, parallelism);
    }

    private static void buildPartitions(
            int[] rowPointers,
            int[] starts,
            int[] ends,
            int totalNnz) {

        int rows = rowPointers.length - 1;
        int partitionCount = starts.length;

        if (partitionCount == 0) {
            return;
        }

        if (totalNnz == 0) {
            buildRowBalancedPartitions(starts, ends, rows);
            return;
        }

        int currentStart = 0;

        for (int partition = 0;
             partition < partitionCount;
             partition++) {

            starts[partition] = currentStart;

            if (partition == partitionCount - 1) {
                ends[partition] = rows;
                currentStart = rows;
                continue;
            }

            int remainingPartitions = partitionCount - partition;
            int remainingRows = rows - currentStart;

            /*
             * Preserve at least one row for every remaining partition.
             */
            int maximumEnd = rows - (remainingPartitions - 1);

            /*
             * Compute the target cumulative NNZ using long arithmetic
             * to avoid intermediate integer overflow.
             */
            long targetNnz =
                    ((long) totalNnz * (partition + 1))
                            / partitionCount;

            int selectedEnd = currentStart + 1;

            while (selectedEnd < maximumEnd
                    && rowPointers[selectedEnd] < targetNnz) {
                selectedEnd++;
            }

            /*
             * Avoid empty partitions and ensure forward progress.
             */
            if (selectedEnd <= currentStart) {
                selectedEnd = currentStart + 1;
            }

            /*
             * Do not consume rows reserved for subsequent partitions.
             */
            if (selectedEnd > maximumEnd) {
                selectedEnd = maximumEnd;
            }

            ends[partition] = selectedEnd;
            currentStart = selectedEnd;
        }

        if (currentStart != rows) {
            throw new IllegalStateException(
                    "Partition construction did not cover all CSR rows");
        }

        validatePartitionCoverage(starts, ends, rows);
    }

    private static void buildRowBalancedPartitions(
            int[] starts,
            int[] ends,
            int rows) {

        int partitionCount = starts.length;

        for (int partition = 0;
             partition < partitionCount;
             partition++) {

            starts[partition] =
                    (int) (((long) rows * partition) / partitionCount);

            ends[partition] =
                    (int) (((long) rows * (partition + 1))
                            / partitionCount);
        }

        validatePartitionCoverage(starts, ends, rows);
    }

    private static void validatePartitionCoverage(
            int[] starts,
            int[] ends,
            int rows) {

        if (starts.length != ends.length) {
            throw new IllegalStateException(
                    "Partition boundary arrays have different lengths");
        }

        if (starts.length == 0) {
            if (rows != 0) {
                throw new IllegalStateException(
                        "Non-empty matrix has no partitions");
            }
            return;
        }

        if (starts[0] != 0) {
            throw new IllegalStateException(
                    "First partition must start at row zero");
        }

        for (int i = 0; i < starts.length; i++) {

            if (starts[i] < 0 || ends[i] > rows) {
                throw new IllegalStateException(
                        "Partition boundary is outside the CSR row range");
            }

            if (starts[i] >= ends[i]) {
                throw new IllegalStateException(
                        "Every partition must contain at least one row");
            }

            if (i > 0 && starts[i] != ends[i - 1]) {
                throw new IllegalStateException(
                        "Partitions must be contiguous and non-overlapping");
            }
        }

        if (ends[ends.length - 1] != rows) {
            throw new IllegalStateException(
                    "Partitions must cover every CSR row");
        }
    }

    public int getRows() {
        return rows;
    }

    public int getNnz() {
        return nnz;
    }

    public int getThreshold() {
        return threshold;
    }

    public int getParallelism() {
        return parallelism;
    }

    public MultiplyTask.SplitPolicy getSplitPolicy() {
        return splitPolicy;
    }

    public int getPartitionCount() {
        return startRows.length;
    }

    public int getStartRow(int partition) {
        checkPartitionIndex(partition);
        return startRows[partition];
    }

    public int getEndRow(int partition) {
        checkPartitionIndex(partition);
        return endRows[partition];
    }

    /**
     * Returns a defensive copy of all partition start rows.
     */
    public int[] getStartRows() {
        return startRows.clone();
    }

    /**
     * Returns a defensive copy of all partition end rows.
     */
    public int[] getEndRows() {
        return endRows.clone();
    }

    /**
     * Returns the NNZ count assigned to a partition.
     *
     * @param partition partition index
     * @param rowPointers CSR row-pointer array to verify
     * @return number of non-zero elements in the partition
     */
    public int getPartitionNnz(
            int partition,
            int[] rowPointers) {

        checkPartitionIndex(partition);

        if (!isCompatibleWith(rowPointers)) {
            throw new IllegalArgumentException(
                    "SpmvPlan is incompatible with the supplied CSR structure");
        }

        return rowPointers[endRows[partition]]
                - rowPointers[startRows[partition]];
    }

    /**
     * Checks exact compatibility with the CSR structure used to create
     * this plan.
     *
     * <p>All row-pointer entries must match. Equal dimensions and equal
     * total NNZ are insufficient because different row distributions
     * can have different partition boundaries.</p>
     *
     * @param rowPointers candidate CSR row-pointer array
     * @return true only when the complete structure matches exactly
     */
    public boolean isCompatibleWith(int[] rowPointers) {

        if (rowPointers == null) {
            return false;
        }

        return Arrays.equals(rowPointersSnapshot, rowPointers);
    }

    private void checkPartitionIndex(int partition) {
        if (partition < 0 || partition >= startRows.length) {
            throw new IndexOutOfBoundsException(
                    "Invalid partition index: " + partition);
        }
    }

    /**
     * Returns whether this plan represents an empty CSR matrix.
     */
    public boolean isEmpty() {
        return rows == 0;
    }

    @Override
    public String toString() {
        return "SpmvPlan{"
                + "rows=" + rows
                + ", nnz=" + nnz
                + ", threshold=" + threshold
                + ", parallelism=" + parallelism
                + ", splitPolicy=" + splitPolicy
                + ", partitionCount=" + startRows.length
                + '}';
    }
}
