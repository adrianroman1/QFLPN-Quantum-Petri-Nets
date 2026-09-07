# 07. Concluzii și publicații

## 1. Rolul capitolului

Acest capitol închide argumentația tezei și sintetizează contribuțiile QFLPN, rezultatele matematice, algoritmice și experimentale, limitele demonstrațiilor și direcțiile de continuare.

Nu sunt introduse rezultate matematice noi. Orice afirmație cantitativă trebuie să poată fi urmărită până la metodologia și rezultatele din capitolele anterioare.

## 2. Concluzii generale

Teza propune și analizează un formalism Quantum-Fuzzy Logical Petri Nets (QFLPN) care combină:

- structura logică și de tranziție a rețelelor Petri;
- valori fuzzy pentru reprezentarea graduală a activării;
- stări cuantice în spații Hilbert;
- operatori liniari și unitari;
- compunerea local-globală prin produse tensoriale/Kronecker;
- modele de evoluție ideală și, atunci când sunt implementate, modele zgomotoase;
- metode numerice pentru acțiunea exponențialei unui operator;
- reprezentări sparse CSR și operații SpMV pentru calcul de mare performanță.

Contribuția trebuie prezentată ca un **formalism integrat și o arhitectură computațională**, nu ca o identificare universală între logica fuzzy și mecanica cuantică.

## 3. Întrebarea de cercetare

Întrebarea centrală este:

> În ce măsură poate fi formulat, implementat și validat un formalism QFLPN care păstrează simultan semantica logică a rețelelor Petri, reprezentarea fuzzy a activării, consistența matematică a stărilor cuantice și o implementare numerică reproductibilă și scalabilă?

Răspunsul este construit prin patru niveluri:

$$
\text{formalism}
\rightarrow
\text{analiză matematică}
\rightarrow
\text{algoritmi}
\rightarrow
\text{validare experimentală}.
$$

## 4. Contribuții originale

| ID | Contribuție | Tip | Verificare |
|---|---|---|---|
| C1 | Formalism QFLPN integrat | conceptual/matematic | Capitolul 3 |
| C2 | Mapare fuzzy–cuantică explicită | modelare | Capitolul 3 |
| C3 | Construcție local-globală prin tensorizare | matematic/computațional | Capitolele 3–5 |
| C4 | Separarea activării de transformarea de stare | semantic | Capitolele 3 și 5 |
| C5 | Cadru pentru evoluție operatorială | matematic | Capitolul 4 |
| C6 | Pipeline Taylor/Krylov/Arnoldi | algoritmic | Capitolul 5 |
| C7 | Reprezentare CSR–SpMV | HPC | Capitolele 5–6 |
| C8 | Protocol reproductibil de scalare | experimental | Capitolul 6 |
| C9 | Cadru de metrici pentru corectitudine și performanță | experimental | Capitolul 6 |

## 5. Rezultate matematice sintetizate

Spațiul Hilbert pentru q qubiți este:

$$
\mathcal H_q=(\mathbb C^2)^{\otimes q},
\qquad
N=2^q.
$$

O stare pură este:

$$
|\psi\rangle
=
\sum_{j=0}^{N-1}\alpha_j|j\rangle,
\qquad
\sum_j|\alpha_j|^2=1.
$$

Un operator unitar satisface:

$$
U^\ast U=I,
$$

iar pentru orice vector:

$$
\|U|\psi\rangle\|_2
=
\||\psi\rangle\|_2.
$$

Evoluția liniară este:

$$
x(t)=e^{tA}x_0.
$$

Acțiunea exponențialei, relevantă computațional, este:

$$
y=e^{tA}v.
$$

Subspațiul Krylov este:

$$
\mathcal K_m(A,v)
=
\operatorname{span}
\{v,Av,\ldots,A^{m-1}v\}.
$$

Relația Arnoldi este:

$$
AV_m
=
V_mH_m
+
h_{m+1,m}v_{m+1}e_m^\top.
$$

Aproximarea acțiunii exponențialei este:

$$
e^{tA}v
\approx
\|v\|_2V_m e^{tH_m}e_1.
$$

Principiul contracției Banach poate fi utilizat numai dacă:

$$
d(Tx,Ty)\leq c\,d(x,y),
\qquad
0\leq c<1,
$$

pe un spațiu metric complet.

Concluzia Banach este existența și unicitatea punctului fix; ea nu implică automat deadlock-freedom pentru o rețea Petri.

## 6. Rezultate algoritmice

Arhitectura software este organizată în următorul lanț:

