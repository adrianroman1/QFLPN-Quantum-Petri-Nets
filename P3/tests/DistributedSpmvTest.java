package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.Test;

/**
 * Tests for the distribution plan and the in-process simulation.
 * No MPI is involved: these tests prove the plan and the numerical
 * equivalence, nothing about network performance.
 */
class DistributedSpmvTest {

    private static final int[] RANKS = {1, 2, 3, 5, 8, 64};

    private static void assertBitwiseEqual(double[] expected, double[] actual) {
        assertEquals(expected.length, actual.length);

        for (int i = 0; i < expected.length; i++) {
            assertEquals(
                    Double.doubleToLongBits(expected[i]),
                    Double.doubleToLongBits(actual[i]),
                    "bitwise mismatch at row " + i);
        }
    }

    private static List<SparseMatrixCSR> matrices() {
        return List.of(
                SpmvStrategyTest.uniform(20_000, 2, 1L),
                SpmvStrategyTest.skewed(8_000, 2L),
                SpmvStrategyTest.singleHugeRow(1_500, 3L),
                SpmvStrategyTest.uniform(1, 1, 4L),
                SpmvStrategyTest.uniform(7, 2, 5L));
    }

    @Test
    void distributedProductIsBitwiseIdenticalForEveryRankCount() {
        for (SparseMatrixCSR matrix : matrices()) {
            double[] x = SpmvStrategyTest.vector(matrix.getRows(), 11L);
            double[] expected = matrix.multiply(x);

            for (int ranks : RANKS) {
                DistributedCsrPartition partition =
                        DistributedCsrPartition.create(matrix, ranks);

                try (DistributedSpmvSimulation simulation =
                             new DistributedSpmvSimulation(partition)) {
                    assertBitwiseEqual(expected, simulation.multiply(x));
                }
            }
        }
    }

    @Test
    void rowRangesAreContiguousDisjointAndCoverEveryRow() {
        for (SparseMatrixCSR matrix : matrices()) {
            for (int ranks : RANKS) {
                DistributedCsrPartition p =
                        DistributedCsrPartition.create(matrix, ranks);

                assertEquals(0, p.rowStart(0));
                assertEquals(matrix.getRows(), p.rowEnd(ranks - 1));

                long nnz = 0;

                for (int r = 0; r < ranks; r++) {
                    assertTrue(p.rowStart(r) <= p.rowEnd(r));

                    if (r > 0) {
                        assertEquals(p.rowEnd(r - 1), p.rowStart(r));
                    }

                    nnz += p.localNnz(r);
                }

                assertEquals(matrix.getNnz(), nnz);
            }
        }
    }

    @Test
    void uniformMatrixIsNnzBalancedAcrossRanks() {
        SparseMatrixCSR matrix = SpmvStrategyTest.uniform(100_000, 2, 6L);

        for (int ranks : new int[] {2, 4, 16, 64}) {
            DistributedCsrPartition p =
                    DistributedCsrPartition.create(matrix, ranks);
            assertTrue(p.nnzImbalance() < 1.01,
                    "imbalance " + p.nnzImbalance() + " at " + ranks);
        }
    }

    @Test
    void aSingleVeryLongRowShowsUpAsImbalanceInsteadOfBeingSplit() {
        SparseMatrixCSR matrix = SpmvStrategyTest.singleHugeRow(2_000, 7L);
        DistributedCsrPartition p =
                DistributedCsrPartition.create(matrix, 8);

        assertTrue(p.nnzImbalance() > 1.5);
    }

    @Test
    void haloCountsMatchAnIndependentBruteForceCount() {
        SparseMatrixCSR matrix = SpmvStrategyTest.skewed(5_000, 8L);
        int[] pointers = matrix.getRowPointers();
        int[] columns = matrix.getColumnIndices();

        for (int ranks : new int[] {1, 3, 8}) {
            DistributedCsrPartition p =
                    DistributedCsrPartition.create(matrix, ranks);

            for (int r = 0; r < ranks; r++) {
                Set<Integer> needed = new HashSet<>();
                Set<Integer> remote = new HashSet<>();

                for (int row = p.rowStart(r); row < p.rowEnd(r); row++) {
                    for (int k = pointers[row]; k < pointers[row + 1]; k++) {
                        needed.add(columns[k]);

                        if (columns[k] < p.rowStart(r)
                                || columns[k] >= p.rowEnd(r)) {
                            remote.add(columns[k]);
                        }
                    }
                }

                assertEquals(needed.size(), p.neededColumns(r).length);
                assertEquals(remote.size(), p.remoteColumnCount(r));
                assertEquals(8L * remote.size(), p.haloBytes(r));
            }
        }
    }

    @Test
    void neededColumnsAreSortedAndDistinct() {
        SparseMatrixCSR matrix = SpmvStrategyTest.skewed(3_000, 9L);
        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 4);

