package hpc.mpi;

import hpc.csr.SparseMatrixCSR;

import java.util.Arrays;
import java.util.Objects;

/**
 * Immutable contiguous-row partition of a canonical CSR matrix.
 *
 * This class is independent of a particular MPI Java binding.
 * It defines the deterministic data partition that an MPI transport
 * layer can distribute to ranks.
 *
 * Partition policy:
 * - contiguous row intervals;
 * - approximately balanced by cumulative NNZ;
 * - deterministic tie-breaking;
 * - empty partitions are permitted when processes > rows.
 *
 * The matrix is not modified. All exported arrays are defensive copies.
 */
public final class DistributedCsrPartition {

    private final int rank;
    private final int processCount;

    private final int globalRows;
    private final int globalColumns;
    private final int globalNnz;

    private final int rowStart;
    private final int rowEnd;

    private final int nnzStart;
    private final int nnzEnd;

    private final int[] localRowPointers;
    private final int[] localColumnIndices;
    private final double[] localValues;

    private DistributedCsrPartition(
            int rank,
            int processCount,
            int globalRows,
            int globalColumns,
            int globalNnz,
            int rowStart,
            int rowEnd,
            int nnzStart,
            int nnzEnd,
            int[] localRowPointers,
            int[] localColumnIndices,
            double[] localValues) {

        this.rank = rank;
        this.processCount = processCount;
        this.globalRows = globalRows;
        this.globalColumns = globalColumns;
        this.globalNnz = globalNnz;
        this.rowStart = rowStart;
        this.rowEnd = rowEnd;
        this.nnzStart = nnzStart;
        this.nnzEnd = nnzEnd;

        this.localRowPointers = localRowPointers;
        this.localColumnIndices = localColumnIndices;
        this.localValues = localValues;

        validateInternalState();
    }

    /**
     * Creates all process partitions using contiguous CSR row intervals.
     *
     * The cumulative-NNZ target is used to select row boundaries.
     * A row is never split between processes.
     *
     * @param matrix canonical CSR matrix
     * @param processCount number of distributed processes
     * @return partitions ordered by rank
     */
    public static DistributedCsrPartition[] create(
            SparseMatrixCSR matrix,
            int processCount) {

        Objects.requireNonNull(matrix, "matrix cannot be null");

        if (processCount <= 0) {
            throw new IllegalArgumentException(
                    "processCount must be greater than zero.");
        }

        if (!matrix.isValid()) {
            throw new IllegalArgumentException(
                    "Input matrix is not a valid canonical CSR matrix.");
        }

        int rows = matrix.getRows();
        int columns = matrix.getColumns();
        int nnz = matrix.getNnz();

        int[] globalRowPointers = matrix.getRowPointers();
        int[] globalColumnIndices = matrix.getColumnIndices();
        double[] globalValues = matrix.getValues();

        validateGlobalArrays(
                rows,
                columns,
                nnz,
                globalRowPointers,
                globalColumnIndices,
                globalValues);

        int[] boundaries = computeRowBoundaries(
                globalRowPointers,
                rows,
                nnz,
                processCount);

        DistributedCsrPartition[] partitions =
                new DistributedCsrPartition[processCount];

        for (int rank = 0; rank < processCount; rank++) {

            int startRow = boundaries[rank];
            int endRow = boundaries[rank + 1];

            int startNnz = globalRowPointers[startRow];
            int endNnz = globalRowPointers[endRow];

            int localRows = endRow - startRow;
            int localNnz = endNnz - startNnz;

            int[] localRowPointers = new int[localRows + 1];
            int[] localColumns = new int[localNnz];
            double[] localValues = new double[localNnz];

            for (int localRow = 0;
                 localRow <= localRows;
                 localRow++) {

                localRowPointers[localRow] =
                        globalRowPointers[startRow + localRow]
                                - startNnz;
            }

            System.arraycopy(
                    globalColumnIndices,
                    startNnz,
                    localColumns,
                    0,
                    localNnz);

            System.arraycopy(
                    globalValues,
                    startNnz,
                    localValues,
                    0,
                    localNnz);

            partitions[rank] = new DistributedCsrPartition(
                    rank,
                    processCount,
                    rows,
                    columns,
                    nnz,
                    startRow,
                    endRow,
                    startNnz,
                    endNnz,
                    localRowPointers,
                    localColumns,
                    localValues);
        }

        validateCompleteCoverage(partitions, rows, nnz);

        return partitions;
    }

