package hpc.csr;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Independent, filesystem-free validator for benchmark metadata
 * and derived performance metrics.
 *
 * This class validates in-memory objects only.
 * It does not read CSV files, environment files, Git metadata,
 * or benchmark artifacts.
 */
public final class BenchmarkAuditValidator {

    private static final Pattern FULL_GIT_SHA =
            Pattern.compile("[0-9a-fA-F]{40}");

    private static final double RELATIVE_TOLERANCE =
            1.0e-8;

    private static final double ABSOLUTE_TOLERANCE =
            1.0e-12;

    private BenchmarkAuditValidator() {
        // Utility class.
    }

    /**
     * Validates a benchmark result and its provenance metadata.
     *
     * @param result benchmark result
     * @param environment execution environment information
     * @param metadata benchmark provenance metadata
     * @return immutable audit result
     */
    public static AuditResult validate(
            BenchmarkResult result,
            EnvironmentInfo environment,
            BenchmarkMetadata metadata) {

        List<String> failures = new ArrayList<>();

        if (result == null) {
            failures.add("Benchmark result is missing.");
        }

        if (environment == null) {
            failures.add("Environment metadata is missing.");
        }

        if (metadata == null) {
            failures.add("Benchmark metadata is missing.");
        }

        if (result == null
                || environment == null
                || metadata == null) {

            return failedAudit(failures);
        }

        validateBenchmarkIdentity(
                result,
                metadata,
                failures);

        validateCommitSha(
                metadata.commitSha(),
                "metadata.commitSha",
                failures);

        validateEnvironment(
                environment,
                failures);

        validateCommitConsistency(
                environment,
                metadata,
                failures);

        double sequentialMs =
                result.sequentialMs();

        double parallelMs =
                result.parallelMs();

        double calculatedSpeedup =
                Double.NaN;

        double calculatedReductionPercent =
                Double.NaN;

        boolean validTimes =
                Double.isFinite(sequentialMs)
                        && Double.isFinite(parallelMs)
                        && sequentialMs > 0.0
                        && parallelMs > 0.0;

        if (!validTimes) {

            failures.add(
                    "Sequential and parallel times must be finite "
                            + "and greater than zero.");

        } else {

            calculatedSpeedup =
                    sequentialMs / parallelMs;

            calculatedReductionPercent =
                    100.0 * (
                            1.0 - parallelMs / sequentialMs);

            if (!Double.isFinite(calculatedSpeedup)
                    || calculatedSpeedup <= 0.0) {

                failures.add(
                        "Recomputed speedup is not finite and positive.");
            }

            if (!Double.isFinite(calculatedReductionPercent)) {

                failures.add(
                        "Recomputed time reduction is not finite.");
            }

            validateStoredSpeedup(
                    result.speedup(),
                    calculatedSpeedup,
                    failures);
        }

        return new AuditResult(
                failures.isEmpty(),
                calculatedSpeedup,
                calculatedReductionPercent,
                failures);
    }

    private static void validateBenchmarkIdentity(
            BenchmarkResult result,
            BenchmarkMetadata metadata,
            List<String> failures) {

        if (isBlank(result.benchmarkId())) {
            failures.add(
                    "Benchmark result ID is missing.");
        }

        if (isBlank(metadata.benchmarkId())) {
            failures.add(
                    "Benchmark metadata ID is missing.");
        }

        if (!isBlank(result.benchmarkId())
                && !isBlank(metadata.benchmarkId())
                && !result.benchmarkId().equals(
                        metadata.benchmarkId())) {

            failures.add(
                    "Benchmark ID does not match metadata.");
        }
    }

    private static void validateEnvironment(
            EnvironmentInfo environment,
            List<String> failures) {

        if (isBlank(environment.javaVersion())) {
            failures.add(
                    "Java version is missing from environment metadata.");
        }

        if (isBlank(environment.operatingSystem())) {
            failures.add(
                    "Operating system is missing from environment metadata.");
        }

        if (isBlank(environment.cpuModel())) {
            failures.add(
                    "CPU model is missing from environment metadata.");
        }

        validateCommitSha(
                environment.commitSha(),
                "environment.commitSha",
                failures);
    }

    private static void validateCommitSha(
            String sha,
            String fieldName,
            List<String> failures) {

        if (sha == null
                || !FULL_GIT_SHA.matcher(sha).matches()) {

            failures.add(
                    fieldName
                            + " must contain a full 40-character Git SHA.");
        }
    }

    private static void validateCommitConsistency(
            EnvironmentInfo environment,
            BenchmarkMetadata metadata,
            List<String> failures) {

        if (isBlank(environment.commitSha())
                || isBlank(metadata.commitSha())) {
            return;
        }

        if (!environment.commitSha().equalsIgnoreCase(
                metadata.commitSha())) {

            failures.add(
                    "Environment commit SHA does not match "
                            + "benchmark metadata commit SHA.");
        }
    }

    private static void validateStoredSpeedup(
            double storedSpeedup,
            double calculatedSpeedup,
            List<String> failures) {

        if (!Double.isFinite(storedSpeedup)
                || storedSpeedup <= 0.0) {

            failures.add(
                    "Stored speedup must be finite and positive.");

            return;
        }

        if (!Double.isFinite(calculatedSpeedup)) {
            return;
        }

        if (!closeEnough(
                storedSpeedup,
                calculatedSpeedup)) {

            failures.add(
                    "Stored speedup does not match independently "
                            + "recomputed speedup.");
        }
    }

    private static boolean closeEnough(
            double actual,
            double expected) {

        double difference =
                Math.abs(actual - expected);

        double tolerance =
                Math.max(
                        ABSOLUTE_TOLERANCE,
                        RELATIVE_TOLERANCE
                                * Math.abs(expected));

        return difference <= tolerance;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static AuditResult failedAudit(
            List<String> failures) {

        return new AuditResult(
                false,
                Double.NaN,
                Double.NaN,
                failures);
    }
}
