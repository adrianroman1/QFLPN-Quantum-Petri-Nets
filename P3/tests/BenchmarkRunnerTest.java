package hpc.csr;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class BenchmarkRunnerTest {
    @Test void computesMeanMedianAndPopulationDeviation() {
        double[] x={1.0,2.0,3.0,4.0};
        assertEquals(2.5,BenchmarkRunner.mean(x),1e-12);
        assertEquals(2.5,BenchmarkRunner.median(x),1e-12);
        assertEquals(Math.sqrt(1.25),BenchmarkRunner.populationStdDev(x),1e-12);
    }
    @Test void medianHandlesOddSampleCount() { assertEquals(2.0,BenchmarkRunner.median(new double[]{9,2,1}),1e-12); }
    @Test void rejectsEmptySamples() { assertThrows(IllegalArgumentException.class,()->BenchmarkRunner.mean(new double[0])); }
    @Test void rejectsNonFiniteSamples() { assertThrows(IllegalArgumentException.class,()->BenchmarkRunner.median(new double[]{1,Double.NaN})); }
    @Test void comparesAgainstIndependentVector() { assertEquals(0.0,BenchmarkRunner.maxAbsoluteError(new double[]{1.5,1.5},new double[]{1.5,1.5}),0.0); }
    @Test void rejectsDifferentVectorLengths() { assertThrows(IllegalArgumentException.class,()->BenchmarkRunner.maxAbsoluteError(new double[]{1},new double[]{1,2})); }
}
