/*
 * P3 — Distributed CSR Sparse Matrix-Vector Multiplication
 *
 * Native MPI backend.
 *
 * Build:
 *   mpicc -std=c11 -O3 -Wall -Wextra -Wpedantic \
 *     -Wconversion -Wshadow \
 *     P3/hpc/mpi/native/p3_mpi_spmv.c \
 *     -o p3_mpi_spmv -lm
 *
 * Run:
 *   mpirun -np 2 ./p3_mpi_spmv request.p3mpi response.p3mpi
 *
 * Input protocol, little-endian:
 *   8 bytes  magic = "P3SPMV01"
 *   8 bytes  rows
 *   8 bytes  columns
 *   8 bytes  nnz
 *   8 bytes  vector_length
 *   8 bytes  flags
 *   8 bytes  reserved
 *   rows + 1 uint64 row pointers
 *   nnz uint64 column indices
 *   nnz IEEE-754 binary64 values
 *   columns IEEE-754 binary64 vector elements
 *
 * Output protocol, little-endian:
 *   8 bytes  magic = "P3OUT001"
 *   8 bytes  rows
 *   8 bytes  status (0 = success)
 *   8 bytes  reserved (0)
 *   rows IEEE-754 binary64 result elements
 *
 * Distribution:
 *   - contiguous whole-row partitions;
 *   - CSR row pointers are rebased locally;
 *   - input vector is replicated with MPI_Bcast;
 *   - local SpMV is computed independently by each rank;
 *   - output rows are gathered in global row order.
 *
 * Important:
 *   MPI_Scatterv / MPI_Gatherv use int counts and displacements.
 *   This implementation fails closed if any individual MPI count
 *   or displacement exceeds INT_MAX. Large-scale MPI-4 large-count
 *   support is a separate extension and is not silently emulated.
 */

#define _POSIX_C_SOURCE 200809L

#include <mpi.h>

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#define INPUT_MAGIC  "P3SPMV01"
#define OUTPUT_MAGIC "P3OUT001"

#define INPUT_HEADER_BYTES  56U
#define OUTPUT_HEADER_BYTES 32U

#define INPUT_FLAGS_SUPPORTED UINT64_C(0)

typedef struct {
    uint64_t rows;
    uint64_t columns;
    uint64_t nnz;
    uint64_t vector_length;
    uint64_t flags;
    uint64_t reserved;

    uint64_t *row_ptr;
    uint64_t *column_indices;
    double *values;
    double *x;
} CsrInput;

static void fail_message(const char *message) {
    fprintf(stderr, "P3_MPI_ERROR: %s\n", message);
}

static int checked_size(uint64_t count, size_t element_size,
                        size_t *result) {
    if (element_size != 0U &&
        count > (uint64_t)(SIZE_MAX / element_size)) {
        return 0;
    }

    *result = (size_t)count * element_size;
    return 1;
}

static int read_exact(FILE *file, void *buffer, size_t bytes) {
    return fread(buffer, 1U, bytes, file) == bytes;
}

static int write_exact(FILE *file, const void *buffer, size_t bytes) {
    return fwrite(buffer, 1U, bytes, file) == bytes;
}

/*
 * Decode unsigned 64-bit little-endian integers explicitly.
 * This avoids relying on host endianness for protocol headers.
 */
static uint64_t decode_u64_le(const unsigned char bytes[8]) {
    uint64_t value = 0U;

    for (unsigned int i = 0U; i < 8U; ++i) {
        value |= ((uint64_t)bytes[i]) << (8U * i);
    }

    return value;
}

static void encode_u64_le(unsigned char bytes[8], uint64_t value) {
    for (unsigned int i = 0U; i < 8U; ++i) {
        bytes[i] = (unsigned char)((value >> (8U * i)) & UINT64_C(0xff));
    }
}

static int host_is_little_endian(void) {
    const uint16_t value = UINT16_C(1);
    return *((const unsigned char *)&value) == 1U;
}

static void free_input(CsrInput *input) {
    if (input == NULL) {
        return;
    }

    free(input->row_ptr);
    free(input->column_indices);
    free(input->values);
    free(input->x);

    memset(input, 0, sizeof(*input));
}

static int read_binary64_array(FILE *file, double *array,
                               uint64_t count) {
    size_t bytes = 0U;

    if (!checked_size(count, sizeof(double), &bytes)) {
        return 0;
    }

    if (!read_exact(file, array, bytes)) {
        return 0;
    }

    for (uint64_t i = 0U; i < count; ++i) {
        if (!isfinite(array[i])) {
            return 0;
        }
    }

    return 1;
}

