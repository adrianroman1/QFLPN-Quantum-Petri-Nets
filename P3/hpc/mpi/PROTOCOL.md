# P3 Java–MPI Interoperability Protocol

Protocol version: 1
Project: QFLPN — P3 Distributed SpMV
Status: DESIGN CONTRACT — NOT YET IMPLEMENTED
Acceptance authority: p3_validation

## 1. Purpose

This document defines the binary interoperability contract between
the Java 21 P3 application and the native MPI backend based on the
Open MPI C API.

The protocol is independent of any unofficial Java MPI binding.

Java remains responsible for:
- input validation;
- CSR structural validation;
- process orchestration;
- experiment configuration;
- result validation;
- reproducibility metadata;
- integration with p3_validation.

The native MPI backend is responsible for:
- MPI initialization and finalization;
- rank and communicator management;
- distributed data movement;
- local CSR SpMV computation;
- result aggregation;
- communication timing.

## 2. Execution architecture

The initial implementation uses a separate native MPI executable.

Java launches the executable using ProcessBuilder.

The MPI executable is started by the configured MPI launcher.

The initial data-exchange mechanism uses versioned binary files.
Input preparation, MPI computation, and output collection must be
timed separately.

File I/O time must never be reported as pure SpMV kernel time.

The benchmark must report:
- input serialization time;
- MPI initialization time;
- distribution time;
- local computation time;
- aggregation time;
- output serialization time;
- end-to-end execution time.

## 3. Binary representation

All multibyte fields use little-endian byte order.

All floating-point values use IEEE 754 binary64 representation.

Unsigned integer fields are encoded using fixed-width 64-bit values
unless explicitly stated otherwise.

No compiler-dependent native structure layout is permitted.

No implicit padding is permitted.

## 4. Request file

Filename:

request.p3mpi

Magic:

P3SPMV01

The magic field consists of exactly 8 ASCII bytes.

Header layout:

| Offset | Size | Field | Type |
|---:|---:|---|---|
| 0 | 8 | magic | ASCII |
| 8 | 4 | protocol_version | uint32 |
| 12 | 4 | header_bytes | uint32 |
| 16 | 8 | rows | uint64 |
| 24 | 8 | columns | uint64 |
| 32 | 8 | nnz | uint64 |
| 40 | 8 | vector_length | uint64 |
| 48 | 4 | flags | uint32 |
| 52 | 4 | reserved | uint32 |

The version 1 header size is exactly 56 bytes.

Version 1 requires:

vector_length == columns

reserved == 0

Unknown flag bits must be rejected.

## 5. Request payload

The payload follows the header without padding.

The arrays appear in this exact order:

1. CSR row pointers
2. CSR column indices
3. CSR values
4. Input vector x

Array encoding:

| Array | Element type | Element count |
|---|---|---:|
| row_pointers | uint64 | rows + 1 |
| column_indices | uint64 | nnz |
| values | float64 | nnz |
| x | float64 | columns |

The final request file size must equal:

56 + 8(rows + 1) + 8(nnz) + 8(nnz) + 8(columns)

All size calculations must use checked arithmetic.

The implementation must reject:
- truncated files;
- trailing unexpected bytes;
- invalid magic;
- unsupported protocol versions;
- inconsistent dimensions;
- invalid CSR pointers;
- out-of-range column indices;
- NaN or infinite matrix values;
- NaN or infinite vector values;
- integer overflow;
- files exceeding configured resource limits.

## 6. CSR invariants

The input matrix must satisfy:

row_pointers[0] == 0

row_pointers[rows] == nnz

row_pointers[i] <= row_pointers[i + 1]

0 <= column_indices[k] < columns

The row pointer array must be monotonic.

The number of column indices and values must equal nnz.

The matrix must use the canonical CSR representation required by
the existing P3 implementation.

Empty rows are permitted.

A zero-NNZ matrix is permitted.

## 7. Distributed execution

The first MPI implementation uses contiguous row partitions.

Every matrix row belongs to exactly one MPI rank.

A row must never be split between ranks.

The initial vector policy is replicated input vector:

1. Rank 0 reads and validates the request.
2. Rank 0 distributes the required matrix partitions.
3. The input vector x is broadcast to all ranks.
4. Each rank computes its local output rows.
5. Local output segments are gathered in global row order.
6. Rank 0 validates and writes the complete result.

The initial implementation must not claim halo exchange,
overlapped communication, or communication avoidance.

Those are separate future optimizations.

