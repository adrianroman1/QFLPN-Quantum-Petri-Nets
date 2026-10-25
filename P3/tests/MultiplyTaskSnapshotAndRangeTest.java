package hpc.csr;

import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class MultiplyTaskSnapshotAndRangeTest {

    private static final double EPS = 1.0e-12;

    @Test
    void constructorTakesDefensiveCopiesOfInputArrays() {
        double[] values = {2.0, 3.0};
        int[] columns = {0, 1};
        int[] pointers = {0, 2};
        double[] input = {4.0, 5.0};
        double[] output = new double[1];

        MultiplyTask task = new MultiplyTask(
                values,
                columns,
                pointers,
                input,
                output,
                0,
                1,
                1);

        values[0] = 100.0;
        values[1] = 100.0;

        columns[0] = 1;
        columns[1] = 0;

        pointers[0] = 1;
        pointers[1] = 1;

        input[0] = 100.0;
        input[1] = 100.0;

        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            pool.invoke(task);
        } finally {
            pool.shutdown();
        }

        assertEquals(23.0, output[0], EPS);
    }

    @Test
    void taskWritesOnlyInsideAssignedRowRange() {
        double[] values = {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };

        int[] columns = {
                0, 1,
                0, 1,
                0, 1,
                0, 1
        };

        int[] pointers = {0, 2, 4, 6, 8};
        double[] input = {2.0, 3.0};

        double[] output = {-99.0, -99.0, -99.0, -99.0};

        MultiplyTask task = new MultiplyTask(
                values,
                columns,
                pointers,
                input,
                output,
                1,
                3,
                1);

        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            pool.invoke(task);
        } finally {
            pool.shutdown();
        }

        assertEquals(-99.0, output[0], EPS);
        assertEquals(18.0, output[1], EPS);
        assertEquals(28.0, output[2], EPS);
        assertEquals(-99.0, output[3], EPS);
    }

    @Test
    void emptyRowRangeDoesNotModifyOutput() {
        double[] output = {-1.0, -2.0};

        MultiplyTask task = new MultiplyTask(
                new double[] {2.0, 3.0},
                new int[] {0, 1},
                new int[] {0, 1, 2},
                new double[] {4.0, 5.0},
                output,
                1,
                1,
                1);

        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            pool.invoke(task);
        } finally {
            pool.shutdown();
        }

        assertArrayEquals(
                new double[] {-1.0, -2.0},
                output,
                EPS);
    }

    @Test
    void rejectsNullArrays() {
        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        null,
                        new int[0],
                        new int[] {0},
                        new double[0],
                        new double[0],
                        0,
                        0,
                        1));

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        new double[0],
                        null,
                        new int[] {0},
                        new double[0],
                        new double[0],
                        0,
                        0,
                        1));

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        null,
                        new double[0],
                        0,
                        0,
                        1));

        assertThrows(
                NullPointerException.class,
                () -> new MultiplyTask(
                        new double[0],
                        new int[0],
                        new int[] {0},
                        new double[0],
                        null,
                        0,
                        0,
                        1));
    }

    @Test
    void rejectsInvalidRowRange() {
        double[] values = {1.0};
        int[] columns = {0};
        int[] pointers = {0, 1};
        double[] input = {2.0};
        double[] output = new double[1];

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values, columns, pointers, input,
                        output, -1, 1, 1));

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values, columns, pointers, input,
                        output, 0, 2, 1));

        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        values, columns, pointers, input,
                        output, 1, 0, 1));
    }

    @Test
    void rejectsNonPositiveThreshold() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 1},
                        new double[] {2.0},
                        new double[1],
                        0,
                        1,
                        0));
    }

    @Test
    void rejectsOutputLengthDifferentFromRowCount() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0},
                        new int[] {0},
                        new int[] {0, 1, 1},
                        new double[] {2.0},
                        new double[1],
                        0,
                        2,
                        1));
    }

    @Test
    void rejectsInputVectorTooShortForColumnIndices() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new MultiplyTask(
                        new double[] {1.0},
                        new int[] {2},
                        new int[] {0, 1},
                        new double[] {2.0},
                        new double[1],
                        0,
                        1,
                        1));
    }
}
