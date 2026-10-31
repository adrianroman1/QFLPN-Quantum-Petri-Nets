package hpc.csr.harness;

import hpc.csr.MultiplyTask;
import hpc.csr.PlannedForkJoinSpmvStrategy;
import hpc.csr.SparseMatrixCSR;
import hpc.csr.SpmvStrategies;
import hpc.csr.SpmvStrategy;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryPoolMXBean;
import java.lang.management.MemoryType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.RecursiveAction;

/**
 * Fork-based SpMV measurement harness (no external dependencies).
 *
 * One invocation = one JVM = one fork. The driver script starts several
 * forks so that JIT, GC and layout noise is sampled across JVM instances,
 * which is the property a JMH-style protocol provides. Raw per-iteration
 * times are written, never only means.
 *
 * Modes (key=value arguments):
 *   mode=cores
 *   mode=preflight n=.. workload=..
 *   mode=child     run=.. commit=.. fork=.. n=.. workload=.. p=1,2,4
 *                  strategies=SEQ,FJ_PLAN,STATIC warmup=.. iterations=..
 *                  thresholds=4096[,...] thresholdMode=ROW_THRESHOLD|NNZ_THRESHOLD
 *                  raw=<csv> forks=<csv>
 *
 * FJ_PLAN is reported once per threshold under the label FJ_PLAN_T<threshold>.
 *   mode=stream    run=.. p=1,2,4 reps=.. out=<csv>
 */
public final class ParallelSpmvHarness {

    private static final long INT_ARRAY_LIMIT = Integer.MAX_VALUE - 8L;
    private static final double PREFLIGHT_HEAP_FRACTION = 0.85;
    private static final long PREFLIGHT_SLACK_BYTES = 64L << 20;

    private ParallelSpmvHarness() {
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> a = parse(args);
        String mode = a.getOrDefault("mode", "");

        switch (mode) {
            case "cores":
                System.out.println(
                        Runtime.getRuntime().availableProcessors());
                break;
            case "preflight":
                preflight(a);
                break;
            case "child":
                child(a);
                break;
            case "stream":
                stream(a);
                break;
            default:
                System.err.println("Unknown mode: " + mode);
                System.exit(2);
        }
    }

    // ------------------------------------------------------------------
    // workloads
    // ------------------------------------------------------------------

    static long mix(long z) {
        z += 0x9E3779B97F4A7C15L;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }

    /** Entries in a row; deterministic, no allocation. */
    static int rowCount(String workload, int n, int row) {
        switch (workload) {
            case "UNIFORM_2":
                return Math.min(2, n);
            case "POWERLAW": {
                long h = mix(row);
                double u = ((h >>> 11) * (1.0 / (1L << 53)));

                if (u < 0.25) {
                    return 0;
                }

                if (u < 0.995) {
                    return Math.min(n, 1 + (int) ((h >>> 3) & 3));
                }

                return Math.min(n, 50 + (int) ((h >>> 7) % 200L));
            }
            default:
                throw new IllegalArgumentException(
                        "Unknown workload: " + workload);
        }
    }

    static long countNnz(String workload, int n) {
        long total = 0;

        for (int row = 0; row < n; row++) {
            total += rowCount(workload, n, row);
        }

        return total;
    }

    static SparseMatrixCSR build(String workload, int n) {
        long nnzLong = countNnz(workload, n);

        if (nnzLong > INT_ARRAY_LIMIT) {
            throw new IllegalStateException(
                    "NNZ " + nnzLong + " exceeds the Java int array limit.");
        }

        int nnz = (int) nnzLong;
        double[] values = new double[nnz];
        int[] columns = new int[nnz];
        int[] pointers = new int[n + 1];
        int position = 0;

        for (int row = 0; row < n; row++) {
            int count = rowCount(workload, n, row);
            int start;

            if ("UNIFORM_2".equals(workload)) {
                // columns row and row+1 (wrapping), kept strictly increasing
                for (int k = 0; k < count; k++) {
                    int column = row + k;
                    if (column >= n) {
                        column -= n;
                    }
                    columns[position + k] = column;
                    values[position + k] = (k == 0) ? 1.0 : 0.5;
                }

                if (count == 2 && columns[position] > columns[position + 1]) {
                    int c = columns[position];
                    columns[position] = columns[position + 1];
                    columns[position + 1] = c;
                    double v = values[position];
                    values[position] = values[position + 1];
                    values[position + 1] = v;
                }
            } else {
                start = (count == 0) ? 0
                        : (int) Math.floorMod(mix(~(long) row), n - count + 1L);

                for (int k = 0; k < count; k++) {
                    columns[position + k] = start + k;
                    values[position + k] =
                            0.25 + ((mix(position + k) >>> 40) & 1023) / 1024.0;
                }
            }

            position += count;
            pointers[row + 1] = position;
        }

        return new SparseMatrixCSR(values, columns, pointers, n, n);
    }

