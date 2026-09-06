package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
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
 * 3. încărcarea CSR;
 * 4. încărcarea unei matrice SparseMatrixCSR;
 * 5. validarea dimensională;
 * 6. multiplicarea secvențială;
 * 7. multiplicarea paralelă;
 * 8. echivalența numerică secvențial/paralel;
 * 9. validarea vectorilor;
 * 10. metadatele;
 * 11. starea motorului înainte și după încărcarea matricei;
 * 12. comportamentul shutdown().
 */
class QFLPNCoreEngineTest {

    private static final int N = 4;

    private static final double TOLERANCE = 1.0e-12;

    /*
     * Matrice de referință:
     *
     * [ 1  0  2  0 ]
     * [ 0  3  0  4 ]
     * [ 5  0  6  0 ]
     * [ 0  7  0  8 ]
     *
     * x = [1, 2, 3, 4]^T
     *
     * A*x = [7, 22, 23, 46]^T
     */

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
                new QFLPNCoreEngine(N);

        engine.loadCSR(
                values(),
                columns(),
                rowPointers());

        return engine;
    }

    private static SparseMatrixCSR createReferenceMatrix() {

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
                new QFLPNCoreEngine(N);

        try {
            assertEquals(
                    N,
                    engine.getDimension());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectZeroDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(0));
    }

    @Test
    void shouldRejectNegativeDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(-1));
    }

    @Test
    void shouldRejectMultiplyBeforeMatrixIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        try {
            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiply(input()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectParallelMultiplyBeforeMatrixIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        try {
            assertThrows(
                    IllegalStateException.class,
                    () -> engine.multiplyParallel(input()));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldLoadCSRMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

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
                new QFLPNCoreEngine(N);

        try {
            SparseMatrixCSR matrix =
                    createReferenceMatrix();

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
                new QFLPNCoreEngine(N);

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
                new QFLPNCoreEngine(N);

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
                new QFLPNCoreEngine(N);

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
                new QFLPNCoreEngine(N);

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
                new QFLPNCoreEngine(N);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadMatrix(null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectSparseMatrixDimensionMismatch() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

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
                    () -> engine.loadMatrix(matrix));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeCorrectSequentialResult() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            double[] result =
                    engine.multiply(input());

            assertArrayEquals(
                    expected(),
                    result,
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
            double[] result =
                    engine.multiplyParallel(
                            input(),
                            1,
                            2);

            assertArrayEquals(
                    expected(),
                    result,
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
                    engine.multiplyParallel(
                            input(),
                            1,
                            2);

            assertArrayEquals(
                    sequential,
                    parallel,
                    TOLERANCE);

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
                    () -> engine.multiply(null));

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
                    () -> engine.multiplyParallel(null));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectWrongInputDimensionForSequentialMultiply() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiply(
                            new double[] {
                                    1.0, 2.0, 3.0
                            }));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectWrongInputDimensionForParallelMultiply() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            new double[] {
                                    1.0, 2.0, 3.0
                            },
                            1,
                            2));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidParallelThreshold() {

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
    void shouldRejectInvalidParallelism() {

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

            assertEquals(
                    N,
                    matrix.getRows());

            assertEquals(
                    N,
                    matrix.getColumns());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReportNotLoadedStateInToString() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(N);

        try {
            String text =
                    engine.toString();

            assertTrue(
                    text.contains("dimension=4"));

            assertTrue(
                    text.contains("matrix=not-loaded"));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldReportLoadedStateInToString() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        try {
            String text =
                    engine.toString();

            assertTrue(
                    text.contains("dimension=4"));

            assertTrue(
                    text.contains("nonZeroCount=8"));

            assertTrue(
                    text.contains("density="));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shutdownShouldBeSafe() {

        QFLPNCoreEngine engine =
                createLoadedEngine();

        engine.shutdown();
        engine.shutdown();
    }
}