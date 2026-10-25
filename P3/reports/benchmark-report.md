## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40157013651-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 15
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.440436 | 10.685575 |
| Median (ms) | 2.616998 | 10.680641 |
| Std. dev. (ms) | 1.043454 | 2.176730 |
| Throughput (states/s) | 290660860.193 | 93584111.050 |

- Speedup: **0.321970×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40157013651-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
