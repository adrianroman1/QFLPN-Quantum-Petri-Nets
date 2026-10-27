package hpc.csr;

import static org.junit.jupiter.api.Assertions.*;

import java.util.HashSet;
import java.util.Set;

import org.junit.jupiter.api.Test;

class BenchmarkV3RunnerTest {

    private static final String TEST_RUN_ID = "test-run";
    private static final String TEST_WORKFLOW_RUN_ID = "12345";
    private static final String TEST_COMMIT_SHA =
            "0123456789abcdef0123456789abcdef01234567";

    // ------------------------------------------------------------
    // Configuration matrix
    // ------------------------------------------------------------

    @Test
    void configurationMatrixContainsExactlyOneHundredNinetyTwoCases() {
        assertEquals(192, BenchmarkV3Runner.configurationCount());
        assertEquals(96, BenchmarkV3Runner.legacyConfigurationCount());

        Set<String> keys = new HashSet<>();

        for (String workload : BenchmarkV3Runner.WORKLOADS) {
            for (MultiplyTask.SplitPolicy policy
                    : BenchmarkV3Runner.SPLIT_POLICIES) {
                for (int parallelism : BenchmarkV3Runner.PARALLELISMS) {
                    for (int threshold : BenchmarkV3Runner.THRESHOLDS) {
                        assertTrue(keys.add(
                                workload + "|" + policy.name()
                                        + "|" + parallelism + "|" + threshold));
                    }
                }
            }
        }

        assertEquals(192, keys.size());
    }

