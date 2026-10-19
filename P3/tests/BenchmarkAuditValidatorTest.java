package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BenchmarkAuditValidatorTest {

    private static final String SHA_A =
            "8c5238fba3f1d74305c5039a6f8a4529a09ade24";

    private static final String SHA_B =
            "47cdce78a28a1d7a3f097a869a206bd0ec72477d";

    @Test
    void testCompleteAuditPasses() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        validBenchmarkResult(),
                        validEnvironment(SHA_A),
                        validMetadata(SHA_A));

        assertTrue(audit.pass());
        assertEquals(0, audit.failures().size());
    }

    @Test
    void testAcceptsFullGitSha() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        validBenchmarkResult(),
                        validEnvironment(SHA_A),
                        validMetadata(SHA_A));

        assertTrue(audit.pass());
    }

    @Test
    void testRejectsInvalidCommitSha() {

        BenchmarkMetadata metadata =
                new BenchmarkMetadata(
                        "QFLPN-1M",
                        "1234");

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        validBenchmarkResult(),
                        validEnvironment(SHA_A),
                        metadata);

        assertFalse(audit.pass());
        assertTrue(
                audit.failures().stream()
                        .anyMatch(message ->
                                message.contains(
                                        "metadata.commitSha")));
    }

    @Test
    void testRejectsMissingBenchmarkIdInMetadata() {

        BenchmarkMetadata metadata =
                new BenchmarkMetadata(
                        "",
                        SHA_A);

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        validBenchmarkResult(),
                        validEnvironment(SHA_A),
                        metadata);

        assertFalse(audit.pass());
    }

    @Test
    void testRejectsZeroSequentialTime() {

        assertThrows(
                IllegalArgumentException.class,
                () -> benchmarkResult(
                        0.0,
                        500.0,
                        2.0));
    }

    @Test
    void testRejectsNegativeParallelTime() {

        assertThrows(
                IllegalArgumentException.class,
                () -> benchmarkResult(
                        1000.0,
                        -1.0,
                        2.0));
    }

    @Test
    void testSpeedupRecalculation() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        benchmarkResult(
                                1000.0,
                                500.0,
                                2.0),
                        validEnvironment(SHA_A),
                        validMetadata(SHA_A));

        assertTrue(audit.pass());

        assertEquals(
                2.0,
                audit.speedup(),
                1.0e-12);
    }

    @Test
    void testRejectsInconsistentStoredSpeedup() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        benchmarkResult(
                                1000.0,
                                500.0,
                                999.0),
                        validEnvironment(SHA_A),
                        validMetadata(SHA_A));

        assertFalse(audit.pass());

        assertTrue(
                audit.failures().stream()
                        .anyMatch(message ->
                                message.contains("speedup")));
    }

    @Test
    void testReductionCalculation() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        benchmarkResult(
                                1000.0,
                                500.0,
                                2.0),
                        validEnvironment(SHA_A),
                        validMetadata(SHA_A));

        assertTrue(audit.pass());

        assertEquals(
                50.0,
                audit.reductionPercent(),
                1.0e-12);
    }

    @Test
    void testNegativeReductionAllowed() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        benchmarkResult(
                                1000.0,
                                1500.0,
                                1000.0 / 1500.0),
                        validEnvironment(SHA_A),
                        validMetadata(SHA_A));

        assertTrue(audit.pass());

        assertEquals(
                -50.0,
                audit.reductionPercent(),
                1.0e-12);
    }

    @Test
    void testRejectsMissingEnvironmentData() {

        EnvironmentInfo environment =
                new EnvironmentInfo(
                        "",
                        "",
                        "",
                        "");

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        validBenchmarkResult(),
                        environment,
                        validMetadata(SHA_A));

        assertFalse(audit.pass());
        assertTrue(audit.failures().size() >= 4);
    }

    @Test
    void testRejectsEnvironmentCommitMismatch() {

        AuditResult audit =
                BenchmarkAuditValidator.validate(
                        validBenchmarkResult(),
                        validEnvironment(SHA_B),
                        validMetadata(SHA_A));

        assertFalse(audit.pass());

        assertTrue(
                audit.failures().stream()
                        .anyMatch(message ->
                                message.contains(
                                        "does not match")));
    }

    private static BenchmarkResult validBenchmarkResult() {
        return benchmarkResult(
                1000.0,
                500.0,
                2.0);
    }

    private static BenchmarkResult benchmarkResult(
            double sequentialMs,
            double parallelMs,
            double speedup) {

        return new BenchmarkResult(
                "2026-10-19T21:18:32Z",
                "QFLPN-1M",
                1_000_000,
                2_000_000L,
                2,
                4096,
                5,
                10,
                sequentialMs,
                parallelMs,
                speedup,
                1_000_000.0,
                2_000_000.0,
                0.0,
                0.0,
                0.0,
                1.0,
                "x86_64",
                4_294_967_296L,
                "21",
                "Linux",
                "JUnit benchmark audit test");
    }

    private static EnvironmentInfo validEnvironment(
            String commitSha) {

        return new EnvironmentInfo(
                "21",
                "Linux",
                "x86_64",
                commitSha);
    }

    private static BenchmarkMetadata validMetadata(
            String commitSha) {

        return new BenchmarkMetadata(
                "QFLPN-1M",
                commitSha);
    }
}
