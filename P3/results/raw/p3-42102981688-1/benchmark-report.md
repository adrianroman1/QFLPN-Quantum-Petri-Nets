## QFLPN P3 benchmark summary

- Validation: **PASS**
- Run ID: `p3-42102981688-1`
- Schema: `qflpn-benchmark-v2`
- Valid CSV records: 85
- Benchmark ID: `QFLPN-1M`
- Dimension: 1000000
- Non-zero values: 2000000
- Warm-up iterations: 5
- Measured iterations: 10

| Metric | Sequential | Parallel |
|---|---:|---:|
| Mean (ms) | 3.976596 | 4.350592 |
| Median (ms) | 3.011325 | 4.364697 |
| Std. dev. (ms) | 1.411244 | 1.215777 |
| Throughput (states/s) | 251471384.216 | 229853802.638 |

- Speedup: **0.914036×**
- Sequential oracle error: `0.000000000000e+00`
- Parallel oracle error: `0.000000000000e+00`
- Maximum absolute error: `0.000000000000e+00`
- JSON report: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/results/raw/p3-42102981688-1/validation-report.json`
- CSV evidence: `/home/runner/work/QFLPN-Quantum-Petri-Nets/QFLPN-Quantum-Petri-Nets/P3/benchmarks/benchmark_results_v2.csv`

The CSV row and JSON validation report were matched by the exact RUN_ID.
