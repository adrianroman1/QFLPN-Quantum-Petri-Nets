## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40148345796-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 4
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.242915 | 6.522911 |
| Median (ms) | 1.947243 | 6.353975 |
| Std. dev. (ms) | 0.392074 | 1.159091 |
| Throughput (states/s) | 445848311.793 | 153305798.079 |

- Speedup: **0.343852×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40148345796-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
