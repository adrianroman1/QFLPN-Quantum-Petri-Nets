package hpc.csr;

/**
 * MainApp
 *
 * Test de validare pentru nucleul CSR al proiectului QFLPN.
 *
 * Testul verifică:
 * 1. construirea unei matrice CSR;
 * 2. încărcarea matricei în QFLPNCoreEngine;
 * 3. multiplicarea secvențială y = A * x;
 * 4. multiplicarea paralelă y = A * x;
 * 5. compararea rezultatelor;
 * 6. afișarea metadatelor matricei.
 */
public final class MainApp {

    private MainApp() {
        // Utility class.
    }

    public static void main(String[] args) {

        System.out.println();
        System.out.println("==============================================");
        System.out.println(" QFLPN - CSR CORE VALIDATION TEST");
        System.out.println("==============================================");

        /*
         * Matricea testată:
         *
         * A =
         *
         * [ 1  0  2  0 ]
         * [ 0  3  0  4 ]
         * [ 5  0  6  0 ]
         * [ 0  7  0  8 ]
         *
         * Vector:
         *
         * x = [1, 2, 3, 4]^T
         *
         * Rezultat așteptat:
         *
         * y = [7, 22, 23, 46]^T
         */

        double[] values = {
                1.0, 2.0,
                3.0, 4.0,
                5.0, 6.0,
                7.0, 8.0
        };

        int[] columns = {
                0, 2,
                1, 3,
                0, 2,
                1, 3
        };

        int[] rowPointers = {
                0, 2, 4, 6, 8
        };

        double[] input = {
                1.0, 2.0, 3.0, 4.0
        };

        double[] expected = {
                7.0, 22.0, 23.0, 46.0
        };

        QFLPNCoreEngine engine =
                new QFLPNCoreEngine(4);

        engine.loadCSR(
                values,
                columns,
                rowPointers);

        System.out.println();
        System.out.println("[MATRIX]");
        System.out.println("Rows        : "
                + engine.getDimension());
        System.out.println("Columns     : "
                + engine.getMatrix().getColumns());
        System.out.println("NNZ         : "
                + engine.getNonZeroCount());
        System.out.println("Density     : "
                + engine.getMatrixDensity());

        System.out.println();
        System.out.println("[TEST] Sequential CSR x Vector");

        long sequentialStart =
                System.nanoTime();

        double[] sequentialResult =
                engine.multiply(input);

        long sequentialEnd =
                System.nanoTime();

        double sequentialTimeNs =
                sequentialEnd - sequentialStart;

        printVector(
                "Sequential result",
                sequentialResult);

        boolean sequentialCorrect =
                compareVectors(
                        sequentialResult,
                        expected,
                        1.0e-12);

        System.out.println(
                "Sequential correctness: "
                        + (sequentialCorrect
                        ? "PASS"
                        : "FAIL"));

        System.out.println(
                "Sequential time: "
                        + sequentialTimeNs
                        + " ns");

        System.out.println();
        System.out.println("[TEST] Parallel CSR x Vector");

        long parallelStart =
                System.nanoTime();

        double[] parallelResult =
                engine.multiplyParallel(
                        input,
                        1,
                        Math.max(
                                1,
                                Runtime.getRuntime()
                                        .availableProcessors()));

        long parallelEnd =
                System.nanoTime();

        double parallelTimeNs =
                parallelEnd - parallelStart;

        printVector(
                "Parallel result",
                parallelResult);

        boolean parallelCorrect =
                compareVectors(
                        parallelResult,
                        expected,
                        1.0e-12);

        System.out.println(
                "Parallel correctness: "
                        + (parallelCorrect
                        ? "PASS"
                        : "FAIL"));

        System.out.println(
                "Parallel time: "
                        + parallelTimeNs
                        + " ns");

        boolean sameResult =
                compareVectors(
                        sequentialResult,
                        parallelResult,
                        1.0e-12);

        System.out.println();
        System.out.println(
                "Sequential vs Parallel: "
                        + (sameResult
                        ? "MATCH"
                        : "MISMATCH"));

        boolean allPassed =
                sequentialCorrect
                        && parallelCorrect
                        && sameResult;

        System.out.println();
        System.out.println("==============================================");

        if (allPassed) {
            System.out.println(
                    " STATUS: PASS - CSR CORE VALIDAT");
        } else {
            System.out.println(
                    " STATUS: FAIL - VERIFICARE NECESARA");
        }

        System.out.println("==============================================");
        System.out.println();

        engine.shutdown();

        if (!allPassed) {
            throw new IllegalStateException(
                    "CSR validation test failed.");
        }
    }

    /**
     * Compară două vectori utilizând o toleranță absolută.
     */
    private static boolean compareVectors(
            double[] actual,
            double[] expected,
            double tolerance) {

        if (actual == null || expected == null) {
            return false;
        }

        if (actual.length != expected.length) {
            return false;
        }

        for (int i = 0; i < actual.length; i++) {

            if (Math.abs(
                    actual[i] - expected[i])
                    > tolerance) {

                return false;
            }
        }

        return true;
    }

    /**
     * Afișează un vector numeric.
     */
    private static void printVector(
            String label,
            double[] vector) {

        System.out.print(label + ": [");

        for (int i = 0; i < vector.length; i++) {

            if (i > 0) {
                System.out.print(", ");
            }

            System.out.print(vector[i]);
        }

        System.out.println("]");
    }
}
