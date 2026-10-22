package hpc.csr;

import java.util.Objects;
import java.util.concurrent.RecursiveAction;

/**
 * Fork/Join task pentru multiplicarea unei matrice CSR cu un vector:
 * y = A * x.
 *
 * Partiționarea se face pe rânduri. Fiecare subtask scrie exclusiv
 * în intervalul propriu din vectorul de ieșire.
 *
 * Matricile dreptunghiulare sunt acceptate: startRow/endRow se
 * raportează la rândurile matricei și la vectorul de ieșire, nu
 * la dimensiunea vectorului de intrare.
 */
public final class MultiplyTask extends RecursiveAction {

    private static final long serialVersionUID = 1L;

    private final double[] values;
    private final int[] columns;
    private final int[] rowPointers;
    private final double[] input;
    private final double[] output;
    private final int startRow;
    private final int endRow;
    private final int threshold;

    /**
     * @param values valorile nenule CSR
     * @param columns indicii coloanelor
     * @param rowPointers pointerii CSR ai rândurilor
     * @param input vectorul de intrare
     * @param output vectorul rezultat
     * @param startRow primul rând inclus
     * @param endRow ultimul rând exclus
     * @param threshold numărul maxim de rânduri calculate direct
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

        this.values = Objects.requireNonNull(values, "values cannot be null");
        this.columns = Objects.requireNonNull(columns, "columns cannot be null");
        this.rowPointers = Objects.requireNonNull(
                rowPointers, "rowPointers cannot be null");
        this.input = Objects.requireNonNull(input, "input cannot be null");
        this.output = Objects.requireNonNull(output, "output cannot be null");

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

        /*
         * endRow este exclusiv și reprezintă un indice de rând.
         * Numărul de rânduri poate depăși numărul de coloane.
         * Prin urmare, nu comparăm startRow cu input.length.
         */
        if (endRow > output.length) {
            throw new IllegalArgumentException(
                    "endRow exceeds output vector length");
        }

        this.startRow = startRow;
        this.endRow = endRow;
        this.threshold = threshold;
    }

    @Override
    protected void compute() {
        int rowCount = endRow - startRow;

        if (rowCount <= threshold) {
            computeSequentially();
            return;
        }

        int middle = startRow + rowCount / 2;

        MultiplyTask leftTask = new MultiplyTask(
                values, columns, rowPointers, input, output,
                startRow, middle, threshold);

        MultiplyTask rightTask = new MultiplyTask(
                values, columns, rowPointers, input, output,
                middle, endRow, threshold);

        invokeAll(leftTask, rightTask);
    }

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

    public int getStartRow() {
        return startRow;
    }

    public int getEndRow() {
        return endRow;
    }

    public int getThreshold() {
        return threshold;
    }
}