    /**
     * Computes deterministic contiguous row boundaries.
     *
     * For rank boundary r, the target cumulative NNZ is:
     *
     * floor(totalNNZ * r / processCount)
     *
     * The selected row boundary is the closest valid cumulative
     * NNZ boundary. Ties select the earlier row boundary.
     *
     * Empty rows and zero-NNZ matrices are supported.
     */
    private static int[] computeRowBoundaries(
            int[] rowPointers,
            int rows,
            int nnz,
            int processCount) {

        int[] boundaries = new int[processCount + 1];

        boundaries[0] = 0;
        boundaries[processCount] = rows;

        if (rows == 0) {
            Arrays.fill(boundaries, 0);
            return boundaries;
        }

        if (nnz == 0) {
            for (int rank = 1; rank < processCount; rank++) {
                boundaries[rank] =
                        (int) (((long) rows * rank) / processCount);
            }
            return boundaries;
        }

        int previousBoundary = 0;

        for (int rank = 1; rank < processCount; rank++) {

            long target = ((long) nnz * rank) / processCount;

            int minimumRow = previousBoundary;
            int maximumRow = rows;

            int low = minimumRow;
            int high = maximumRow;

            /*
             * Lower-bound search for the first row boundary whose
             * cumulative NNZ is >= target.
             */
            while (low < high) {
                int middle = low + (high - low) / 2;

                if ((long) rowPointers[middle] < target) {
                    low = middle + 1;
                } else {
                    high = middle;
                }
            }

            int candidateRight = low;
            int candidateLeft = Math.max(
                    minimumRow,
                    candidateRight - 1);

            if (candidateRight > maximumRow) {
                candidateRight = maximumRow;
            }

            long leftDistance = Math.abs(
                    (long) rowPointers[candidateLeft] - target);

            long rightDistance = Math.abs(
                    (long) rowPointers[candidateRight] - target);

            /*
             * Deterministic tie-breaking: choose the earlier boundary.
             */
            int selected = leftDistance <= rightDistance
                    ? candidateLeft
                    : candidateRight;

            selected = Math.max(previousBoundary, selected);
            selected = Math.min(rows, selected);

            boundaries[rank] = selected;
            previousBoundary = selected;
        }

        return boundaries;
    }

    private static void validateGlobalArrays(
            int rows,
            int columns,
            int nnz,
            int[] rowPointers,
            int[] columnIndices,
            double[] values) {

        if (rows < 0 || columns < 0 || nnz < 0) {
            throw new IllegalArgumentException(
                    "Global CSR dimensions cannot be negative.");
        }

        if (rows == Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "CSR row count exceeds int32 pointer capacity.");
        }

        if (rowPointers.length != rows + 1) {
            throw new IllegalArgumentException(
                    "Global row pointer length must equal rows + 1.");
        }

        if (columnIndices.length != nnz || values.length != nnz) {
            throw new IllegalArgumentException(
                    "Global CSR arrays have inconsistent NNZ lengths.");
        }

        if (rowPointers[0] != 0 || rowPointers[rows] != nnz) {
            throw new IllegalArgumentException(
                    "Global CSR row pointer endpoints are invalid.");
        }

        int previousPointer = 0;

        for (int i = 0; i < rowPointers.length; i++) {
            int pointer = rowPointers[i];

            if (pointer < previousPointer
                    || pointer < 0
                    || pointer > nnz) {

                throw new IllegalArgumentException(
                        "Invalid global row pointer at index " + i + ".");
            }

            previousPointer = pointer;
        }