    // ------------------------------------------------------------------
    // preflight
    // ------------------------------------------------------------------

    static void preflight(Map<String, String> a) {
        int n = Integer.parseInt(req(a, "n"));
        String workload = req(a, "workload");

        long nnz = countNnz(workload, n);
        long csrBytes = 12L * nnz + 4L * (n + 1L);
        long modelPeak = 2L * csrBytes + 24L * n + PREFLIGHT_SLACK_BYTES;
        long maxHeap = Runtime.getRuntime().maxMemory();

        String verdict = "RUN";
        String reason = "fits";

        if (nnz > INT_ARRAY_LIMIT) {
            verdict = "SKIP";
            reason = "nnz exceeds Java int array limit";
        } else if (modelPeak > PREFLIGHT_HEAP_FRACTION * maxHeap) {
            verdict = "SKIP";
            reason = "model peak " + modelPeak + " B exceeds "
                    + (int) (PREFLIGHT_HEAP_FRACTION * 100)
                    + "% of max heap " + maxHeap + " B";
        }

        System.out.println(String.join(",",
                "PREFLIGHT", String.valueOf(n), workload,
                String.valueOf(nnz), String.valueOf(csrBytes),
                String.valueOf(modelPeak), String.valueOf(maxHeap),
                verdict, "\"" + reason + "\""));
    }

    // ------------------------------------------------------------------
    // child (one fork)
    // ------------------------------------------------------------------

