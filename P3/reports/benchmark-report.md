QFLPN P3 — BENCHMARK REPORT

Raport central al performanței secvențiale și paralele pentru toate dimensiunile canonice

Ultima actualizare a dovezilor istorice: "2026-10-31"
Ultimul RUN_ID istoric verificat: "p3-41236675753-1"

1. Obiectivul benchmarkului

Evaluarea comparativă a algoritmilor secvențiali și paraleli pentru evoluția stărilor QFLPN, la toate cele patru dimensiuni temporizate canonice:

- QFLPN-1M — 1.000.000;
- QFLPN-10M — 10.000.000;
- QFLPN-70M — 70.000.000;
- QFLPN-100M — 100.000.000.

Pentru fiecare dimensiune se urmăresc timpul de execuție, throughput-ul, speedup-ul, variabilitatea măsurătorilor și corectitudinea numerică.

Dimensiunea 12 este exclusiv fixture de corectitudine. Dimensiunea 30M nu face parte din catalogul canonic.

2. Catalogul canonic și starea măsurătorilor

Benchmark| Dimensiune| Valori nenule| Statutul dovezilor
QFLPN-1M| 1.000.000| 2.000.000| Istoric confirmat
QFLPN-10M| 10.000.000| 20.000.000| De măsurat
QFLPN-70M| 70.000.000| 140.000.000| De măsurat
QFLPN-100M| 100.000.000| 200.000.000| De măsurat; necesită preflight de memorie

Important: existența unei dimensiuni în catalog nu înseamnă că benchmarkul a fost executat. Numai înregistrările CSV validate și asociate rapoartelor JSON prin RUN_ID constituie dovezi de performanță.

3. Tabelul central al performanței

Valorile de mai jos trebuie completate din măsurători efective. Rezultatele istorice pentru 1M sunt prezentate separat în secțiunea 4.

Dimensiune| Timp secvențial mediu (ms)| Timp paralel mediu (ms)| Speedup| Verdict
1.000.000| 3,470417| 3,744938| 0,926695×| Istoric măsurat
10.000.000| NEDISPONIBIL| NEDISPONIBIL| NEDISPONIBIL| De măsurat
70.000.000| NEDISPONIBIL| NEDISPONIBIL| NEDISPONIBIL| De măsurat
100.000.000| NEDISPONIBIL| NEDISPONIBIL| NEDISPONIBIL| De măsurat

Speedup-ul se calculează astfel:

[
S(N)=\frac{T_{\mathrm{secvențial}}(N)}
{T_{\mathrm{paralel}}(N)}
]

Interpretare:

- (S(N)>1): accelerare paralelă;
- (S(N)=1): performanță echivalentă;
- (S(N)<1): execuția paralelă este mai lentă.

Nu se extrapolează speedup-ul de la o dimensiune la alta.

4. Rezultatul istoric QFLPN-1M

RUN_ID: "p3-41236675753-1"

Parametru| Valoare
Benchmark ID| QFLPN-1M
Dimensiune| 1.000.000
Valori nenule| 2.000.000
Warm-up| 5
Iterații măsurate| 10
Parallelism| 2
Threshold| 4096
Înregistrări CSV validate| 78
Validare| PASS

4.1. Timpi și throughput

Metrică| Secvențial| Paralel
Medie (ms)| 3,470417| 3,744938
Mediană (ms)| 3,012406| 3,500631
Abatere standard (ms)| 0,895481| 0,827544
Throughput (stări/s)| 288.149.826,845| 267.027.082,020

Speedup istoric: 0,926695×.

Execuția paralelă a fost mai lentă decât execuția secvențială în această măsurătoare. Această valoare nu demonstrează accelerare paralelă.

4.2. Corectitudine numerică

Verificare| Eroare
Oracle secvențial| 0,000000000000e+00
Oracle paralel| 0,000000000000e+00
Eroare absolută maximă| 0,000000000000e+00

Rezultatul numeric istoric a trecut verificările raportate.

5. Indicatorii obligatorii pentru fiecare dimensiune

Pentru fiecare dintre cele patru dimensiuni, raportul final trebuie să conțină:

Indicator| Secvențial| Paralel
Timp mediu (ms)| Din măsurare| Din măsurare
Timp median (ms)| Din măsurare| Din măsurare
Abatere standard (ms)| Din măsurare| Din măsurare
Throughput (stări/s)| Din măsurare| Din măsurare
Eroare față de oracle| Din validare| Din validare

Indicatori suplimentari:

- speedup pentru fiecare dimensiune;
- raportul dintre timpul paralel și cel secvențial;
- configurația de execuție;
- numărul de iterații de warm-up și măsurate;
- numărul de fire de execuție;
- threshold-ul;
- memoria JVM disponibilă și utilizată;
- RUN_ID și commit-ul sursă;
- verdictul validatorului.

6. Istoricul CSV V2

Fișier-sursă:

"P3/benchmarks/benchmark_results_v2.csv"

Ultima validare istorică a raportat:

- 78 de înregistrări CSV valide;
- o singură dimensiune distinctă confirmată: 1.000.000;
- schema: "qflpn-benchmark-v2";
- validare: PASS.

Cele 78 de înregistrări nu reprezintă 78 de dimensiuni. Nu se atribuie rezultatele istorice de 1M dimensiunilor 10M, 70M sau 100M.

7. Rezultatele V3

Fișier-sursă:

"P3/benchmarks/benchmark_results_v3.csv"

În evidența istorică prezentată, nu existau înregistrări V3 disponibile. Nu se atribuie V3 rezultate de performanță fără înregistrări validate.

8. Dovezile istorice

- RUN_ID: "p3-41236675753-1"
- CSV V2: "P3/benchmarks/benchmark_results_v2.csv"
- Raport JSON: "P3/results/raw/p3-41236675753-1/validation-report.json"
- Directorul dovezilor: "P3/results/raw/p3-41236675753-1/"
- Raport central: "P3/reports/benchmark-report.md"

9. Reguli de validare și integritate

Raportul central trebuie să respecte următoarele reguli:

1. Fiecare rezultat trebuie să provină dintr-o înregistrare CSV validată.
2. Fiecare înregistrare trebuie asociată raportului JSON corespunzător prin RUN_ID.
3. Dimensiunea din CSV, identitatea benchmarkului și configurația execuției trebuie să coincidă.
4. Rezultatele pentru dimensiuni diferite trebuie păstrate distincte.
5. Valorile lipsă trebuie marcate ca indisponibile, nu estimate.
6. Rezultatele secvențiale și paralele trebuie comparate numai pentru aceeași dimensiune și aceeași configurație experimentală.
7. Raportul trebuie generat și verificat în cadrul jobului "p3_validation".
8. Integritatea dovezilor trebuie legată de "MANIFEST.txt" și "SHA256SUMS.txt" din același flux "p3_validation".

10. Verdict

QFLPN-1M: există dovezi istorice validate, cu speedup de 0,926695×.

QFLPN-10M: performanță încă nemăsurată în dovezile istorice prezentate.

QFLPN-70M: performanță încă nemăsurată în dovezile istorice prezentate.

QFLPN-100M: performanță încă nemăsurată în dovezile istorice prezentate; execuția necesită verificarea prealabilă a memoriei.

Catalogul canonic cuprinde toate cele patru dimensiuni. Benchmarkul P3 nu poate fi declarat complet din punctul de vedere al performanței până când fiecare dimensiune nu are măsurători secvențiale și paralele validate.

---

QFLPN P3 — Benchmark Report. Raport central al performanței, bazat exclusiv pe dovezi măsurate și validate.
