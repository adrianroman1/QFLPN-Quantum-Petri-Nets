package hpc.csr;

import java.util.Arrays;
import java.util.Random;
import java.util.concurrent.ForkJoinPool;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class MultiplyTaskDeterminismTest {

    private static final double EPS = 1.0e-12;

    private static double[] oracle(
            double[] values,
            int[] columns,
            int[] pointers,
            double[] input,
            int rows) {

        double[] expected = new double[rows];

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            for (int p = pointers[row]; p < pointers[row + 1]; p++) {
                sum += values[p] * input[columns[p]];
            }

            expected[row] = sum;
        }

        return expected;
    }

    @Test
    void sameInputProducesSameOutputAcrossRepeatedRuns() {
        int rows = 400;
        int cols = 23;
        int entries = 6;

        double[] values = new double[rows * entries];
        int[] columns = new int[rows * entries];
        int[] pointers = new int[rows + 1];

        Random random = new Random(20261022L);

        for (int row = 0; row < rows; row++) {
            pointers[row] = row * entries;

            for (int j = 0; j < entries; j++) {
                int p = row * entries + j;
                values[p] = random.nextDouble() * 10.0 - 5.0;
                columns[p] = random.nextInt(cols);
            }
        }

        pointers[rows] = rows * entries;

        double[] input = new double[cols];

        for (int i = 0; i < cols; i++) {
            input[i] = random.nextDouble() * 4.0 - 2.0;
        }

        double[] expected = oracle(
                values, columns, pointers, input, rows);

        ForkJoinPool pool = new ForkJoinPool(4);

        try {
            double[] baseline = null;

            for (int repetition = 0; repetition < 50; repetition++) {
                double[] output = new double[rows];

                pool.invoke(new MultiplyTask(
                        values,
                        columns,
                        pointers,
                        input,
                        output,
                        0,
                        rows,
                        2));

                assertArrayEquals(expected, output, EPS);

                if (baseline == null) {
                    baseline = output.clone();
                } else {
                    assertArrayEquals(
                            baseline,
                            output,
                            EPS,
                            "Output changed between repetitions");
                }
            }
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void differentThresholdsProduceEquivalentResults() {
        int rows = 257;
        int cols = 17;
        int entries = 5;

        double[] values = new double[rows * entries];
        int[] columns = new int[rows * entries];
        int[] pointers = new int[rows + 1];

        for (int row = 0; row < rows; row++) {
            pointers[row] = row * entries;

            for (int j = 0; j < entries; j++) {
                int p = row * entries + j;
                values[p] = (row + j + 1) * 0.125;
                columns[p] = (row * 3 + j) % cols;
            }
        }

        pointers[rows] = rows * entries;

        double[] input = new double[cols];

        for (int i = 0; i < cols; i++) {
            input[i] = i - 5.0;
        }

        double[] expected = oracle(
                values, columns, pointers, input, rows);

        int[] thresholds = {1, 2, 3, 8, 16, 64, 512};

        ForkJoinPool pool = new ForkJoinPool(4);

        try {
            for (int threshold : thresholds) {
                double[] output = new double[rows];

                pool.invoke(new MultiplyTask(
                        values,
                        columns,
                        pointers,
                        input,
                        output,
                        0,
                        rows,
                        threshold));

                assertArrayEquals(
                        expected,
                        output,
                        EPS,
                        "Incorrect result for threshold " + threshold);
            }
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void sequentialAndParallelExecutionMatchIndependentOracle() {
        int rows = 100;
        int cols = 13;
        int entries = 4;

        double[] values = new double[rows * entries];
        int[] columns = new int[rows * entries];
        int[] pointers = new int[rows + 1];

        for (int row = 0; row < rows; row++) {
            pointers[row] = row * entries;

            for (int j = 0; j < entries; j++) {
                int p = row * entries + j;
                values[p] = (p % 9) - 3.0;
                columns[p] = (row + j * 2) % cols;
            }
        }

        pointers[rows] = rows * entries;

        double[] input = new double[cols];
        Arrays.fill(input, 1.25);

        double[] expected = oracle(
                values, columns, pointers, input, rows);

        double[] sequential = new double[rows];
        double[] parallel = new double[rows];

        for (int row = 0; row < rows; row++) {
            double sum = 0.0;

            for (int p = pointers[row]; p < pointers[row + 1]; p++) {
                sum += values[p] * input[columns[p]];
            }

            sequential[row] = sum;
        }

        ForkJoinPool pool = new ForkJoinPool(3);

        try {
            pool.invoke(new MultiplyTask(
                    values,
                    columns,
                    pointers,
                    input,
                    parallel,
                    0,
                    rows,
                    1));
        } finally {
            pool.shutdown();
        }

        assertArrayEquals(expected, sequential, EPS);
        assertArrayEquals(expected, parallel, EPS);
        assertArrayEquals(sequential, parallel, EPS);
    }

    @Test
    void inputSnapshotsAreNotAffectedByCallerMutation() {
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

        values[0] = 1000.0;
        columns[0] = 1;
        pointers[1] = 0;
        input[0] = -500.0;

        ForkJoinPool pool = new ForkJoinPool(1);

        try {
            pool.invoke(task);
        } finally {
            pool.shutdown();
        }

        assertEquals(23.0, output[0], EPS);
    }

    @Test
    void duplicateColumnsAreDeterministic() {
        double[] values = {
                2.0, 3.0, -1.0,
                4.0, 5.0
        };

        int[] columns = {
                0, 0, 1,
                1, 1
        };

        int[] pointers = {0, 3, 5};

        double[] input = {4.0, 7.0};
        double[] expected = {13.0, 63.0};

        ForkJoinPool pool = new ForkJoinPool(2);

        try {
            for (int repetition = 0; repetition < 30; repetition++) {
                double[] output = new double[2];

                pool.invoke(new MultiplyTask(
                        values,
                        columns,
                        pointers,
                        input,
                        output,
                        0,
                        2,
                        1));

                assertArrayEquals(expected, output, EPS);
            }
        } finally {
            pool.shutdown();
        }
    }
}
