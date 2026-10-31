# QFLPN P3 — Benchmark Results and HPC Scaling Report

## 1. Scopul campaniei

Campania evaluează algoritmii Sparse Matrix-Vector Multiplication (SpMV) utilizați pentru evoluția spațiului de stări QFLPN.

Evaluarea urmărește:

- scalarea în funcție de dimensiunea spațiului de stări;
- comparația execuției secvențiale cu execuția paralelă;
- influența pragurilor SpMV asupra performanței;
- influența numărului de nuclee de calcul;
- speedup și eficiență paralelă;
- throughput și consum de memorie;
- corectitudinea numerică;
- reproductibilitatea și integritatea rezultatelor.

Toate rezultatele experimentale trebuie să provină din execuții reale, identificabile prin RUN_ID și susținute de fișiere brute.

Nu se completează tabelele cu valori interpolate, estimate sau simulate.

## 2. Dimensiunile benchmarkului

Campania urmărește următoarele dimensiuni ale spațiului de stări:

| Nr. | Dimensiune | N | Statut în RUN_ID analizat |
|---:|---|---:|---|
| 1 | 1 milion de stări | 1.000.000 | MEASURED |
| 2 | 10 milioane de stări | 10.000.000 | NOT MEASURED |
| 3 | 70 milioane de stări | 70.000.000 | NOT MEASURED |
| 4 | 100 milioane de stări | 100.000.000 | NOT MEASURED |

Dimensiunile de 1M, 10M, 70M și 100M sunt dimensiuni distincte ale campaniei.

Rezultatele pentru o dimensiune nu pot fi extrapolate la altă dimensiune.

Fiecare dimensiune trebuie executată independent și identificată prin RUN_ID.

## 3. Configurația pragurilor SpMV

Pragurile SpMV urmărite în campanie sunt:

| Nr. | Prag SpMV |
|---:|---:|
| 1 | 256 |
| 2 | 512 |
| 3 | 1.024 |
| 4 | 2.048 |
| 5 | 4.096 |
| 6 | 8.192 |
| 7 | 16.384 |

Campania pragurilor SpMV urmărește dimensiunile până la:

**N = 10.000.000 de stări.**

Matricea de evaluare a pragurilor este:

| Prag SpMV | N = 1M | N = 10M |
|---:|---|---|
| 256 | NOT MEASURED | NOT MEASURED |
| 512 | NOT MEASURED | NOT MEASURED |
| 1.024 | NOT MEASURED | NOT MEASURED |
| 2.048 | NOT MEASURED | NOT MEASURED |
| 4.096 | CONFIGURATION MEASURED | NOT MEASURED |
| 8.192 | NOT MEASURED | NOT MEASURED |
| 16.384 | NOT MEASURED | NOT MEASURED |

Pragul 4.096 este prezent în configurația benchmarkului V2 verificat. Această execuție nu demonstrează evaluarea comparativă a tuturor pragurilor.

Fiecare combinație dimensiune–prag trebuie să aibă măsurători proprii și identificator de execuție.

Dimensiunile de 70M și 100M rămân incluse în campania generală de benchmark, dar nu sunt declarate automat parte a matricei de praguri SpMV până la 10M.

## 4. Configurația paralelă HPC

Campania HPC urmărește paralelismul de la 1 până la 664 de nuclee fizice.

Intervalul de evaluare este:

**1–664 nuclee fizice.**

Configurația include valorile întregi ale numărului de nuclee din interval, în măsura în care acestea sunt disponibile și executate în mediul HPC.

Configurația de referință din repository:

| Parametru | Valoare |
|---|---:|
| Noduri de calcul | 16 |
| Nuclee fizice totale | 664 |
| RAM totală | 4.096 GiB |
| RAM per nod | 256 GiB |
| Noduri cu 42 nuclee | 8 |
| Noduri cu 41 nuclee | 8 |

Inventarul hardware al fiecărei execuții trebuie să includă:

- producătorul și modelul plăcii de bază;
- producătorul și modelul procesorului;
- numărul de socketuri;
- numărul de nuclee fizice;
- numărul de procesoare logice;
- topologia NUMA;
- memoria RAM;
- sistemul de operare și kernelul;
- versiunea Java;
- versiunea Maven;
- afinitatea CPU;
- numărul efectiv de workers;
- configurația MPI, dacă este utilizată.

Configurația declarată în repository nu reprezintă dovada că toate resursele au fost efectiv utilizate într-o execuție.

## 5. Ultima execuție verificată

| Câmp | Valoare |
|---|---|
| RUN_ID | p3-41240843414-1 |
| Commit | 4ed8a67ee6ff78d7753455128e10788e229700dd |
| Schema | qflpn-benchmark-v2 |
| Benchmark ID | QFLPN-1M |
| Dimensiune N | 1.000.000 |
| Valori nenule | 2.000.000 |
| Warm-up | 5 |
| Iterații măsurate | 10 |
| Înregistrări CSV validate | 81 |
| Verdict workflow | PASS |

## 6. Rezultate experimentale — N = 1.000.000

Rezultatele următoare provin din execuția identificată prin RUN_ID `p3-41240843414-1`.

| Indicator | Secvențial | Paralel |
|---|---:|---:|
| Timp mediu (ms) | 3.035330 | 3.792832 |
| Timp median (ms) | 2.688117 | 3.914198 |
| Deviație standard (ms) | 0.712947 | 0.671135 |
| Throughput (stări/s) | 329453447.931 | 263655203.958 |
| Eroare față de oracle | 0.000000000000e+00 | 0.000000000000e+00 |

**Speedup măsurat: 0.800281×.**

În această execuție, varianta paralelă este mai lentă decât varianta secvențială.

