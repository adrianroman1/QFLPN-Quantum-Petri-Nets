package hpc.csr;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Teste unitare pentru QFLPNCoreEngine.
 *
 * Verifică integrarea dintre motorul QFLPN
 * și reprezentarea SparseMatrixCSR.
 */
class QFLPNCoreEngineTest {

    private static final double TOLERANCE = 1.0e-12;

    /**
     * Matricea de referință:
     *
     * A =
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

        return new double[]{
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };
    }

    private static int[] columns() {

        return new int[]{
                0, 2,
                1, 3,
                0, 2,
                1, 3
        };
    }

    private static int[] rowPointers() {

        return new int[]{
                0, 2, 4, 6, 8
        };
    }

    private static double[] input() {

        return new double[]{
                1.0, 2.0, 3.0, 4.0
        };
    }

    private static double[] expected() {

        return new double[]{
                7.0, 22.0, 23.0, 46.0
        };
    }

    @Test
    void shouldCreateEngineWithValidDimension() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            assertEquals(
                    4,
                    engine.getDimension());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNegativeDimension() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new QFLPNCoreEngine(-1));
    }

    @Test
    void shouldRejectMultiplyBeforeCSRIsLoaded() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

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
    void shouldLoadCSRMatrixCorrectly() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            assertEquals(
                    4,
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
    void shouldComputeCorrectSequentialResult() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            double[] actual =
                    engine.multiply(input());

            assertArrayEquals(
                    expected(),
                    actual,
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldComputeCorrectParallelResult() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            double[] actual =
                    engine.multiplyParallel(
                            input(),
                            1,
                            2);

            assertArrayEquals(
                    expected(),
                    actual,
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void sequentialAndParallelResultsShouldMatch() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

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
    void shouldRejectWrongInputDimension() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiply(
                            new double[]{1.0, 2.0, 3.0}));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidCSRData() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            new double[]{1.0},
                            new int[]{4},
                            new int[]{0, 1, 1, 1, 1}));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectNullCSRArrays() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            null,
                            columns(),
                            rowPointers()));

            assertThrows(
                    NullPointerException.class,
                    () -> engine.loadCSR(
                            values(),
                            null,
                            rowPointers()));

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
    void shouldRejectCSRDimensionMismatch() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.loadCSR(
                            new double[]{1.0},
                            new int[]{0},
                            new int[]{0, 1, 1, 1}));

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldExposeLoadedMatrix() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            assertEquals(
                    4,
                    engine.getMatrix().getRows());

            assertEquals(
                    4,
                    engine.getMatrix().getColumns());

            assertEquals(
                    8,
                    engine.getMatrix().getNonZeroCount());

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldSupportParallelismAndThresholdConfiguration() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            double[] result =
                    engine.multiplyParallel(
                            input(),
                            2,
                            1);

            assertArrayEquals(
                    expected(),
                    result,
                    TOLERANCE);

        } finally {
            engine.shutdown();
        }
    }

    @Test
    void shouldRejectInvalidParallelConfiguration() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        try {
            engine.loadCSR(
                    values(),
                    columns(),
                    rowPointers());

            assertThrows(
                    IllegalArgumentException.class,
                    () -> engine.multiplyParallel(
                            input(),
                            0,
                            2));

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
    void shouldShutdownWithoutFailure() {

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        engine.shutdown();
    }
}