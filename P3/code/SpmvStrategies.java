package hpc.csr;

import java.util.List;
import java.util.Locale;
import java.util.Objects;

/** Factory for the SpmvStrategy implementations. */
public final class SpmvStrategies {

    private static final List<String> NAMES = List.of(
            SequentialSpmvStrategy.NAME,
            PlannedForkJoinSpmvStrategy.NAME,
            StaticChunkSpmvStrategy.NAME);

    private SpmvStrategies() {
    }

    /** Names accepted by create(). */
    public static List<String> names() {
        return NAMES;
    }

    /**
     * Creates a strategy by name. The returned strategy owns its pool (if
     * any) and must be closed by the caller.
     */
    public static SpmvStrategy create(
            String name,
            SparseMatrixCSR matrix,
            int parallelism) {

        Objects.requireNonNull(name, "name cannot be null");
        Objects.requireNonNull(matrix, "matrix cannot be null");

        switch (name.toUpperCase(Locale.ROOT)) {
            case SequentialSpmvStrategy.NAME:
                return new SequentialSpmvStrategy(matrix);

            case PlannedForkJoinSpmvStrategy.NAME:
                return new PlannedForkJoinSpmvStrategy(matrix, parallelism);

            case StaticChunkSpmvStrategy.NAME:
                return new StaticChunkSpmvStrategy(matrix, parallelism);

            default:
                throw new IllegalArgumentException(
                        "Unknown SpMV strategy: " + name
                                + ". Known strategies: " + NAMES);
        }
    }
}
