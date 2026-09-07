# 06. Validarea experimentală

## 1. Rolul capitolului

Capitolul verifică experimental corectitudinea numerică, proprietățile structurale și performanța implementărilor QFLPN. Protocolul este controlat și reproductibil, iar comparațiile sunt făcute numai între configurații comparabile.

## 2. Principii de validare

Validarea este împărțită în patru niveluri:

1. **corectitudine matematică** — concordanța cu referința independentă;
2. **invariante structurale** — de exemplu conservarea normei pentru operatori unitari;
3. **performanță** — timp, mediană, throughput, speedup, memorie;
4. **scalare** — evoluția costurilor cu `q`, `N` și `NNZ`.

Un rezultat de performanță nu demonstrează singur corectitudinea matematică.

## 3. Domeniul de scalare cu qubiți

Pentru reprezentarea completă:

$$
N=2^q,
\qquad q=4,5,\ldots,17.
$$

| q | N |
|---:|---:|
| 4 | 16 |
| 5 | 32 |
| 6 | 64 |
| 7 | 128 |
| 8 | 256 |
| 9 | 512 |
| 10 | 1024 |
| 11 | 2048 |
| 12 | 4096 |
| 13 | 8192 |
| 14 | 16384 |
| 15 | 32768 |
| 16 | 65536 |
| 17 | 131072 |

## 4. Protocol numeric

Protocolul de referință utilizează:

| Parametru | Valoare |
|---|---:|
| precizie | float64/double |
| warm-up | 20 |
| repetări | 1000 |
| q | 4,...,17 |
| t | 1.0 |
| μ | 0.70, unde este relevant |
| m/K Arnoldi | 20, unde este relevant |
| reper timp | 15 ms |

Reperul de 15 ms este obiectivul de performanță al proiectului pentru configurațiile la care este aplicabil și nu reprezintă o limită teoretică universală.

## 5. Referința independentă

Validarea numerică utilizează o referință care nu reproduce algoritmul evaluat.

Pentru un operator bloc-diagonal:

$$
U=\operatorname{diag}(U_1,\ldots,U_r),
$$

și

$$
Uv=[U_1v_1^T,\ldots,U_rv_r^T]^T.
$$

Pentru blocuri mici, referința poate fi evaluată analitic sau la precizie controlată. Această construcție este independentă de rutina evaluată.

## 6. Eroarea absolută maximă

Se calculează

$$
E_{\max}=\max_i|y_i-y_i^{ref}|.
$$

Pentru comparații de scalare se păstrează aceeași definiție pe toate dimensiunile.

## 7. Eroarea relativă

$$
E_{rel}=
\frac{\|y-y^{ref}\|_2}
{\max(\|y^{ref}\|_2,\varepsilon)}.
$$

`ε` este o constantă pozitivă de protecție numerică.

## 8. Conservarea normei

Pentru un operator unitar:

$$
E_{norm}=|\|y\|_2-\|v\|_2|.
$$

În plus, pentru diagnosticul mai strict al operatorului se poate calcula

$$
E_U=\|U^*U-I\|.
$$

## 9. Fidelitatea

Pentru stări pure normalizate:

$$
F(\psi,\phi)=|\langle\psi|\phi\rangle|^2.
$$

Pentru stări mixte, forma utilizată trebuie specificată explicit și aplicată consistent. Fidelitatea nu trebuie confundată cu eroarea de coordonate a vectorului.

## 10. Timpi de execuție

Se raportează cel puțin:

- media;
- mediana;
- minimul;
- maximul.

Media este

$$
\bar T=\frac1R\sum_{r=1}^{R}T_r,
$$

unde `R` este numărul de repetări după warm-up.

Mediana este utilizată ca indicator robust la outlieri.

## 11. Speedup

Pentru două configurații comparabile:

$$
S=\frac{T_{seq}}{T_{par}}.
$$

Un speedup trebuie raportat împreună cu configurația hardware și cu definiția exactă a timpului măsurat.

## 12. Throughput

Dacă `W` este volumul de lucru și `T` timpul:

