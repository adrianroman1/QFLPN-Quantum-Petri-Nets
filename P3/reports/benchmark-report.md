# QFLPN P3 — BENCHMARK REPORT

Raport central al rezultatelor benchmarkurilor validate și al campaniei
de evaluare HPC.

Ultima actualizare documentată: 2026-10-31
Ultimul RUN_ID de referință: p3-41236675753-1
Workflow obligatoriu: p3_validation
Repository: adrianroman1/QFLPN-Quantum-Petri-Nets

---

## 1. Situația generală a dovezilor

Raportul separă rezultatele experimentale validate de configurația
HPC de referință și de măsurătorile care urmează să fie executate.

| Indicator | Situație documentată |
|---|---|
| Schema benchmark V2 | qflpn-benchmark-v2 |
| RUN_ID de referință | p3-41236675753-1 |
| Validarea raportului V2 | PASS |
| Înregistrări CSV validate | 78 |
| Dimensiunea benchmarkului măsurat | 1.000.000 |
| Valori nenule | 2.000.000 |
| Iterații warm-up | 5 |
| Iterații măsurate | 10 |
| Paralelism măsurat | 2 |
| Prag SpMV măsurat | 4.096 |
| Campanie HPC 1–664 nuclee | În curs de demonstrare |
| Dimensiune N = 10.000.000 | De demonstrat experimental |

Validarea PASS se referă la execuția V2 identificată prin RUN_ID.
Nu reprezintă dovada executării benchmarkului pe 664 de nuclee.

---

## 2. Rezultatul benchmarkului V2 verificat

### 2.1 Identificarea execuției

| Câmp | Valoare |
|---|---|
| RUN_ID | p3-41236675753-1 |
| Workflow run ID | 41236675753 |
| Timestamp UTC | 2026-10-31T19:59:13.136882156Z |
| Schema | qflpn-benchmark-v2 |
| Benchmark ID | QFLPN-1M |
| Dimension | 1.000.000 |
| NNZ | 2.000.000 |
| Warm-up | 5 |
| Iterații măsurate | 10 |
| Paralelism | 2 |
| Prag SpMV | 4.096 |
| Înregistrări CSV validate | 78 |
| Validare | PASS |

### 2.2 Timpi de execuție

| Indicator | Secvențial | Paralel |
|---|---:|---:|
| Timp mediu (ms) | 3,470417 | 3,744938 |
| Timp median (ms) | 3,012406 | 3,500631 |
| Abatere standard (ms) | 0,895481 | 0,827544 |
| Debit (stări/s) | 288.149.826,845 | 267.027.082,020 |

**Speedup: 0,926695×**

Interpretare: pentru configurația măsurată, execuția paralelă este
mai lentă decât execuția secvențială. Această măsurătoare nu demonstrează
un avantaj de performanță al paralelizării la două nuclee.

### 2.3 Corectitudine numerică

| Indicator | Rezultat |
|---|---:|
| Eroare oracle secvențial | 0,000000000000e+00 |
| Eroare oracle paralel | 0,000000000000e+00 |
| Eroare absolută maximă | 0,000000000000e+00 |

Rezultatele numerice ale execuției de referință coincid cu oracle-ul
independent pentru datele validate în acel RUN_ID.

---

## 3. Configurația HPC de referință

Configurația este definită în:

`P3/hpc/config/hpc-664.json`

Statutul configurației:

`PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE`

Aceasta descrie infrastructura HPC de referință și nu constituie,
prin ea însăși, dovada existenței sau inventarierii infrastructurii.

### 3.1 Paralelism pe nuclee

Campania de benchmark utilizează intervalul:

**1–664 nuclee inclusiv.**

Configurația de evaluare urmărește scalabilitatea execuției secvențiale
și paralele pe întregul interval de paralelism definit pentru campanie.

Valorile efectiv măsurate trebuie înregistrate în CSV și asociate
cu RUN_ID-ul execuției.

### 3.2 Praguri SpMV

Pragurile SpMV sunt parametri independenți de numărul de nuclee:

| Praguri SpMV |
|---:|
| 256 |
| 512 |
| 1.024 |
| 2.048 |
| 4.096 |
| 8.192 |
| 16.384 |

Fiecare prag trebuie evaluat în condiții comparabile, păstrând
aceeași dimensiune a problemei și aceeași configurație hardware
pentru comparațiile corespunzătoare.

### 3.3 Dimensiunile benchmarkului

Campania urmărește dimensiuni până la:

**N = 10.000.000.**

Pentru fiecare dimensiune trebuie păstrate rezultatele brute,
configurația efectivă, identificatorul execuției și rapoartele
de validare.

Nu se introduc valori estimate sau interpolate în tabelele
de rezultate experimentale.

---

## 4. Indicatorii raportării HPC

Pentru fiecare combinație executată de dimensiune, paralelism
și prag SpMV se raportează:

| Indicator | Secvențial | Paralel |
|---|---:|---:|
| Timp minim (ms) | De măsurat | De măsurat |
| Timp median (ms) | De măsurat | De măsurat |
| Timp mediu (ms) | De măsurat | De măsurat |
| Timp maxim (ms) | De măsurat | De măsurat |
| Abatere standard (ms) | De măsurat | De măsurat |
| Debit (stări/s) | De măsurat | De măsurat |
| Eroare numerică maximă | De măsurat | De măsurat |

Indicatori calculați pentru comparație:

- Speedup = T_secvențial / T_paralel.
- Eficiență paralelă = Speedup / numărul de nuclee utilizate.
- Eroare absolută maximă față de oracle.
- Numărul măsurătorilor valide.
- Numărul măsurătorilor respinse.
- RUN_ID și identificatorul workflow-ului.
- Configurația hardware și software efectivă.

