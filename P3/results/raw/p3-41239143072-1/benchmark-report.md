## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-41239143072-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 80
- Benchmark ID: `QFLPN-1M`
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.483929 | 2.832920 |
| Median (ms) | 2.328942 | 2.853722 |
| Std. dev. (ms) | 0.315228 | 0.236975 |
| Throughput (states/s) | 402587931.847 | 352992622.031 |

- Speedup: **0.876809×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/results/raw/p3-41239143072-1/validation-report.json`
- CSV evidence: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