$$
\text{date QFLPN}
\rightarrow
\text{marcare}
\rightarrow
\text{activare}
\rightarrow
\text{operator}
\rightarrow
\text{evoluție}
\rightarrow
\text{metrici}.
$$

Pentru operatori rari:

$$
w=Av
$$

este evaluat prin CSR–SpMV, cu un cost dominant proporțional cu:

$$
O(\operatorname{NNZ}(A)).
$$

Pentru Arnoldi, costul total depinde de produsele SpMV și de ortogonalizare:

$$
C_{\mathrm{Arnoldi}}
=
O(m\,C_{\mathrm{SpMV}})
+
O(Nm^2)
+
C_{\mathrm{small}}(m).
$$

Această expresie trebuie interpretată ca analiză de complexitate, nu ca măsurătoare experimentală.

## 7. Rezultate experimentale

Domeniul de scalare cu reprezentare completă a stării este:

$$
q=4,\ldots,17,
\qquad
N=2^q.
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

Protocolul experimental trebuie menținut identic pentru metodele comparate:

| Parametru | Configurație de referință |
|---|---|
| q | 4–17 |
| precizie | float64 / double |
| warm-up | 20 |
| repetări | 1000 |
| parametru rotație | $\mu=0.70$ |
| timp de evoluție | $t=1.0$ |
| dimensiune Krylov | $m\leq20$ |
| eroare | maximum absolute error |
| conservare | eroare de normă |
| reper de performanță | 15 ms, ca obiectiv al proiectului |

Valoarea de 15 ms este un **obiectiv/reper de performanță al proiectului**, nu o limită universală a metodei.

## 8. Indicatori de validare

Eroarea absolută maximă este:

$$
E_{\max}
=
\max_i
|y_i-y_i^{\mathrm{ref}}|.
$$

Eroarea relativă poate fi definită prin:

$$
E_{\mathrm{rel}}
=
\frac{
\|y-y^{\mathrm{ref}}\|_2
}{
\max(\|y^{\mathrm{ref}}\|_2,\varepsilon)
}.
$$

Pentru conservarea normei:

$$
E_{\mathrm{norm}}
=
\left|
\|y\|_2-\|v\|_2
\right|.
$$

Pentru stări cuantice, fidelitatea trebuie definită conform convenției adoptate în Capitolul 6 și aplicată numai asupra stărilor pentru care ipotezele metricii sunt îndeplinite.

## 9. Reproductibilitate

Un rezultat experimental este considerat reproductibil numai dacă sunt documentate:

1. versiunea codului;
2. configurația hardware;
3. mediul software;
4. parametrii algoritmului;
5. dimensiunea q/N;
6. reprezentarea matricei;
7. protocolul de măsurare;
8. numărul de repetări;
9. criteriul de eroare;
10. rezultatul brut sau tabelul derivat.

## 10. Limitele lucrării

### 10.1 Limita dimensională

Reprezentarea completă a unui vector de stare crește exponențial cu q:

$$
N=2^q.
$$

Prin urmare, scalarea completă nu poate fi extrapolată nelimitat numai din experimente de dimensiune redusă.

### 10.2 Limita demonstrațiilor de stabilitate

Concluziile de tip punct fix necesită ipotezele principiului contracției. Nu se afirmă stabilitate globală în absența acestora.

### 10.3 Limita afirmațiilor de performanță

O metodă nu este declarată superioară universal pe baza unei singure implementări sau a unui singur hardware.

### 10.4 Limita modelelor zgomotoase

Formalismul CPTP/Kraus și ecuația Lindblad oferă cadrul matematic pentru zgomot. Rezultatele experimentale privind decoerența trebuie raportate numai pentru modelele efectiv implementate și măsurate.

### 10.5 Limita analizei spectrale

Analiza spectrală oferă instrumente teoretice. O metodă spectrală este prezentată ca rezultat experimental numai dacă există implementare și măsurători reproductibile.

## 11. Publicațiile rezultate

Portofoliul de publicații trebuie să fie organizat în jurul contribuțiilor efectiv demonstrate.