$$
\mathrm{Throughput}=\frac{W}{T}.
$$

Unitatea trebuie indicată explicit, de exemplu elemente/s sau operații/s.

## 13. Memorie

Pentru reprezentarea densă a unei matrice `N×N`:

$$
M_{dense}=O(N^2).
$$

Pentru CSR:

$$
M_{CSR}=O(\operatorname{NNZ}+N).
$$

În raportarea experimentală se disting memoria matricei, memoria vectorilor și memoria temporară.

## 14. Complexitatea observată

Pentru SpMV:

$$
C_{SpMV}\sim O(\operatorname{NNZ}).
$$

Pentru Arnoldi:

$$
C_{Arnoldi}
\approx
mC_{SpMV}+C_{orth}(N,m)+C_{small}(m).
$$

Se evită extrapolarea unei complexități asimptotice dintr-un singur punct experimental.

## 15. Rezultate pentru operatorul unitar de referință

Pentru domeniul `q=4,...,17`, criteriul numeric urmărește simultan:

$$
E_{max}\leq\tau_E,
\qquad
E_{norm}\leq\tau_N,
$$

cu toleranțele declarate în protocolul software.

Rezultatele trebuie salvate pe fiecare `q`, nu numai pentru valoarea maximă.

## 16. Rezultate q=17 — Python

Pentru rularea de referință existentă în proiect, rezultatele raportate sunt aproximativ:

| Metrică | Valoare |
|---|---:|
| mean | 0.2143 ms |
| median | 0.2086 ms |
| max | 0.3413 ms |
| max abs error | 1.11·10^-16 |
| norm error | 0 |
| statut | PASS |

Aceste valori sunt rezultate de implementare pentru configurația măsurată și nu constituie o afirmație universală despre Python sau despre algoritm.

## 17. Rezultate q=17 — MATLAB/Octave

Pentru rularea de referință existentă în proiect:

| Metrică | Valoare |
|---|---:|
| mean | 1.3258 ms |
| median | 1.3220 ms |
| min | 1.3080 ms |
| max | 1.4405 ms |
| max abs error | 0 |
| norm error | aproximativ 2.0·10^-15 |
| statut | PASS |

Comparația dintre limbaje trebuie interpretată în contextul hardware-ului și runtime-ului folosit.

## 18. Benchmark sparse de ordinul milionului

Pentru benchmark-ul QFLPN-1M, rezultatul măsurat este:

| Configurație | Timp |
|---|---:|
| secvențial | 8.250 ms |
| paralel | 3.139 ms |
| speedup | 2.6281× |
| eroare absolută maximă | 0 |

Acest rezultat este un benchmark experimental punctual și nu trebuie extrapolat automat la 5M, 10M sau 30M fără măsurători.

## 19. Dimensiuni HPC mari

Volumele `5M`, `10M`, `20M` și `30M`, atunci când sunt raportate, trebuie tratate ca workload-uri experimentale. Pentru fiecare dimensiune se raportează numai rezultate efectiv măsurate.

Nu se confundă aceste volume cu relația cuantică

$$
N=2^q.
$$

## 20. Comparația metodelor

Protocolul comparativ trebuie să păstreze constante, pe cât posibil:

- același `A`;
- același `v`;
- același `t`;
- aceeași precizie;
- aceeași platformă;
- același criteriu de eroare;
- aceeași convenție de măsurare.

| Metodă | Obiectiv | Metrici |
|---|---|---|
| Taylor | acțiune exponențială | timp, eroare |
| Taylor scalat | acțiune exponențială | timp, eroare |
| Arnoldi | acțiune exponențială | timp, eroare, ortogonalitate |
| Lanczos | cazuri compatibile | timp, eroare |
| Chebyshev | referință polynomială | timp, eroare |
| rational Krylov | referință avansată | timp, eroare |
| Padé | referință pentru expm | timp, eroare |
| contour | numai dacă implementat | timp, eroare |

## 21. Separarea corectitudinii de performanță

Un algoritm poate fi rapid și incorect sau lent și corect. Prin urmare, raportarea trebuie să separe:

