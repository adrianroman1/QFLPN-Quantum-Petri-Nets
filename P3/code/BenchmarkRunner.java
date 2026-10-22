package hpc.csr;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ForkJoinPool;

/** Reproducible CSR SpMV benchmark with an independent analytical oracle and V2 evidence. */
public final class BenchmarkRunner {
    private static final int DEFAULT_N=1_000_000, DEFAULT_WARMUP=5, DEFAULT_ITERATIONS=10, DEFAULT_THRESHOLD=4096;
    private static final double EPSILON=1.0e-12;
    private BenchmarkRunner() {}

    public static void main(String[] args) {
        Config c=Config.parse(args); String runId=System.getenv("RUN_ID");
        if(runId==null || runId.isBlank()) runId=DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(java.time.ZoneOffset.UTC).format(Instant.now())+"-"+UUID.randomUUID();
        if(!runId.matches("[A-Za-z0-9._-]+")) throw new IllegalArgumentException("Invalid RUN_ID");
        long setupStart=System.nanoTime(); SparseMatrixCSR matrix=createMatrix(c.n);
        double[] x=new double[c.n], seq=new double[c.n], par=new double[c.n], oracle=new double[c.n];
        Arrays.fill(x,1.0); Arrays.fill(oracle,1.5);
        double setupMs=ms(System.nanoTime()-setupStart); ForkJoinPool pool=new ForkJoinPool(c.parallelism);
        try {
            for(int i=0;i<c.warmup;i++){ matrix.multiplyInto(x,seq); matrix.multiplyParallelInto(x,par,c.threshold,pool); }
            double[] seqTimes=new double[c.iterations], parTimes=new double[c.iterations];
            for(int i=0;i<c.iterations;i++) {
                long t;
                if((i&1)==0){ t=System.nanoTime(); matrix.multiplyInto(x,seq); seqTimes[i]=ms(System.nanoTime()-t); t=System.nanoTime(); matrix.multiplyParallelInto(x,par,c.threshold,pool); parTimes[i]=ms(System.nanoTime()-t); }
                else { t=System.nanoTime(); matrix.multiplyParallelInto(x,par,c.threshold,pool); parTimes[i]=ms(System.nanoTime()-t); t=System.nanoTime(); matrix.multiplyInto(x,seq); seqTimes[i]=ms(System.nanoTime()-t); }
                if(seqTimes[i]<=0 || parTimes[i]<=0) throw new IllegalStateException("Non-positive measurement");
            }
            double seqMean=mean(seqTimes), parMean=mean(parTimes), seqMedian=median(seqTimes), parMedian=median(parTimes);
            double seqSd=populationStdDev(seqTimes), parSd=populationStdDev(parTimes);
            double seqErr=maxAbsoluteError(seq,oracle), parErr=maxAbsoluteError(par,oracle), diff=maxAbsoluteError(seq,par);
            if(seqErr>EPSILON || parErr>EPSILON || diff>EPSILON) throw new IllegalStateException("Independent numerical oracle failed: seq="+seqErr+", parallel="+parErr+", diff="+diff);
            Runtime rt=Runtime.getRuntime(); double speedup=seqMean/parMean;
            BenchmarkResult r=new BenchmarkResult(Instant.now().toString(),runId,benchmarkId(c.n),c.n,matrix.getNnz(),c.parallelism,c.threshold,c.warmup,c.iterations,
                seqMean,seqMedian,seqSd,parMean,parMedian,parSd,speedup,c.n/(seqMean/1000),c.n/(parMean/1000),seqErr,parErr,diff,setupMs,
                System.getProperty("os.arch","unknown")+"; processors="+rt.availableProcessors(),rt.maxMemory(),rt.freeMemory(),
                System.getProperty("java.version","unknown"),System.getProperty("os.name","unknown")+" "+System.getProperty("os.version","unknown"),
                "V2; population standard deviation; independent analytical oracle y[i]=1.5; alternating measurement order");
            BenchmarkResultWriter.append(r);
            writeReports(r, Path.of("results","raw",runId));
            print(r);
        } catch(IOException e){ throw new IllegalStateException("Unable to persist benchmark evidence",e); }
        finally { pool.shutdown(); }
    }

