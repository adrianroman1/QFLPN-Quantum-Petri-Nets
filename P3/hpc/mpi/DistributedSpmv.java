package hpc.mpi;

import hpc.csr.SparseMatrixCSR;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

/**
 * P3 distributed CSR SpMV adapter.
 *
 * This class invokes a native MPI executable. It does not emulate MPI
 * with ForkJoinPool and does not claim that a local multi-process run
 * demonstrates inter-node scaling.
 *
 * Native protocol:
 *
 * Input:
 *   8 bytes  "P3SPMV01"
 *   6 x uint64 little-endian:
 *       rows, columns, nnz, vector_length, flags, reserved
 *   rows + 1 uint64 little-endian row pointers
 *   nnz uint64 little-endian column indices
 *   nnz IEEE-754 binary64 little-endian values
 *   columns IEEE-754 binary64 little-endian vector elements
 *
 * Output:
 *   8 bytes  "P3OUT001"
 *   uint64 rows
 *   uint64 status
 *   uint64 reserved
 *   rows IEEE-754 binary64 little-endian result elements
 *
 * The native backend currently uses MPI int counts and displacements.
 * It must reject unsupported dimensions; this adapter does not silently
 * split or truncate such inputs.
 *
 * Configuration:
 *   P3_MPI_EXECUTABLE  path to p3_mpi_spmv
 *   P3_MPI_LAUNCHER    MPI launcher; defaults to mpirun
 *
 * Invocation:
 *   mpirun -np <ranks> <executable> <input-file> <output-file>
 */
public final class DistributedSpmv {

    private static final byte[] INPUT_MAGIC =
            "P3SPMV01".getBytes(StandardCharsets.US_ASCII);

    private static final byte[] OUTPUT_MAGIC =
            "P3OUT001".getBytes(StandardCharsets.US_ASCII);

    private static final int OUTPUT_HEADER_BYTES = 32;

    private static final int PROTOCOL_FLAGS = 0;
    private static final int PROTOCOL_RESERVED = 0;

    private static final int DEFAULT_TIMEOUT_SECONDS = 600;
    private static final int MAX_LOG_CHARACTERS = 12_000;

    private DistributedSpmv() {
        throw new AssertionError("No instances.");
    }

    /**
     * Result of one completed distributed SpMV invocation.
     *
     * elapsedTime measures complete launcher process wall time.
     * It is not a communication-only or kernel-only timing.
     */
    public record Result(
            double[] values,
            int rows,
            int columns,
            int nnz,
            int processCount,
            Duration elapsedTime,
            int processExitCode) {

        public Result {
            Objects.requireNonNull(values, "values cannot be null");
            Objects.requireNonNull(
                    elapsedTime,
                    "elapsedTime cannot be null");

            if (rows < 0 || columns < 0 || nnz < 0) {
                throw new IllegalArgumentException(
                        "Result dimensions cannot be negative.");
            }

            if (values.length != rows) {
                throw new IllegalArgumentException(
                        "Result vector length must equal row count.");
            }

            if (processCount <= 0) {
                throw new IllegalArgumentException(
                        "Process count must be positive.");
            }

            if (processExitCode != 0) {
                throw new IllegalArgumentException(
                        "A successful result must have exit code zero.");
            }

            if (elapsedTime.isNegative()) {
                throw new IllegalArgumentException(
                        "Elapsed time cannot be negative.");
            }

            values = values.clone();

            for (int i = 0; i < values.length; i++) {
                if (!Double.isFinite(values[i])) {
                    throw new IllegalArgumentException(
                            "Result contains a non-finite value at index "
                                    + i + ".");
                }
            }
        }

        @Override
        public double[] values() {
            return values.clone();
        }
    }

    /**
     * Executes the native MPI backend using environment configuration.
     *
     * Required:
     *   P3_MPI_EXECUTABLE
     *
     * Optional:
     *   P3_MPI_LAUNCHER
     *
     * @param matrix canonical CSR matrix
     * @param x input vector
     * @param processCount number of MPI processes
     * @return validated global result
     */
    public static Result multiply(
            SparseMatrixCSR matrix,
            double[] x,
            int processCount)
            throws IOException, InterruptedException {

        String executable = System.getenv("P3_MPI_EXECUTABLE");

        if (executable == null || executable.isBlank()) {
            throw new IllegalStateException(
                    "P3_MPI_EXECUTABLE is not configured.");
        }

        String launcher = System.getenv("P3_MPI_LAUNCHER");

        if (launcher == null || launcher.isBlank()) {
            launcher = "mpirun";
        }

        return multiply(
                matrix,
                x,
                processCount,
                Path.of(launcher),
                Path.of(executable),
                Duration.ofSeconds(DEFAULT_TIMEOUT_SECONDS));
    }