        for (int i = 0; i < nnz; i++) {

            int column = columnIndices[i];

            if (column < 0 || column >= columns) {
                throw new IllegalArgumentException(
                        "Global column index out of range at position "
                                + i + ".");
            }

            if (!Double.isFinite(values[i])) {
                throw new IllegalArgumentException(
                        "Non-finite CSR value at position " + i + ".");
            }
        }
    }

    private static void validateCompleteCoverage(
            DistributedCsrPartition[] partitions,
            int rows,
            int nnz) {

        int expectedRow = 0;
        int expectedNnz = 0;

        for (int rank = 0; rank < partitions.length; rank++) {

            DistributedCsrPartition partition = partitions[rank];

            if (partition.rank != rank) {
                throw new IllegalStateException(
                        "Partition rank order is inconsistent.");
            }

            if (partition.rowStart != expectedRow
                    || partition.nnzStart != expectedNnz) {

                throw new IllegalStateException(
                        "CSR partitions contain a gap or overlap.");
            }

            expectedRow = partition.rowEnd;
            expectedNnz = partition.nnzEnd;
        }

        if (expectedRow != rows || expectedNnz != nnz) {
            throw new IllegalStateException(
                    "CSR partitions do not cover the complete matrix.");
        }
    }

    private void validateInternalState() {

        int localRows = rowEnd - rowStart;
        int localNnz = nnzEnd - nnzStart;

        if (rank < 0 || rank >= processCount) {
            throw new IllegalArgumentException("Invalid rank.");
        }

        if (rowStart < 0
                || rowEnd < rowStart
                || rowEnd > globalRows) {
            throw new IllegalArgumentException(
                    "Invalid row interval.");
        }

        if (nnzStart < 0
                || nnzEnd < nnzStart
                || nnzEnd > globalNnz) {
            throw new IllegalArgumentException(
                    "Invalid NNZ interval.");
        }

        if (localRowPointers.length != localRows + 1
                || localColumnIndices.length != localNnz
                || localValues.length != localNnz) {
            throw new IllegalArgumentException(
                    "Local CSR array lengths are inconsistent.");
        }

        if (localRowPointers[0] != 0
                || localRowPointers[localRows] != localNnz) {
            throw new IllegalArgumentException(
                    "Local CSR row pointer endpoints are invalid.");
        }

        int previous = 0;

        for (int pointer : localRowPointers) {
            if (pointer < previous || pointer > localNnz) {
                throw new IllegalArgumentException(
                        "Local CSR row pointers are invalid.");
            }
            previous = pointer;
        }

        for (int i = 0; i < localNnz; i++) {
            if (localColumnIndices[i] < 0
                    || localColumnIndices[i] >= globalColumns) {
                throw new IllegalArgumentException(
                        "Local column index is outside global dimensions.");
            }

            if (!Double.isFinite(localValues[i])) {
                throw new IllegalArgumentException(
                        "Local CSR values must be finite.");
            }
        }
    }

    public int getRank() {
        return rank;
    }

    public int getProcessCount() {
        return processCount;
    }

    public int getGlobalRows() {
        return globalRows;
    }

    public int getGlobalColumns() {
        return globalColumns;
    }

    public int getGlobalNnz() {
        return globalNnz;
    }

    public int getRowStart() {
        return rowStart;
    }

    public int getRowEnd() {
        return rowEnd;
    }

    public int getLocalRowCount() {
        return rowEnd - rowStart;
    }

    public int getNnzStart() {
        return nnzStart;
    }

    public int getNnzEnd() {
        return nnzEnd;
    }

    public int getLocalNnz() {
        return nnzEnd - nnzStart;
    }

    public int[] getLocalRowPointers() {
        return Arrays.copyOf(
                localRowPointers,
                localRowPointers.length);
    }

    public int[] getLocalColumnIndices() {
        return Arrays.copyOf(
                localColumnIndices,
                localColumnIndices.length);
    }

    public double[] getLocalValues() {
        return Arrays.copyOf(
                localValues,
                localValues.length);
    }

    /**
     * Returns the maximum local NNZ divided by mean local NNZ.
     *
     * Returns 0 when the global matrix contains no nonzero entries.
     */
    public static double calculateNnzImbalance(
            DistributedCsrPartition[] partitions) {

        Objects.requireNonNull(
                partitions,
                "partitions cannot be null");

        if (partitions.length == 0) {
            throw new IllegalArgumentException(
                    "At least one partition is required.");
        }

        long totalNnz = 0L;
        int maximumNnz = 0;

        for (DistributedCsrPartition partition : partitions) {
            Objects.requireNonNull(
                    partition,
                    "partition cannot be null");

            totalNnz += partition.getLocalNnz();
            maximumNnz = Math.max(
                    maximumNnz,
                    partition.getLocalNnz());
        }

        if (totalNnz == 0L) {
            return 0.0;
        }

        double mean = (double) totalNnz / partitions.length;
        return maximumNnz / mean;
    }

    /**
     * Returns the coefficient of variation of local NNZ counts.
     *
     * Population standard deviation is used because the supplied
     * partitions represent the complete process population.
     */
    public static double calculateNnzCoefficientOfVariation(
            DistributedCsrPartition[] partitions) {

        Objects.requireNonNull(
                partitions,
                "partitions cannot be null");

        if (partitions.length == 0) {
            throw new IllegalArgumentException(
                    "At least one partition is required.");
        }

        double mean = 0.0;

        for (DistributedCsrPartition partition : partitions) {
            Objects.requireNonNull(
                    partition,
                    "partition cannot be null");
            mean += partition.getLocalNnz();
        }

        mean /= partitions.length;

        if (mean == 0.0) {
            return 0.0;
        }

        double squaredDeviation = 0.0;

        for (DistributedCsrPartition partition : partitions) {
            double difference = partition.getLocalNnz() - mean;
            squaredDeviation += difference * difference;
        }

        double variance = squaredDeviation / partitions.length;
        return Math.sqrt(variance) / mean;
    }

    @Override
    public String toString() {
        return "DistributedCsrPartition{"
                + "rank=" + rank
                + ", processCount=" + processCount
                + ", rows=[" + rowStart + ',' + rowEnd + ')'
                + ", nnz=[" + nnzStart + ',' + nnzEnd + ')'
                + ", localRows=" + getLocalRowCount()
                + ", localNnz=" + getLocalNnz()
                + '}';
    }
}