    static void child(Map<String, String> a) throws IOException {
        String run = req(a, "run");
        String commit = a.getOrDefault("commit", "unknown");
        int fork = Integer.parseInt(req(a, "fork"));
        int n = Integer.parseInt(req(a, "n"));
        String workload = req(a, "workload");
        int warmup = Integer.parseInt(req(a, "warmup"));
        int iterations = Integer.parseInt(req(a, "iterations"));
        Path raw = Paths.get(req(a, "raw"));
        Path forks = Paths.get(req(a, "forks"));
        int cores = Runtime.getRuntime().availableProcessors();

        List<Integer> parallelisms = new ArrayList<>();

        for (String token : req(a, "p").split(",")) {
            int p = Integer.parseInt(token.trim());

            if (p <= cores) {
                parallelisms.add(p);
            }
        }

        List<Integer> thresholds = new ArrayList<>();

        for (String token : a.getOrDefault("thresholds", "4096").split(",")) {
            thresholds.add(Integer.parseInt(token.trim()));
        }

        MultiplyTask.ThresholdMode thresholdMode =
                MultiplyTask.ThresholdMode.valueOf(
                        a.getOrDefault("thresholdMode", "ROW_THRESHOLD"));

        List<String> strategyNames = Arrays.asList(
                req(a, "strategies").toUpperCase(Locale.ROOT).split(","));

        List<MemoryPoolMXBean> heapPools = new ArrayList<>();

        for (MemoryPoolMXBean pool : ManagementFactory.getMemoryPoolMXBeans()) {
            if (pool.getType() == MemoryType.HEAP) {
                heapPools.add(pool);
                pool.resetPeakUsage();
            }
        }

        long buildStart = System.nanoTime();
        SparseMatrixCSR matrix = build(workload, n);
        double setupMs = (System.nanoTime() - buildStart) / 1e6;
        long peakAfterBuild = sumPeaks(heapPools);
        long nnz = matrix.getNnz();

        double[] x = new double[n];

        for (int i = 0; i < n; i++) {
            x[i] = 1.0 + (i % 7) * 0.01;
        }

        double[] reference = new double[n];
        matrix.multiplyInto(x, reference);
        double[] y = new double[n];

        List<SpmvStrategy> strategies = new ArrayList<>();
        List<String> labels = new ArrayList<>();
        List<Integer> labelP = new ArrayList<>();

        try {
            for (String name : strategyNames) {
                if ("SEQ".equals(name)) {
                    strategies.add(SpmvStrategies.create(name, matrix, 1));
                    labels.add(name);
                    labelP.add(1);
                    continue;
                }

                if ("FJ_PLAN".equals(name)) {
                    for (int p : parallelisms) {
                        for (int threshold : thresholds) {
                            strategies.add(new PlannedForkJoinSpmvStrategy(
                                    matrix, p, threshold,
                                    thresholdMode, null));
                            labels.add("FJ_PLAN_T" + threshold);
                            labelP.add(p);
                        }
                    }
                    continue;
                }

                for (int p : parallelisms) {
                    strategies.add(SpmvStrategies.create(name, matrix, p));
                    labels.add(name);
                    labelP.add(p);
                }
            }

            // Verification pass (untimed): bitwise equality with sequential.
            boolean[] bitExact = new boolean[strategies.size()];
            long[] hashes = new long[strategies.size()];

            for (int s = 0; s < strategies.size(); s++) {
                Arrays.fill(y, Double.NaN);
                strategies.get(s).multiplyInto(x, y);
                boolean same = true;

                for (int i = 0; i < n; i++) {
                    if (Double.doubleToLongBits(y[i])
                            != Double.doubleToLongBits(reference[i])) {
                        same = false;
                        break;
                    }
                }

                bitExact[s] = same;
                hashes[s] = Arrays.hashCode(y);
            }

            for (int w = 0; w < warmup; w++) {
                for (SpmvStrategy strategy : strategies) {
                    strategy.multiplyInto(x, y);
                }
            }

            StringBuilder rows = new StringBuilder();
            int count = strategies.size();

            for (int it = 0; it < iterations; it++) {
                for (int offset = 0; offset < count; offset++) {
                    int s = (it + offset) % count;
                    long t0 = System.nanoTime();
                    strategies.get(s).multiplyInto(x, y);
                    long t1 = System.nanoTime();

                    rows.append(run).append(',')
                            .append(commit).append(',')
                            .append(fork).append(',')
                            .append(it).append(',')
                            .append(workload).append(',')
                            .append(n).append(',')
                            .append(nnz).append(',')
                            .append(labels.get(s)).append(',')
                            .append(labelP.get(s)).append(',')
                            .append(String.format(Locale.ROOT, "%.6f",
                                    (t1 - t0) / 1e6))
                            .append('\n');
                }
            }

            long peakTotal = sumPeaks(heapPools);
            long maxHeap = Runtime.getRuntime().maxMemory();
            String java = System.getProperty("java.version");
            String flags = String.join(" ",
                    ManagementFactory.getRuntimeMXBean().getInputArguments());

            StringBuilder forkRows = new StringBuilder();

            for (int s = 0; s < count; s++) {
                forkRows.append(String.join(",",
                        run,
                        String.valueOf(fork),
                        workload,
                        String.valueOf(n),
                        String.valueOf(nnz),
                        labels.get(s),
                        String.valueOf(labelP.get(s)),
                        String.valueOf(bitExact[s]),
                        Long.toHexString(hashes[s]),
                        String.format(Locale.ROOT, "%.3f", setupMs),
                        String.valueOf(peakAfterBuild),
                        String.valueOf(peakTotal),
                        String.valueOf(maxHeap),
                        String.valueOf(cores),
                        "\"" + java + "\"",
                        "\"" + flags.replace("\"", "'") + "\""))
                        .append('\n');
            }

            append(raw, rows.toString());
            append(forks, forkRows.toString());
        } finally {
            for (SpmvStrategy strategy : strategies) {
                strategy.close();
            }
        }
    }

