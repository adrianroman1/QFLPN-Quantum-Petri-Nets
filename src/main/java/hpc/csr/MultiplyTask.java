package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * MultiplyTask
 *
 * Fork/Join task pentru multiplicarea unei matrice CSR cu un vector:
 *
 *                         y = A * x
 *
 * Task-ul împarte intervalul de rânduri al matricei în subintervale
 * independente. Fiecare subtask calculează rezultatul pentru propriile
 * rânduri, fără modificarea rezultatelor celorlalte task-uri.
 *
 * Implementarea este orientată către execuție deterministică și
 * thread-safe la nivelul partiționării pe rânduri: fiecare task scrie
 * exclusiv în pozițiile de output aferente intervalului său.
 */
public final class MultiplyTask extends RecursiveAction {

    private final double[] values;
    private final int[] columns;
    private final int[] rowPointers;

    private final double[] input;
    private final double[] output;

    private final int startRow;
    private final int endRow;

    private final int threshold;

    /**
     * Constructor principal.
     *
     * @param values valorile nenule ale matricei CSR
     * @param columns indicii coloanelor pentru valorile CSR
     * @param rowPointers pointerii de început și sfârșit ai fiecărui rând
     * @param input vectorul de intrare x
     * @param output vectorul de ieșire y
     * @param startRow primul rând inclus în interval
     * @param endRow ultimul rând exclus din interval
     * @param threshold numărul maxim de rânduri procesate direct de un task
     */
    public MultiplyTask(
            double[] values,
            int[] columns,
            int[] rowPointers,
            double[] input,
            double[] output,
            int startRow,
            int endRow,
            int threshold) {

        this.values = Objects.requireNonNull(
                values,
                "values cannot be null");

        this.columns = Objects.requireNonNull(
                columns,
                "columns cannot be null");

        this.rowPointers = Objects.requireNonNull(
                rowPointers,
                "rowPointers cannot be null");

        this.input = Objects.requireNonNull(
                input,
                "input cannot be null");

        this.output = Objects.requireNonNull(
                output,
                "output cannot be null");

        if (values.length != columns.length) {
            throw new IllegalArgumentException(
                    "values and columns must have the same length");
        }

        if (rowPointers.length == 0) {
            throw new IllegalArgumentException(
                    "rowPointers cannot be empty");
        }

        if (startRow < 0) {
            throw new IllegalArgumentException(
                    "startRow cannot be negative");
        }

        if (endRow < startRow) {
            throw new IllegalArgumentException(
                    "endRow cannot be smaller than startRow");
        }

        if (endRow >= rowPointers.length) {
            throw new IllegalArgumentException(
                    "endRow exceeds the CSR row range");
        }

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be greater than zero");
        }

        if (startRow > input.length) {
            throw new IllegalArgumentException(
                    "startRow exceeds input vector length");
        }

        if (endRow > output.length) {
            throw new IllegalArgumentException(
                    "endRow exceeds output vector length");
        }

        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
    }

    /**
     * Execută task-ul Fork/Join.
     *
     * Dacă intervalul este suficient de mic, calculul este efectuat
     * direct. În caz contrar, intervalul este împărțit în două
     * subtask-uri independente.
     */
    @Override
    protected void compute() {

        int rowCount = endRow - startRow;

        if (rowCount <= threshold) {
            computeSequentially();
            return;
        }

        int middle = startRow + rowCount / 2;

        MultiplyTask leftTask =
                new MultiplyTask(
                        values,
                        columns,
                        rowPointers,
                        input,
                        output,
                        startRow,
                        middle,
                        threshold);

        MultiplyTask rightTask =
                new MultiplyTask(
                        values,
                        columns,
                        rowPointers,
                        input,
                        output,
                        middle,
                        endRow,
                        threshold);

        invokeAll(leftTask, rightTask);
    }

    /**
     * Calculează secvențial rezultatul pentru intervalul de rânduri
     * alocat acestui task.
     */
    private void computeSequentially() {

        for (int row = startRow; row < endRow; row++) {

            int begin = rowPointers[row];
            int end = rowPointers[row + 1];

            double sum = 0.0;

            for (int index = begin; index < end; index++) {

                int column = columns[index];

                if (column < 0 || column >= input.length) {
                    throw new IllegalArgumentException(
                            "CSR column index out of input vector bounds: "
                                    + column);
                }

                sum += values[index] * input[column];
            }

            output[row] = sum;
        }
    }

    /**
     * @return primul rând inclus în task
     */
    public int getStartRow() {
        return startRow;
    }

    /**
     * @return ultimul rând exclus din task
     */
    public int getEndRow() {
        return endRow;
    }

    /**
     * @return pragul de divizare Fork/Join
     */
    public int getThreshold() {
        return threshold;
    }
}