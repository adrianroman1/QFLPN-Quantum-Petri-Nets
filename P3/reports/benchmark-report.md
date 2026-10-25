## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40237128816-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 35
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.988289 | 11.324798 |
| Median (ms) | 3.179227 | 10.224165 |
| Std. dev. (ms) | 1.231627 | 2.747757 |
| Throughput (states/s) | 250734111.869 | 88301793.419 |

- Speedup: **0.352173×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40237128816-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