    private static long sumPeaks(List<MemoryPoolMXBean> pools) {
        long total = 0;

        for (MemoryPoolMXBean pool : pools) {
            total += pool.getPeakUsage().getUsed();
        }

        return total;
    }

    // ------------------------------------------------------------------
    // STREAM-like triad: memory-bandwidth ceiling
    // ------------------------------------------------------------------

    static void stream(Map<String, String> a) throws IOException {
        String run = req(a, "run");
        int reps = Integer.parseInt(a.getOrDefault("reps", "15"));
        Path out = Paths.get(req(a, "out"));
        int cores = Runtime.getRuntime().availableProcessors();
        int length = 1 << 24; // 16M doubles = 128 MiB per array

        double[] x = new double[length];
        double[] b = new double[length];
        double[] c = new double[length];

        for (int i = 0; i < length; i++) {
            b[i] = 1.0 + (i & 7);
            c[i] = 2.0 - (i & 3);
        }

        StringBuilder rows = new StringBuilder();

        for (String token : req(a, "p").split(",")) {
            int p = Integer.parseInt(token.trim());

            if (p > cores) {
                continue;
            }

            ForkJoinPool pool = new ForkJoinPool(p);
            double[] times = new double[reps];

            try {
                for (int rep = -3; rep < reps; rep++) {
                    long t0 = System.nanoTime();
                    pool.invoke(new Triad(x, b, c, 0, length, p));
                    long t1 = System.nanoTime();

                    if (rep >= 0) {
                        times[rep] = (t1 - t0) / 1e9;
                    }
                }
            } finally {
                pool.shutdown();
            }

            double bytes = 24.0 * length; // read b, read c, write x
            double[] gbs = new double[reps];

            for (int i = 0; i < reps; i++) {
                gbs[i] = bytes / times[i] / 1e9;
            }

            Arrays.sort(gbs);
            rows.append(String.join(",",
                    run, String.valueOf(p),
                    String.format(Locale.ROOT, "%.3f", gbs[reps - 1]),
                    String.format(Locale.ROOT, "%.3f", gbs[reps / 2]),
                    String.valueOf(length))).append('\n');
        }

        append(out, rows.toString());

        if (x[length / 2] == -1.0) {
            System.out.println();
        }
    }

    private static final class Triad extends RecursiveAction {
        private static final long serialVersionUID = 1L;
        private final transient double[] x;
        private final transient double[] b;
        private final transient double[] c;
        private final int from;
        private final int to;
        private final int parts;

        Triad(double[] x, double[] b, double[] c,
              int from, int to, int parts) {
            this.x = x;
            this.b = b;
            this.c = c;
            this.from = from;
            this.to = to;
            this.parts = parts;
        }

        @Override
        protected void compute() {
            if (parts <= 1) {
                for (int i = from; i < to; i++) {
                    x[i] = b[i] + 3.0 * c[i];
                }
                return;
            }

            int leftParts = parts / 2;
            int mid = from + (int) ((long) (to - from) * leftParts / parts);
            invokeAll(
                    new Triad(x, b, c, from, mid, leftParts),
                    new Triad(x, b, c, mid, to, parts - leftParts));
        }
    }

    // ------------------------------------------------------------------
    // utilities
    // ------------------------------------------------------------------

    private static void append(Path file, String text) throws IOException {
        if (text.isEmpty()) {
            return;
        }

        Files.write(file, text.getBytes(StandardCharsets.UTF_8),
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    private static Map<String, String> parse(String[] args) {
        Map<String, String> map = new HashMap<>();

        for (String arg : args) {
            int eq = arg.indexOf('=');

            if (eq > 0) {
                map.put(arg.substring(0, eq), arg.substring(eq + 1));
            }
        }

        return map;
    }

    private static String req(Map<String, String> a, String key) {
        String value = a.get(key);

        if (value == null) {
            throw new IllegalArgumentException("Missing argument: " + key);
        }

        return value;
    }
}