static int read_u64_array(FILE *file, uint64_t *array,
                          uint64_t count) {
    for (uint64_t i = 0U; i < count; ++i) {
        unsigned char bytes[8];

        if (!read_exact(file, bytes, sizeof(bytes))) {
            return 0;
        }

        array[i] = decode_u64_le(bytes);
    }

    return 1;
}

static int validate_csr(const CsrInput *input) {
    if (input->rows == UINT64_MAX) {
        return 0;
    }

    if (input->vector_length != input->columns) {
        return 0;
    }

    if (input->flags != INPUT_FLAGS_SUPPORTED ||
        input->reserved != 0U) {
        return 0;
    }

    if (input->row_ptr == NULL) {
        return 0;
    }

    if (input->row_ptr[0] != 0U ||
        input->row_ptr[input->rows] != input->nnz) {
        return 0;
    }

    for (uint64_t row = 0U; row < input->rows; ++row) {
        if (input->row_ptr[row] > input->row_ptr[row + 1U]) {
            return 0;
        }

        if (input->row_ptr[row + 1U] > input->nnz) {
            return 0;
        }
    }

    for (uint64_t k = 0U; k < input->nnz; ++k) {
        if (input->column_indices[k] >= input->columns) {
            return 0;
        }

        if (!isfinite(input->values[k])) {
            return 0;
        }
    }

    for (uint64_t k = 0U; k < input->columns; ++k) {
        if (!isfinite(input->x[k])) {
            return 0;
        }
    }

    return 1;
}

static int load_input(const char *path, CsrInput *input) {
    FILE *file = fopen(path, "rb");

    if (file == NULL) {
        fail_message("Cannot open MPI request file.");
        return 0;
    }

    unsigned char magic[8];
    unsigned char field[8];

    if (!read_exact(file, magic, sizeof(magic)) ||
        memcmp(magic, INPUT_MAGIC, sizeof(magic)) != 0) {
        fail_message("Invalid input magic or truncated header.");
        fclose(file);
        return 0;
    }

    uint64_t *header_fields[] = {
        &input->rows,
        &input->columns,
        &input->nnz,
        &input->vector_length,
        &input->flags,
        &input->reserved
    };

    for (size_t i = 0U; i < 6U; ++i) {
        if (!read_exact(file, field, sizeof(field))) {
            fail_message("Truncated input header.");
            fclose(file);
            return 0;
        }

        *header_fields[i] = decode_u64_le(field);
    }

    if (input->rows == UINT64_MAX) {
        fail_message("Row count exceeds supported CSR dimensions.");
        fclose(file);
        return 0;
    }

    size_t row_bytes = 0U;
    size_t nnz_bytes = 0U;
    size_t vector_bytes = 0U;

    if (!checked_size(input->rows + 1U,
                      sizeof(uint64_t), &row_bytes) ||
        !checked_size(input->nnz,
                      sizeof(uint64_t), &nnz_bytes) ||
        !checked_size(input->nnz,
                      sizeof(double), &nnz_bytes) ||
        !checked_size(input->columns,
                      sizeof(double), &vector_bytes)) {
        fail_message("Input dimensions exceed addressable memory.");
        fclose(file);
        return 0;
    }

    input->row_ptr = malloc(row_bytes);
    input->column_indices = malloc(
        (size_t)input->nnz * sizeof(uint64_t));
    input->values = malloc(
        (size_t)input->nnz * sizeof(double));
    input->x = malloc(vector_bytes);

    if (input->row_ptr == NULL ||
        (input->nnz > 0U &&
         (input->column_indices == NULL || input->values == NULL)) ||
        (input->columns > 0U && input->x == NULL)) {
        fail_message("Memory allocation failed while loading CSR input.");
        fclose(file);
        free_input(input);
        return 0;
    }

    if (!read_u64_array(file, input->row_ptr, input->rows + 1U) ||
        !read_u64_array(file, input->column_indices, input->nnz) ||
        !read_binary64_array(file, input->values, input->nnz) ||
        !read_binary64_array(file, input->x, input->columns)) {
        fail_message("Truncated or invalid CSR payload.");
        fclose(file);
        free_input(input);
        return 0;
    }

    /*
     * Reject trailing bytes. A request must match the declared
     * protocol length exactly.
     */
    int trailing = fgetc(file);

    if (trailing != EOF || ferror(file)) {
        fail_message("Unexpected trailing bytes in request file.");
        fclose(file);
        free_input(input);
        return 0;
    }

    if (fclose(file) != 0) {
        fail_message("Could not close request file cleanly.");
        free_input(input);
        return 0;
    }

    if (!validate_csr(input)) {
        fail_message("CSR structure or numeric data is invalid.");
        free_input(input);
        return 0;
    }

    return 1;
}

