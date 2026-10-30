#include <mpi.h>

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#define REQUEST_MAGIC "P3SPMV01"
#define RESPONSE_MAGIC "P3OUT001"
#define PROTOCOL_VERSION 1U
#define REQUEST_HEADER_BYTES 56U
#define RESPONSE_HEADER_BYTES 32U

#define EXIT_INPUT_ERROR 10
#define EXIT_PROTOCOL_ERROR 11
#define EXIT_MPI_ERROR 12
#define EXIT_OUTPUT_ERROR 13
#define EXIT_RESOURCE_ERROR 14

typedef struct {
    uint64_t rows;
    uint64_t columns;
    uint64_t nnz;
    uint64_t vector_length;
    uint32_t flags;
} RequestHeader;

static int checked_mul_u64(uint64_t a, uint64_t b, uint64_t *out) {
    if (a != 0 && b > UINT64_MAX / a) {
        return 0;
    }
    *out = a * b;
    return 1;
}

static int checked_add_u64(uint64_t a, uint64_t b, uint64_t *out) {
    if (b > UINT64_MAX - a) {
        return 0;
    }
    *out = a + b;
    return 1;
}

static uint32_t read_u32_le(const unsigned char *p) {
    return ((uint32_t)p[0])
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static uint64_t read_u64_le(const unsigned char *p) {
    return ((uint64_t)p[0])
        | ((uint64_t)p[1] << 8)
        | ((uint64_t)p[2] << 16)
        | ((uint64_t)p[3] << 24)
        | ((uint64_t)p[4] << 32)
        | ((uint64_t)p[5] << 40)
        | ((uint64_t)p[6] << 48)
        | ((uint64_t)p[7] << 56);
}

static void write_u32_le(unsigned char *p, uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i) {
        p[i] = (unsigned char)((value >> (8U * i)) & 0xffU);
    }
}

static void write_u64_le(unsigned char *p, uint64_t value) {
    for (unsigned int i = 0; i < 8; ++i) {
        p[i] = (unsigned char)((value >> (8U * i)) & 0xffU);
    }
}

static int read_exact(FILE *file, void *buffer, size_t bytes) {
    return fread(buffer, 1, bytes, file) == bytes;
}

static int write_exact(FILE *file, const void *buffer, size_t bytes) {
    return fwrite(buffer, 1, bytes, file) == bytes;
}

