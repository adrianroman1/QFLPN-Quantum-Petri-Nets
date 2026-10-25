## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40147404114-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 2
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 2.730331 | 7.493091 |
| Median (ms) | 2.306774 | 7.194007 |
| Std. dev. (ms) | 0.680196 | 1.176618 |
| Throughput (states/s) | 366255972.857 | 133456267.909 |

- Speedup: **0.364380×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `P3/results/raw/p3-40147404114-1/validation-report.json`
- CSV evidence: `P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