    /**
     * Executes the native MPI backend with explicit launcher and
     * executable paths.
     *
     * A bare launcher name such as "mpirun" is deliberately preserved
     * so ProcessBuilder can resolve it through the operating-system PATH.
     * A launcher supplied with a directory component, such as
     * "./bin/mpirun", is resolved to an absolute path.
     *
     * The native executable is always resolved to an absolute path.
     *
     * @param matrix canonical CSR matrix
     * @param x input vector
     * @param processCount MPI process count
     * @param launcher MPI launcher, e.g. mpirun or srun
     * @param nativeExecutable compiled p3_mpi_spmv executable
     * @param timeout maximum wall-clock duration
     * @return validated global output vector and execution metadata
     */
    public static Result multiply(
            SparseMatrixCSR matrix,
            double[] x,
            int processCount,
            Path launcher,
            Path nativeExecutable,
            Duration timeout)
            throws IOException, InterruptedException {

        validateArguments(
                matrix,
                x,
                processCount,
                launcher,
                nativeExecutable,
                timeout);

        if (!matrix.isValid()) {
            throw new IllegalArgumentException(
                    "Input matrix is not a valid CSR matrix.");
        }

        if (x.length != matrix.getColumns()) {
            throw new IllegalArgumentException(
                    "Input vector length must equal matrix column count.");
        }

        validateFiniteVector(x, "Input vector");

        ensureNativeIntRange(
                matrix.getRows(),
                matrix.getColumns(),
                matrix.getNnz());

        String launcherCommand = resolveLauncherCommand(launcher);

        Path absoluteExecutable =
                nativeExecutable.toAbsolutePath().normalize();

        if (!Files.isRegularFile(absoluteExecutable)
                || !Files.isExecutable(absoluteExecutable)) {
            throw new IOException(
                    "MPI executable is missing or not executable: "
                            + absoluteExecutable);
        }

        Path temporaryDirectory =
                Files.createTempDirectory("p3-mpi-spmv-");

        Path requestFile =
                temporaryDirectory.resolve("request.p3mpi");

        Path responseFile =
                temporaryDirectory.resolve("response.p3mpi");

        Path processLog =
                temporaryDirectory.resolve("mpi-process.log");

        try {
            writeRequest(matrix, x, requestFile);

            ProcessBuilder processBuilder = new ProcessBuilder(
                    launcherCommand,
                    "-np",
                    Integer.toString(processCount),
                    absoluteExecutable.toString(),
                    requestFile.toString(),
                    responseFile.toString());

            /*
             * Redirecting output to a file avoids blocking the MPI
             * process because of an unconsumed stdout/stderr pipe.
             */
            processBuilder.redirectErrorStream(true);
            processBuilder.redirectOutput(processLog.toFile());

            long startNanos = System.nanoTime();
            Process process = processBuilder.start();

            boolean completed;

            try {
                completed = process.waitFor(
                        timeout.toMillis(),
                        TimeUnit.MILLISECONDS);
            } catch (InterruptedException exception) {
                terminateProcess(process);
                Thread.currentThread().interrupt();
                throw exception;
            }

            if (!completed) {
                terminateProcess(process);

                throw new IOException(
                        "MPI process exceeded timeout of "
                                + timeout.toMillis()
                                + " milliseconds. Log: "
                                + readLogIfPresent(processLog));
            }

            long elapsedNanos = System.nanoTime() - startNanos;
            int exitCode = process.exitValue();

            if (exitCode != 0) {
                throw new IOException(
                        "MPI process failed with exit code "
                                + exitCode
                                + ". Log: "
                                + readLogIfPresent(processLog));
            }

            if (!Files.isRegularFile(responseFile)) {
                throw new IOException(
                        "MPI process returned success but did not create "
                                + "the response file. Log: "
                                + readLogIfPresent(processLog));
            }

            double[] output = readResponse(
                    responseFile,
                    matrix.getRows());

            return new Result(
                    output,
                    matrix.getRows(),
                    matrix.getColumns(),
                    matrix.getNnz(),
                    processCount,
                    Duration.ofNanos(elapsedNanos),
                    exitCode);

        } finally {
            deleteIfExists(responseFile);
            deleteIfExists(requestFile);
            deleteIfExists(processLog);
            deleteIfExists(temporaryDirectory);
        }
    }