Acest tabel definește structura raportării; nu reprezintă rezultate
experimentale deja obținute.

---

## 5. Cerințe de validare pentru campania HPC

Fiecare execuție trebuie să păstreze și să valideze:

1. Dimensiunea N și numărul NNZ.
2. Numărul efectiv de nuclee utilizate.
3. Pragul SpMV.
4. Numărul de iterații warm-up.
5. Numărul măsurătorilor valide.
6. Timpii secvențiali și paraleli.
7. Speedup și debit.
8. Eroarea numerică față de oracle.
9. Identitatea hardware și software a mașinii.
10. RUN_ID și identificatorul workflow-ului.
11. Fișierele brute și rapoartele generate.
12. Integritatea artefactelor.

Configurația HPC de referință solicită minimum:

- 5 iterații warm-up;
- 30 de măsurători valide.

Execuția V2 de referință documentată în secțiunea 2 a utilizat
5 iterații warm-up și 10 iterații măsurate. Aceasta nu trebuie
confundată cu cerința de minimum 30 de măsurători pentru campania HPC.

---

## 6. Infrastructura HPC de referință

Configurația propusă în `hpc-664.json` descrie:

| Componentă | Configurație |
|---|---:|
| Noduri de calcul | 16 |
| Nuclee fizice totale | 664 |
| RAM totală | 4.096 GiB |
| RAM per nod | 256 GiB |
| Noduri HPC-01–HPC-08 | 8 × 42 nuclee |
| Noduri HPC-09–HPC-16 | 8 × 41 nuclee |
| Nod de management | HPC-MGMT |

Verificarea aritmetică:

8 × 42 + 8 × 41 = 664 nuclee fizice.

Nodul de management nu este inclus în totalul nucleelor de calcul.

Configurația este o țintă de referință. Inventarul hardware real
trebuie atașat separat înainte ca rezultatele să poată fi atribuite
unei infrastructuri de 664 de nuclee.

---

## 7. Mediul execuției V2 de referință

Sursa: `P3/results/raw/p3-41236675753-1/environment.json`

| Componentă | Valoare |
|---|---|
| Sistem de operare | Linux |
| Platformă | Linux 7.0.0-1017-azure |
| Arhitectură | amd64 |
| Java | OpenJDK 21.0.13 |
| Maven | Apache Maven 3.10.0 |
| Python | 3.12.15 |
| Commit | f5ea02c80aad12fda06f11942ff2ad0ec8a49560 |
| Workflow run ID | 41236675753 |

Configurația V2 efectivă:

- dimension = 1.000.000;
- parallelism = 2;
- threshold = 4.096;
- warmup = 5;
- iterations = 10.

Acest mediu nu constituie inventarul unei infrastructuri HPC
cu 664 de nuclee.

---

## 8. Trasabilitatea dovezilor

### 8.1 Dovezi benchmark

Artefactele de referință sunt:

- `P3/benchmarks/benchmark_results_v2.csv`
- `P3/reports/benchmark-report.json`
- `P3/reports/validation-report.json`
- `P3/results/raw/p3-41236675753-1/benchmark-report.md`
- `P3/results/raw/p3-41236675753-1/benchmark-report.json`
- `P3/results/raw/p3-41236675753-1/validation-report.json`
- `P3/results/raw/p3-41236675753-1/environment.json`

### 8.2 Lanțul de integritate

Lanțul obligatoriu de validare și integritate este:

`p3_validation`
    |
    v
`MANIFEST.txt`
    |
    v
`SHA256SUMS.txt`
    |
    v
Verificarea integrității artefactelor

Raportul central nu înlocuiește validatorul, manifestul sau verificarea
SHA-256. El prezintă rezultatele și trimite la artefactele care le susțin.

### 8.3 Regula de acceptare

Un rezultat poate fi prezentat drept măsurătoare validată numai dacă:

- există înregistrarea brută;
- RUN_ID este identificabil;
- raportul JSON corespunde înregistrării CSV;
- validarea asociată execuției este PASS;
- artefactele sunt incluse în lanțul de integritate;
- configurația hardware și software este documentată.

---

## 9. Limitări și interpretarea rezultatelor

Rezultatul V2 documentat aici este limitat la:

- N = 1.000.000;
- NNZ = 2.000.000;
- paralelism = 2;
- prag SpMV = 4.096;
- 5 iterații warm-up;
- 10 iterații măsurate.

Speedup-ul măsurat este 0,926695×. Prin urmare, această execuție
nu demonstrează accelerare paralelă.

Dovezile acestei execuții nu demonstrează încă:

- scalabilitatea pe intervalul 1–664 nuclee;
- performanța la N = 10.000.000;
- comparația completă a celor șapte praguri SpMV;
- scalabilitatea puternică sau slabă pe infrastructura HPC;
- eficiența paralelă pe infrastructura de referință.

Aceste concluzii vor putea fi formulate numai după executarea
și validarea măsurătorilor corespunzătoare.

---

## 10. Verdictul raportului

**V2 — PASS pentru execuția de referință `p3-41236675753-1`.**

Verdictul confirmă validarea înregistrărilor și concordanța dovezilor
pentru execuția V2 identificată.

**Campania HPC 1–664 nuclee — NEDEMONSTRATĂ în dovezile acestui RUN_ID.**

**Dimensiuni până la N = 10.000.000 — NEDEMONSTRATE în dovezile
acestui RUN_ID.**

Nu se declară scalabilitate HPC, speedup la 664 de nuclee sau
performanță la N = 10.000.000 fără măsurători reale.

Toate rezultatele viitoare trebuie integrate în fluxul:

**p3_validation → MANIFEST.txt → SHA256SUMS.txt**
