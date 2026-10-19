package hpc.csr;

/**
 * Provenance metadata associated with one benchmark result.
 *
 * The commit SHA is expected to identify the repository revision
 * from which the benchmark was executed.
 */
public record BenchmarkMetadata(
        String benchmarkId,
        String commitSha) {
}
