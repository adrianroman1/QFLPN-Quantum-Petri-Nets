package hpc.csr;

import static org.junit.jupiter.api.Assertions.*;

import java.util.HashSet;
import java.util.Set;

import org.junit.jupiter.api.Test;

class BenchmarkV3RunnerTest {

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
            String workloadId, int expectedPerRow) {
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
                            workloadId, 128).matrix();

            int[] columns = matrix.getColumnIndices();
            int[] pointers = matrix.getRowPointers();

            for (int row = 0; row < matrix.getRows(); row++) {
                Set<Integer> rowColumns = new HashSet<>();

                for (int i = pointers[row]; i < pointers[row + 1]; i++) {
                    assertTrue(
                            rowColumns.add(columns[i]),
                            "Duplicate column in " + workloadId
                                    + " row " + row);
                }
            }
        }
    }

    @Test
    void bothPoliciesMatchIndependentCsrOracle() {
        BenchmarkV3Runner.Workload workload =
                BenchmarkV3Runner.generateWorkload("POWERLAW", 128);

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
                    input, parallel, 16, 4, policy);

            assertTrue(
                    BenchmarkV3Runner.maxAbsoluteError(parallel, oracle)
                            <= 1.0e-12,
                    "Oracle mismatch for " + policy);
            assertTrue(
                    BenchmarkV3Runner.maxAbsoluteError(
                            sequential, parallel) <= 1.0e-12,
                    "Sequential/parallel mismatch for " + policy);
        }
    }

    @Test
    void executeOneRecordsTheActuallySelectedSplitPolicy() {
        BenchmarkV3Runner.Workload workload =
                BenchmarkV3Runner.generateWorkload("UNIFORM_2", 128);

        String[] scan = BenchmarkV3Runner.executeOne(
                workload,
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN,
                2,
                16,
                0,
                2,
                "test-run-scan",
                "12345",
                "0123456789abcdef0123456789abcdef01234567");

        String[] binary = BenchmarkV3Runner.executeOne(
                workload,
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT,
                2,
                16,
                0,
                2,
                "test-run-binary",
                "12345",
                "0123456789abcdef0123456789abcdef01234567");

        assertEquals(
                MultiplyTask.SplitPolicy.ROW_BOUNDARY_SCAN.name(),
                scan[16]);
        assertEquals(
                MultiplyTask.SplitPolicy.BINARY_NNZ_SPLIT.name(),
                binary[16]);

        // CSV index 43 is status; index 44 is verdict.
        assertEquals("PASS", scan[43]);
        assertEquals("PASS", binary[43]);

        assertEquals(46, scan.length);
        assertEquals(46, binary.length);
    }

    private static double[] independentReference(
            SparseMatrixCSR matrix, double[] input) {
        double[] values = matrix.getValues();
        int[] columns = matrix.getColumnIndices();
        int[] pointers = matrix.getRowPointers();
        double[] result = new double[matrix.getRows()];

        for (int row = 0; row < result.length; row++) {
            double sum = 0.0;
            for (int i = pointers[row]; i < pointers[row + 1]; i++) {
                sum += values[i] * input[columns[i]];
            }
            result[row] = sum;
        }
        return result;
    }

    @Test
    void statisticsAreCorrectForKnownSamples() {
        double[] samples = {1.0, 2.0, 3.0, 4.0};

        assertEquals(2.5, BenchmarkV3Runner.mean(samples), 1.0e-12);
        assertEquals(2.5, BenchmarkV3Runner.median(samples), 1.0e-12);
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

    @Test
    void generatorRejectsUnknownWorkloadAndInvalidDimension() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateWorkload("UNKNOWN", 128));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateWorkload("UNIFORM_2", 0));
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
                        "UNIFORM_20", 128).family());

        assertEquals(
                "BANDED",
                BenchmarkV3Runner.generateWorkload(
                        "BANDED", 128).family());

        assertEquals(
                "BLOCK_DIAGONAL",
                BenchmarkV3Runner.generateWorkload(
                        "BLOCK", 128).family());

        assertEquals(
                "POWER_LAW",
                BenchmarkV3Runner.generateWorkload(
                        "POWERLAW", 128).family());

        assertEquals(
                "DETERMINISTIC_INVERSE_SQRT",
                BenchmarkV3Runner.generateWorkload(
                        "POWERLAW", 128).distribution());
    }
}
