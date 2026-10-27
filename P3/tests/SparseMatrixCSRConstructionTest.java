package hpc.csr;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class SparseMatrixCSRConstructionTest {

    private static final int N = 128;

    // ------------------------------------------------------------
    // Public CSR constructor
    // ------------------------------------------------------------

    @Test
    void constructorCreatesValidCanonicalMatrix() {
        double[] values = {2.0, 3.0, 4.0, 5.0};
        int[] columns = {0, 2, 1, 3};
        int[] pointers = {0, 2, 4};

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(values, columns, pointers, 2, 4);

        assertTrue(matrix.isValid());
        assertEquals(2, matrix.getRows());
        assertEquals(4, matrix.getColumns());
        assertEquals(4, matrix.getNnz());

        assertArrayEquals(
                new int[] {0, 2, 1, 3},
                matrix.getColumnIndices());
    }

    @Test
    void constructorSortsColumnsWithinEachRow() {
        double[] values = {5.0, 2.0, 4.0, 3.0};
        int[] columns = {3, 0, 2, 1};
        int[] pointers = {0, 2, 4};

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(values, columns, pointers, 2, 4);

        assertArrayEquals(
                new int[] {0, 3, 1, 2},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {2.0, 5.0, 3.0, 4.0},
                matrix.getValues(),
                0.0);

        assertTrue(matrix.isValid());
    }

    @Test
    void constructorAggregatesDuplicateColumnsAdditively() {
        double[] values = {2.0, 3.0, 4.0, 5.0};
        int[] columns = {1, 1, 2, 1};
        int[] pointers = {0, 3, 4};

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(values, columns, pointers, 2, 3);

        assertEquals(3, matrix.getNnz());

        assertArrayEquals(
                new int[] {1, 2, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new double[] {5.0, 4.0, 5.0},
                matrix.getValues(),
                0.0);

        assertEquals(5.0, matrix.get(0, 1), 0.0);
        assertEquals(4.0, matrix.get(0, 2), 0.0);
        assertEquals(5.0, matrix.get(1, 1), 0.0);
    }

    @Test
    void constructorPreservesEmptyRows() {
        double[] values = {2.0, 3.0};
        int[] columns = {0, 2};
        int[] pointers = {0, 1, 1, 2};

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(values, columns, pointers, 3, 3);

        assertArrayEquals(
                new int[] {0, 1, 1, 2},
                matrix.getRowPointers());

        assertEquals(2, matrix.getNnz());
        assertTrue(matrix.isValid());
    }

    @Test
    void constructorDefensivelyCopiesInputArrays() {
        double[] values = {2.0, 3.0};
        int[] columns = {0, 1};
        int[] pointers = {0, 1, 2};

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(values, columns, pointers, 2, 2);

        values[0] = 99.0;
        columns[0] = 1;
        pointers[1] = 2;

        assertArrayEquals(
                new double[] {2.0, 3.0},
                matrix.getValues(),
                0.0);

        assertArrayEquals(
                new int[] {0, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 1, 2},
                matrix.getRowPointers());
    }

    @Test
    void constructorRejectsNullValues() {
        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        null,
                        new int[0],
                        new int[] {0},
                        0,
                        0));
    }

    @Test
    void constructorRejectsNullColumnIndices() {
        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        new double[0],
                        null,
                        new int[] {0},
                        0,
                        0));
    }

    @Test
    void constructorRejectsNullRowPointers() {
        assertThrows(
                NullPointerException.class,
                () -> new SparseMatrixCSR(
                        new double[0],
                        new int[0],
                        null,
                        0,
                        0));
    }

    @Test
    void constructorRejectsMismatchedValuesAndColumns() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[0],
                        new int[] {0, 1},
                        1,
                        1));
    }

    @Test
    void constructorRejectsInvalidRowPointerLength() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0},
                        1,
                        1));
    }

    @Test
    void constructorRejectsNonzeroFirstRowPointer() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {1, 1},
                        1,
                        1));
    }

    @Test
    void constructorRejectsDecreasingRowPointers() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 1, 0},
                        2,
                        1));
    }

    @Test
    void constructorRejectsLastPointerDifferentFromNnz() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 0},
                        1,
                        1));
    }

    @Test
    void constructorRejectsOutOfRangeColumn() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {2},
                        new int[] {0, 1},
                        1,
                        2));
    }

    @Test
    void constructorRejectsNonFiniteValues() {
        for (double invalid : new double[] {
                Double.NaN,
                Double.POSITIVE_INFINITY,
                Double.NEGATIVE_INFINITY
        }) {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> new SparseMatrixCSR(
                            new double[] {invalid},
                            new int[] {0},
                            new int[] {0, 1},
                            1,
                            1));
        }
    }

    @Test
    void constructorRejectsNegativeDimensions() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        -1,
                        0));

        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        0,
                        -1));
    }

    @Test
    void constructorRejectsDuplicateAggregationOverflow() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SparseMatrixCSR(
                        new double[] {
                                Double.MAX_VALUE,
                                Double.MAX_VALUE
                        },
                        new int[] {0, 0},
                        new int[] {0, 2},
                        1,
                        1));
    }

    // ------------------------------------------------------------
    // Trusted canonical factory
    // ------------------------------------------------------------

    @Test
    void trustedFactoryAcceptsCanonicalCsr() {
        double[] values = {2.0, 3.0, 4.0};
        int[] columns = {0, 2, 1};
        int[] pointers = {0, 2, 3};

        SparseMatrixCSR matrix =
                SparseMatrixCSR.fromTrustedCanonical(
                        values,
                        columns,
                        pointers,
                        2,
                        3);

        assertTrue(matrix.isValid());
        assertEquals(3, matrix.getNnz());

        assertArrayEquals(
                new double[] {2.0, 3.0, 4.0},
                matrix.getValues(),
                0.0);

        assertArrayEquals(
                new int[] {0, 2, 1},
                matrix.getColumnIndices());

        assertArrayEquals(
                new int[] {0, 2, 3},
                matrix.getRowPointers());
    }

    @Test
    void trustedFactoryRejectsUnsortedColumns() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {2.0, 3.0},
                        new int[] {2, 1},
                        new int[] {0, 2},
                        1,
                        3));
    }

    @Test
    void trustedFactoryRejectsDuplicateColumns() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {2.0, 3.0},
                        new int[] {1, 1},
                        new int[] {0, 2},
                        1,
                        3));
    }

    @Test
    void trustedFactoryRejectsNonFiniteValues() {
        assertThrows(
                IllegalArgumentException.class,
                () -> SparseMatrixCSR.fromTrustedCanonical(
                        new double[] {Double.NaN},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1));
    }

    // ------------------------------------------------------------
    // V3 workload generation
    // ------------------------------------------------------------

    @Test
    void allSixWorkloadsGenerateValidCsrMatrices() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            BenchmarkV3Runner.Workload workload =
                    BenchmarkV3Runner.generateWorkload(
                            workloadId,
                            N);

            assertNotNull(workload);
            assertEquals(workloadId, workload.id());
            assertEquals(N, workload.matrix().getRows());
            assertEquals(N, workload.matrix().getColumns());
            assertTrue(workload.matrix().isValid());
            assertTrue(workload.matrix().getNnz() > 0);
        }
    }

    @Test
    void fixedDensityWorkloadsHaveExpectedNnz() {
        assertEquals(
                2L * N,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_2",
                        N));

        assertEquals(
                20L * N,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_20",
                        N));

        assertEquals(
                100L * N,
                BenchmarkV3Runner.calculateNonZeroCount(
                        "UNIFORM_100",
                        N));
    }

    @Test
    void generatedFixedDensityMatricesHaveExactNnz() {
        assertEquals(
                2 * N,
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_2",
                        N).matrix().getNnz());

        assertEquals(
                20 * N,
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_20",
                        N).matrix().getNnz());

        assertEquals(
                100 * N,
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_100",
                        N).matrix().getNnz());
    }

    @Test
    void generatedRowsHaveStrictlyIncreasingColumnIndices() {
        for (String workloadId : BenchmarkV3Runner.WORKLOADS) {
            SparseMatrixCSR matrix =
                    BenchmarkV3Runner.generateWorkload(
                            workloadId,
                            N).matrix();

            int[] columns = matrix.getColumnIndices();
            int[] pointers = matrix.getRowPointers();

            for (int row = 0; row < N; row++) {
                int previous = -1;

                for (int index = pointers[row];
                     index < pointers[row + 1];
                     index++) {

                    assertTrue(
                            columns[index] > previous,
                            workloadId + " row " + row);

                    previous = columns[index];
                }
            }
        }
    }

    @Test
    void generatorRejectsUnknownWorkload() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateWorkload(
                        "UNKNOWN",
                        N));
    }

    @Test
    void generatorRejectsDimensionBelowMinimum() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_2",
                        BenchmarkV3Runner.MINIMUM_DIMENSION - 1));
    }

    @Test
    void trustedGeneratorRejectsNullPreflight() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateTrustedWorkload(
                        "UNIFORM_2",
                        N,
                        null));
    }

    @Test
    void trustedGeneratorRejectsMismatchedPreflight() {
        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_2",
                        N);

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.generateTrustedWorkload(
                        "UNIFORM_20",
                        N,
                        preflight));
    }

    @Test
    void trustedAndCompatibilityGeneratorsProduceIdenticalMatrices() {
        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_20",
                        N);

        SparseMatrixCSR trusted =
                BenchmarkV3Runner.generateTrustedWorkload(
                        "UNIFORM_20",
                        N,
                        preflight).matrix();

        SparseMatrixCSR compatibility =
                BenchmarkV3Runner.generateWorkload(
                        "UNIFORM_20",
                        N).matrix();

        assertArrayEquals(
                trusted.getRowPointers(),
                compatibility.getRowPointers());

        assertArrayEquals(
                trusted.getColumnIndices(),
                compatibility.getColumnIndices());

        assertArrayEquals(
                trusted.getValues(),
                compatibility.getValues(),
                0.0);
    }

    // ------------------------------------------------------------
    // NNZ calculation and memory preflight
    // ------------------------------------------------------------

    @Test
    void nnzCalculationRejectsUnknownWorkload() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.calculateNonZeroCount(
                        "UNKNOWN",
                        N));
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
    void csrPayloadEstimateMatchesPrimitiveArrayFormula() {
        long nnz = 256L;

        long expected =
                8L * nnz
                        + 4L * nnz
                        + 4L * (N + 1L);

        assertEquals(
                expected,
                BenchmarkV3Runner.estimateCsrPayloadBytes(
                        N,
                        nnz));
    }

    @Test
    void csrPayloadEstimateUsesLongArithmetic() {
        assertEquals(
                12_400_000_004L,
                BenchmarkV3Runner.estimateCsrPayloadBytes(
                        100_000_000,
                        1_000_000_000L));
    }

    @Test
    void csrPayloadEstimateRejectsInvalidArguments() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.estimateCsrPayloadBytes(
                        0,
                        10L));

        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.estimateCsrPayloadBytes(
                        N,
                        -1L));
    }

    @Test
    void preflightReportsConsistentWorkloadAndMemoryValues() {
        BenchmarkV3Runner.MemoryPreflight preflight =
                BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_2",
                        N);

        assertEquals("UNIFORM_2", preflight.workloadId());
        assertEquals(N, preflight.dimension());
        assertEquals(2L * N, preflight.nonZeroCount());

        assertEquals(
                BenchmarkV3Runner.estimateCsrPayloadBytes(
                        N,
                        2L * N),
                preflight.csrPayloadBytes());

        assertTrue(
                preflight.estimatedRequiredBytes()
                        >= preflight.csrPayloadBytes());

        assertTrue(
                preflight.requiredWithHeadroomBytes()
                        >= preflight.estimatedRequiredBytes());

        assertTrue(preflight.availableBytes() >= 0L);
        assertTrue(preflight.maximumHeapBytes() > 0L);
    }

    @Test
    void preflightRejectsUnknownWorkload() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.preflightWorkload(
                        "UNKNOWN",
                        N));
    }

    @Test
    void preflightRejectsDimensionBelowMinimum() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_2",
                        BenchmarkV3Runner.MINIMUM_DIMENSION - 1));
    }

    @Test
    void preflightRejectsUniformHundredAtThirtyMillionBeforeAllocation() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkV3Runner.preflightWorkload(
                        "UNIFORM_100",
                        30_000_000));
    }
}
