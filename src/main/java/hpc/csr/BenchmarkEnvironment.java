package hpc.csr;

/**
 * Describes the execution environment used for a benchmark.
 *
 * The information is intended for reproducibility and research
 * reporting rather than for performance measurement itself.
 */
public record BenchmarkEnvironment(
        String cpuArchitecture,
        int availableProcessors,
        long maxJvmMemoryBytes,
        String javaVersion,
        String javaVmName,
        String operatingSystem,
        String operatingSystemVersion) {

    public BenchmarkEnvironment {

        if (cpuArchitecture == null
                || cpuArchitecture.isBlank()) {

            throw new IllegalArgumentException(
                    "cpuArchitecture must not be blank");
        }

        if (availableProcessors <= 0) {

            throw new IllegalArgumentException(
                    "availableProcessors must be > 0");
        }

        if (maxJvmMemoryBytes < 0L) {

            throw new IllegalArgumentException(
                    "maxJvmMemoryBytes must be >= 0");
        }

        if (javaVersion == null
                || javaVersion.isBlank()) {

            throw new IllegalArgumentException(
                    "javaVersion must not be blank");
        }

        if (javaVmName == null
                || javaVmName.isBlank()) {

            throw new IllegalArgumentException(
                    "javaVmName must not be blank");
        }

        if (operatingSystem == null
                || operatingSystem.isBlank()) {

            throw new IllegalArgumentException(
                    "operatingSystem must not be blank");
        }

        if (operatingSystemVersion == null
                || operatingSystemVersion.isBlank()) {

            throw new IllegalArgumentException(
                    "operatingSystemVersion must not be blank");
        }
    }

    /**
     * Captures the JVM-visible execution environment.
     */
    public static BenchmarkEnvironment capture() {

        Runtime runtime =
                Runtime.getRuntime();

        return new BenchmarkEnvironment(
                System.getProperty(
                        "os.arch",
                        "unknown"),
                runtime.availableProcessors(),
                runtime.maxMemory(),
                System.getProperty(
                        "java.version",
                        "unknown"),
                System.getProperty(
                        "java.vm.name",
                        "unknown"),
                System.getProperty(
                        "os.name",
                        "unknown"),
                System.getProperty(
                        "os.version",
                        "unknown"));
    }

    /**
     * Returns a compact human-readable description.
     */
    public String description() {

        return cpuArchitecture
                + ", processors="
                + availableProcessors
                + ", JVM="
                + javaVersion
                + " ("
                + javaVmName
                + "), OS="
                + operatingSystem
                + " "
                + operatingSystemVersion
                + ", maxJvmMemory="
                + maxJvmMemoryBytes
                + " bytes";
    }
}