    /**
     * Preserves bare executable names for PATH lookup.
     *
     * Examples:
     *   mpirun       -> mpirun
     *   srun         -> srun
     *   ./mpirun     -> absolute path
     *   bin/mpirun   -> absolute path
     */
    private static String resolveLauncherCommand(Path launcher) {
        if (launcher.getParent() == null) {
            return launcher.toString();
        }

        return launcher.toAbsolutePath().normalize().toString();
    }

    private static void validateArguments(
            SparseMatrixCSR matrix,
            double[] x,
            int processCount,
            Path launcher,
            Path nativeExecutable,
            Duration timeout) {

        Objects.requireNonNull(matrix, "matrix cannot be null");
        Objects.requireNonNull(x, "input vector cannot be null");
        Objects.requireNonNull(launcher, "launcher cannot be null");
        Objects.requireNonNull(
                nativeExecutable,
                "nativeExecutable cannot be null");
        Objects.requireNonNull(timeout, "timeout cannot be null");

        if (processCount <= 0) {
            throw new IllegalArgumentException(
                    "MPI process count must be positive.");
        }

        if (launcher.toString().isBlank()) {
            throw new IllegalArgumentException(
                    "MPI launcher cannot be blank.");
        }

        if (nativeExecutable.toString().isBlank()) {
            throw new IllegalArgumentException(
                    "Native executable path cannot be blank.");
        }

        if (timeout.isZero() || timeout.isNegative()) {
            throw new IllegalArgumentException(
                    "Timeout must be strictly positive.");
        }

        if (timeout.toMillis() <= 0) {
            throw new IllegalArgumentException(
                    "Timeout must be at least one millisecond.");
        }
    }

    private static void validateFiniteVector(
            double[] vector,
            String description) {

        for (int i = 0; i < vector.length; i++) {
            if (!Double.isFinite(vector[i])) {
                throw new IllegalArgumentException(
                        description
                                + " contains a non-finite value at index "
                                + i + ".");
            }
        }
    }

    private static void ensureNativeIntRange(
            int rows,
            int columns,
            int nnz) {

        if (rows < 0 || columns < 0 || nnz < 0) {
            throw new IllegalArgumentException(
                    "CSR dimensions cannot be negative.");
        }

        /*
         * The Java matrix uses signed int32 dimensions and the current
         * C backend uses MPI int counts/displacements. This is a
         * deliberate range guard, not a claim of MPI large-count support.
         */
        if (rows == Integer.MAX_VALUE) {
            throw new IllegalArgumentException(
                    "Row count exceeds the supported native range.");
        }
    }

    private static void writeRequest(
            SparseMatrixCSR matrix,
            double[] x,
            Path requestFile) throws IOException {

        int rows = matrix.getRows();
        int columns = matrix.getColumns();
        int nnz = matrix.getNnz();

        int[] rowPointers = matrix.getRowPointers();
        int[] columnIndices = matrix.getColumnIndices();
        double[] values = matrix.getValues();

        if (rowPointers.length != rows + 1
                || columnIndices.length != nnz
                || values.length != nnz) {
            throw new IOException(
                    "CSR arrays have inconsistent dimensions.");
        }

        validateFiniteVector(values, "CSR values");

        try (DataOutputStream output = new DataOutputStream(
                new BufferedOutputStream(
                        Files.newOutputStream(requestFile)))) {

            output.write(INPUT_MAGIC);

            writeLittleEndianLong(output, rows);
            writeLittleEndianLong(output, columns);
            writeLittleEndianLong(output, nnz);
            writeLittleEndianLong(output, columns);
            writeLittleEndianLong(output, PROTOCOL_FLAGS);
            writeLittleEndianLong(output, PROTOCOL_RESERVED);

            int previousPointer = 0;

            for (int row = 0; row < rowPointers.length; row++) {
                int pointer = rowPointers[row];

                if (pointer < previousPointer || pointer < 0
                        || pointer > nnz) {
                    throw new IOException(
                            "Invalid CSR row pointer at index " + row);
                }

                writeLittleEndianLong(output, pointer);
                previousPointer = pointer;
            }

            if (rowPointers[0] != 0
                    || rowPointers[rows] != nnz) {
                throw new IOException(
                        "CSR row pointers must start at zero and end at NNZ.");
            }

            for (int i = 0; i < columnIndices.length; i++) {
                int column = columnIndices[i];

                if (column < 0 || column >= columns) {
                    throw new IOException(
                            "CSR column index is outside matrix bounds "
                                    + "at position " + i + ".");
                }

                writeLittleEndianLong(output, column);
            }

            for (double value : values) {
                writeLittleEndianDouble(output, value);
            }

            for (double value : x) {
                writeLittleEndianDouble(output, value);
            }

            output.flush();
        }
    }