static int read_request(
    const char *path,
    RequestHeader *header,
    uint64_t **row_ptr,
    uint64_t **column_indices,
    double **values,
    double **x
) {
    FILE *file = NULL;
    unsigned char raw[REQUEST_HEADER_BYTES];
    uint64_t expected_size = REQUEST_HEADER_BYTES;
    uint64_t part = 0;
    int result = EXIT_INPUT_ERROR;

    *row_ptr = NULL;
    *column_indices = NULL;
    *values = NULL;
    *x = NULL;

    file = fopen(path, "rb");
    if (file == NULL) {
        fprintf(stderr, "Cannot open request file: %s\n", path);
        goto cleanup;
    }

    if (!read_exact(file, raw, sizeof(raw))) {
        fprintf(stderr, "Truncated request header.\n");
        goto cleanup;
    }

    if (memcmp(raw, REQUEST_MAGIC, 8) != 0) {
        fprintf(stderr, "Invalid request magic.\n");
        result = EXIT_PROTOCOL_ERROR;
        goto cleanup;
    }

    if (read_u32_le(raw + 8) != PROTOCOL_VERSION
            || read_u32_le(raw + 12) != REQUEST_HEADER_BYTES) {
        fprintf(stderr, "Unsupported request protocol/header size.\n");
        result = EXIT_PROTOCOL_ERROR;
        goto cleanup;
    }

    header->rows = read_u64_le(raw + 16);
    header->columns = read_u64_le(raw + 24);
    header->nnz = read_u64_le(raw + 32);
    header->vector_length = read_u64_le(raw + 40);
    header->flags = read_u32_le(raw + 48);

    if (read_u32_le(raw + 52) != 0 || header->flags != 0) {
        fprintf(stderr, "Unsupported flags or nonzero reserved field.\n");
        result = EXIT_PROTOCOL_ERROR;
        goto cleanup;
    }

    if (header->vector_length != header->columns) {
        fprintf(stderr, "Vector length must equal matrix columns.\n");
        result = EXIT_PROTOCOL_ERROR;
        goto cleanup;
    }

    /*
     * MPI Scatterv/Gatherv use int counts and displacements in this
     * implementation. Reject larger inputs rather than truncating them.
     */
    if (header->rows > INT_MAX
            || header->columns > INT_MAX
            || header->nnz > INT_MAX) {
        fprintf(stderr, "Input exceeds MPI int count/displacement limits.\n");
        result = EXIT_RESOURCE_ERROR;
        goto cleanup;
    }

    if (!checked_add_u64(header->rows, 1, &part)
            || !checked_mul_u64(part, 8, &part)
            || !checked_add_u64(expected_size, part, &expected_size)
            || !checked_mul_u64(header->nnz, 8, &part)
            || !checked_add_u64(expected_size, part, &expected_size)
            || !checked_mul_u64(header->nnz, 8, &part)
            || !checked_add_u64(expected_size, part, &expected_size)
            || !checked_mul_u64(header->columns, 8, &part)
            || !checked_add_u64(expected_size, part, &expected_size)) {
        fprintf(stderr, "Request size arithmetic overflow.\n");
        result = EXIT_RESOURCE_ERROR;
        goto cleanup;
    }

    if (expected_size > (uint64_t)LLONG_MAX) {
        fprintf(stderr, "Request file exceeds supported file size.\n");
        result = EXIT_RESOURCE_ERROR;
        goto cleanup;
    }

    if (fseeko(file, 0, SEEK_END) != 0) {
        fprintf(stderr, "Cannot determine request file size.\n");
        goto cleanup;
    }

    off_t actual_size = ftello(file);
    if (actual_size < 0 || (uint64_t)actual_size != expected_size) {
        fprintf(stderr, "Request file size mismatch.\n");
        result = EXIT_PROTOCOL_ERROR;
        goto cleanup;
    }

    if (fseeko(file, REQUEST_HEADER_BYTES, SEEK_SET) != 0) {
        fprintf(stderr, "Cannot seek to request payload.\n");
        goto cleanup;
    }

    if (header->rows + 1 > SIZE_MAX / sizeof(uint64_t)
            || header->nnz > SIZE_MAX / sizeof(uint64_t)
            || header->nnz > SIZE_MAX / sizeof(double)
            || header->columns > SIZE_MAX / sizeof(double)) {
        fprintf(stderr, "Allocation size overflow.\n");
        result = EXIT_RESOURCE_ERROR;
        goto cleanup;
    }

    *row_ptr = malloc((size_t)(header->rows + 1) * sizeof(uint64_t));
    *column_indices = malloc((size_t)header->nnz * sizeof(uint64_t));
    *values = malloc((size_t)header->nnz * sizeof(double));
    *x = malloc((size_t)header->columns * sizeof(double));

    if (*row_ptr == NULL || (header->nnz > 0
            && (*column_indices == NULL || *values == NULL))
            || (header->columns > 0 && *x == NULL)) {
        fprintf(stderr, "Request allocation failed.\n");
        result = EXIT_RESOURCE_ERROR;
        goto cleanup;
    }

    for (uint64_t i = 0; i <= header->rows; ++i) {
        unsigned char b[8];
        if (!read_exact(file, b, 8)) {
            fprintf(stderr, "Truncated CSR row pointer array.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
        (*row_ptr)[i] = read_u64_le(b);
    }

    for (uint64_t i = 0; i < header->nnz; ++i) {
        unsigned char b[8];
        if (!read_exact(file, b, 8)) {
            fprintf(stderr, "Truncated CSR column index array.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
        (*column_indices)[i] = read_u64_le(b);
    }

    for (uint64_t i = 0; i < header->nnz; ++i) {
        unsigned char b[8];
        uint64_t bits;
        if (!read_exact(file, b, 8)) {
            fprintf(stderr, "Truncated CSR value array.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
        bits = read_u64_le(b);
        memcpy(&(*values)[i], &bits, sizeof(bits));
        if (!isfinite((*values)[i])) {
            fprintf(stderr, "Non-finite matrix value.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
    }

    for (uint64_t i = 0; i < header->columns; ++i) {
        unsigned char b[8];
        uint64_t bits;
        if (!read_exact(file, b, 8)) {
            fprintf(stderr, "Truncated input vector.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
        bits = read_u64_le(b);
        memcpy(&(*x)[i], &bits, sizeof(bits));
        if (!isfinite((*x)[i])) {
            fprintf(stderr, "Non-finite input vector value.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
    }

    if ((*row_ptr)[0] != 0 || (*row_ptr)[header->rows] != header->nnz) {
        fprintf(stderr, "Invalid CSR row pointer endpoints.\n");
        result = EXIT_PROTOCOL_ERROR;
        goto cleanup;
    }

    for (uint64_t i = 0; i < header->rows; ++i) {
        if ((*row_ptr)[i] > (*row_ptr)[i + 1]) {
            fprintf(stderr, "CSR row pointers are not monotonic.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
    }

    for (uint64_t i = 0; i < header->nnz; ++i) {
        if ((*column_indices)[i] >= header->columns) {
            fprintf(stderr, "CSR column index out of range.\n");
            result = EXIT_PROTOCOL_ERROR;
            goto cleanup;
        }
    }

    result = 0;

cleanup:
    if (file != NULL) {
        fclose(file);
    }

    if (result != 0) {
        free(*row_ptr);
        free(*column_indices);
        free(*values);
        free(*x);
        *row_ptr = NULL;
        *column_indices = NULL;
        *values = NULL;
        *x = NULL;
    }

    return result;
}

static int write_response(
    const char *path,
    uint64_t rows,
    const double *y
) {
    FILE *file = fopen(path, "wb");
    unsigned char header[RESPONSE_HEADER_BYTES];

    if (file == NULL) {
        fprintf(stderr, "Cannot create response file: %s\n", path);
        return EXIT_OUTPUT_ERROR;
    }

    memset(header, 0, sizeof(header));
    memcpy(header, RESPONSE_MAGIC, 8);
    write_u32_le(header + 8, PROTOCOL_VERSION);
    write_u32_le(header + 12, RESPONSE_HEADER_BYTES);
    write_u64_le(header + 16, rows);
    write_u32_le(header + 24, 0);
    write_u32_le(header + 28, 0);

    if (!write_exact(file, header, sizeof(header))) {
        fclose(file);
        return EXIT_OUTPUT_ERROR;
    }

    for (uint64_t i = 0; i < rows; ++i) {
        uint64_t bits;
        unsigned char b[8];

        if (!isfinite(y[i])) {
            fprintf(stderr, "Non-finite output value at row %" PRIu64 ".\n", i);
            fclose(file);
            return EXIT_OUTPUT_ERROR;
        }

        memcpy(&bits, &y[i], sizeof(bits));
        write_u64_le(b, bits);

        if (!write_exact(file, b, sizeof(b))) {
            fclose(file);
            return EXIT_OUTPUT_ERROR;
        }
    }

    if (fflush(file) != 0) {
        fclose(file);
        return EXIT_OUTPUT_ERROR;
    }

    if (fclose(file) != 0) {
        return EXIT_OUTPUT_ERROR;
    }

    return 0;
}

static void free_all(
    uint64_t *row_ptr,
    uint64_t *columns,
    double *values,
    double *x,
    double *local_y,
    double *global_y,
    int *row_counts,
    int *row_displs,
    int *nnz_counts,
    int *nnz_displs,
    uint64_t *local_row_ptr,
    uint64_t *local_columns,
    double *local_values
) {
    free(row_ptr);
    free(columns);
    free(values);
    free(x);
    free(local_y);
    free(global_y);
    free(row_counts);
    free(row_displs);
    free(nnz_counts);
    free(nnz_displs);
    free(local_row_ptr);
    free(local_columns);
    free(local_values);
}

int main(int argc, char **argv) {
    int rank = 0;
    int process_count = 0;
    int mpi_initialized = 0;
    int exit_code = 0;

    RequestHeader request = {0, 0, 0, 0, 0};

    uint64_t *global_row_ptr = NULL;
    uint64_t *global_columns = NULL;
    double *global_values = NULL;
    double *x = NULL;
    double *global_y = NULL;
    double *local_y = NULL;

    int *row_counts = NULL;
    int *row_displs = NULL;
    int *nnz_counts = NULL;
    int *nnz_displs = NULL;

    uint64_t *local_row_ptr = NULL;
    uint64_t *local_columns = NULL;
    double *local_values = NULL;

    uint64_t local_rows = 0;
    uint64_t local_nnz = 0;
    uint64_t row_start = 0;
    uint64_t nnz_start = 0;

    double t_start = 0.0;
    double t_local_start = 0.0;
    double local_spmv_seconds = 0.0;
    double max_spmv_seconds = 0.0;

    const char *request_path =
            argc > 1 ? argv[1] : "request.p3mpi";
    const char *response_path =
            argc > 2 ? argv[2] : "response.p3mpi";

    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        fprintf(stderr, "MPI_Init failed.\n");
        return EXIT_MPI_ERROR;
    }
    mpi_initialized = 1;

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &process_count);

    t_start = MPI_Wtime();

    int root_status = 0;

    if (rank == 0) {
        root_status = read_request(
                request_path,
                &request,
                &global_row_ptr,
                &global_columns,
                &global_values,
                &x);
    }

    MPI_Bcast(&root_status, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (root_status != 0) {
        exit_code = root_status;
        goto finalize;
    }

    uint64_t dimensions[3] = {
        request.rows,
        request.columns,
        request.nnz
    };

    MPI_Bcast(dimensions, 3, MPI_UINT64_T, 0, MPI_COMM_WORLD);

    request.rows = dimensions[0];
    request.columns = dimensions[1];
    request.nnz = dimensions[2];

    if (request.rows > INT_MAX
            || request.columns > INT_MAX
            || request.nnz > INT_MAX) {
        exit_code = EXIT_RESOURCE_ERROR;
        goto finalize;
    }

    row_counts = calloc((size_t)process_count, sizeof(int));
    row_displs = calloc((size_t)process_count, sizeof(int));
    nnz_counts = calloc((size_t)process_count, sizeof(int));
    nnz_displs = calloc((size_t)process_count, sizeof(int));

    if (row_counts == NULL || row_displs == NULL
            || nnz_counts == NULL || nnz_displs == NULL) {
        exit_code = EXIT_RESOURCE_ERROR;
        goto finalize;
    }

    /*
     * Deterministic contiguous row partition.
     * The initial backend balances row counts. A later version may
     * introduce NNZ-balanced boundaries without changing the protocol.
     */
    uint64_t base_rows = request.rows / (uint64_t)process_count;
    uint64_t extra_rows = request.rows % (uint64_t)process_count;
    uint64_t current_row = 0;

    if (rank == 0) {
        for (int r = 0; r < process_count; ++r) {
            uint64_t count = base_rows + ((uint64_t)r < extra_rows ? 1 : 0);
            uint64_t start = current_row;
            uint64_t end = start + count;

            uint64_t start_nnz = global_row_ptr[start];
            uint64_t end_nnz = global_row_ptr[end];

            uint64_t local_nnz_for_rank = end_nnz - start_nnz;

            if (count > INT_MAX || local_nnz_for_rank > INT_MAX
                    || start > INT_MAX || start_nnz > INT_MAX) {
                exit_code = EXIT_RESOURCE_ERROR;
                break;
            }

            row_counts[r] = (int)count;
            row_displs[r] = (int)start;
            nnz_counts[r] = (int)local_nnz_for_rank;
            nnz_displs[r] = (int)start_nnz;

            current_row = end;
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        goto finalize;
    }

    MPI_Scatter(
            row_counts, 1, MPI_INT,
            &local_rows, 0, MPI_BYTE,
            0, MPI_COMM_WORLD);

    /*
     * Scatter metadata as explicit fixed-width values. This avoids
     * assuming that uint64_t has the same layout as an MPI integer type.
     */
    uint64_t *metadata = NULL;
    if (rank == 0) {
        metadata = calloc((size_t)process_count * 2, sizeof(uint64_t));
        if (metadata == NULL) {
            exit_code = EXIT_RESOURCE_ERROR;
        } else {
            for (int r = 0; r < process_count; ++r) {
                metadata[2 * r] = (uint64_t)row_counts[r];
                metadata[2 * r + 1] = (uint64_t)nnz_counts[r];
            }
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        free(metadata);
        goto finalize;
    }

    uint64_t my_metadata[2] = {0, 0};
    MPI_Scatter(
            metadata, 2, MPI_UINT64_T,
            my_metadata, 2, MPI_UINT64_T,
            0, MPI_COMM_WORLD);

    free(metadata);

    local_rows = my_metadata[0];
    local_nnz = my_metadata[1];

    row_start = 0;
    nnz_start = 0;

    if (rank == 0) {
        row_start = (uint64_t)row_displs[0];
        nnz_start = (uint64_t)nnz_displs[0];
    }

    uint64_t *starts = NULL;
    if (rank == 0) {
        starts = calloc((size_t)process_count * 2, sizeof(uint64_t));
        if (starts == NULL) {
            exit_code = EXIT_RESOURCE_ERROR;
        } else {
            for (int r = 0; r < process_count; ++r) {
                starts[2 * r] = (uint64_t)row_displs[r];
                starts[2 * r + 1] = (uint64_t)nnz_displs[r];
            }
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        free(starts);
        goto finalize;
    }

    uint64_t my_starts[2] = {0, 0};
    MPI_Scatter(
            starts, 2, MPI_UINT64_T,
            my_starts, 2, MPI_UINT64_T,
            0, MPI_COMM_WORLD);

    free(starts);

    row_start = my_starts[0];
    nnz_start = my_starts[1];

    if (local_rows > SIZE_MAX / sizeof(uint64_t) - 1
            || local_nnz > SIZE_MAX / sizeof(uint64_t)
            || local_nnz > SIZE_MAX / sizeof(double)
            || local_rows > SIZE_MAX / sizeof(double)) {
        exit_code = EXIT_RESOURCE_ERROR;
        goto finalize;
    }

    local_row_ptr = malloc((size_t)(local_rows + 1) * sizeof(uint64_t));
    local_columns = malloc((size_t)local_nnz * sizeof(uint64_t));
    local_values = malloc((size_t)local_nnz * sizeof(double));
    local_y = calloc((size_t)local_rows, sizeof(double));

    if (local_row_ptr == NULL
            || (local_nnz > 0
                && (local_columns == NULL || local_values == NULL))
            || (local_rows > 0 && local_y == NULL)) {
        exit_code = EXIT_RESOURCE_ERROR;
        goto finalize;
    }

    if (rank == 0) {
        global_y = calloc((size_t)request.rows, sizeof(double));
        if (request.rows > 0 && global_y == NULL) {
            exit_code = EXIT_RESOURCE_ERROR;
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        goto finalize;
    }

    int local_row_pointer_count = (int)(local_rows + 1);
    int *row_pointer_counts = NULL;
    int *row_pointer_displs = NULL;

    if (rank == 0) {
        row_pointer_counts = calloc((size_t)process_count, sizeof(int));
        row_pointer_displs = calloc((size_t)process_count, sizeof(int));

        if (row_pointer_counts == NULL || row_pointer_displs == NULL) {
            exit_code = EXIT_RESOURCE_ERROR;
        } else {
            for (int r = 0; r < process_count; ++r) {
                row_pointer_counts[r] = row_counts[r] + 1;
                row_pointer_displs[r] = row_displs[r];
            }
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        free(row_pointer_counts);
        free(row_pointer_displs);
        goto finalize;
    }

    uint64_t *adjusted_global_row_ptr = NULL;
    if (rank == 0) {
        adjusted_global_row_ptr =
                malloc((size_t)(request.rows + process_count)
                        * sizeof(uint64_t));

        if (adjusted_global_row_ptr == NULL) {
            exit_code = EXIT_RESOURCE_ERROR;
        } else {
            /*
             * Each rank receives its own row-pointer segment,
             * with the first element equal to zero.
             */
            uint64_t offset = 0;
            for (int r = 0; r < process_count; ++r) {
                uint64_t start = (uint64_t)row_displs[r];
                uint64_t rows_for_rank = (uint64_t)row_counts[r];
                uint64_t nnz_offset = global_row_ptr[start];

                for (uint64_t j = 0; j <= rows_for_rank; ++j) {
                    adjusted_global_row_ptr[offset++] =
                            global_row_ptr[start + j] - nnz_offset;
                }
            }
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        free(row_pointer_counts);
        free(row_pointer_displs);
        free(adjusted_global_row_ptr);
        goto finalize;
    }

    /*
     * MPI_Scatterv requires non-overlapping receive segments.
     * Build a packed row-pointer array with one independent segment
     * per rank, each of length local_rows + 1.
     */
    uint64_t *packed_row_ptr = NULL;
    int *packed_row_counts = NULL;
    int *packed_row_displs = NULL;

    if (rank == 0) {
        packed_row_counts = calloc((size_t)process_count, sizeof(int));
        packed_row_displs = calloc((size_t)process_count, sizeof(int));

        if (packed_row_counts == NULL || packed_row_displs == NULL) {
            exit_code = EXIT_RESOURCE_ERROR;
        } else {
            uint64_t total = 0;
            for (int r = 0; r < process_count; ++r) {
                uint64_t count = (uint64_t)row_counts[r] + 1;
                if (count > INT_MAX || total > INT_MAX) {
                    exit_code = EXIT_RESOURCE_ERROR;
                    break;
                }
                packed_row_counts[r] = (int)count;
                packed_row_displs[r] = (int)total;
                total += count;
            }

            if (exit_code == 0) {
                packed_row_ptr = malloc((size_t)total * sizeof(uint64_t));
                if (packed_row_ptr == NULL) {
                    exit_code = EXIT_RESOURCE_ERROR;
                } else {
                    uint64_t out = 0;
                    for (int r = 0; r < process_count; ++r) {
                        uint64_t start = (uint64_t)row_displs[r];
                        uint64_t count = (uint64_t)row_counts[r];
                        uint64_t base = global_row_ptr[start];

                        for (uint64_t j = 0; j <= count; ++j) {
                            packed_row_ptr[out++] =
                                    global_row_ptr[start + j] - base;
                        }
                    }
                }
            }
        }
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        free(row_pointer_counts);
        free(row_pointer_displs);
        free(adjusted_global_row_ptr);
        free(packed_row_ptr);
        free(packed_row_counts);
        free(packed_row_displs);
        goto finalize;
    }

    MPI_Scatterv(
            packed_row_ptr,
            packed_row_counts,
            packed_row_displs,
            MPI_UINT64_T,
            local_row_ptr,
            local_row_pointer_count,
            MPI_UINT64_T,
            0,
            MPI_COMM_WORLD);

    MPI_Scatterv(
            global_columns,
            nnz_counts,
            nnz_displs,
            MPI_UINT64_T,
            local_columns,
            (int)local_nnz,
            MPI_UINT64_T,
            0,
            MPI_COMM_WORLD);

    MPI_Scatterv(
            global_values,
            nnz_counts,
            nnz_displs,
            MPI_DOUBLE,
            local_values,
            (int)local_nnz,
            MPI_DOUBLE,
            0,
            MPI_COMM_WORLD);

    if (request.columns > INT_MAX) {
        exit_code = EXIT_RESOURCE_ERROR;
        goto finalize;
    }

    MPI_Bcast(
            x,
            (int)request.columns,
            MPI_DOUBLE,
            0,
            MPI_COMM_WORLD);

    t_local_start = MPI_Wtime();

    for (uint64_t row = 0; row < local_rows; ++row) {
        double sum = 0.0;

        for (uint64_t k = local_row_ptr[row];
             k < local_row_ptr[row + 1];
             ++k) {
            uint64_t column = local_columns[k];
            sum += local_values[k] * x[column];
        }

        if (!isfinite(sum)) {
            exit_code = EXIT_PROTOCOL_ERROR;
            break;
        }

        local_y[row] = sum;
    }

    local_spmv_seconds = MPI_Wtime() - t_local_start;

    MPI_Allreduce(
            &local_spmv_seconds,
            &max_spmv_seconds,
            1,
            MPI_DOUBLE,
            MPI_MAX,
            MPI_COMM_WORLD);

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (exit_code != 0) {
        goto finalize;
    }

    MPI_Gatherv(
            local_y,
            (int)local_rows,
            MPI_DOUBLE,
            global_y,
            row_counts,
            row_displs,
            MPI_DOUBLE,
            0,
            MPI_COMM_WORLD);

    if (rank == 0) {
        exit_code = write_response(
                response_path,
                request.rows,
                global_y);

        fprintf(
                stderr,
                "P3_MPI ranks=%d rows=%" PRIu64
                " nnz=%" PRIu64
                " local_spmv_max_seconds=%.9f"
                " end_to_end_seconds=%.9f\n",
                process_count,
                request.rows,
                request.nnz,
                max_spmv_seconds,
                MPI_Wtime() - t_start);
    }

    MPI_Bcast(&exit_code, 1, MPI_INT, 0, MPI_COMM_WORLD);

    free(row_pointer_counts);
    free(row_pointer_displs);
    free(adjusted_global_row_ptr);
    free(packed_row_ptr);
    free(packed_row_counts);
    free(packed_row_displs);

finalize:
    free_all(
            global_row_ptr,
            global_columns,
            global_values,
            x,
            local_y,
            global_y,
            row_counts,
            row_displs,
            nnz_counts,
            nnz_displs,
            local_row_ptr,
            local_columns,
            local_values);

    if (mpi_initialized) {
        MPI_Finalize();
    }

    return exit_code;
}
