package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for QFLPNCoreEngine.
 *
 * Verifies:
 * 1. engine construction;
 * 2. CSR loading;
 * 3. matrix loading;
 * 4. sequential multiplication;
 * 5. parallel multiplication;
 * 6. sequential/parallel numerical equivalence;
 * 7. dimension validation;
 * 8. metadata exposure;
 * 9. invalid CSR input handling;
 * 10. engine lifecycle behavior.
 */
class QFLPNCoreEngineTest {

    private static final int N = 4;

    private static final double[] VALUES = {
        1.0, 2.0,
        3.0, 4.0,
        5.0, 6.0,
        7.0, 8.0
    };

    private static final int[] COLUMNS = {
        0, 2,
        1, 3,
        0, 2,
        1, 3
    };

    private static final int[] ROW_POINTERS = {
        0, 2, 4, 6, 8
    };

    private static final double[] INPUT = {
        1.0, 2.0, 3.0, 4.0
    };

    private static final double[] EXPECTED = {
        7.0, 22.0, 23.0, 46.0
    };

    @Test
    void constructorShouldStoreDimension() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertEquals(
                N,
                engine.getDimension());

        engine.shutdown();
    }

    @Test
    void constructorShouldRejectNonPositiveDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(0));

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(-1));
    }

    @Test
    void multiplyShouldRejectCallBeforeMatrixIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiply(INPUT));

        engine.shutdown();
    }

    @Test
    void multiplyParallelShouldRejectCallBeforeMatrixIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiplyParallel(INPUT));

        engine.shutdown();
    }

    @Test
    void loadCSRShouldLoadValidMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertEquals(
                N,
                engine.getMatrix().getRows());

        assertEquals(
                N,
                engine.getMatrix().getColumns());

        assertEquals(
                VALUES.length,
                engine.getNonZeroCount());

        engine.shutdown();
    }

    @Test
    void loadCSRShouldRejectNullValues() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertThrows(
                NullPointerException.class,
                () -> engine.loadCSR(
                        null,
                        COLUMNS,
                        ROW_POINTERS));

        engine.shutdown();
    }

    @Test
    void loadCSRShouldRejectNullColumns() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertThrows(
                NullPointerException.class,
                () -> engine.loadCSR(
                        VALUES,
                        null,
                        ROW_POINTERS));

        engine.shutdown();
    }

    @Test
    void loadCSRShouldRejectNullRowPointers() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertThrows(
                NullPointerException.class,
                () -> engine.loadCSR(
                        VALUES,
                        COLUMNS,
                        null));

        engine.shutdown();
    }

    @Test
    void loadCSRShouldRejectInvalidCSRStructure() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        int[] invalidRowPointers = {
            0, 2, 4, 6, 7
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> engine.loadCSR(
                        VALUES,
                        COLUMNS,
                        invalidRowPointers));

        engine.shutdown();
    }

    @Test
    void loadMatrixShouldAcceptCompatibleMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(
                        VALUES,
                        COLUMNS,
                        ROW_POINTERS,
                        N,
                        N);

        engine.loadMatrix(matrix);

        assertEquals(
                matrix,
                engine.getMatrix());

        engine.shutdown();
    }

    @Test
    void loadMatrixShouldRejectNullMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        assertThrows(
                NullPointerException.class,
                () -> engine.loadMatrix(null));

        engine.shutdown();
    }

    @Test
    void loadMatrixShouldRejectDimensionMismatch() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        SparseMatrixCSR matrix =
                new SparseMatrixCSR(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 1},
                        1,
                        1);

        assertThrows(
                IllegalArgumentException.class,
                () -> engine.loadMatrix(matrix));

        engine.shutdown();
    }

    @Test
    void multiplyShouldReturnExpectedResult() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        double[] result =
                engine.multiply(INPUT);

        assertArrayEquals(
                EXPECTED,
                result,
                1.0e-12);

        engine.shutdown();
    }

    @Test
    void multiplyParallelShouldReturnExpectedResult() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        double[] result =
                engine.multiplyParallel(
                        INPUT,
                        1,
                        2);

        assertArrayEquals(
                EXPECTED,
                result,
                1.0e-12);

        engine.shutdown();
    }

    @Test
    void sequentialAndParallelResultsShouldMatch() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        double[] sequential =
                engine.multiply(INPUT);

        double[] parallel =
                engine.multiplyParallel(
                        INPUT,
                        1,
                        2);

        assertArrayEquals(
                sequential,
                parallel,
                1.0e-12);

        engine.shutdown();
    }

    @Test
    void multiplyShouldRejectNullInputVector() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertThrows(
                NullPointerException.class,
                () -> engine.multiply(null));

        engine.shutdown();
    }

    @Test
    void multiplyParallelShouldRejectNullInputVector() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertThrows(
                NullPointerException.class,
                () -> engine.multiplyParallel(null));

        engine.shutdown();
    }

    @Test
    void multiplyShouldRejectWrongInputDimension() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        double[] wrongInput = {
            1.0, 2.0, 3.0
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> engine.multiply(wrongInput));

        engine.shutdown();
    }

    @Test
    void multiplyParallelShouldRejectWrongInputDimension() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        double[] wrongInput = {
            1.0, 2.0, 3.0
        };

        assertThrows(
                IllegalArgumentException.class,
                () -> engine.multiplyParallel(
                        wrongInput,
                        1,
                        2));

        engine.shutdown();
    }

    @Test
    void parallelMultiplyShouldRejectInvalidThreshold() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertThrows(
                IllegalArgumentException.class,
                () -> engine.multiplyParallel(
                        INPUT,
                        0,
                        2));

        engine.shutdown();
    }

    @Test
    void parallelMultiplyShouldRejectInvalidParallelism() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertThrows(
                IllegalArgumentException.class,
                () -> engine.multiplyParallel(
                        INPUT,
                        1,
                        0));

        engine.shutdown();
    }

    @Test
    void metadataShouldBeCorrect() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertEquals(
                N,
                engine.getDimension());

        assertEquals(
                VALUES.length,
                engine.getNonZeroCount());

        double expectedDensity =
                (double) VALUES.length
                        / (double) (N * N);

        assertEquals(
                expectedDensity,
                engine.getMatrixDensity(),
                1.0e-12);

        engine.shutdown();
    }

    @Test
    void loadedMatrixShouldRemainValid() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        assertTrue(
                engine.getMatrix().isValid());

        engine.shutdown();
    }

    @Test
    void shutdownShouldBeSafeToCall() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        engine.shutdown();
        engine.shutdown();
    }

    @Test
    void toStringShouldReportNotLoadedState() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        String text =
                engine.toString();

        assertTrue(
                text.contains("dimension=4"));

        assertTrue(
                text.contains("matrix=not-loaded"));

        engine.shutdown();
    }

    @Test
    void toStringShouldReportLoadedState() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                VALUES,
                COLUMNS,
                ROW_POINTERS);

        String text =
                engine.toString();

        assertTrue(
                text.contains("dimension=4"));

        assertTrue(
                text.contains("nonZeroCount=8"));

        engine.shutdown();
    }
}
