package hpc.csr;

import java.util.concurrent.RecursiveAction;

/**
 * MultiplyTask
 *
 * Task Fork/Join pentru multiplicarea unei matrice CSR cu un vector:
 *
 *                  y = A * x
 *
 * Task-ul împarte intervalul de rânduri al matricei în subintervale
 * independente. Fiecare subtask calculează rezultatul pentru propriile
 * rânduri, fără modificarea rezultatelor celorlalte task-uri.
 *
 * Această structură permite execuția paralelă pe procesoare multi-core.
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
     * @param columns indicii coloanelor
     * @param rowPointers pointerii de început/sfârșit ai rândurilor
     * @param input vectorul x
     * @param output vectorul y
     * @param startRow primul rând inclus
     * @param endRow ultimul rând exclus
     * @param threshold dimensiunea maximă a unui task înainte de calcul direct
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

        if (values == null) {
            throw new NullPointerException("values cannot be null");
        }

        if (columns == null) {
            throw new NullPointerException("columns cannot be null");
        }

        if (rowPointers == null) {
            throw new NullPointerException("rowPointers cannot be null");
        }

        if (input == null) {
            throw new NullPointerException("input cannot be null");
        }

        if (output == null) {
            throw new NullPointerException("output cannot be null");
        }

        if (startRow < 0 || endRow < startRow) {
            throw new IllegalArgumentException(
                    "Invalid row interval: "
                            + startRow + " .. " + endRow);
        }

        if (threshold <= 0) {
            throw new IllegalArgumentException(
                    "threshold must be greater than zero");
        }

        this.values = values;
        this.columns = columns;
        this.rowPointers = rowPointers;

        this.input = input;
        this.output = output;

        this.startRow = startRow;
        this.endRow = endRow;

        this.threshold = threshold;
    }

    /**
     * Execută task-ul Fork/Join.
     *
     * Dacă intervalul este suficient de mic, calculul este executat
     * direct. Altfel, intervalul este împărțit în două subtask-uri.
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
     * alocat task-ului.
     */
    private void computeSequentially() {

        for (int row = startRow; row < endRow; row++) {

            int begin = rowPointers[row];
            int end = rowPointers[row + 1];

            double sum = 0.0;

            for (int index = begin; index < end; index++) {

                int column = columns[index];

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
     * @return pragul de divizare
     */
    public int getThreshold() {
        return threshold;
    }
}
