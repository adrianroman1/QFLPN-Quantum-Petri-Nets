# QFLPN Reproduction Registry
**Version:** 1.0  
**Date:** 2026-11-11  
**Articles Covered:** P1, P2, P3 (*Information Fusion*, Elsevier Submission)  
**Author & Principal Investigator:** Adrian Roman (adrianroman304@gmail.com / adrian.roman@campus.utcluj.ro)  
**Affiliation:** Technical University of Cluj-Napoca, Faculty of Automation and Computer Science, Cluj-Napoca, Romania  
**Official Repository:** https://github.com/adrianroman1/QFLPN-Quantum-Petri-Nets  
**Commit:** `9f8e4c2b7d14a6ef83b2a5c0d9e7f1a3b5c7d9e1` | **Release Tag:** `v1.0.0`  

---

## 1. Executive Summary & Purpose
This registry serves as the authoritative single point of truth across the QFLPN trilogy. It details the exact computational environment, deterministic seeds, mathematical invariants, analytical tolerances, and scripts required to reproduce every table, figure, and numerical claim across:
- **P1**: Formal Operator Semantics for Quantum-Fuzzy Logical Petri Nets (DOI: 10.5281/zenodo.10823479)
- **P2**: A Four-Qubit Reference Instance of Quantum-Fuzzy Logical Petri Nets (DOI: 10.5281/zenodo.10823480)
- **P3**: Sparse Numerical Evolution for Quantum-Fuzzy Logical Petri Nets: A Parallel Benchmark (DOI: 10.5281/zenodo.10823481)

---

## 2. Article-Level Metadata & Persistent Identifiers
| Article | Short Title | Status | DOI | Supplementary Code | Verification Contract |
|---|---|---|---|---|---|
| **P1** | Formal Operator Semantics | 10/10 Verified | 10.5281/zenodo.10823479 | `p1_worked_examples.py`, `test_p1_formalism.py` | Complete CPTP, trace preservation $\mathrm{Tr}(\rho)=1$, $\mathcal{D}(\rho_{t_1 t_2}, \rho_{t_2 t_1}) = 1.91$ |
| **P2** | 4-Qubit Reference Instance | 10/10 Verified | 10.5281/zenodo.10823480 | `p2_verify.py`, `p2_extended_study.py`, `recompute_variants.py` | Meyer-Wallach $Q=0.0809$, state vector tolerance $10^{-14}$, 1000-vector Monte Carlo sweep |
| **P3** | Sparse Numerical Evolution | 10/10 Verified | 10.5281/zenodo.10823481 | `spmv_csr_kernel.c`, `qflpn_spmv_benchmark.py`, `model_scaling_p3.py` | Strictly discrete markings ($N=10^6 \dots 3\times 10^8$), Roofline $I=0.0909$ FLOP/Byte, speedup ceiling $\le 7.74\times$ |

---

## 3. Strict Semantic & Architectural Demarcation
1. **P3 Discrete markings vs. Qubits**: P3 operates exclusively on classical/discrete Petri net markings ($N = 10^6 \dots 3 \times 10^8$ rows). All quantum state vectors and qubit representations are strictly confined to P1 and P2.
2. **Three-Tier Operational Status**:
   - **MEASURED**: Single-node Platform A / Sandbox ($N \le 10^7$).
   - **ESTIMATED**: Analytical memory footprint envelope (Table 13, up to $3\times 10^8$ markings, 12.29 GiB RAM).
   - **PLANNED**: Multi-node HPC / EOSC campaign on 16 nodes with 664 worker cores.
3. **Four Keywords (Golden Quad)**: Exactly 4 keywords for each article to maximize Scopus/WoS TF-IDF relevance without semantic dilution.
4. **Elsevier Mandatory Declarations**: CRediT, Competing Interests, Funding, Generative AI, and Data Availability statements attached to all articles.

---

## 4. Environment & Dependency Specifications
- **Python**: 3.10+ (Standard library + NumPy, SciPy, Matplotlib; Qiskit 2.6.1 & PennyLane 0.45 optional for cross-check)
- **C Compiler**: GCC 11+ or Clang with OpenMP (`-O3 -fopenmp -std=c99`)
- **Java**: OpenJDK 17+ / 21+ for ParallelSpmvHarness benchmark
- **LaTeX**: TeX Live 2024 / pdflatex (`elsarticle.cls`)
- **Deterministic Seed**: `20260311` for all stochastic sweeps and pseudo-random matrix generators.

---

## 5. Automated Verification
Run the unified verification script from the repository root:
```bash
python3 verify_all_outputs.py [--skip-p3-campaign]
```
All assertions execute in sub-second to minute intervals and produce exact machine-precision match with archived results.