    @Test
    void bothSplitPoliciesArePresentExactlyOnceInPolicyArray() {
        assertEquals(2, BenchmarkV3Runner.SPLIT_POLICIES.length);

        assertEquals(
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                BenchmarkV3Runner.SPLIT_POLICIES[0]);

        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                BenchmarkV3Runner.SPLIT_POLICIES[1]);
    }

    // ------------------------------------------------------------
    // Workload generation
    // ------------------------------------------------------------

    @Test
    void workloadGeneratorCreatesAllSixFamilies() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            BenchmarkV3Runner.Workload workload =
                    BenchmarkV3Runner.generateWorkload(workloadId, 128);

            assertNotNull(workload);
            assertEquals(workloadId, workload.id());
            assertEquals(128, workload.matrix().getRows());
            assertEquals(128, workload.matrix().getColumns());
            assertTrue(workload.matrix().isValid());
            assertTrue(workload.matrix().getNnz() > 0);
            assertTrue(workload.minNnz() >= 0);
            assertTrue(workload.averageNnz() >= workload.minNnz());
            assertTrue(workload.maxNnz() >= workload.averageNnz());
        }
    }

    @Test
    void fixedDensityWorkloadsHaveExactNnzPerRow() {
        assertFixedDensity("UNIFORM_2", 2);
        assertFixedDensity("UNIFORM_20", 20);
        assertFixedDensity("UNIFORM_100", 100);
    }

    private static void assertFixedDensity(
            String workloadId,
            int expectedPerRow) {

        BenchmarkV3Runner.Workload workload =
                BenchmarkV3Runner.generateWorkload(workloadId, 128);

        assertEquals(
                128 * expectedPerRow,
                workload.matrix().getNnz());

        assertEquals(expectedPerRow, workload.minNnz());
        assertEquals(expectedPerRow, workload.maxNnz());

        assertEquals(
                expectedPerRow,
                workload.averageNnz(),
                1.0e-12);
    }

    @Test
    void generatedRowsContainNoDuplicateColumnIndices() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            SparseMatrixCSR matrix =
                    BenchmarkV3Runner.generateWorkload(
                            workloadId,
                            128).matrix();

            int[] columns = matrix.getColumnIndices();
            int[] pointers = matrix.getRowPointers();

            for (int row = 0; row < matrix.getRows(); row++) {
                Set<Integer> rowColumns = new HashSet<>();

                for (int i = pointers[row];
                        i < pointers[row + 1];
                        i++) {

                    assertTrue(
                            rowColumns.add(columns[i]),
                            "Duplicate column in "
                                    + workloadId
                                    + " row "
                                    + row);
                }
            }
        }
    }

    @Test
    void generatedWorkloadsHaveConsistentCsrStructure() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            SparseMatrixCSR matrix =
                    BenchmarkV3Runner.generateWorkload(
                            workloadId,
                            128).matrix();

            int[] pointers = matrix.getRowPointers();
            int[] columns = matrix.getColumnIndices();
            double[] values = matrix.getValues();

            assertEquals(129, pointers.length);
            assertEquals(matrix.getNnz(), columns.length);
            assertEquals(matrix.getNnz(), values.length);

            assertEquals(0, pointers[0]);
            assertEquals(matrix.getNnz(), pointers[128]);

            for (int row = 0; row < matrix.getRows(); row++) {
                assertTrue(pointers[row] <= pointers[row + 1]);

                int previousColumn = -1;

                for (int i = pointers[row];
                        i < pointers[row + 1];
                        i++) {

                    assertTrue(columns[i] > previousColumn);
                    assertTrue(columns[i] >= 0);
                    assertTrue(columns[i] < matrix.getColumns());
                    assertTrue(Double.isFinite(values[i]));

                    previousColumn = columns[i];
                }
            }
        }
    }

    // ------------------------------------------------------------
    // Trusted workload factory
    // ------------------------------------------------------------

    @Test
    void trustedFactoryAcceptsMatchingPreflight() {
        String workloadId = "UNIFORM_2";
        int dimension = 128;

        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        workloadId,
                        dimension);

        BenchmarkV3Runner.Workload workload =
                BenchmarkV3Runner.generateTrustedWorkload(
                        workloadId,
                        dimension,
                        preflight);

        assertNotNull(workload);
        assertEquals(workloadId, workload.id());
        assertEquals(dimension, workload.matrix().getRows());
        assertTrue(workload.matrix().isValid());

        assertEquals(
                preflight.nonZeroCount(),
                workload.matrix().getNnz());
    }

    @Test
    void trustedFactoryRejectsNullPreflight() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateTrustedWorkload(
                        "UNIFORM_2",
                        128,
                        null));
    }

    @Test
    void trustedFactoryRejectsMismatchedWorkload() {
        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_2",
                        128);

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateTrustedWorkload(
                        "UNIFORM_20",
                        128,
                        preflight));
    }

    @Test
    void trustedFactoryRejectsMismatchedDimension() {
        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_2",
                        128);

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateTrustedWorkload(
                        "UNIFORM_2",
                        256,
                        preflight));
    }

    @Test
    void compatibilityGeneratorProducesSameNnzAsTrustedFactory() {
        String workloadId = "UNIFORM_20";
        int dimension = 128;

        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        workloadId,
                        dimension);

        BenchmarkV3Runner.Workload trusted =
                BenchmarkV3Runner.generateTrustedWorkload(
                        workloadId,
                        dimension,
                        preflight);

        BenchmarkV3Runner.Workload compatibility =
                BenchmarkV3Runner.generateWorkload(
                        workloadId,
                        dimension);

        assertEquals(
                trusted.matrix().getNnz(),
                compatibility.matrix().getNnz());

        assertArrayEquals(
                trusted.matrix().getRowPointers(),
                compatibility.matrix().getRowPointers());

        assertArrayEquals(
                trusted.matrix().getColumnIndices(),
                compatibility.matrix().getColumnIndices());

        assertArrayEquals(
                trusted.matrix().getValues(),
                compatibility.matrix().getValues(),
                0.0);
    }

    // ------------------------------------------------------------
    // NNZ calculation and scalability limits
    // ------------------------------------------------------------

    @Test
    void nnzCalculationMatchesAllWorkloadDefinitions() {
        int n = 128;

        assertEquals(
                2L * n,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_2",
                        n));

        assertEquals(
                20L * n,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_20",
                        n));

        assertEquals(
                100L * n,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_100",
                        n));

        assertEquals(
                5L * n,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "BANDED",
                        n));

        assertEquals(
                8L * n,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "BLOCK",
                        n));

        long expectedPowerLawNnz = 0L;

        for (int row = 0; row < n; row++) {
            expectedPowerLawNnz += Math.min(
                    n,
                    1 + (int) (
                            32.0 / Math.sqrt(row + 1.0)));
        }

        assertEquals(
                expectedPowerLawNnz,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "POWERLAW",
                        n));
    }

    @Test
    void nnzCalculationRejectsUnknownWorkload() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.calculateNonZeroCount(
                        "UNKNOWN",
                        128));
    }

    @Test
    void nnzCalculationRejectsDimensionBelowMinimum() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_2",
                        BenchmarkV3Runner.MINIMUM_DIMENSION - 1));
    }

    @Test
    void thirtyMillionUniformHundredIsRejectedBeforeAllocation() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_100",
                        30_000_000));
    }

    @Test
    void oneHundredMillionIsAnAuthorizedTimedScale() {
        assertDoesNotThrow(
                () -> BenchmarkV3Runner.requireTimedBenchmarkDimension(
                        100_000_000));
    }

    @Test
    void correctnessFixtureIsNotAcceptedAsTimedScale() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.requireTimedBenchmarkDimension(12));
    }

    @Test
    void arbitraryDimensionIsNotAcceptedAsTimedScale() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.requireTimedBenchmarkDimension(128));
    }

    @Test
    void historicalDevelopmentDimensionRemainsSupportedForGeneration() {
        assertDoesNotThrow(
                () -> BenchmarkV3Runner.requireSupportedDimension(
                        BenchmarkV3Runner.DIMENSION));
    }

    // ------------------------------------------------------------
    // CSR memory model
    // ------------------------------------------------------------

    @Test
    void csrPayloadEstimateMatchesPrimitiveArrayFormula() {
        int n = 128;
        long nnz = 256L;

        long expected =
                8L * nnz
                        + 4L * nnz
                        + 4L * (n + 1L);

        assertEquals(
                expected,
                BenchmarkV3Runner.estimateCsrPayloadBytes(
                        n,
                        nnz));
    }

    @Test
    void csrPayloadEstimateRejectsInvalidDimensions() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.estimateCsrPayloadBytes(
                        0,
                        10));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.estimateCsrPayloadBytes(
                        10,
                        -1));
    }

    @Test
    void csrPayloadEstimateUsesLongArithmetic() {
        long nnz = 1_000_000_000L;

        long estimate =
                BenchmarkV3Runner.estimateCsrPayloadBytes(
                        100_000_000,
                        nnz);

        assertEquals(
                12_400_000_004L,
                estimate);
    }

    @Test
    void preflightReportsExpectedNnzAndCsrPayload() {
        String workloadId = "UNIFORM_2";
        int n = 128;

        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        workloadId,
                        n);

        assertEquals(workloadId, preflight.workloadId());
        assertEquals(n, preflight.dimension());
        assertEquals(256L, preflight.nonZeroCount());

        assertEquals(
                BenchmarkV3Runner.estimateCsrPayloadBytes(
                        n,
                        256L),
                preflight.csrPayloadBytes());

        assertTrue(preflight.estimatedRequiredBytes() >=
                preflight.csrPayloadBytes());

        assertTrue(preflight.requiredWithHeadroomBytes() >=
                preflight.estimatedRequiredBytes());

        assertTrue(preflight.maximumHeapBytes() > 0L);
        assertTrue(preflight.availableBytes() >= 0L);
    }

    // ------------------------------------------------------------
    // Numerical correctness
    // ------------------------------------------------------------

    @Test
    void bothPoliciesMatchIndependentCsrOracle() {
        BenchmarkV3Runner.Workload workload =
                BenchmarkV3Runner.generateWorkload(
                        "POWERLAW",
                        128);

        SparseMatrixCSR matrix = workload.matrix();

        double[] input = new double[128];
        double[] sequential = new double[128];

        for (int i = 0; i < input.length; i++) {
            input[i] = 0.25 + (i % 17) / 13.0;
        }

        double[] oracle = independentReference(matrix, input);

        matrix.multiplyInto(input, sequential);

        for (MultiplyTask.SplitPolicy policy
                : BenchmarkV3Runner.SPLIT_POLICIES) {

            double[] parallel = new double[128];

            matrix.multiplyParallelInto(
                    input,
                    parallel,
                    16,
                    4,
                    policy);

            assertTrue(
                    BenchmarkV3Runner.maxAbsoluteError(
                            parallel,
                            oracle) <= 1.0e-12,
                    "Oracle mismatch for " + policy);

            assertTrue(
                    BenchmarkV3Runner.maxAbsoluteError(
                            sequential,
                            parallel) <= 1.0e-12,
                    "Sequential/parallel mismatch for " + policy);
        }
    }

    @Test
    void executeOneRecordsTheActuallySelectedSplitPolicy() {
        BenchmarkV3Runner.Workload workload =
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_2",
                        128);

        String[] scan = BenchmarkV3Runner.executeOne(
                workload,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                2,
                16,
                0,
                2,
                "test-run-scan",
                TEST_WORKFLOW_RUN_ID,
                TEST_COMMIT_SHA);

        String[] binary = BenchmarkV3Runner.executeOne(
                workload,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                2,
                16,
                0,
                2,
                "test-run-binary",
                TEST_WORKFLOW_RUN_ID,
                TEST_COMMIT_SHA);

        assertEquals(
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN.name(),
                scan[16]);

        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT.name(),
                binary[16]);

        assertEquals("PASS", scan[43]);
        assertEquals("PASS", binary[43]);

        assertEquals(46, scan.length);
        assertEquals(46, binary.length);

        assertTrue(scan[45].contains("peak_heap_used_bytes="));
        assertTrue(binary[45].contains("peak_heap_used_bytes="));
    }

    private static double[] independentReference(
            SparseMatrixCSR matrix,
            double[] input) {

        double[] values = matrix.getValues();
        int[] columns = matrix.getColumnIndices();
        int[] pointers = matrix.getRowPointers();

        double[] result = new double[matrix.getRows()];

        for (int row = 0; row < result.length; row++) {
            double sum = 0.0;

            for (int i = pointers[row];
                    i < pointers[row + 1];
                    i++) {

                sum += values[i] * input[columns[i]];
            }

            result[row] = sum;
        }

        return result;
    }

    // ------------------------------------------------------------
    // Statistics
    // ------------------------------------------------------------

    @Test
    void statisticsAreCorrectForKnownSamples() {
        double[] samples = {1.0, 2.0, 3.0, 4.0};

        assertEquals(
                2.5,
                BenchmarkV3Runner.mean(samples),
                1.0e-12);

        assertEquals(
                2.5,
                BenchmarkV3Runner.median(samples),
                1.0e-12);

        assertEquals(
                Math.sqrt(1.25),
                BenchmarkV3Runner.populationStdDev(samples),
                1.0e-12);
    }

    @Test
    void statisticsRejectInvalidSamples() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.mean(new double[0]));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.mean(
                        new double[] {1.0, Double.NaN}));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.median(
                        new double[] {1.0, 0.0}));
    }

    // ------------------------------------------------------------
    // Generator validation and workload metadata
    // ------------------------------------------------------------

    @Test
    void generatorRejectsUnknownWorkloadAndInvalidDimension() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateWorkload(
                        "UNKNOWN",
                        128));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_2",
                        0));
    }

    @Test
    void generatorRejectsDimensionsBelowMinimumForEveryWorkload() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            IllegalArgumentException exception = assertThrows(
                    IllegalArgumentException.class,
                    () -> BenchmarkV3Runner.generateWorkload(
                            workloadId,
                            BenchmarkV3Runner.MINIMUM_DIMENSION - 1));

            assertTrue(exception.getMessage().contains("at least 100"));
        }
    }

    @Test
    void generatorAcceptsMinimumSupportedDimension() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            BenchmarkV3Runner.Workload workload =
                    BenchmarkV3Runner.generateWorkload(
                            workloadId,
                            BenchmarkV3Runner.MINIMUM_DIMENSION);

            assertNotNull(workload);

            assertEquals(
                    BenchmarkV3Runner.MINIMUM_DIMENSION,
                    workload.matrix().getRows());

            assertTrue(workload.matrix().isValid());
        }

        BenchmarkV3Runner.Workload uniform100 =
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_100",
                        BenchmarkV3Runner.MINIMUM_DIMENSION);

        assertEquals(
                100 * 100,
                uniform100.matrix().getNnz());
    }

    @Test
    void allWorkloadsHaveExpectedFamilyAndDistributionMetadata() {
        assertEquals(
                "UNIFORM",
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_20",
                        128).family());

        assertEquals(
                "BANDED",
                BenchmarkV3Runner.generateWorkload(
                        "BANDED",
                        128).family());

        assertEquals(
                "BLOCK_DIAGONAL",
                BenchmarkV3Runner.generateWorkload(
                        "BLOCK",
                        128).family());

        assertEquals(
                "POWER_LAW",
                BenchmarkV3Runner.generateWorkload(
                        "POWERLAW",
                        128).family());

        assertEquals(
                "DETERMINISTIC_INVERSE_SQRT",
                BenchmarkV3Runner.generateWorkload(
                        "POWERLAW",
                        128).distribution());
    }
}
