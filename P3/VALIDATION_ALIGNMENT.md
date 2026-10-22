# P3 — VALIDATION ALIGNMENT
## Alinierea manuscrisului, codului, testelor și rezultatelor

## 1. Scop

Acest document stabilește corespondența dintre:

- specificația matematică din manuscrisul P3;
- implementarea Java;
- testele automate;
- validarea independentă Python;
- workflow-ul GitHub Actions;
- măsurătorile experimentale;
- artefactele de reproducibilitate.

Documentul completează:

- `P3/results/Traceability.md`;
- `P3/results/Results.md`;
- `P3/results/Reproducibility.md`;
- `P3/P3_AUDIT_REPORT.md`.

Nu înlocuiește trasabilitatea detaliată a fiecărei ecuații și afirmații din manuscris.

## 2. Ierarhia dovezilor

| Nivel | Dovadă | Ce demonstrează |
|---|---|---|
| E1 | Definiție în manuscris | Specificația matematică sau algoritmică |
| E2 | Cod sursă | Existența implementării |
| E3 | Teste automate executate | Comportamentul acoperit de teste |
| E4 | CI pe commit identificat | Rezultatul buildului și testelor pentru acel commit |
| E5 | Benchmark brut | Măsurători obținute prin execuție |
| E6 | Validare independentă | Consistența datelor măsurate |
| E7 | Pachet de reproducibilitate | Proveniență, mediu, loguri și integritate |

Niciun nivel nu demonstrează automat afirmații care depășesc domeniul său.

Exemple:

- existența codului nu demonstrează corectitudinea;
- testele unitare nu demonstrează speedup;
- CI PASS nu demonstrează performanța pe un alt hardware;
- un rezultat istoric nu demonstrează configurația experimentală curentă;
- un checksum verificat demonstrează integritatea fișierului, nu corectitudinea sa științifică.

## 3. Alinierea manuscris–implementare–verificare

| Afirmație / componentă | Implementare | Verificare necesară | Criteriu |
|---|---|---|---|
| Reprezentare CSR | `SparseMatrixCSR.java` | Teste CSR | Indici și pointeri valizi |
| SpMV secvențial | `SparseMatrixCSR.java` | Oracol dens | Rezultate echivalente numeric |
| SpMV paralel | `SparseMatrixCSR.java` | Teste paralele | Echivalență cu rezultatul secvențial |
| Decompoziție Fork/Join | `MultiplyTask.java` | Teste Fork/Join | Acoperire corectă a rândurilor |
| Matrice dreptunghiulare | CSR și MultiplyTask | Teste rectangulare | Separarea dimensiunii rândurilor de coloane |
| Motor QFLPN | `QFLPNCoreEngine.java` | Teste de motor | Contractul matematic este respectat |
| Benchmark | `BenchmarkRunner.java` | Execuție reală | Parametrii efectivi sunt înregistrați |
| Timing secvențial | `BenchmarkRunner.java` | CSV și log | Timp pozitiv și finit |
| Timing paralel | `BenchmarkRunner.java` | CSV și log | Timp pozitiv și finit |
| Speedup | `BenchmarkRunner.java` | Recalculare independentă | `T_seq / T_par` |
| Reducere timp | Derivată din timpi | Recalculare independentă | `1 - T_par / T_seq` |
| CSV writer | `BenchmarkResultWriter.java` | Teste writer | Schema și valorile sunt persistate |
| CSV reader | `BenchmarkResultReader.java` | Teste reader | Înregistrările sunt citite corect |
| Validator Java | `BenchmarkAuditValidator.java` | Teste validator | Reguli numerice și structurale |
| Validator Python | `validate_benchmark.py` | pytest | Validare independentă |
| Mediu de execuție | `BenchmarkEnvironment.java` | Metadate | Mediu identificabil |
| Reproducibilitate | Script și artefacte | Execuție repetabilă | RUN_ID și pachet complet |

Un criteriu poate fi declarat PASS numai dacă există dovada corespunzătoare nivelului său.

## 4. Specificația matematică și workload-ul sintetic

Workload-ul sintetic de benchmark trebuie separat de exemplele mici de corectitudine din manuscris.

Parametrii workload-ului:

- `N` — numărul de rânduri și coloane pentru workload-ul pătratic;
- `NNZ` — numărul de elemente nenule;
- matricea este stocată în format CSR;
- operația măsurată este SpMV.

Pentru workload-ul determinist descris de script:

```text
NNZ = 2N
x[i] = 1.0