| Nr. | Temă | Contribuție centrală | Bază tehnică |
|---:|---|---|---|
| P1 | Formalism QFLPN | definiția formală | Capitolul 3 |
| P2 | Fuzzy–quantum mapping | maparea $\mu\rightarrow\theta$ | Capitolul 3 |
| P3 | Operatorial QFLPN | operatori și tensorizare | Capitolele 3–4 |
| P4 | Analiză matematică | Banach, operatori, spectru | Capitolul 4 |
| P5 | Taylor/exponential action | aproximarea $e^{tA}v$ | Capitolul 5 |
| P6 | Krylov/Arnoldi | reducerea dimensională | Capitolul 5 |
| P7 | CSR–SpMV | calcul sparse | Capitolele 5–6 |
| P8 | Scalare și performanță | benchmark reproductibil | Capitolul 6 |
| P9 | Validare quantum | fidelitate și invariants | Capitolul 6 |
| P10 | Sinteza QFLPN | integrarea contribuțiilor | Capitolele 3–6 |

Temele de mai sus trebuie transformate în articole distincte numai în măsura în care fiecare are o contribuție și rezultate suficient de autonome.

## 12. Matricea teză–publicații

| Componentă | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| QFLPN | ✓ | ✓ | ✓ |  |  |  |  |  |  | ✓ |
| fuzzy–quantum | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ | ✓ |
| Hilbert/operatori | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | ✓ |
| Banach/spectru |  |  |  | ✓ |  |  |  |  |  | ✓ |
| Taylor |  |  |  |  | ✓ |  |  |  |  | ✓ |
| Krylov/Arnoldi |  |  |  |  |  | ✓ |  | ✓ |  | ✓ |
| CSR/SpMV |  |  |  |  |  |  | ✓ | ✓ |  | ✓ |
| scalare |  |  |  |  |  |  | ✓ | ✓ |  | ✓ |
| fidelitate |  |  |  |  |  |  |  | ✓ | ✓ | ✓ |

## 13. Figuri finale recomandate

### Figura 7.1 — Sinteza contribuției QFLPN

Flux:

$$
\text{Petri}
+
\text{Fuzzy}
+
\text{Quantum}
\rightarrow
\text{QFLPN}
\rightarrow
\text{algoritmi}
\rightarrow
\text{validare}.
$$

Figura finală trebuie realizată vectorial și trebuie să distingă fundamentul bibliografic de contribuțiile originale.

### Figura 7.2 — Lanțul de trasabilitate

$$
\text{definiție}
\rightarrow
\text{teoremă/propoziție}
\rightarrow
\text{algoritm}
\rightarrow
\text{cod}
\rightarrow
\text{experiment}
\rightarrow
\text{rezultat}.
$$

### Figura 7.3 — Arhitectura globală a tezei

$$
\text{Cap. 1}
\rightarrow
\text{Cap. 2}
\rightarrow
\text{Cap. 3}
\rightarrow
\text{Cap. 4}
\rightarrow
\text{Cap. 5}
\rightarrow
\text{Cap. 6}
\rightarrow
\text{Cap. 7}.
$$

## 14. Tabel final de închidere

| Criteriu | Condiție de închidere |
|---|---|
| Formalism | definiție QFLPN completă |
| Matematică | ecuații și ipoteze consistente |
| Algoritmi | pseudocod și parametri reproductibili |
| Software | trasabilitate către fișiere |
| Numeric | metrici definite explicit |
| HPC | CSR/SpMV și complexitate |
| Scalare | q și $N=2^q$ consecvente |
| Quantum | normă și fidelitate documentate |
| Publicații | contribuții distincte și trasabile |
| Figuri | toate figurile finale specificate |
| Tabele | toate tabelele necesare incluse |
| Bibliografie | surse complete și verificabile |

## 15. Concluzie finală

Contribuția centrală a tezei este construirea unui cadru QFLPN coerent în care dinamica logică, reprezentarea fuzzy și evoluția cuantică sunt conectate printr-o formulare matematică și o implementare computațională reproductibilă.

Schema conceptuală finală este:

$$
\boxed{
\text{QFLPN}
\rightarrow
\text{Hilbert}
\rightarrow
\text{operatori}
\rightarrow
 e^{tA}v
\rightarrow
\text{CSR/Krylov}
\rightarrow
\text{validare}
}
$$

Validitatea științifică a concluziilor este condiționată de respectarea ipotezelor matematice, de trasabilitatea implementării și de reproducibilitatea rezultatelor experimentale.

## 16. Criteriul de finalizare a capitolului

Capitolul 7 este închis numai după ce:

- toate contribuțiile sunt trasabile;
- toate afirmațiile cantitative au sursă experimentală;
- rezultatele teoretice sunt separate de cele măsurate;
- lista publicațiilor este sincronizată cu contribuțiile reale;
- figurile finale sunt specificate;
- tabelele sunt complete;
- bibliografia este verificată;
- nu sunt introduse rezultate noi care aparțin capitolelor 3–6.
