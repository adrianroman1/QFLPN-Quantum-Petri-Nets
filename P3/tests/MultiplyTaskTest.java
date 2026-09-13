package hpc.csr;

import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Teste unitare pentru MultiplyTask.
 *
 * Verifică:
 *
 * 1. calculul direct al unui interval de rânduri;
 * 2. calculul prin divizare Fork/Join;
 * 3. consistența rezultatelor;
 * 4. validarea constructorului;
 * 5. comportamentul cu intervale parțiale;
 * 6. accesul la metadatele task-ului.
 */
class MultiplyTaskTest {

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

    @Test
    void shouldExposeTaskMetadata() {

        double[] output =
                new double[4];

        MultiplyTask task =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        0,
                        4,
                        2);

        assertEquals(
                0,
                task.getStartRow());

        assertEquals(
                4,
                task.getEndRow());

        assertEquals(
                2,
                task.getThreshold());
    }

    @Test
    void shouldComputeEntireMatrixWithLargeThreshold() {

        double[] output =
                new double[4];

        MultiplyTask task =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        0,
                        4,
                        100);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(task);
        }

        assertArrayEquals(
                expected(),
                output,
                TOLERANCE);
    }

    @Test
    void shouldComputeEntireMatrixWithRecursiveSplitting() {

        double[] output =
                new double[4];

        MultiplyTask task =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        0,
                        4,
                        1);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(task);
        }

        assertArrayEquals(
                expected(),
                output,
                TOLERANCE);
    }

    @Test
    void shouldComputeOnlySelectedRowInterval() {

        double[] output = {
                -1.0,
                -1.0,
                -1.0,
                -1.0
        };

        MultiplyTask task =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        1,
                        3,
                        1);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(task);
        }

        assertEquals(
                -1.0,
                output[0],
                TOLERANCE);

        assertEquals(
                22.0,
                output[1],
                TOLERANCE);

        assertEquals(
                23.0,
                output[2],
                TOLERANCE);

        assertEquals(
                -1.0,
                output[3],
                TOLERANCE);
    }

    @Test
    void shouldComputeSingleRowInterval() {

        double[] output = {
                -1.0,
                -1.0,
                -1.0,
                -1.0
        };

        MultiplyTask task =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        2,
                        3,
                        1);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(task);
        }

        assertEquals(
                -1.0,
                output[0],
                TOLERANCE);

        assertEquals(
                -1.0,
                output[1],
                TOLERANCE);

        assertEquals(
                23.0,
                output[2],
                TOLERANCE);

        assertEquals(
                -1.0,
                output[3],
                TOLERANCE);
    }

    @Test
    void shouldSupportEmptyRowInterval() {

        double[] output = {
                11.0,
                22.0,
                33.0,
                44.0
        };

        MultiplyTask task =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        output,
                        2,
                        2,
                        1);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(task);
        }

        assertArrayEquals(
                new double[] {
                        11.0,
                        22.0,
                        33.0,
                        44.0
                },
                output,
                TOLERANCE);
    }

    @Test
    void shouldRejectNullValues() {

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        null,
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        4,
                        1));
    }

    @Test
    void shouldRejectNullColumns() {

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        values(),
                        null,
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        4,
                        1));
    }

    @Test
    void shouldRejectNullRowPointers() {

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        null,
                        input(),
                        new double[4],
                        0,
                        4,
                        1));
    }

    @Test
    void shouldRejectNullInput() {

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        null,
                        new double[4],
                        0,
                        4,
                        1));
    }

    @Test
    void shouldRejectNullOutput() {

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        null,
                        0,
                        4,
                        1));
    }

    @Test
    void shouldRejectNegativeStartRow() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        -1,
                        4,
                        1));
    }

    @Test
    void shouldRejectEndRowSmallerThanStartRow() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        3,
                        2,
                        1));
    }

    @Test
    void shouldRejectEndRowOutsideCSRRange() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        5,
                        1));
    }

    @Test
    void shouldRejectNonPositiveThreshold() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        4,
                        0));

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        new double[4],
                        0,
                        4,
                        -1));
    }

    @Test
    void shouldRejectMismatchedValuesAndColumns() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {
                                1.0, 2.0
                        },
                        new int[] {
                                0
                        },
                        new int[] {
                                0, 1, 1
                        },
                        new double[] {
                                1.0, 2.0
                        },
                        new double[] {
                                0.0, 0.0
                        },
                        0,
                        2,
                        1));
    }

    @Test
    void shouldRejectEmptyRowPointerArray() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[0],
                        new int[0],
                        new int[0],
                        new double[0],
                        new double[0],
                        0,
                        0,
                        1));
    }

    @Test
    void shouldRejectStartRowBeyondInputVector() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        new double[2],
                        new double[4],
                        3,
                        4,
                        1));
    }

    @Test
    void shouldRejectEndRowBeyondOutputVector() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        new double[4],
                        new double[2],
                        0,
                        4,
                        1));
    }

    @Test
    void recursiveAndDirectExecutionShouldProduceIdenticalResults() {

        double[] directOutput =
                new double[4];

        double[] recursiveOutput =
                new double[4];

        MultiplyTask directTask =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        directOutput,
                        0,
                        4,
                        100);

        MultiplyTask recursiveTask =
                new MultiplyTask(
                        values(),
                        columns(),
                        rowPointers(),
                        input(),
                        recursiveOutput,
                        0,
                        4,
                        1);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(directTask);
            pool.invoke(recursiveTask);
        }

        assertArrayEquals(
                directOutput,
                recursiveOutput,
                TOLERANCE);
    }

    @Test
    void shouldHandleEmptyRowsCorrectly() {

        double[] output =
                new double[3];

        MultiplyTask task =
                new MultiplyTask(
                        new double[] {
                                1.0, 2.0
                        },
                        new int[] {
                                0, 2
                        },
                        new int[] {
                                0, 1, 1, 2
                        },
                        new double[] {
                                5.0, 7.0, 11.0
                        },
                        output,
                        0,
                        3,
                        1);

        try (ForkJoinPool pool =
                     new ForkJoinPool(2)) {

            pool.invoke(task);
        }

        assertArrayEquals(
                new double[] {
                        5.0,
                        0.0,
                        22.0
                },
                output,
                TOLERANCE);
    }
}