**Eroarea absolută maximă: 0.000000000000e+00.**

Aceste rezultate sunt valabile pentru configurația executată. Nu demonstrează scalabilitate la alte dimensiuni sau pe alte configurații hardware.

## 7. Tabelul rezultatelor pentru dimensiunile campaniei

| N | Timp secvențial | Timp paralel | Speedup | Throughput | Eroare numerică | Statut |
|---:|---|---|---|---|---|---|
| 1.000.000 | 3.035330 ms | 3.792832 ms | 0.800281× | Măsurat | 0 | MEASURED |
| 10.000.000 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 70.000.000 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 100.000.000 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |

## 8. Matricea campaniei HPC

Fiecare dimensiune trebuie evaluată cu configurațiile de paralelism executate efectiv.

| Nuclee fizice | 1M | 10M | 70M | 100M |
|---:|---|---|---|---|
| 1 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 2 | CONFIGURATION MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 4 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 8 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 16 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 32 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 64 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 128 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 256 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 512 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 640 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |
| 664 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |

Acest tabel prezintă configurații de referință, nu toate valorile intermediare. Fiecare configurație executată în intervalul 1–664 trebuie păstrată individual în fișierele brute.

Numărul de workers nu trebuie confundat cu numărul de nuclee fizice utilizate.

## 9. Indicatori obligatorii

| Indicator | Definiție |
|---|---|
| Timp secvențial | Durata execuției secvențiale |
| Timp paralel | Durata execuției paralele |
| Speedup | Timp secvențial / timp paralel |
| Eficiență paralelă | Speedup / număr workers |
| Throughput | Stări procesate pe secundă |
| Deviație standard | Dispersia măsurătorilor |
| Memorie | Consum maxim de memorie |
| Eroare numerică | Abaterea față de oracle |
| N | Dimensiunea spațiului de stări |
| NNZ | Numărul de valori nenule |
| Prag SpMV | Pragul utilizat efectiv |
| Workers | Numărul efectiv de workers |
| Nuclee fizice | Numărul verificat de nuclee fizice |
| RUN_ID | Identificator unic al execuției |

Protocolul pentru campania finală:

- minimum 5 iterații de warm-up;
- minimum 30 de iterații măsurate;
- aceleași date de intrare pentru comparația secvențială și paralelă;
- verificarea echivalenței numerice;
- păstrarea tuturor rezultatelor brute;
- raportarea configurațiilor eșuate și incomplete.

## 10. Artefacte și dovezi

Fiecare execuție trebuie să păstreze:

| Artefact | Rol |
|---|---|
| benchmark CSV | Măsurători brute |
| benchmark JSON | Rezultate structurate |
| benchmark-report.md | Raport lizibil |
| benchmark-report.txt | Raport text |
| validation-report.json | Rezultatul validării |
| environment.json | Mediul de execuție |
| hardware inventory | Inventarul hardware |
| benchmark logs | Jurnalele execuției |
| MANIFEST.txt | Inventarul global |
| SHA256SUMS.txt | Integritatea fișierelor |

Toate rezultatele trebuie asociate RUN_ID-ului corespunzător.

## 11. Integrarea în p3_validation

Lanțul obligatoriu de validare:

`benchmark CSV/JSON/MD/TXT`
→ `p3_validation`
→ `validation-report.json`
→ `environment.json`
→ `hardware inventory`
→ `MANIFEST.txt`
→ `SHA256SUMS.txt`
→ verificarea independentă a pachetului
→ `P3_ACCEPTED`

`MANIFEST.txt` trebuie să inventarieze toate artefactele relevante.

`SHA256SUMS.txt` trebuie să permită verificarea independentă a integrității.

Un rezultat nu este considerat validat dacă nu poate fi asociat unei execuții reale și unui RUN_ID verificabil.

## 12. Verdict pentru RUN_ID analizat

RUN_ID: `p3-41240843414-1`

| Element | Verdict |
|---|---|
| Workflow p3_validation | PASS |
| Benchmark V2 | PASS |
| CSV V2 | VALIDATED |
| Corelare CSV/JSON prin RUN_ID | PASS |
| Verificare numerică V2 | PASS |
| Etapa de validare V3 | PASS |
| Etapa de validare MPI | PASS |
| Generare MANIFEST.txt | PASS |
| Generare SHA256SUMS.txt | PASS |
| Verificarea pachetului final | PASS |
| N = 1.000.000 | MEASURED |
| N = 10.000.000 | NOT MEASURED |
| N = 70.000.000 | NOT MEASURED |
| N = 100.000.000 | NOT MEASURED |
| Campania completă SpMV până la N = 10M | NOT DEMONSTRATED |
| Campania HPC 1–664 nuclee | NOT DEMONSTRATED |
| Scalabilitate HPC | NOT DEMONSTRATED |

**Campania HPC 1–664 nuclee — NEDEMONSTRATĂ în dovezile acestui RUN_ID.**

**Dimensiunile până la N = 10.000.000 — NEDEMONSTRATE în dovezile acestui RUN_ID.**

**Dimensiunile N = 70.000.000 și N = 100.000.000 — NEDEMONSTRATE în dovezile acestui RUN_ID.**

Nu se declară scalabilitate HPC, speedup la 664 de nuclee sau performanță la dimensiuni nemăsurate fără rezultate experimentale reale.

PASS-ul workflow-ului `p3_validation` confirmă trecerea porților configurate în execuția respectivă. Nu demonstrează automat executarea tuturor dimensiunilor, pragurilor SpMV sau configurațiilor HPC definite în acest raport.

Raportul separă rezultatele măsurate de configurațiile planificate și de experimentele încă nedemonstrate.
