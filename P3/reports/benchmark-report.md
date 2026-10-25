## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40238724492-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 40
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 1.825371 | 6.918682 |
| Median (ms) | 1.555915 | 6.542506 |
| Std. dev. (ms) | 0.380402 | 1.667075 |
| Throughput (states/s) | 547833777.590 | 144536207.592 |

- Speedup: **0.263832×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40238724492-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