    private static double[] readResponse(
            Path responseFile,
            int expectedRows) throws IOException {

        long expectedBytes =
                OUTPUT_HEADER_BYTES + 8L * expectedRows;

        long actualBytes = Files.size(responseFile);

        if (actualBytes != expectedBytes) {
            throw new IOException(
                    "MPI response has invalid length. Expected "
                            + expectedBytes + " bytes but received "
                            + actualBytes + ".");
        }

        double[] output = new double[expectedRows];

        try (DataInputStream input = new DataInputStream(
                new BufferedInputStream(
                        Files.newInputStream(responseFile)))) {

            byte[] magic = new byte[8];
            input.readFully(magic);

            if (!matches(magic, OUTPUT_MAGIC)) {
                throw new IOException(
                        "MPI response magic is invalid.");
            }

            long rows = readLittleEndianLong(input);
            long status = readLittleEndianLong(input);
            long reserved = readLittleEndianLong(input);

            if (rows != expectedRows) {
                throw new IOException(
                        "MPI response row count mismatch. Expected "
                                + expectedRows + " but received "
                                + rows + ".");
            }

            if (status != 0L) {
                throw new IOException(
                        "MPI backend reported failure status "
                                + status + ".");
            }

            if (reserved != 0L) {
                throw new IOException(
                        "MPI response reserved field must be zero.");
            }

            for (int i = 0; i < output.length; i++) {
                double value = readLittleEndianDouble(input);

                if (!Double.isFinite(value)) {
                    throw new IOException(
                            "MPI response contains a non-finite value "
                                    + "at row " + i + ".");
                }

                output[i] = value;
            }

            if (input.read() != -1) {
                throw new IOException(
                        "MPI response contains unexpected trailing bytes.");
            }

        } catch (EOFException exception) {
            throw new IOException(
                    "MPI response is truncated.",
                    exception);
        }

        return output;
    }

    private static void terminateProcess(Process process)
            throws InterruptedException {

        process.destroy();

        if (!process.waitFor(5, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            process.waitFor();
        }
    }

    private static void writeLittleEndianLong(
            DataOutputStream output,
            long value) throws IOException {

        output.writeLong(Long.reverseBytes(value));
    }

    private static long readLittleEndianLong(
            DataInputStream input) throws IOException {

        return Long.reverseBytes(input.readLong());
    }

    private static void writeLittleEndianDouble(
            DataOutputStream output,
            double value) throws IOException {

        writeLittleEndianLong(
                output,
                Double.doubleToRawLongBits(value));
    }

    private static double readLittleEndianDouble(
            DataInputStream input) throws IOException {

        return Double.longBitsToDouble(
                readLittleEndianLong(input));
    }

    private static boolean matches(
            byte[] actual,
            byte[] expected) {

        if (actual.length != expected.length) {
            return false;
        }

        for (int i = 0; i < actual.length; i++) {
            if (actual[i] != expected[i]) {
                return false;
            }
        }

        return true;
    }

    private static String readLogIfPresent(Path logFile) {
        try {
            if (!Files.isRegularFile(logFile)) {
                return "(no process log available)";
            }

            String content = Files.readString(logFile);

            if (content.length() > MAX_LOG_CHARACTERS) {
                return content.substring(0, MAX_LOG_CHARACTERS)
                        + "\n[log truncated]";
            }

            return content;

        } catch (IOException exception) {
            return "(could not read process log: "
                    + exception.getMessage() + ")";
        }
    }

    private static void deleteIfExists(Path path) {
        try {
            Files.deleteIfExists(path);
        } catch (IOException ignored) {
            /*
             * Cleanup must not replace the primary execution exception.
             * The uniquely named temporary directory can be inspected
             * or removed by an external cleanup policy.
             */
        }
    }
}