static int u64_to_int(uint64_t value, int *result) {
    if (value > (uint64_t)INT_MAX) {
        return 0;
    }

    *result = (int)value;
    return 1;
}

static int write_output(const char *path,
                        uint64_t rows,
                        const double *y) {
    FILE *file = fopen(path, "wb");

    if (file == NULL) {
        fail_message("Cannot create MPI response file.");
        return 0;
    }

    unsigned char header[OUTPUT_HEADER_BYTES];

    memcpy(header, OUTPUT_MAGIC, 8U);
    encode_u64_le(header + 8U, rows);
    encode_u64_le(header + 16U, 0U);
    encode_u64_le(header + 24U, 0U);

    if (!write_exact(file, header, sizeof(header))) {
        fail_message("Could not write response header.");
        fclose(file);
        return 0;
    }

    size_t output_bytes = 0U;

    if (!checked_size(rows, sizeof(double), &output_bytes)) {
        fail_message("Output dimensions exceed addressable memory.");
        fclose(file);
        return 0;
    }

    if (!write_exact(file, y, output_bytes)) {
        fail_message("Could not write response vector.");
        fclose(file);
        return 0;
    }

    if (fflush(file) != 0 || fclose(file) != 0) {
        fail_message("Could not finalize response file.");
        return 0;
    }

    return 1;
}

static void abort_mpi(int rank, const char *message, int error_code) {
    fprintf(stderr, "P3_MPI_ERROR rank=%d: %s\n", rank, message);
    MPI_Abort(MPI_COMM_WORLD, error_code);
}

