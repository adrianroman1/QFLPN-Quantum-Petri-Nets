## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-41240843414-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 81
- Benchmark ID: `QFLPN-1M`
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.035330 | 3.792832 |
| Median (ms) | 2.688117 | 3.914198 |
| Std. dev. (ms) | 0.712947 | 0.671135 |
| Throughput (states/s) | 329453447.931 | 263655203.958 |

- Speedup: **0.800281×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/results/raw/p3-41240843414-1/validation-report.json`
- CSV evidence: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
