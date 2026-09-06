package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Teste unitare pentru QFLPNCoreEngine.
 *
 * Verifică:
 *
 * 1. construcția motorului;
 * 2. validarea dimensiunii;
 * 3. configurarea paralelismului;
 * 4. încărcarea CSR;
 * 5. încărcarea unei matrice SparseMatrixCSR;
 * 6. validarea dimensională;
 * 7. multiplicarea secvențială;
 * 8. multiplicarea paralelă;
 * 9. echivalența numerică secvențial/paralel;
 * 10. reutilizarea pool-ului persistent;
 * 11. validarea vectorilor;
 * 12. metadatele;
 * 13. ciclul de viață shutdown;
 * 14. starea textuală a motorului.
 */
class QFLPNCoreEngineTest {

    private static final int N = 4;

    private static final double TOLERANCE = 1.0e-12;

    private static double[] values() {

        return new double[] {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };
    }

    private static int[] columns() {

        return new int[] {
                0, 2,
                1, 3,
                0, 2,
                1, 3
        };
    }

    private static int[] rowPointers() {

        return new int[] {
                0, 2, 4, 6, 8
        };
    }

    private static double[] input() {

        return new double[] {
                1.0, 2.0, 3.0, 4.0
        };
    }

    private static double[] expected() {

        return new double[] {
                7.0, 22.0, 23.0, 46.0
        };
    }

    private static QFLPNCoreEngine createLoadedEngine() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        engine.loadCSR(
                values(),
                columns(),
                rowPointers());

        return engine;
    }

    private static SparseMatrixCSR createMatrix() {

        return new SparseMatrixCSR(
                values(),
                columns(),
                rowPointers(),
                N,
                N);
    }

    @Test
    void shouldStoreDimension() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertEquals(
                    N,
                    engine.getDimension());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldStoreParallelism() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertEquals(
                    2,
                    engine.getParallelism());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectZeroDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(
                        0,
                        2));
    }

    @Test
    void shouldRejectNegativeDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(
                        -1,
                        2));
    }

    @Test
    void shouldRejectZeroParallelism() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(
                        N,
                        0));
    }

    @Test
    void shouldRejectNegativeParallelism() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(
                        N,
                        -1));
    }

    @Test
    void shouldRejectMultiplyBeforeMatrixIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiply(
                            input()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectParallelMultiplyBeforeMatrixIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiplyParallel(
                            input()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadCSRMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            SparseMatrixCSR matrix =
                    engine.getMatrix();

            assertNotNull(matrix);

            assertEquals(
                    N,
                    matrix.getRows());

            assertEquals(
                    N,
                    matrix.getColumns());

            assertEquals(
                    8,
                    engine.getNonZeroCount());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadSparseMatrixCSR() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            SparseMatrixCSR matrix =
                    createMatrix();

            engine.loadMatrix(matrix);

            assertEquals(
                    matrix,
                    engine.getMatrix());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullCSRValues() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            null,
                            columns(),
                            rowPointers()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullCSRColumns() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            values(),
                            null,
                            rowPointers()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullCSRRowPointers() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            values(),
                            columns(),
                            null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidCSRStructure() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            int[] invalidRowPointers = {
                    0, 2, 4, 6, 7
            };

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            values(),
                            columns(),
                            invalidRowPointers));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullSparseMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadMatrix(
                            null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectSparseMatrixDimensionMismatch() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            SparseMatrixCSR matrix =
                    new SparseMatrixCSR(
                            new double[] {1.0},
                            new int[] {0},
                            new int[] {0, 1},
                            1,
                            1);

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadMatrix(
                            matrix));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeCorrectSequentialResult() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiply(
                            input()),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeCorrectParallelResult() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(
                            input()),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeCorrectParallelResultWithExplicitConfiguration() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertArrayEquals(
                    expected(),
                    engine.multiplyParallel(
                            input(),
                            1,
                            2),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void sequentialAndParallelResultsShouldMatch() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            double[] sequential =
                    engine.multiply(input());

            double[] parallel =
                    engine.multiplyParallel(input());

            assertArrayEquals(
                    sequential,
                    parallel,
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void parallelPoolShouldBeReusable() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            double[] first =
                    engine.multiplyParallel(
                            input());

            double[] second =
                    engine.multiplyParallel(
                            input());

            assertArrayEquals(
                    first,
                    second,
                    TOLERANCE);

            assertFalse(
                    engine.isShutdown());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullInputForSequentialMultiply() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.multiply(
                            null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullInputForParallelMultiply() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.multiplyParallel(
                            null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectWrongInputDimension() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            double[] wrongInput = {
                    1.0, 2.0, 3.0
            };

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiply(
                            wrongInput));

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            wrongInput));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidThreshold() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            input(),
                            0,
                            2));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidExplicitParallelism() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            input(),
                            1,
                            0));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldExposeCorrectMetadata() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertEquals(
                    N,
                    engine.getDimension());

            assertEquals(
                    2,
                    engine.getParallelism());

            assertEquals(
                    8,
                    engine.getNonZeroCount());

            assertEquals(
                    0.5,
                    engine.getMatrixDensity(),
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldExposeLoadedMatrix() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            SparseMatrixCSR matrix =
                    engine.getMatrix();

            assertNotNull(matrix);

            assertTrue(
                    matrix.isValid());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReportCorrectInitialState() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(
                        N,
                        2);

        try {
            String text =
                    engine.toString();

            assertTrue(
                    text.contains(
                            "dimension=4"));

            assertTrue(
                    text.contains(
                            "parallelism=2"));

            assertTrue(
                    text.contains(
                            "matrix=not-loaded"));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReportCorrectLoadedState() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            String text =
                    engine.toString();

            assertTrue(
                    text.contains(
                            "dimension=4"));

            assertTrue(
                    text.contains(
                            "parallelism=2"));

            assertTrue(
                    text.contains(
                            "nonZeroCount=8"));

            assertTrue(
                    text.contains(
                            "density="));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shutdownShouldBeIdempotent() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        engine.shutdown();
        engine.shutdown();

        assertTrue(
                engine.isShutdown());
    }

    @Test
    void operationsAfterShutdownShouldBeRejected() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        engine.shutdown();

        assertTrue(
                engine.isShutdown());

        assertThrows(
                IllegalStateException.class,
                () -> engine.getMatrix());

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiply(
                        input()));

        assertThrows(
                IllegalStateException.class,
                () -> engine.multiplyParallel(
                        input()));
    }

    @Test
    void toStringShouldReportShutdownState() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        engine.shutdown();

        String text =
                engine.toString();

        assertTrue(
                text.contains(
                        "shutdown=true"));
    }
}