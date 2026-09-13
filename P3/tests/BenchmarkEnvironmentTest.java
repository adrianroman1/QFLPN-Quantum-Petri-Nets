package hpc.csr;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BenchmarkEnvironmentTest {

    @Test
    void shouldCaptureCurrentEnvironment() {

        BenchmarkEnvironment environment =
                BenchmarkEnvironment.capture();

        assertNotNull(environment);

        assertTrue(
                environment.availableProcessors() > 0);

        assertTrue(
                environment.maxJvmMemoryBytes() > 0L);

        assertTrue(
                environment.cpuArchitecture() != null
                        && !environment.cpuArchitecture()
                        .isBlank());

        assertTrue(
                environment.javaVersion() != null
                        && !environment.javaVersion()
                        .isBlank());

        assertTrue(
                environment.javaVmName() != null
                        && !environment.javaVmName()
                        .isBlank());

        assertTrue(
                environment.operatingSystem() != null
                        && !environment.operatingSystem()
                        .isBlank());

        assertTrue(
                environment.operatingSystemVersion() != null
                        && !environment.operatingSystemVersion()
                        .isBlank());
    }

    @Test
    void shouldGenerateDescription() {

        BenchmarkEnvironment environment =
                new BenchmarkEnvironment(
                        "x86_64",
                        4,
                        4_000_000_000L,
                        "21.0.12",
                        "OpenJDK 64-Bit Server VM",
                        "Linux",
                        "6.8");

        String description =
                environment.description();

        assertTrue(
                description.contains(
                        "x86_64"));

        assertTrue(
                description.contains(
                        "processors=4"));

        assertTrue(
                description.contains(
                        "21.0.12"));

        assertTrue(
                description.contains(
                        "Linux"));
    }

    @Test
    void shouldRejectBlankArchitecture() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new BenchmarkEnvironment(
                                "",
                                4,
                                1L,
                                "21",
                                "JVM",
                                "Linux",
                                "6.8"));
    }

    @Test
    void shouldRejectNonPositiveProcessors() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new BenchmarkEnvironment(
                                "x86_64",
                                0,
                                1L,
                                "21",
                                "JVM",
                                "Linux",
                                "6.8"));
    }

    @Test
    void shouldRejectNegativeJvmMemory() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new BenchmarkEnvironment(
                                "x86_64",
                                4,
                                -1L,
                                "21",
                                "JVM",
                                "Linux",
                                "6.8"));
    }

    @Test
    void shouldRejectBlankJavaVersion() {

        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new BenchmarkEnvironment(
                                "x86_64",
                                4,
                                1L,
                                "",
                                "JVM",
                                "Linux",
                                "6.8"));
    }

    @Test
    void shouldExposeConstructorValues() {

        BenchmarkEnvironment environment =
                new BenchmarkEnvironment(
                        "aarch64",
                        8,
                        8_000_000_000L,
                        "21.0.12",
                        "OpenJDK",
                        "Ubuntu",
                        "24.04");

        assertEquals(
                "aarch64",
                environment.cpuArchitecture());

        assertEquals(
                8,
                environment.availableProcessors());

        assertEquals(
                8_000_000_000L,
                environment.maxJvmMemoryBytes());

        assertEquals(
                "21.0.12",
                environment.javaVersion());

        assertEquals(
                "OpenJDK",
                environment.javaVmName());

        assertEquals(
                "Ubuntu",
                environment.operatingSystem());

        assertEquals(
                "24.04",
                environment.operatingSystemVersion());
    }
}
