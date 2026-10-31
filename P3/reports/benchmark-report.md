QFLPN P3 — BENCHMARK REPORT

Raport central al rezultatelor benchmarkurilor validate

- Ultima actualizare documentată: "2026-10-31"
- Ultimul RUN_ID verificat: "p3-41236675753-1"
- Schema: "qflpn-benchmark-v2"

1. Situația generală a dovezilor

Indicator| Rezultat
Înregistrări CSV V2 validate| 78
Dimensiuni V2 distincte confirmate| 1
Dimensiune V2 confirmată| 1.000.000
Înregistrări CSV V3 disponibile| 0
Schema validării ultimei execuții| "qflpn-benchmark-v2"
Ultima validare| PASS

Atenție: cele 78 de înregistrări reprezintă numărul înregistrărilor CSV V2 validate, nu numărul dimensiunilor benchmarkului.

2. Catalogul dimensiunilor benchmarkului

Benchmark| Dimensiune| Valori nenule| Dovezi disponibile
QFLPN-1M| 1.000.000| 2.000.000| CONFIRMATE
QFLPN-10M| 10.000.000| 20.000.000| NECONFIRMATE
QFLPN-70M| 70.000.000| 140.000.000| NECONFIRMATE
QFLPN-100M| 100.000.000| 200.000.000| NECONFIRMATE

Dimensiunea 12 este fixture de corectitudine, nu benchmark temporizat. Dimensiunea 30M nu face parte din catalogul canonic.

3. Ultima execuție V2 validată

RUN_ID: "p3-41236675753-1"

Parametru| Valoare
Benchmark ID| "QFLPN-1M"
Dimensiune| 1.000.000
Valori nenule| 2.000.000
Warm-up| 5
Iterații măsurate| 10
Parallelism| 2
Threshold| 4096
Înregistrări CSV validate| 78
Validare| PASS

3.1. Performanță

Metrică| Secvențial| Paralel
Medie (ms)| 3,470417| 3,744938
Mediană (ms)| 3,012406| 3,500631
Abatere standard (ms)| 0,895481| 0,827544
Throughput (stări/s)| 288.149.826,845| 267.027.082,020

Speedup: 0,926695×

Interpretare: execuția paralelă a fost mai lentă decât cea secvențială în această măsurătoare. Rezultatul nu demonstrează accelerare paralelă.

3.2. Corectitudine numerică

Verificare| Eroare
Oracle secvențial| "0.000000000000e+00"
Oracle paralel| "0.000000000000e+00"
Eroare absolută maximă| "0.000000000000e+00"

Corectitudinea numerică a trecut pentru această execuție.

4. Tabel central al performanței pentru toate dimensiunile

Acest tabel sintetizează situația măsurătorilor disponibile. Valorile indisponibile nu sunt estimate și nu sunt extrapolate de la dimensiunea de 1.000.000.

Dimensiune| Timp secvențial mediu (ms)| Timp paralel mediu (ms)| Speedup| Statut
1.000.000| 3,470417| 3,744938| 0,926695×| MĂSURAT — istoric
10.000.000| NEDISPONIBIL| NEDISPONIBIL| NEDISPONIBIL| NEMĂSURAT
70.000.000| NEDISPONIBIL| NEDISPONIBIL| NEDISPONIBIL| NEMĂSURAT
100.000.000| NEDISPONIBIL| NEDISPONIBIL| NEDISPONIBIL| NEMĂSURAT — necesită preflight de memorie

Speedup-ul se calculează prin:

[
S(N)=\frac{T_{\mathrm{secvențial}}(N)}
{T_{\mathrm{paralel}}(N)}
]

Interpretare:

- (S(N)>1): accelerare paralelă;
- (S(N)=1): performanță echivalentă;
- (S(N)<1): execuția paralelă este mai lentă.

Rezultatele se compară numai pentru aceeași dimensiune și aceeași configurație experimentală.

5. Istoricul V2

Fișier-sursă: "P3/benchmarks/benchmark_results_v2.csv"

Ultima validare istorică a raportat:

- 78 de înregistrări CSV valide;
- o singură dimensiune distinctă confirmată: 1.000.000;
- schema "qflpn-benchmark-v2";
- validare PASS.

Toate înregistrările trebuie interpretate la granularitatea lor reală. În versiunea verificată, dimensiunea confirmată este 1.000.000.

Nu se extrapolează rezultatele de la 1M la 10M, 70M sau 100M.

6. Rezultatele V3

Fișier-sursă: "P3/benchmarks/benchmark_results_v3.csv"

În versiunea verificată nu existau înregistrări V3 disponibile.

Prin urmare, acest raport nu atribuie V3 rezultate, speedup-uri sau dimensiuni executate care nu sunt susținute de dovezi.

7. Indicatorii obligatorii pentru fiecare dimensiune

Pentru fiecare dintre cele patru dimensiuni, raportarea completă trebuie să includă:

Indicator| Secvențial| Paralel
Timp mediu (ms)| Măsurat| Măsurat
Timp median (ms)| Măsurat| Măsurat
Abatere standard (ms)| Măsurată| Măsurată
Throughput (stări/s)| Măsurat| Măsurat
Eroare față de oracle| Validată| Validată

Indicatori experimentali suplimentari:

- speedup pentru fiecare dimensiune;
- raportul dintre timpul paralel și cel secvențial;
- numărul de iterații de warm-up și de măsurare;
- numărul de fire de execuție;
- threshold-ul;
- memoria JVM disponibilă și utilizată;
- RUN_ID și commit-ul sursă;
- verdictul validatorului.

8. Dovezile ultimei execuții

- RUN_ID: "p3-41236675753-1"
- CSV V2: "P3/benchmarks/benchmark_results_v2.csv"
- Raport JSON: "P3/results/raw/p3-41236675753-1/validation-report.json"
- Directorul dovezilor brute: "P3/results/raw/p3-41236675753-1/"
- Raport central: "P3/reports/benchmark-report.md"

9. Reguli de validare și integritate

Raportul central trebuie să respecte următoarele reguli:

1. Fiecare rezultat trebuie să provină dintr-o înregistrare CSV validată.
2. Fiecare înregistrare trebuie asociată raportului JSON corespunzător prin RUN_ID.
3. Dimensiunea din CSV, identitatea benchmarkului și configurația execuției trebuie să coincidă.
4. Rezultatele pentru dimensiuni diferite trebuie păstrate distincte.
5. Valorile lipsă trebuie marcate ca indisponibile, nu estimate.
6. Rezultatele secvențiale și paralele trebuie comparate numai pentru aceeași dimensiune și aceeași configurație experimentală.
7. Raportul central trebuie generat și verificat în cadrul jobului "p3_validation".
8. Integritatea dovezilor trebuie legată de "MANIFEST.txt" și "SHA256SUMS.txt" din același flux "p3_validation".

10. Verdict

- QFLPN-1M: există dovezi istorice validate; speedup-ul măsurat este 0,926695×.
- QFLPN-10M: performanță nemăsurată în dovezile istorice verificate.
- QFLPN-70M: performanță nemăsurată în dovezile istorice verificate.
- QFLPN-100M: performanță nemăsurată în dovezile istorice verificate; execuția necesită verificarea prealabilă a memoriei.

Catalogul canonic cuprinde toate cele patru dimensiuni. Benchmarkul P3 nu poate fi declarat complet din punctul de vedere al performanței până când fiecare dimensiune temporizată nu are măsurători secvențiale și paralele validate.

---

QFLPN P3 — Benchmark Report. Raportul prezintă exclusiv rezultate susținute de dovezi disponibile și validate.
