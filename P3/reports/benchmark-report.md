## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40225391867-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 27
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.279891 | 10.019133 |
| Median (ms) | 2.641374 | 10.346248 |
| Std. dev. (ms) | 0.982975 | 1.726963 |
| Throughput (states/s) | 304888143.553 | 99809035.373 |

- Speedup: **0.327363×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40225391867-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
