package hpc.csr;

/**
 * Execution environment metadata used by the benchmark audit.
 *
 * Values are deliberately not validated in the constructor:
 * BenchmarkAuditValidator must be able to report incomplete
 * or inconsistent metadata as an audit failure.
 */
public record EnvironmentInfo(
        String javaVersion,
        String operatingSystem,
        String cpuModel,
        String commitSha) {
}
