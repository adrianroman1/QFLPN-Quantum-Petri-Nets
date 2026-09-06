# QFLPN CSR Benchmark Protocol

## 1. Scop

Acest document definește protocolul experimental utilizat pentru
evaluarea implementării sparse CSR a proiectului QFLPN.

Scopul este obținerea unor rezultate:

- reproductibile;
- comparabile;
- documentate;
- verificabile;
- separate de rezultatele CI de validare.

---

# 2. Scările experimentale

Proiectul utilizează trei scări standard:

| ID | N | NNZ |
|---|---:|---:|
| QFLPN-12 | 12 | 24 |
| QFLPN-1M | 1,000,000 | 2,000,000 |
| QFLPN-30M | 30,000,000 | 60,000,000 |

---

# 3. Operația evaluată

Operația benchmark-ului este:

`y = A * x`

unde `A` este stocată în format CSR.

Matricea standard de benchmark este construită astfel:

`A[i,i] = 1.0`

`A[i,i+1] = 0.5`

pentru ultimul rând indicele coloanei secundare revine la zero.

Vectorul de intrare este:

`x[i] = 1.0`

Prin urmare rezultatul așteptat este:

`y[i] = 1.5`

pentru fiecare element.

---

# 4. Indicatori măsurați

Pentru fiecare rulare se înregistrează:

- timpul secvențial;
- timpul paralel;
- speedup;
- throughput secvențial;
- throughput paralel;
- eroarea față de rezultatul așteptat;
- eroarea dintre rezultatul secvențial și cel paralel;
- timpul de setup;
- dimensiunea matricei;
- numărul de elemente nenule;
- gradul de paralelism;
- threshold;
- numărul de warmup-uri;
- numărul de iterații măsurate;
- mediul de execuție.

---

# 5. Validare numerică

Un rezultat este considerat numeric valid numai dacă sunt simultan
îndeplinite:

`sequentialExpectedError <= 1e-12`

`parallelExpectedError <= 1e-12`

`maxAbsoluteError <= 1e-12`

Rezultatul trebuie să raporteze:

`Sequential PASS`

`Parallel PASS`

`Seq/Par match PASS`

---

# 6. Măsurarea timpului

Timpul operației CSR este măsurat cu:

`System.nanoTime()`

Warmup-ul este executat înaintea perioadei măsurate.

ForkJoinPool-ul este creat înaintea perioadei măsurate și este
reutilizat pentru toate iterațiile paralele.

Crearea și închiderea pool-ului nu trebuie incluse în timpul
raportat pentru multiplicarea CSR.

Persistarea CSV se realizează după efectuarea măsurătorilor.

Prin urmare:

**CSV write time NU este benchmark time.**

---

# 7. Benchmark CI

GitHub Actions execută un benchmark smoke pe:

`QFLPN-1M`

cu configurația:

- N = 1,000,000
- warmup = 1
- iterations = 2
- threshold = 4096
- parallelism = 2

Acest test are rolul de a confirma că benchmark-ul funcționează
într-un mediu automatizat.

Valorile CI nu sunt considerate automat rezultate experimentale
finale pentru teză.

---

# 8. Benchmark experimental final

Pentru rezultatele finale trebuie documentate:

## Hardware

- producător;
- model CPU;
- număr nuclee;
- număr thread-uri;
- RAM;
- GPU, dacă este utilizat.

## Software

- sistem de operare;
- versiune;
- Java;
- JVM;
- versiune Maven;
- parametri JVM.

## Experiment

- N;
- NNZ;
- threshold;
- parallelism;
- warmup;
- număr de iterații;
- timpul secvențial;
- timpul paralel;
- speedup;
- throughput;
- eroare numerică.

---

# 9. QFLPN-12

Rol:

Validare funcțională și verificarea comportamentului pentru o
instanță foarte mică.

Status:

- [ ] benchmark executat
- [ ] rezultat numeric valid
- [ ] rezultat în CSV
- [ ] analiză

---

# 10. QFLPN-1M

Rol:

Validare la scară medie și benchmark de referință.

Rezultat CI actual:

- Sequential avg = 8.250 ms
- Parallel avg = 3.139 ms
- Speedup = 2.6281x
- Sequential throughput = 121216205.831 states/s
- Parallel throughput = 318564472.034 states/s
- Max absolute error = 0
- Validation = PASS

Acest rezultat provine din GitHub Actions și trebuie tratat ca
rezultat exploratoriu CI.

Status:

- [x] benchmark CI
- [x] validare numerică
- [x] rezultat înregistrat
- [ ] benchmark experimental controlat

---

# 11. QFLPN-30M

Rol:

Validarea obiectivului de scalare la scară mare.

Această rulare:

- nu trebuie executată la fiecare commit;
- trebuie realizată pe hardware documentat;
- trebuie verificată memoria disponibilă;
- trebuie păstrate toate valorile benchmarkului.

Status:

- [ ] benchmark executat
- [ ] memorie verificată
- [ ] rezultat numeric valid
- [ ] rezultat înregistrat
- [ ] hardware documentat
- [ ] analiză

---

# 12. Reguli pentru raportarea în teză

Nu se raportează o valoare de performanță fără:

`N + NNZ + hardware + software + parametri + rezultat`

Nu se prezintă o țintă drept rezultat obținut.

Exemplu:

`< 15 ms` este o țintă până când există măsurători reproductibile
care demonstrează această valoare în condițiile declarate.

---

# 13. Legătura cu registrul doctoral

Pentru fiecare rezultat important:

`Benchmark -> CSV -> commit Git -> tabel teză -> articol`

Fiecare rezultat experimental important trebuie să poată fi urmărit
înapoi până la versiunea codului care l-a produs.

---

# 14. Starea curentă

| Componentă | Status |
|---|---|
| SparseMatrixCSR | DONE |
| MultiplyTask | DONE |
| QFLPNCoreEngine | DONE |
| BenchmarkRunner | DONE |
| BenchmarkResult | DONE |
| BenchmarkResultWriter | DONE |
| BenchmarkResultReader | DONE |
| BenchmarkScale | DONE |
| Benchmark environment | DONE |
| JUnit validation | DONE |
| GitHub CI | DONE |
| QFLPN-1M CI benchmark | DONE |
| QFLPN-12 final benchmark | TODO |
| QFLPN-1M controlled benchmark | TODO |
| QFLPN-30M benchmark | TODO |
| JMH final benchmark | TODO |

---

# 15. Obiectiv

Obiectivul experimental este să existe o bază de rezultate:

**QFLPN-12 → QFLPN-1M → QFLPN-30M**

cu aceeași metodologie și cu mediul de execuție documentat.

Aceste rezultate vor constitui baza pentru:

- analiza de performanță;
- comparații;
- grafice;
- tabele;
- articole;
- capitolul experimental al tezei.
