package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SpmvPlanTest {

    private static final int THRESHOLD = 4096;
    private static final int PARALLELISM = 4;
    private static final int TEN_MILLION = 10_000_000;
    private static final int PARALLELISM_664 = 664;

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

        assertEquals(
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD,
                plan.getThresholdMode()
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

        assertEquals(
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD,
                plan.getThresholdMode()
        );

        assertEquals(2, plan.getPartitionCount());
    }

    @Test
    void shouldCreatePlanWithExplicitRowThresholdMode() {
        SpmvPlan plan = SpmvPlan.create(
                ROW_POINTERS.clone(),
                2,
                2,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD
        );

        assertEquals(
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                plan.getThresholdMode()
        );

        assertEquals(2, plan.getThreshold());
    }

    @Test
    void shouldCreatePlanWithExplicitNnzThresholdMode() {
        SpmvPlan plan = SpmvPlan.create(
                ROW_POINTERS.clone(),
                2,
                2,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        assertEquals(
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD,
                plan.getThresholdMode()
        );
    }

    @Test
    void shouldCreatePlanWithExplicitSplitPolicyAndThresholdMode() {
        SpmvPlan plan = SpmvPlan.create(
                ROW_POINTERS.clone(),
                2,
                2,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD
        );

        assertEquals(
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                plan.getSplitPolicy()
        );

        assertEquals(
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                plan.getThresholdMode()
        );
    }

    @Test
    void shouldPartitionAllRowsIntoContiguousNonEmptyIntervals() {
        SpmvPlan plan = createPlan();

        assertCompletePartitionCoverage(plan);

        assertEquals(
                plan.getPartitionCount(),
                plan.getStartRows().length
        );

        assertEquals(
                plan.getPartitionCount(),
                plan.getEndRows().length
        );
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
        int[] rowPointers = {0, 5};

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                THRESHOLD,
                16
        );

        assertEquals(1, plan.getPartitionCount());
        assertEquals(0, plan.getStartRow(0));
        assertEquals(1, plan.getEndRow(0));
        assertEquals(5, plan.getPartitionNnz(0, rowPointers));
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

        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldCreateNonEmptyPartitionsForRowsWithZeroNnz() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 0, 0, 0, 0, 0},
                THRESHOLD,
                5
        );

        assertEquals(5, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);
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

        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldPreserveContiguousCoverageForSkewedRows() {
        SpmvPlan plan = SpmvPlan.create(
                new int[]{0, 1, 2, 3, 4, 100, 101, 102, 103},
                1,
                4
        );

        assertCompletePartitionCoverage(plan);
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
        assertCompletePartitionCoverage(plan);
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

        long totalPartitionNnz = 0L;

        for (int i = 0; i < plan.getPartitionCount(); i++) {
            totalPartitionNnz +=
                    plan.getPartitionNnz(i, rowPointers);
        }

        assertEquals(8L, totalPartitionNnz);
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

        assertTrue(plan.isCompatibleWith(ROW_POINTERS.clone()));
        assertTrue(plan.isCompatible(ROW_POINTERS.clone()));

        assertTrue(
                plan.isCompatible(
                        4,
                        8,
                        ROW_POINTERS.clone()
                )
        );

        assertFalse(plan.isCompatibleWith(SKEWED_ROW_POINTERS));

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

        assertTrue(plan.isCompatibleWith(ROW_POINTERS));
        assertFalse(plan.isCompatibleWith(source));
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

        assertArrayEquals(expectedStarts, plan.getStartRows());
        assertArrayEquals(expectedEnds, plan.getEndRows());
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
        assertCompletePartitionCoverage(plan);
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
    void shouldRejectNullThresholdMode() {
        assertThrows(
                NullPointerException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        THRESHOLD,
                        PARALLELISM,
                        (MultiplyTask.ThresholdMode) null
                )
        );
    }

    @Test
    void shouldRejectNullThresholdModeWithExplicitSplitPolicy() {
        assertThrows(
                NullPointerException.class,
                () -> SpmvPlan.create(
                        ROW_POINTERS,
                        THRESHOLD,
                        PARALLELISM,
                        MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                        null
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
    void shouldAcceptTenMillionThresholdInNnzMode() {
        int[] rowPointers = createUniformRowPointers(1_000, 10);

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                TEN_MILLION,
                PARALLELISM_664,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        assertEquals(TEN_MILLION, plan.getThreshold());
        assertEquals(PARALLELISM_664, plan.getParallelism());

        assertEquals(
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD,
                plan.getThresholdMode()
        );

        assertEquals(PARALLELISM_664, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldAcceptTenMillionThresholdInRowMode() {
        int[] rowPointers = createUniformRowPointers(1_000, 10);

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                TEN_MILLION,
                PARALLELISM_664,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD
        );

        assertEquals(TEN_MILLION, plan.getThreshold());

        assertEquals(
                MultiplyTask.ThresholdMode.ROW_THRESHOLD,
                plan.getThresholdMode()
        );

        assertEquals(PARALLELISM_664, plan.getParallelism());
        assertEquals(PARALLELISM_664, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldAcceptParallelism664WhenRowsAreFewerThanRequestedWorkers() {
        int[] rowPointers = createUniformRowPointers(100, 2);

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                THRESHOLD,
                PARALLELISM_664
        );

        assertEquals(PARALLELISM_664, plan.getParallelism());
        assertEquals(100, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldCreate664PartitionsWhenAtLeast664RowsExist() {
        int[] rowPointers = createUniformRowPointers(1_000, 1);

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                THRESHOLD,
                PARALLELISM_664
        );

        assertEquals(PARALLELISM_664, plan.getPartitionCount());
        assertEquals(PARALLELISM_664, plan.getParallelism());
        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldPreserveAllNnzWith664PartitionsAndSkewedRows() {
        int rows = 1_000;
        int[] rowPointers = new int[rows + 1];

        for (int row = 0; row < rows; row++) {
            int rowNnz = row < 900 ? 1 : 100;
            rowPointers[row + 1] = rowPointers[row] + rowNnz;
        }

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                TEN_MILLION,
                PARALLELISM_664,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        assertEquals(PARALLELISM_664, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);

        long assignedNnz = 0L;

        for (int partition = 0;
             partition < plan.getPartitionCount();
             partition++) {

            assignedNnz += plan.getPartitionNnz(
                    partition,
                    rowPointers
            );
        }

        assertEquals(plan.getNnz(), assignedNnz);
    }

    @Test
    void shouldKeepPlanSnapshotIndependentAfterSourceMutation() {
        int[] source = createUniformRowPointers(100, 3);
        int[] original = source.clone();

        SpmvPlan plan = SpmvPlan.create(
                source,
                100,
                8
        );

        source[10] = source[9];

        assertTrue(plan.isCompatibleWith(original));
        assertFalse(plan.isCompatibleWith(source));
    }

    @Test
    void shouldRejectPartitionNnzWhenCandidateHasSameTotalsButDifferentRows() {
        int[] original = {0, 1, 3, 6, 8};
        int[] different = {0, 2, 3, 5, 8};

        SpmvPlan plan = SpmvPlan.create(
                original,
                2,
                2
        );

        assertEquals(original[4], different[4]);

        assertThrows(
                IllegalArgumentException.class,
                () -> plan.getPartitionNnz(0, different)
        );
    }

    @Test
    void shouldHandleThresholdLargerThanTotalNnz() {
        int[] rowPointers = {0, 1, 2, 3, 4, 5};

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                TEN_MILLION,
                4,
                MultiplyTask.ThresholdMode.NNZ_THRESHOLD
        );

        assertEquals(5, plan.getNnz());
        assertEquals(TEN_MILLION, plan.getThreshold());
        assertEquals(4, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldHandleThresholdLargerThanRowCount() {
        int[] rowPointers = {0, 10, 20, 30, 40, 50};

        SpmvPlan plan = SpmvPlan.create(
                rowPointers,
                TEN_MILLION,
                4,
                MultiplyTask.ThresholdMode.ROW_THRESHOLD
        );

        assertEquals(5, plan.getRows());
        assertEquals(TEN_MILLION, plan.getThreshold());
        assertEquals(4, plan.getPartitionCount());
        assertCompletePartitionCoverage(plan);
    }

    @Test
    void shouldRejectPartitionNnzForInvalidPartitionIndexBeforeReadingStructure() {
        SpmvPlan plan = createPlan();

        assertThrows(
                IndexOutOfBoundsException.class,
                () -> plan.getPartitionNnz(-1, ROW_POINTERS)
        );
    }

    @Test
    void toStringShouldDescribePlanMetadata() {
        SpmvPlan plan = createPlan();

        String description = plan.toString();

        assertNotNull(description);
        assertTrue(description.contains("rows=4"));
        assertTrue(description.contains("nnz=8"));
        assertTrue(description.contains("threshold=4096"));
        assertTrue(description.contains("thresholdMode=NNZ_THRESHOLD"));
        assertTrue(description.contains("parallelism=4"));
        assertTrue(description.contains("partitionCount=4"));
    }

    private static int[] createUniformRowPointers(
            int rows,
            int nnzPerRow) {

        int[] rowPointers = new int[rows + 1];

        for (int row = 0; row < rows; row++) {
            rowPointers[row + 1] =
                    rowPointers[row] + nnzPerRow;
        }

        return rowPointers;
    }

    private static void assertCompletePartitionCoverage(
            SpmvPlan plan) {

        if (plan.getRows() == 0) {
            assertEquals(0, plan.getPartitionCount());
            return;
        }

        assertTrue(plan.getPartitionCount() > 0);
        assertEquals(0, plan.getStartRow(0));

        assertEquals(
                plan.getRows(),
                plan.getEndRow(plan.getPartitionCount() - 1)
        );

        int expectedStart = 0;

        for (int partition = 0;
             partition < plan.getPartitionCount();
             partition++) {

            int start = plan.getStartRow(partition);
            int end = plan.getEndRow(partition);

            assertEquals(expectedStart, start);
            assertTrue(start < end);
            assertTrue(end <= plan.getRows());

            expectedStart = end;
        }

        assertEquals(plan.getRows(), expectedStart);
    }
}
