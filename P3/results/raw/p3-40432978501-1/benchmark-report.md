## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-40432978501-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 50
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.171858 | 2.368564 |
| Median (ms) | 2.948914 | 2.050393 |
| Std. dev. (ms) | 0.699596 | 0.636281 |
| Throughput (states/s) | 315272665.456 | 422196722.478 |

- Speedup: **1.339148×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/results/raw/p3-40432978501-1/validation-report.json`
- CSV evidence: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
