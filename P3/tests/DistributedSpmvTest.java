package hpc.mpi;

import hpc.csr.SparseMatrixCSR;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.nio.file.Path;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.*;

class DistributedSpmvTest {

    private static SparseMatrixCSR sampleMatrix() {
        /*
         * Matrix:
         *
         * [ 2  0  3 ]
         * [ 0  0  0 ]
         * [ 0  4  0 ]
         *
         * CSR:
         * values       = [2, 3, 4]
         * columns      = [0, 2, 1]
         * rowPointers  = [0, 2, 2, 3]
         */
        return new SparseMatrixCSR(
                new double[]{2.0, 3.0, 4.0},
                new int[]{0, 2, 1},
                new int[]{0, 2, 2, 3},
                3,
                3);
    }

    private static double[] sampleVector() {
        return new double[]{5.0, 7.0, 11.0};
    }

    @Test
    void matrixFixtureIsValidAndHasExpectedDimensions() {
        SparseMatrixCSR matrix = sampleMatrix();

        assertTrue(matrix.isValid());
        assertEquals(3, matrix.getRows());
        assertEquals(3, matrix.getColumns());
        assertEquals(3, matrix.getNnz());
    }

    @Test
    void expectedSequentialReferenceIsCorrect() {
        SparseMatrixCSR matrix = sampleMatrix();

        assertArrayEquals(
                new double[]{43.0, 0.0, 28.0},
                matrix.multiply(sampleVector()),
                1.0e-12);
    }

    @Test
    void resultRecordDefensivelyCopiesItsVector() {
        double[] source = new double[]{1.0, 2.0};

        DistributedSpmv.Result result =
                new DistributedSpmv.Result(
                        source,
                        2,
                        2,
                        2,
                        2,
                        Duration.ofMillis(10),
                        0);

        source[0] = 999.0;

        assertArrayEquals(
                new double[]{1.0, 2.0},
                result.values(),
                0.0);

        double[] returned = result.values();
        returned[1] = 999.0;

        assertArrayEquals(
                new double[]{1.0, 2.0},
                result.values(),
                0.0);
    }

    @Test
    void resultRecordRejectsWrongVectorLength() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{1.0},
                        2,
                        2,
                        1,
                        2,
                        Duration.ofMillis(1),
                        0));
    }

    @Test
    void resultRecordRejectsNegativeDimensions() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[0],
                        -1,
                        0,
                        0,
                        1,
                        Duration.ofMillis(1),
                        0));
    }

    @Test
    void resultRecordRejectsNonFiniteValues() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{Double.NaN},
                        1,
                        1,
                        1,
                        2,
                        Duration.ofMillis(1),
                        0));
    }

    @Test
    void resultRecordRejectsPositiveInfinity() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{Double.POSITIVE_INFINITY},
                        1,
                        1,
                        1,
                        2,
                        Duration.ofMillis(1),
                        0));
    }

    @Test
    void resultRecordRejectsNegativeInfinity() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{Double.NEGATIVE_INFINITY},
                        1,
                        1,
                        1,
                        2,
                        Duration.ofMillis(1),
                        0));
    }

    @Test
    void resultRecordRejectsNonZeroExitCode() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{1.0},
                        1,
                        1,
                        1,
                        2,
                        Duration.ofMillis(1),
                        1));
    }

    @Test
    void resultRecordRejectsZeroProcessCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{1.0},
                        1,
                        1,
                        1,
                        0,
                        Duration.ofMillis(1),
                        0));
    }

    @Test
    void resultRecordRejectsNegativeElapsedTime() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DistributedSpmv.Result(
                        new double[]{1.0},
                        1,
                        1,
                        1,
                        1,
                        Duration.ofNanos(-1),
                        0));
    }

    @Test
    void mpiInvocationRejectsNullMatrix() {
        assertThrows(
                NullPointerException.class,
                () -> DistributedSpmv.multiply(
                        null,
                        sampleVector(),
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsNullInputVector() {
        assertThrows(
                NullPointerException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        null,
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsZeroProcessesBeforeStartingLauncher() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        0,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsNegativeProcessCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        -2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsInputVectorWithWrongLength() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        new double[]{1.0, 2.0},
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsNonFiniteInputVector() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        new double[]{
                                1.0,
                                Double.POSITIVE_INFINITY,
                                3.0
                        },
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsNanInputVector() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        new double[]{
                                1.0,
                                Double.NaN,
                                3.0
                        },
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsZeroTimeout() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ZERO));
    }

    @Test
    void mpiInvocationRejectsNegativeTimeout() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(-1)));
    }

    @Test
    void mpiInvocationRejectsSubMillisecondTimeout() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        2,
                        Path.of("mpirun"),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofNanos(1)));
    }

    @Test
    void mpiInvocationRejectsBlankLauncher() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        2,
                        Path.of(""),
                        Path.of("p3_mpi_spmv"),
                        Duration.ofSeconds(5)));
    }

    @Test
    void mpiInvocationRejectsBlankNativeExecutable() {
        assertThrows(
                IllegalArgumentException.class,
                () -> DistributedSpmv.multiply(
                        sampleMatrix(),
                        sampleVector(),
                        2,
                        Path.of("mpirun"),
                        Path.of(""),
                        Duration.ofSeconds(5)));
    }

    /**
     * This is the real native MPI integration test.
     *
     * It is enabled only when p3_validation has compiled the C backend
     * and supplied P3_MPI_EXECUTABLE. The test launches two MPI ranks
     * and compares the distributed result against the sequential CSR
     * implementation.
     *
     * A local two-rank test validates the MPI protocol and result
     * aggregation. It does not establish inter-node scaling.
     */
    @Test
    @EnabledIfEnvironmentVariable(
            named = "P3_MPI_EXECUTABLE",
            matches = ".+")
    void nativeMpiTwoProcessResultMatchesSequentialReference()
            throws Exception {

        SparseMatrixCSR matrix = sampleMatrix();
        double[] x = sampleVector();

        String executableSetting =
                System.getenv("P3_MPI_EXECUTABLE");

        String launcherSetting =
                System.getenv("P3_MPI_LAUNCHER");

        assertNotNull(executableSetting);
        assertFalse(executableSetting.isBlank());

        Path executable = Path.of(executableSetting);

        Path launcher = launcherSetting == null
                || launcherSetting.isBlank()
                ? Path.of("mpirun")
                : Path.of(launcherSetting);

        DistributedSpmv.Result result =
                DistributedSpmv.multiply(
                        matrix,
                        x,
                        2,
                        launcher,
                        executable,
                        Duration.ofSeconds(60));

        assertEquals(3, result.rows());
        assertEquals(3, result.columns());
        assertEquals(3, result.nnz());
        assertEquals(2, result.processCount());
        assertEquals(0, result.processExitCode());

        assertArrayEquals(
                matrix.multiply(x),
                result.values(),
                1.0e-12);

        assertTrue(
                result.elapsedTime().toNanos() > 0,
                "Elapsed wall-clock time must be positive.");
    }
}