        for (int r = 0; r < 4; r++) {
            int[] needed = p.neededColumns(r);

            for (int i = 1; i < needed.length; i++) {
                assertTrue(needed[i] > needed[i - 1]);
            }
        }
    }

    @Test
    void haloVolumeNeverExceedsTheAllgatherVolume() {
        SparseMatrixCSR matrix = SpmvStrategyTest.skewed(6_000, 10L);

        for (int ranks : RANKS) {
            DistributedCsrPartition p =
                    DistributedCsrPartition.create(matrix, ranks);

            for (int r = 0; r < ranks; r++) {
                assertTrue(p.haloBytes(r) <= p.allgatherBytes(r));
            }

            assertTrue(p.totalHaloBytes() <= p.totalAllgatherBytes());
        }
    }

    @Test
    void aSingleRankNeedsNoCommunication() {
        SparseMatrixCSR matrix = SpmvStrategyTest.skewed(2_000, 12L);
        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 1);

        assertEquals(0, p.remoteColumnCount(0));
        assertEquals(0L, p.totalHaloBytes());
        assertEquals(0L, p.totalAllgatherBytes());
    }

    @Test
    void aBandedMatrixHasASmallHaloComparedWithAllgather() {
        int n = 50_000;
        double[] values = new double[3 * n];
        int[] columns = new int[3 * n];
        int[] pointers = new int[n + 1];
        int position = 0;

        for (int row = 0; row < n; row++) {
            for (int d = -1; d <= 1; d++) {
                int column = Math.min(n - 1, Math.max(0, row + d));
                columns[position] = column;
                values[position++] = 1.0 + d;
            }
            pointers[row + 1] = position;
        }

        // columns are non-decreasing but may repeat at the borders: use the
        // normalizing public constructor
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                values, columns, pointers, n, n);
        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 16);

        assertTrue(p.totalHaloBytes() * 100 < p.totalAllgatherBytes(),
                "banded halo " + p.totalHaloBytes()
                        + " vs allgather " + p.totalAllgatherBytes());
    }

    @Test
    void moreRanksThanRowsLeavesEmptyRangesAndStillWorks() {
        SparseMatrixCSR matrix = SpmvStrategyTest.uniform(5, 2, 13L);
        double[] x = SpmvStrategyTest.vector(5, 14L);
        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 64);

        int empty = 0;

        for (int r = 0; r < 64; r++) {
            if (p.localRows(r) == 0) {
                empty++;
            }
        }

        assertTrue(empty > 0);

        try (DistributedSpmvSimulation simulation =
                     new DistributedSpmvSimulation(p)) {
            assertBitwiseEqual(matrix.multiply(x), simulation.multiply(x));
        }
    }

    @Test
    void emptyMatrixWorks() {
        SparseMatrixCSR matrix = new SparseMatrixCSR(
                new double[0], new int[0], new int[] {0}, 0, 0);
        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 4);

        try (DistributedSpmvSimulation simulation =
                     new DistributedSpmvSimulation(p)) {
            assertEquals(0, simulation.multiply(new double[0]).length);
        }
    }

    @Test
    void inPlaceAndRepeatedMultiplicationsAreCorrect() {
        SparseMatrixCSR matrix = SpmvStrategyTest.skewed(4_000, 15L);
        double[] x = SpmvStrategyTest.vector(4_000, 16L);
        double[] expected = matrix.multiply(x);

        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 5);

        try (DistributedSpmvSimulation simulation =
                     new DistributedSpmvSimulation(p)) {
            double[] aliased = x.clone();
            simulation.multiplyInto(aliased, aliased);
            assertBitwiseEqual(expected, aliased);

            for (int i = 0; i < 20; i++) {
                assertBitwiseEqual(expected, simulation.multiply(x));
            }

            assertEquals(p.totalHaloBytes(), simulation.lastHaloBytes());
            assertEquals(p.totalAllgatherBytes(),
                    simulation.lastAllgatherBytes());
        }
    }

    @Test
    void nonSquareMatricesAndInvalidArgumentsAreRejected() {
        SparseMatrixCSR rectangular = new SparseMatrixCSR(
                new double[] {1.0}, new int[] {0}, new int[] {0, 1, 1}, 2, 3);
        SparseMatrixCSR square = SpmvStrategyTest.uniform(10, 2, 17L);

        assertThrows(IllegalArgumentException.class,
                () -> DistributedCsrPartition.create(rectangular, 2));
        assertThrows(IllegalArgumentException.class,
                () -> DistributedCsrPartition.create(square, 0));
        assertThrows(NullPointerException.class,
                () -> DistributedCsrPartition.create(null, 2));
        assertThrows(NullPointerException.class,
                () -> new DistributedSpmvSimulation(null));

        DistributedCsrPartition p = DistributedCsrPartition.create(square, 2);

        assertThrows(IllegalArgumentException.class, () -> p.rowStart(-1));
        assertThrows(IllegalArgumentException.class, () -> p.rowEnd(2));

        try (DistributedSpmvSimulation simulation =
                     new DistributedSpmvSimulation(p)) {
            assertThrows(IllegalArgumentException.class,
                    () -> simulation.multiply(new double[9]));
            assertThrows(NullPointerException.class,
                    () -> simulation.multiplyInto(null, new double[10]));
        }
    }

    @Test
    void closedSimulationRejectsMultiplication() {
        SparseMatrixCSR matrix = SpmvStrategyTest.uniform(100, 2, 18L);
        DistributedSpmvSimulation simulation = new DistributedSpmvSimulation(
                DistributedCsrPartition.create(matrix, 3));

        simulation.close();

        assertTrue(simulation.isClosed());
        assertThrows(IllegalStateException.class,
                () -> simulation.multiply(new double[100]));
    }

    @Test
    void neededColumnsAreDefensivelyCopied() {
        SparseMatrixCSR matrix = SpmvStrategyTest.uniform(100, 2, 19L);
        DistributedCsrPartition p = DistributedCsrPartition.create(matrix, 2);

        int[] first = p.neededColumns(0);
        int original = first[0];
        Arrays.fill(first, -1);

        assertEquals(original, p.neededColumns(0)[0]);
    }
}