## 8. MPI collective contract

The initial backend uses:

- MPI_Init / MPI_Finalize;
- MPI_Comm_rank;
- MPI_Comm_size;
- MPI_Bcast;
- MPI_Scatterv or an explicitly documented equivalent;
- MPI_Gatherv or an explicitly documented equivalent;
- MPI_Barrier only where required by the measurement protocol;
- MPI_Wtime for native timing.

All collective calls must be reached consistently by participating ranks.

MPI errors must not be silently ignored.

The implementation must define a fail-closed policy for rank failures.

MPI count and displacement limits must be checked before communication.

If a payload exceeds the supported MPI count range, the backend
must reject it or use an explicitly implemented chunked transfer.

## 9. Response file

Filename:

response.p3mpi

Magic:

P3OUT001

Header layout:

| Offset | Size | Field | Type |
|---:|---:|---|---|
| 0 | 8 | magic | ASCII |
| 8 | 4 | protocol_version | uint32 |
| 12 | 4 | header_bytes | uint32 |
| 16 | 8 | rows | uint64 |
| 24 | 4 | status | uint32 |
| 28 | 4 | reserved | uint32 |

Version 1 header size is exactly 32 bytes.

The response payload contains exactly:

rows float64 values

The response file size must equal:

32 + 8 * rows

The result must be finite.

The output row order must match the original global matrix row order.

## 10. Numerical correctness

The Java validation layer compares the distributed result against
the trusted sequential CSR SpMV result.

For each output row i:

y_reference[i] = sum(A[i,j] * x[j])

The validation report must include:

- maximum absolute error;
- maximum relative error;
- L2 error;
- reference norm;
- distributed result norm;
- comparison tolerance;
- number of rows checked;
- final numerical verdict.

Tolerance must be explicit and configurable.

Bitwise identity must not be claimed unless the reduction order
and floating-point execution are proven identical.

## 11. Timing contract

The following durations must be recorded separately:

- T_initialization
- T_distribution
- T_vector_broadcast
- T_local_spmv
- T_gather
- T_finalization
- T_end_to_end

The MPI kernel time is not interchangeable with end-to-end time.

The reported distributed runtime must state which timing definition
is used.

All ranks must record sufficient timing information to identify
the slowest rank.

The experiment report must include rank-level load imbalance.

## 12. Resource and safety limits

All dimensions and file sizes must be validated before allocation.

The implementation must reject negative, overflowing, or impossible
allocation sizes.

The implementation must not assume that 664 MPI ranks are optimal.

The number of MPI ranks, nodes, CPU binding, and memory allocation
must be obtained from the actual execution environment.

The proposed 16-node configuration is not proof of available hardware.

## 13. Versioning and compatibility

Protocol version 1 is immutable after acceptance.

Any incompatible change requires a new protocol version.

The Java adapter and native backend must report their protocol
versions.

A version mismatch must fail closed.

No silent fallback to a different protocol is permitted.

## 14. Required test cases

The implementation must test:

- empty matrix;
- zero-NNZ matrix;
- one-row matrix;
- rectangular matrix;
- empty CSR rows;
- uneven row partition;
- uneven NNZ distribution;
- more ranks than rows;
- one MPI rank;
- two MPI ranks;
- multiple MPI ranks;
- invalid column index;
- invalid row pointer;
- truncated request;
- invalid magic;
- unsupported version;
- non-finite values;
- output dimension mismatch;
- numerical disagreement.

## 15. CI acceptance

All checks must execute under the existing job:

p3_validation

The MPI smoke test must use a small deterministic matrix and
at least two MPI ranks.

The CI smoke test demonstrates MPI execution only.

It does not demonstrate multi-node HPC scaling.

The 16-node experiment must remain NOT_EVALUATED until an actual
Slurm allocation and real multi-node execution are recorded.

The workflow must preserve:

P3/MANIFEST.txt
P3/SHA256SUMS.txt

All new source files, test files, protocol documents, logs,
and generated reports must be included in the central integrity chain.

A failed compile, failed MPI launch, invalid result, or checksum
mismatch must fail p3_validation.

## 16. Acceptance status

This document defines the protocol contract only.

It does not implement MPI communication.

It does not establish a performance result.

It does not authorize P3_ACCEPTED.

Acceptance requires:
- native MPI backend implementation;
- Java adapter implementation;
- automated tests;
- successful two-rank CI smoke test;
- numerical validation;
- reproducible reports;
- final integrity verification through p3_validation.
