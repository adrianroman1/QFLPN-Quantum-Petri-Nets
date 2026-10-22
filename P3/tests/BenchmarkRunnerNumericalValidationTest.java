package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class BenchmarkRunnerNumericalValidationTest {

    @Test
    void shouldRejectNaNOutput() {
        double[] output = {
                Double.NaN
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxExpectedError(
                        output,
                        1.0));
    }

    @Test
    void shouldRejectPositiveInfinityOutput() {
        double[] output = {
                Double.POSITIVE_INFINITY
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxExpectedError(
                        output,
                        1.0));
    }

    @Test
    void shouldRejectNegativeInfinityOutput() {
        double[] output = {
                Double.NEGATIVE_INFINITY
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxExpectedError(
                        output,
                        1.0));
    }

    @Test
    void shouldRejectNaNComputedError() {
        double[] reference = {
                1.0
        };

        double[] actual = {
                Double.NaN
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxAbsoluteError(
                        reference,
                        actual));
    }

    @Test
    void shouldRejectInfiniteComputedAbsoluteError() {
        double[] first = {
                Double.MAX_VALUE
        };

        double[] second = {
                -Double.MAX_VALUE
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxAbsoluteError(
                        first,
                        second));
    }

    @Test
    void shouldRejectInfiniteComputedExpectedError() {
        double[] output = {
                Double.MAX_VALUE
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxExpectedError(
                        output,
                        -Double.MAX_VALUE));
    }

    @Test
    void shouldRejectNonFiniteExpectedValue() {
        double[] output = {
                1.0
        };

        assertThrows(
                IllegalStateException.class,
                () -> BenchmarkRunner.maxExpectedError(
                        output,
                        Double.NaN));
    }

    @Test
    void shouldRejectNullOutputVector() {
        assertThrows(
                IllegalArgumentException.class,
                () -> BenchmarkRunner.maxExpectedError(
                        null,
                        1.0));
    }

    @Test
    void shouldCalculateFiniteAbsoluteError() {
        double[] first = {
                1.0,
                2.0,
                3.0
        };

        double[] second = {
                1.0,
                2.000000000001,
                3.0
        };

        double error =
                assertDoesNotThrow(
                        () -> BenchmarkRunner.maxAbsoluteError(
                                first,
                                second));

        assertEquals(
                1.000088900582341E-12,
                error,
                1.0E-15);
    }

    @Test
    void shouldCalculateFiniteExpectedError() {
        double[] output = {
                1.5,
                1.5,
                1.5
        };

        double error =
                assertDoesNotThrow(
                        () -> BenchmarkRunner.maxExpectedError(
                                output,
                                1.5));

        assertEquals(
                0.0,
                error,
                0.0);
    }
}