$$
\text{corectitudine}
\quad\text{de}
\quad
\text{performanță}.
$$

Criteriul final de acceptare este o combinație a celor două, nu un singur timp de execuție.

## 22. Reproductibilitate

Pentru fiecare experiment se păstrează:

| Câmp | Conținut |
|---|---|
| q | număr qubiți |
| N | 2^q |
| NNZ | elemente nenule |
| method | metodă |
| precision | float64/double |
| warmup | 20 |
| repetitions | 1000 |
| mean/median/min/max | timpi |
| max_abs_error | eroare |
| norm_error | eroare normă |
| hardware | platformă |
| software | versiuni relevante |
| output | CSV/figură |

## 23. Figuri obligatorii

### Figura 6.1 — Eroarea în funcție de q

Axa x: `q`; axa y: `E_max` pe scară adecvată. Se marchează toleranța.

### Figura 6.2 — Timpul în funcție de q

Se reprezintă `mean_ms` și, separat sau prin bare de eroare, variația măsurată. Reperul de 15 ms este o linie de obiectiv, etichetată explicit ca atare.

### Figura 6.3 — Speedup secvențial/paralel

Se reprezintă

$$
S=T_{seq}/T_{par}.
$$

### Figura 6.4 — Scalare cu NNZ

Se reprezintă timpul în funcție de `NNZ`, cu aceeași implementare și același protocol.

### Figura 6.5 — Trade-off timp–eroare

Axa x: timp; axa y: eroare. Fiecare metodă trebuie să aibă același set de condiții experimentale.

### Figura 6.6 — Pipeline de reproducibilitate

Cod → parametri → rulare → CSV → verificare → figură → tabel → teză.

## 24. Tabele finale obligatorii

1. Rezultate complete q=4,...,17 Python.
2. Rezultate complete q=4,...,17 MATLAB/Octave.
3. Compararea metricilor.
4. Benchmark sparse.
5. Rezultatele workload-urilor mari, numai dacă sunt măsurate.
6. Comparația metodelor.
7. Hardware/software protocol.

## 25. Criteriul de acceptare

Un rezultat este acceptat numai dacă:

1. parametrii sunt documentați;
2. dimensiunea `N=2^q` este coerentă;
3. referința este independentă;
4. eroarea este raportată;
5. invarianta relevantă este verificată;
6. timpul este măsurat după protocol;
7. hardware-ul și software-ul sunt identificabile;
8. rezultatul este reproductibil din fișierul de rezultate.

## 26. Matricea de validare

| Afirmație | Metodă de verificare | Metrică | Secțiune |
|---|---|---|---|
| stare normalizată | calcul normă | `E_norm` | 8 |
| operator unitar | `U*U` / normă | `E_U`, `E_norm` | 8 |
| acțiune exp(A) corectă | referință independentă | `E_max`, `E_rel` | 6–7 |
| Arnoldi corect | relația Arnoldi | rezidual/eroare | 14 |
| SpMV corect | referință sparse | `E_max` | 18 |
| paralelism eficient | comparație controlată | speedup | 11 |
| scalare | mai multe NNZ/q | timp, throughput | 13–20 |

## 27. Limite și interpretare

Rezultatele experimentale sunt dependente de hardware, runtime, implementare și parametri. Ele susțin numai afirmațiile pentru configurațiile efectiv evaluate.

În special:

- un rezultat la `q=17` nu demonstrează automat comportamentul la dimensiuni arbitrar mai mari;
- un benchmark de ordinul milionului nu validează automat workload-uri de ordinul zecilor de milioane;
- un speedup punctual nu constituie o lege de scalare;
- o referință exactă pe un caz structural nu demonstrează universalitatea metodei.

## 28. Criteriu de închidere

Capitolul este final numai când toate rezultatele din text apar și în tabelele/CSV-urile corespunzătoare, toate figurile pot fi regenerate din date, fiecare afirmație cantitativă are o bază experimentală identificabilă, iar rezultatele teoretice și experimentale sunt separate fără ambiguitate.
