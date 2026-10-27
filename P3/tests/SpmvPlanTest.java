package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SpmvPlanTest {

    private static final int THRESHOLD = 4096;
    private static final int PARALLELISM = 4;

    private static final int[] ROW_POINTERS = {
            0, 2, 4, 6, 8
    };

    private static final int[] SKEWED_ROW_POINTERS = {
            0, 1, 3, 6, 8
    };

    private static SpmvPlan createPlan() {
        return SpmvPlan.create(
                ROW_POINTERS.clone(),
                THRESHOLD,
                PARALLELISM
        );
    }

    @Test
    void shouldCreatePlanWithExpectedMetadata() {
        SpmvPlan plan = createPlan();

        assertEquals(4, plan.getRows());
        assertEquals(8, plan.getNnz());
        assertEquals(THRESHOLD, plan.getThreshold());
        assertEquals(PARALLELISM, plan.getParallelism());

        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                plan.getSplitPolicy()
        );

        assertEquals(4, plan.getPartitionCount());
        assertFalse(plan.isEmpty());
    }

    @Test
    void shouldCreatePlanWithExplicitSplitPolicy() {
        SpmvPlan plan = SpmvPlan.create(
                ROW_POINTERS.clone(),
                2,
                2,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT
        );

        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                plan.getSplitPolicy()
        );

        assertEquals(2, plan.getPartitionCount());
    }

    @Test
    void shouldPartitionAllRowsIntoContiguousNonEmptyIntervals() {
        SpmvPlan plan = createPlan();

        int[] starts = plan.getStartRows();
        int[] ends = plan.getEndRows();

        assertEquals(plan.getPartitionCount(), starts.length);
        assertEquals(plan.getPartitionCount(), ends.length);

        assertEquals(0, starts[0]);
        assertEquals(plan.getRows(), ends[ends.length - 1]);

        for (int i = 0; i < starts.length; i++) {
            assertTrue(starts[i] < ends[i]);

            if (i > 0) {
                assertEquals(ends[i - 1], starts[i]);
            }
        }
    }

    @Test
    void shouldLimitPartitionCountToNumberOfRows() {
        SpmvPlan plan = SpmvPlan.create(
                ROW_POINTERS.clone(),
                THRESHOLD,
                100
        );

        assertEquals(4, plan.getPartitionCount());
    }

    @Test
    void shouldCreateOnePartitionForOneRow() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 5},
                THRESHOLD,
                16
        );

        assertEquals(1, plan.getPartitionCount());
        assertEquals(0, plan.getStartRow(0));
        assertEquals(1, plan.getEndRow(0));
        assertEquals(5, plan.getPartitionNnz(0, new int[]{0, 5}));
    }

    @Test
    void shouldCreateZeroPartitionsForZeroRows() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0},
                THRESHOLD,
                PARALLELISM
        );

        assertEquals(0, plan.getRows());
        assertEquals(0, plan.getNnz());
        assertEquals(0, plan.getPartitionCount());
        assertTrue(plan.isEmpty());
        assertArrayEquals(new int[0], plan.getStartRows());
        assertArrayEquals(new int[0], plan.getEndRows());
    }

    @Test
    void shouldBalanceRowsWhenMatrixHasNoNonZeroElements() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 0, 0, 0, 0, 0, 0, 0, 0},
                THRESHOLD,
                3
        );

        assertEquals(8, plan.getRows());
        assertEquals(0, plan.getNnz());
        assertEquals(3, plan.getPartitionCount());

        assertArrayEquals(
                new int[]{0, 2, 5},
                plan.getStartRows()
        );

        assertArrayEquals(
                new int[]{2, 5, 8},
                plan.getEndRows()
        );
    }

    @Test
    void shouldCreateNonEmptyPartitionsForRowsWithZeroNnz() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 0, 0, 0, 0, 0},
                THRESHOLD,
                5
        );

        assertEquals(5, plan.getPartitionCount());

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            assertTrue(plan.getStartRow(i) < plan.getEndRow(i));
        }
    }

    @Test
    void shouldUseNnzDistributionForPartitionBoundaries() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 1, 2, 3, 4, 5, 6, 7, 8},
                1,
                4
        );

        assertArrayEquals(
                new int[]{0, 2, 4, 6},
                plan.getStartRows()
        );

        assertArrayEquals(
                new int[]{2, 4, 6, 8},
                plan.getEndRows()
        );
    }

    @Test
    void shouldPreserveContiguousCoverageForSkewedRows() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 1, 2, 3, 4, 100, 101, 102, 103},
                1,
                4
        );

        int[] starts = plan.getStartRows();
        int[] ends = plan.getEndRows();

        assertEquals(0, starts[0]);
        assertEquals(8, ends[ends.length - 1]);

        for (int i = 0; i < starts.length; i++) {
            assertTrue(starts[i] < ends[i]);

            if (i > 0) {
                assertEquals(ends[i - 1], starts[i]);
            }
        }
    }

    @Test
    void shouldHandleSingleVeryLargeRowWithoutEmptyPartitions() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 0, 0, 100, 100, 100, 100},
                1,
                4
        );

        assertEquals(4, plan.getPartitionCount());

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            assertTrue(plan.getStartRow(i) < plan.getEndRow(i));
        }

        assertEquals(6, plan.getEndRow(3));
    }

    @Test
    void shouldReturnCorrectNnzCountForEachPartition() {
        int[] rowPointers = {0, 2, 4, 6, 8};

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                THRESHOLD,
                4
        );

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            assertEquals(
                    2,
                    plan.getPartitionNnz(i, rowPointers)
            );
        }
    }

    @Test
    void shouldReturnCorrectNnzCountForUnevenDistribution() {
        int[] rowPointers = {0, 1, 3, 6, 8};

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                1,
                2
        );

        int totalPartitionNnz = 0;

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            totalPartitionNnz +=
                    plan.getPartitionNnz(i, rowPointers);
        }

        assertEquals(8, totalPartitionNnz);
    }

    @Test
    void shouldRejectPartitionNnzForIncompatibleStructure() {
        SpmvPlan plan = createPlan();

        assertThrows(
                IllegalArgumentException.class,
                () -> plan.getPartitionNnz(
                        0,
                        SKEWED_ROW_POINTERS
                )
        );
    }

    @Test
    void shouldCheckExactCsrCompatibility() {
        SpmvPlan plan = createPlan();

        assertTrue(
                plan.isCompatibleWith(ROW_POINTERS.clone())
        );

        assertTrue(
                plan.isCompatible(ROW_POINTERS.clone())
        );

        assertTrue(
                plan.isCompatible(
                        4,
                        8,
                        ROW_POINTERS.clone()
                )
        );

        assertFalse(
                plan.isCompatibleWith(SKEWED_ROW_POINTERS)
        );

        assertFalse(
                plan.isCompatible(
                        4,
                        8,
                        SKEWED_ROW_POINTERS
                )
        );

        assertFalse(
                plan.isCompatible(
                        3,
                        8,
                        ROW_POINTERS
                )
        );

        assertFalse(
                plan.isCompatible(
                        4,
                        7,
                        ROW_POINTERS
                )
        );
    }

    @Test
    void shouldReturnFalseForNullCompatibilityCandidate() {
        SpmvPlan plan = createPlan();

        assertFalse(plan.isCompatibleWith(null));
        assertFalse(plan.isCompatible((int[]) null));
        assertFalse(plan.isCompatible(4, 8, null));
    }

    @Test
    void shouldKeepInternalSnapshotIndependentFromSourceArray() {
        int[] source = ROW_POINTERS.clone();

        SpmvPlan plan = SpmvPlan.create(
                source,
                THRESHOLD,
                PARALLELISM
        );

        source[1] = 0;

        assertTrue(
                plan.isCompatibleWith(ROW_POINTERS)
        );

        assertFalse(
                plan.isCompatibleWith(source)
        );
    }

    @Test
    void shouldReturnDefensiveCopiesOfPartitionBoundaries() {
        SpmvPlan plan = createPlan();

        int[] expectedStarts = plan.getStartRows();
        int[] expectedEnds = plan.getEndRows();

        int[] starts = plan.getStartRows();
        int[] ends = plan.getEndRows();

        starts[0] = -100;
        ends[0] = -100;

        assertArrayEquals(
                expectedStarts,
                plan.getStartRows()
        );

        assertArrayEquals(
                expectedEnds,
                plan.getEndRows()
        );
    }

    @Test
    void shouldExposePartitionBoundariesByIndex() {
        SpmvPlan plan = createPlan();

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            assertEquals(
                    plan.getStartRows()[i],
                    plan.getStartRow(i)
            );

            assertEquals(
                    plan.getEndRows()[i],
                    plan.getEndRow(i)
            );
        }
    }

    @Test
    void shouldRejectInvalidPartitionIndexes() {
        SpmvPlan plan = createPlan();

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> plan.getStartRow(-1)
        );

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> plan.getEndRow(-1)
        );

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> plan.getStartRow(plan.getPartitionCount())
        );

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> plan.getEndRow(plan.getPartitionCount())
        );

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> plan.getPartitionNnz(
                        plan.getPartitionCount(),
                        ROW_POINTERS
                )
        );
    }

    @Test
    void shouldRejectNullRowPointers() {
        assertThrows(
                NullPointerException.class,
                () -> SpmvPlan.create(
                        null,
                        THRESHOLD,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldRejectEmptyRowPointerArray() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        new int[0],
                        THRESHOLD,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldRejectRowPointersNotStartingAtZero() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        new int[]{1, 2, 3},
                        THRESHOLD,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldRejectNegativeRowPointerValues() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        new int[]{0, -1, 2},
                        THRESHOLD,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldRejectDecreasingRowPointers() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        new int[]{0, 3, 2, 4},
                        THRESHOLD,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldAcceptRepeatedRowPointersForEmptyRows() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 0, 2, 2, 2, 5},
                1,
                3
        );

        assertEquals(5, plan.getRows());
        assertEquals(5, plan.getNnz());

        assertEquals(0, plan.getStartRow(0));
        assertEquals(5, plan.getEndRow(2));
    }

    @Test
    void shouldRejectZeroThreshold() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        0,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldRejectNegativeThreshold() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        -1,
                        PARALLELISM
                )
        );
    }

    @Test
    void shouldRejectZeroParallelism() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        THRESHOLD,
                        0
                )
        );
    }

    @Test
    void shouldRejectNegativeParallelism() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        THRESHOLD,
                        -1
                )
        );
    }

    @Test
    void shouldRejectNullSplitPolicy() {
        assertThrows(
                NullPointerException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        THRESHOLD,
                        PARALLELISM,
                        (MultiplyTask.SplitPolicy) null
                )
        );
    }

    @Test
    void shouldUseLongArithmeticForNnzPartitionTargets() {
        int[] rowPointers = {
                0,
                500_000_000,
                1_000_000_000,
                1_500_000_000,
                2_000_000_000
        };

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                1,
                4
        );

        assertEquals(2_000_000_000, plan.getNnz());
        assertEquals(4, plan.getPartitionCount());

        assertArrayEquals(
                new int[]{0, 1, 2, 3},
                plan.getStartRows()
        );

        assertArrayEquals(
                new int[]{1, 2, 3, 4},
                plan.getEndRows()
        );
    }

    @Test
    void shouldPreserveTotalNnzAcrossAllPartitions() {
        int[] rowPointers = {
                0,
                10,
                30,
                60,
                100,
                150,
                210
        };

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                1,
                3
        );

        long totalNnz = 0L;

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            totalNnz += plan.getPartitionNnz(i, rowPointers);
        }

        assertEquals(plan.getNnz(), totalNnz);
    }

    @Test
    void toStringShouldDescribePlanMetadata() {
        SpmvPlan plan = createPlan();

        String description = plan.toString();

        assertNotNull(description);
        assertTrue(description.contains("rows=4"));
        assertTrue(description.contains("nnz=8"));
        assertTrue(description.contains("threshold=4096"));
        assertTrue(description.contains("parallelism=4"));
        assertTrue(description.contains("partitionCount=4"));
    }
}