    static double mean(double[] a){ requireSamples(a); double s=0; for(double v:a){finitePositive(v);s+=v;} return s/a.length; }
    static double median(double[] a){ requireSamples(a); double[] b=a.clone(); for(double v:b)finitePositive(v); Arrays.sort(b); int m=b.length/2; return (b.length%2==0)?(b[m-1]+b[m])/2:b[m]; }
    static double populationStdDev(double[] a){ double m=mean(a),s=0; for(double v:a){double d=v-m;s+=d*d;} return Math.sqrt(s/a.length); }
    static double maxAbsoluteError(double[] a,double[] b){ if(a==null||b==null||a.length!=b.length)throw new IllegalArgumentException("Vectors must have equal non-null lengths"); double max=0; for(int i=0;i<a.length;i++){if(!Double.isFinite(a[i])||!Double.isFinite(b[i]))throw new IllegalStateException("Non-finite vector value at "+i);max=Math.max(max,Math.abs(a[i]-b[i]));}return max; }
    private static void requireSamples(double[] a){if(a==null||a.length==0)throw new IllegalArgumentException("At least one sample is required");}
    private static void finitePositive(double v){if(!Double.isFinite(v)||v<=0)throw new IllegalArgumentException("Samples must be finite and positive");}
    private static double ms(long ns){return ns/1_000_000.0;}
    private static String benchmarkId(int n){return n==12?"QFLPN-12":n==1_000_000?"QFLPN-1M":n==30_000_000?"QFLPN-30M":"QFLPN-"+n;}
    private static SparseMatrixCSR createMatrix(int n){if(n<=0)throw new IllegalArgumentException("N must be positive"); long count=2L*n;if(count>Integer.MAX_VALUE)throw new IllegalArgumentException("NNZ exceeds Java array limit"); double[] v=new double[(int)count];int[] col=new int[(int)count],rp=new int[n+1]; for(int i=0;i<n;i++){int k=2*i;v[k]=1;v[k+1]=0.5;col[k]=i;col[k+1]=(i+1<n)?i+1:0;rp[i+1]=k+2;}return new SparseMatrixCSR(v,col,rp,n,n);}
    private static void writeReports(BenchmarkResult r,Path dir)throws IOException{
        Files.createDirectories(dir);
        String json="{\n  \"schema\": \"qflpn-benchmark-v2\",\n  \"validation\": \"PASS\",\n  \"run_id\": \""+esc(r.runId())+"\",\n  \"timestamp\": \""+esc(r.timestamp())+"\",\n  \"dimension\": "+r.dimension()+",\n  \"nnz\": "+r.nonZeroCount()+",\n  \"warmup\": "+r.warmupIterations()+",\n  \"iterations\": "+r.measuredIterations()+",\n  \"sequential_mean_ms\": "+r.sequentialMs()+",\n  \"sequential_median_ms\": "+r.sequentialMedianMs()+",\n  \"sequential_stddev_ms\": "+r.sequentialStdDevMs()+",\n  \"parallel_mean_ms\": "+r.parallelMs()+",\n  \"parallel_median_ms\": "+r.parallelMedianMs()+",\n  \"parallel_stddev_ms\": "+r.parallelStdDevMs()+",\n  \"speedup\": "+r.speedup()+",\n  \"sequential_throughput_states_per_s\": "+r.sequentialThroughput()+",\n  \"parallel_throughput_states_per_s\": "+r.parallelThroughput()+",\n  \"sequential_oracle_error\": "+r.sequentialExpectedError()+",\n  \"parallel_oracle_error\": "+r.parallelExpectedError()+",\n  \"max_absolute_error\": "+r.maxAbsoluteError()+"\n}\n";
        String md="# QFLPN P3 Benchmark V2\n\n- Run ID: `"+r.runId()+"`\n- Validation: **PASS**\n- Dimension / NNZ: "+r.dimension()+" / "+r.nonZeroCount()+"\n- Warm-up / measured: "+r.warmupIterations()+" / "+r.measuredIterations()+"\n\n| Metric | Sequential | Parallel |\n|---|---:|---:|\n| Mean (ms) | "+r.sequentialMs()+" | "+r.parallelMs()+" |\n| Median (ms) | "+r.sequentialMedianMs()+" | "+r.parallelMedianMs()+" |\n| Std. dev. (ms) | "+r.sequentialStdDevMs()+" | "+r.parallelStdDevMs()+" |\n| Throughput (states/s) | "+r.sequentialThroughput()+" | "+r.parallelThroughput()+" |\n\n- Speedup: **"+r.speedup()+"×**\n- Independent oracle max error: "+Math.max(r.sequentialExpectedError(),r.parallelExpectedError())+"\n- Sequential/parallel max difference: "+r.maxAbsoluteError()+"\n";
        String txt="QFLPN P3 BENCHMARK V2\nRUN_ID="+r.runId()+"\nVALIDATION=PASS\nDIMENSION="+r.dimension()+"\nNNZ="+r.nonZeroCount()+"\nWARMUP="+r.warmupIterations()+"\nITERATIONS="+r.measuredIterations()+"\nSEQUENTIAL_MEAN_MS="+r.sequentialMs()+"\nSEQUENTIAL_MEDIAN_MS="+r.sequentialMedianMs()+"\nSEQUENTIAL_STDDEV_MS="+r.sequentialStdDevMs()+"\nPARALLEL_MEAN_MS="+r.parallelMs()+"\nPARALLEL_MEDIAN_MS="+r.parallelMedianMs()+"\nPARALLEL_STDDEV_MS="+r.parallelStdDevMs()+"\nSPEEDUP="+r.speedup()+"\nSEQUENTIAL_ORACLE_ERROR="+r.sequentialExpectedError()+"\nPARALLEL_ORACLE_ERROR="+r.parallelExpectedError()+"\nMAX_ABSOLUTE_ERROR="+r.maxAbsoluteError()+"\n";
        Files.writeString(dir.resolve("benchmark-report.json"),json,StandardCharsets.UTF_8);
        Files.writeString(dir.resolve("benchmark-report.md"),md,StandardCharsets.UTF_8);
        Files.writeString(dir.resolve("benchmark-report.txt"),txt,StandardCharsets.UTF_8);
    }
    private static String esc(String s){return s.replace("\\","\\\\").replace("\"","\\\"");}
    private static void print(BenchmarkResult r){System.out.printf(Locale.ROOT,"RUN_ID=%s%nVALIDATION=PASS%nSequential mean/median/stddev: %.6f / %.6f / %.6f ms%nParallel mean/median/stddev: %.6f / %.6f / %.6f ms%nSpeedup: %.6f%nOracle max error: %.3e%nCSV: %s%n",r.runId(),r.sequentialMs(),r.sequentialMedianMs(),r.sequentialStdDevMs(),r.parallelMs(),r.parallelMedianMs(),r.parallelStdDevMs(),r.speedup(),Math.max(r.sequentialExpectedError(),r.parallelExpectedError()),BenchmarkResultWriter.defaultOutputPath());}
    private record Config(int n,int warmup,int iterations,int threshold,int parallelism){static Config parse(String[] args){int n=DEFAULT_N,w=DEFAULT_WARMUP,it=DEFAULT_ITERATIONS,t=DEFAULT_THRESHOLD,p=Math.max(1,Runtime.getRuntime().availableProcessors());for(String a:args){if(a.startsWith("--n="))n=val(a, true);else if(a.startsWith("--warmup="))w=val(a,false);else if(a.startsWith("--iterations="))it=val(a,true);else if(a.startsWith("--threshold="))t=val(a,true);else if(a.startsWith("--parallelism="))p=val(a,true);else throw new IllegalArgumentException("Unknown argument: "+a);}return new Config(n,w,it,t,p);}static int val(String a,boolean positive){int x=Integer.parseInt(a.substring(a.indexOf('=')+1));if(positive?x<=0:x<0)throw new IllegalArgumentException("Invalid value: "+a);return x;}}
}