int main(int argc, char **argv) {
    int provided_thread_level = 0;

    if (MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED,
                        &provided_thread_level) != MPI_SUCCESS) {
        return EXIT_FAILURE;
    }

    int rank = 0;
    int process_count = 0;

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &process_count);

    if (provided_thread_level < MPI_THREAD_FUNNELED) {
        abort_mpi(rank, "MPI thread support is insufficient.", 2);
    }

    if (!host_is_little_endian()) {
        abort_mpi(rank,
                  "This protocol implementation requires little-endian hosts.",
                  3);
    }

    if (argc != 3) {
        if (rank == 0) {
            fprintf(stderr,
                    "Usage: %s request.p3mpi response.p3mpi\n",
                    argv[0]);
        }

        MPI_Finalize();
        return EXIT_FAILURE;
    }

    CsrInput input;
    memset(&input, 0, sizeof(input));

    int root_status = 1;

    if (rank == 0) {
        root_status = load_input(argv[1], &input);
    }

    MPI_Bcast(&root_status, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (root_status != 1) {
        free_input(&input);
        MPI_Finalize();
        return EXIT_FAILURE;
    }

    uint64_t metadata[4] = {0U, 0U, 0U, 0U};

    if (rank == 0) {
        metadata[0] = input.rows;
        metadata[1] = input.columns;
        metadata[2] = input.nnz;
        metadata[3] = input.vector_length;
    }

    MPI_Bcast(metadata, 4, MPI_UINT64_T, 0, MPI_COMM_WORLD);

    const uint64_t rows = metadata[0];
    const uint64_t columns = metadata[1];
    const uint64_t nnz = metadata[2];

    /*
     * This backend intentionally uses MPI_Scatterv/Gatherv with
     * int counts. Reject unsupported dimensions before allocating
     * partition metadata or starting data movement.
     */
    int global_rows_int = 0;
    int global_nnz_int = 0;
    int global_columns_int = 0;

    int dimensions_supported =
        u64_to_int(rows, &global_rows_int) &&
        u64_to_int(nnz, &global_nnz_int) &&
        u64_to_int(columns, &global_columns_int);

    MPI_Bcast(&dimensions_supported, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (!dimensions_supported) {
        if (rank == 0) {
            fail_message(
                "MPI int-count limit exceeded; large-count MPI is not implemented.");
        }

        free_input(&input);
        MPI_Finalize();
        return EXIT_FAILURE;
    }

    int *row_counts = calloc((size_t)process_count, sizeof(int));
    int *row_displacements = calloc((size_t)process_count, sizeof(int));
    int *nnz_counts = calloc((size_t)process_count, sizeof(int));
    int *nnz_displacements = calloc((size_t)process_count, sizeof(int));

    if (row_counts == NULL || row_displacements == NULL ||
        nnz_counts == NULL || nnz_displacements == NULL) {
        abort_mpi(rank, "Partition metadata allocation failed.", 4);
    }

    /*
     * Root creates a packed array of rebased local row pointers.
     * Each rank receives local_rows + 1 pointers.
     */
    uint64_t *packed_row_ptr = NULL;
    uint64_t *packed_columns = NULL;
    double *packed_values = NULL;

    int *local_row_counts = calloc((size_t)process_count, sizeof(int));
    int *local_nnz_counts = calloc((size_t)process_count, sizeof(int));

    if (local_row_counts == NULL || local_nnz_counts == NULL) {
        abort_mpi(rank, "Local count allocation failed.", 5);
    }

    uint64_t packed_row_pointer_count = 0U;

    if (rank == 0) {
        for (int r = 0; r < process_count; ++r) {
            const uint64_t row_start =
                (rows * (uint64_t)r) / (uint64_t)process_count;
            const uint64_t row_end =
                (rows * (uint64_t)(r + 1)) / (uint64_t)process_count;

            const uint64_t nnz_start = input.row_ptr[row_start];
            const uint64_t nnz_end = input.row_ptr[row_end];

            const uint64_t local_rows = row_end - row_start;
            const uint64_t local_nnz = nnz_end - nnz_start;

            int local_rows_int = 0;
            int local_nnz_int = 0;
            int row_disp_int = 0;
            int nnz_disp_int = 0;
            int row_ptr_count_int = 0;

            if (!u64_to_int(local_rows, &local_rows_int) ||
                !u64_to_int(local_nnz, &local_nnz_int) ||
                !u64_to_int(packed_row_pointer_count, &row_disp_int) ||
                !u64_to_int(nnz_start, &nnz_disp_int) ||
                !u64_to_int(local_rows + 1U, &row_ptr_count_int)) {
                abort_mpi(rank,
                          "A partition exceeds MPI int count/displacement limits.",
                          6);
            }

            row_counts[r] = row_ptr_count_int;
            row_displacements[r] = row_disp_int;
            nnz_counts[r] = local_nnz_int;
            nnz_displacements[r] = nnz_disp_int;

            local_row_counts[r] = local_rows_int;
            local_nnz_counts[r] = local_nnz_int;

            packed_row_pointer_count += local_rows + 1U;
        }

        size_t packed_row_bytes = 0U;

        if (!checked_size(packed_row_pointer_count,
                          sizeof(uint64_t), &packed_row_bytes)) {
            abort_mpi(rank, "Packed row pointer size overflow.", 7);
        }

        packed_row_ptr = malloc(packed_row_bytes);
        packed_columns = malloc((size_t)nnz * sizeof(uint64_t));
        packed_values = malloc((size_t)nnz * sizeof(double));

        if (packed_row_ptr == NULL ||
            (nnz > 0U &&
             (packed_columns == NULL || packed_values == NULL))) {
            abort_mpi(rank, "Packed CSR allocation failed.", 8);
        }

        uint64_t write_offset = 0U;

        for (int r = 0; r < process_count; ++r) {
            const uint64_t row_start =
                (rows * (uint64_t)r) / (uint64_t)process_count;
            const uint64_t row_end =
                (rows * (uint64_t)(r + 1)) / (uint64_t)process_count;

            const uint64_t nnz_start = input.row_ptr[row_start];
            const uint64_t nnz_end = input.row_ptr[row_end];

            for (uint64_t i = 0U; i <= row_end - row_start; ++i) {
                packed_row_ptr[write_offset + i] =
                    input.row_ptr[row_start + i] - nnz_start;
            }

            write_offset += (row_end - row_start) + 1U;
        }

        if (nnz > 0U) {
            memcpy(packed_columns, input.column_indices,
                   (size_t)nnz * sizeof(uint64_t));
            memcpy(packed_values, input.values,
                   (size_t)nnz * sizeof(double));
        }
    }

    int local_rows = 0;
    int local_nnz = 0;

    MPI_Scatter(local_row_counts, 1, MPI_INT,
                &local_rows, 1, MPI_INT, 0, MPI_COMM_WORLD);

    MPI_Scatter(local_nnz_counts, 1, MPI_INT,
                &local_nnz, 1, MPI_INT, 0, MPI_COMM_WORLD);

    uint64_t *local_row_ptr =
        malloc(((size_t)local_rows + 1U) * sizeof(uint64_t));
    uint64_t *local_columns =
        malloc((size_t)local_nnz * sizeof(uint64_t));
    double *local_values =
        malloc((size_t)local_nnz * sizeof(double));
    double *local_x =
        malloc((size_t)columns * sizeof(double));
    double *local_y =
        calloc((size_t)local_rows, sizeof(double));

    if (local_row_ptr == NULL ||
        (local_nnz > 0 && (local_columns == NULL || local_values == NULL)) ||
        (columns > 0U && local_x == NULL) ||
        (local_rows > 0 && local_y == NULL)) {
        abort_mpi(rank, "Local CSR/vector allocation failed.", 9);
    }

    MPI_Scatterv(packed_row_ptr, row_counts, row_displacements,
                 MPI_UINT64_T,
                 local_row_ptr, local_rows + 1, MPI_UINT64_T,
                 0, MPI_COMM_WORLD);

    MPI_Scatterv(packed_columns, nnz_counts, nnz_displacements,
                 MPI_UINT64_T,
                 local_columns, local_nnz, MPI_UINT64_T,
                 0, MPI_COMM_WORLD);

    MPI_Scatterv(packed_values, nnz_counts, nnz_displacements,
                 MPI_DOUBLE,
                 local_values, local_nnz, MPI_DOUBLE,
                 0, MPI_COMM_WORLD);

    if (rank == 0 && columns > 0U) {
        memcpy(local_x, input.x, (size_t)columns * sizeof(double));
    }

    MPI_Bcast(local_x, global_columns_int, MPI_DOUBLE,
              0, MPI_COMM_WORLD);

    /*
     * Local CSR SpMV.
     * Each rank owns complete rows, so no row-level reduction
     * or cross-rank accumulation is required.
     */
    int local_status = 0;

    for (int row = 0; row < local_rows; ++row) {
        double sum = 0.0;

        const uint64_t begin = local_row_ptr[row];
        const uint64_t end = local_row_ptr[row + 1];

        if (begin > end || end > (uint64_t)local_nnz) {
            local_status = 1;
            break;
        }

        for (uint64_t k = begin; k < end; ++k) {
            const uint64_t column = local_columns[k];

            if (column >= columns) {
                local_status = 1;
                break;
            }

            sum += local_values[k] * local_x[column];
        }

        if (local_status != 0 || !isfinite(sum)) {
            local_status = 1;
            break;
        }

        local_y[row] = sum;
    }

    int global_status = 0;

    MPI_Allreduce(&local_status, &global_status, 1,
                  MPI_INT, MPI_MAX, MPI_COMM_WORLD);

    if (global_status != 0) {
        abort_mpi(rank, "Local SpMV validation failed.", 10);
    }

    int *gather_counts = NULL;
    int *gather_displacements = NULL;
    double *global_y = NULL;

    if (rank == 0) {
        gather_counts = calloc((size_t)process_count, sizeof(int));
        gather_displacements = calloc((size_t)process_count, sizeof(int));
        global_y = malloc((size_t)rows * sizeof(double));

        if (gather_counts == NULL ||
            gather_displacements == NULL ||
            (rows > 0U && global_y == NULL)) {
            abort_mpi(rank, "Gather metadata allocation failed.", 11);
        }

        for (int r = 0; r < process_count; ++r) {
            const uint64_t row_start =
                (rows * (uint64_t)r) / (uint64_t)process_count;
            const uint64_t row_end =
                (rows * (uint64_t)(r + 1)) / (uint64_t)process_count;

            if (!u64_to_int(row_end - row_start, &gather_counts[r]) ||
                !u64_to_int(row_start, &gather_displacements[r])) {
                abort_mpi(rank, "Gather count exceeds MPI int limits.", 12);
            }
        }
    }

    MPI_Gatherv(local_y, local_rows, MPI_DOUBLE,
                global_y, gather_counts, gather_displacements,
                MPI_DOUBLE, 0, MPI_COMM_WORLD);

    int output_status = 1;

    if (rank == 0) {
        output_status = write_output(argv[2], rows, global_y);
    }

    MPI_Bcast(&output_status, 1, MPI_INT, 0, MPI_COMM_WORLD);

    free(row_counts);
    free(row_displacements);
    free(nnz_counts);
    free(nnz_displacements);
    free(local_row_counts);
    free(local_nnz_counts);

    free(packed_row_ptr);
    free(packed_columns);
    free(packed_values);

    free(local_row_ptr);
    free(local_columns);
    free(local_values);
    free(local_x);
    free(local_y);

    free(gather_counts);
    free(gather_displacements);
    free(global_y);

    free_input(&input);

    MPI_Finalize();

    return output_status == 1 ? EXIT_SUCCESS : EXIT_FAILURE;
}
