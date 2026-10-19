package hpc.csr;

import java.util.List;

/**
 * Immutable outcome of an independent benchmark audit.
 *
 * speedup is calculated as:
 * sequential time / parallel time
 *
 * reductionPercent is calculated as:
 * 100 * (1 - parallel time / sequential time)
 *
 * A negative reduction is valid and indicates a slowdown.
 */
public record AuditResult(
        boolean pass,
        double speedup,
        double reductionPercent,
        List<String> failures) {

    public AuditResult {
        failures = failures == null
                ? List.of()
                : List.copyOf(failures);

        if (pass && !failures.isEmpty()) {
            throw new IllegalArgumentException(
                    "A passing audit cannot contain failures.");
        }

        if (!pass && failures.isEmpty()) {
            throw new IllegalArgumentException(
                    "A failing audit must contain at least one failure.");
        }
    }
}
