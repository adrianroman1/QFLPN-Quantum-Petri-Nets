# Capitolul 2 — Stadiul actual al cercetării

## 2.1. Rolul capitolului

Capitolul stabilește fundamentul bibliografic pentru QFLPN și identifică golul de
cercetare. Prezentarea este critică: conceptele consacrate sunt separate de
alegerile de model și de contribuțiile originale dezvoltate ulterior.

Lanțul conceptual este:

$$
\text{Petri}
\rightarrow
\text{Fuzzy}
\rightarrow
\text{Quantum}
\rightarrow
\text{Operatori}
\rightarrow
e^{tA}v
\rightarrow
\text{HPC}.
$$

## 2.2. Rețele Petri

O rețea Petri clasică poate fi reprezentată prin:

$$
\mathcal{P}=(P,T,F),
$$

unde $P$ este mulțimea locurilor, $T$ mulțimea tranzițiilor, iar $F$ relația
de flux.

Marcajul este o aplicație:

$$
M:P\rightarrow\mathbb{N}.
$$

Pentru reprezentarea matricială, matricea de incidență poate fi scrisă:

$$
C=C^+-C^-,
$$

iar o dinamică discretă poate avea forma:

$$
M_{k+1}=M_k+C\sigma_k.
$$

Noțiunile de activare și firing constituie fundamentul semantic al stratului Petri.
Ele nu trebuie confundate cu transformarea operatorială a unei stări cuantice.

## 2.3. Fuzzy Petri nets și logică fuzzy

Un grad de apartenență este:

$$
\mu\in[0,1].
$$

Sunt relevante:

- funcțiile de apartenență;
- t-normele și agregarea;
- inferența fuzzy;
- gradele de activare;
- tratarea informației imprecise.

O distincție fundamentală este:

$$
\mu
\neq
p
\neq
\alpha,
$$

unde $\mu$ este un grad fuzzy, $p$ o probabilitate, iar $\alpha$ poate reprezenta
o amplitudine cuantică.

În QFLPN, o valoare fuzzy este utilizată ca parametru al unei mapări declarate,
nu este identificată universal cu o probabilitate sau cu o amplitudine.

## 2.4. Quantum Petri nets și poziționarea QFLPN

Formalismele quantum Petri net extind structura Petri către reprezentări cuantice,
dar literatura nu impune o semantică universală unică pentru toate variantele.

QFLPN este poziționat ca formalism hibrid cu trei niveluri:

1. structură discretă Petri;
2. activare și agregare fuzzy;
3. evoluție operatorială cuantică.

Principiul de proiectare este:

> **separare semantică → interfață explicită → compoziție controlată.**

Nu se afirmă că un simulator clasic este echivalent cu un procesor cuantic fizic și
nu se deduce scalabilitatea dintr-un circuit de patru qubiți.

## 2.5. Fundamente cuantice

Pentru $q$ qubiți:

$$
\mathcal{H}_q=(\mathbb{C}^2)^{\otimes q},
\qquad
\dim(\mathcal{H}_q)=2^q.
$$

O stare pură este:

$$
|\psi\rangle
=
\sum_{j=0}^{2^q-1}c_j|j\rangle,
\qquad
\sum_j|c_j|^2=1.
$$

O stare mixtă este reprezentată prin:

$$
\rho
=
\sum_i p_i|\psi_i\rangle\langle\psi_i|,
$$

cu:

$$
\rho\succeq0,
\qquad
\operatorname{Tr}(\rho)=1.
$$

Evoluția unitară:

$$
|\psi'\rangle=U|\psi\rangle,
\qquad
U^\dagger U=I.
$$

Conservarea normei rezultă din:

$$
\|U|\psi\rangle\|_2^2
=
\langle\psi|U^\dagger U|\psi\rangle
=
\|\psi\|_2^2.
$$

## 2.6. Canale CPTP și sisteme deschise

Pentru un canal cuantic:

$$
\mathcal{E}(\rho)
=
\sum_kK_k\rho K_k^\dagger,
$$

cu:

$$
\sum_kK_k^\dagger K_k=I.
$$

Această condiție asigură conservarea urmei:

$$
\operatorname{Tr}(\mathcal{E}(\rho))
=
\operatorname{Tr}(\rho).
$$

Pentru dinamica Markoviană continuă, forma Lindblad este:

$$
\frac{d\rho}{dt}
=
-i[H,\rho]
+
\sum_k
\left(
L_k\rho L_k^\dagger
-
\frac12
\{L_k^\dagger L_k,\rho\}
\right).
$$

În teză, cadrul Lindblad este tratat ca rezultat experimental numai dacă există
implementarea și măsurarea corespunzătoare; altfel rămâne un cadru teoretic.

## 2.7. Produse tensoriale și operatori

Pentru sisteme compuse:

$$
\mathcal{H}_q
=
\bigotimes_{i=0}^{q-1}\mathcal{H}_i.
$$

Pentru patru qubiți:

$$
|q_0q_1q_2q_3\rangle
=
|q_0\rangle\otimes|q_1\rangle\otimes|q_2\rangle\otimes|q_3\rangle.
$$

Un operator localizat pe qubitul $i$ este:

$$
\widetilde U_i
=
I_2^{\otimes i}
\otimes U_i
\otimes
I_2^{\otimes(q-i-1)}.
$$

Pentru operații independente:

$$
U_{\mathrm{loc}}
=
U_0\otimes U_1\otimes\cdots\otimes U_{q-1}.
$$

Convenția de ordine tensorială trebuie sincronizată între matematică și software.

## 2.8. Analiză spectrală

Spectrul unui operator $A$ este:

$$
\sigma(A)
=
\{\lambda\in\mathbb{C}:A-\lambda I
\text{ nu este inversabil}\}.
$$

Pentru un operator Hermitian:

$$
A=A^\dagger,
$$

valorile proprii sunt reale, iar descompunerea spectrală poate fi scrisă:

$$
A=\sum_j\lambda_jP_j.
$$

Calculul funcțional conduce la:

$$
f(A)=\sum_jf(\lambda_j)P_j.
$$

Algebrele Artin–Wedderburn pot furniza o perspectivă structurală asupra
decompunerii algebrice, dar sunt utilizate numai acolo unde această structură
este relevantă pentru operatorii considerați.

Integralele de contur nu sunt introduse ca element decorativ; ele apar numai dacă
sunt utilizate efectiv în analiza sau implementarea finală.

## 2.9. Analiză funcțională

Într-un spațiu normat $(X,\|\cdot\|)$, un operator liniar continuu satisface
proprietățile standard de mărginitate și continuitate.

Pentru un operator $T:X\rightarrow X$:

$$
\|T(x)-T(y)\|
\le
q\|x-y\|,
\qquad
0\le q<1,
$$

înseamnă că $T$ este contracție.

Teorema punctului fix Banach oferă existență și unicitate în condițiile sale.
Aceasta nu constituie automat o demonstrație a absenței deadlock-ului într-o
rețea Petri; deadlock-ul este o proprietate distinctă care necesită analiză proprie.

## 2.10. Exponențiala operatorială

Exponențiala unui operator este:

$$
e^A
=
\sum_{k=0}^{\infty}\frac{A^k}{k!}.
$$

În problemele de evoluție este esențială distincția:

$$
e^A
\quad\text{versus}\quad
e^Av.
$$

Teza urmărește în principal a doua problemă, deoarece formarea explicită a lui
$e^A$ poate fi prohibitivă pentru operatori mari și rari.

Aproximarea Taylor:

$$
T_m(A)v
=
\sum_{k=0}^{m}\frac{A^kv}{k!}.
$$

Pentru scalare:

$$
e^A
=
\left(e^{A/2^s}\right)^{2^s}.
$$

Padé și scaling-and-squaring sunt tratate drept metode consacrate de referință,
nu drept contribuții originale QFLPN.

## 2.11. Metode Krylov și Arnoldi

Subspațiul Krylov este:

$$
\mathcal{K}_m(A,v)
=
\operatorname{span}
\{v,Av,A^2v,\ldots,A^{m-1}v\}.
$$

Procesul Arnoldi construiește $V_m$ și $H_m$ astfel încât:

$$
AV_m
=
V_mH_m+h_{m+1,m}v_{m+1}e_m^\top.
$$

Acțiunea exponențialei poate fi aproximată prin:

$$
e^{tA}v
\approx
V_m e^{tH_m}(\beta e_1),
\qquad
\beta=\|v\|_2.
$$

Trebuie analizate:

- ortogonalizarea;
- reortogonalizarea;
- breakdown;
- costul produselor cu $A$;
- costul în funcție de $\operatorname{NNZ}$;
- memoria;
- influența structurii spectrale.

## 2.12. Lanczos

Pentru operatori Hermitieni, Lanczos produce o bază Krylov cu structură
tridiagonală:

$$
AV_m\approx V_mT_m,
$$

unde $T_m$ este Hermitiană tridiagonală.

Avantajul este reducerea memoriei și a costului de stocare față de o matrice
Hessenberg generală. Metoda este aplicabilă numai când ipotezele structurale
corespunzătoare sunt îndeplinite.

## 2.13. Aproximări Chebyshev

Pentru $x\in[-1,1]$:

$$
T_k(x)=\cos(k\arccos x).
$$

O funcție poate fi aproximată printr-o combinație:

$$
f(x)\approx\sum_{k=0}^{m}a_kT_k(x).
$$

Aplicarea la operatori necesită scalarea spectrului într-un interval controlat.
Prin urmare, informația spectrală este parte a condițiilor de aplicare.

## 2.14. Krylov rațional

Krylov rațional utilizează vectori de forma:

$$
(A-\xi_jI)^{-1}v.
$$

Metoda poate fi avantajoasă pentru spectre dificil de aproximat polinomial, dar
introduce costul rezolvărilor liniare și dependența de alegerea polilor $\xi_j$.

## 2.15. Integratoare exponențiale

Pentru ecuații de evoluție:

$$
\frac{dy}{dt}=Ay+g(t,y),
$$

integratoarele exponențiale exploatează explicit operatorul $e^{tA}$ și funcții
înrudite ale operatorului. Aceste metode constituie puntea dintre analiza
exponențialei și dinamica temporală mai generală.

## 2.16. Calcul sparse și HPC

Pentru:

$$
y=Ax,
$$

cu $A$ rară, costul SpMV este dominat de:

$$
O(\operatorname{NNZ}(A)).
$$

Formatul CSR utilizează:

- `data`;
- `indices`;
- `indptr`.

Performanța depinde nu numai de numărul de operații aritmetice, ci și de:

- lățimea de bandă a memoriei;
- localitate;
- sincronizare;
- partiționare;
- numărul de fire;
- costul administrării execuției paralele.

Prin urmare, o implementare sparse nu implică automat un speedup universal.

## 2.17. Metrici

Latența se raportează prin:

$$
T_{\mathrm{mean}},
\quad
T_{\mathrm{median}},
\quad
T_{\min},
\quad
T_{\max}.
$$

Speedup-ul este:

$$
S
=
\frac{T_{\mathrm{seq}}}{T_{\mathrm{par}}}.
$$

Throughput-ul poate fi definit prin:

$$
\mathrm{Throughput}
=
\frac{N_{\mathrm{work}}}{T}.
$$

Eroarea absolută maximă:

$$
E_\infty
=
\max_j|x_j-\widehat{x}_j|.
$$

Conservarea normei:

$$
E_{\mathrm{norm}}
=
\left|\|x\|_2-1\right|.
$$

Pentru stări cuantice, fidelitatea trebuie definită conform tipului de stare;
pentru două stări pure:

$$
F(\psi,\phi)=|\langle\psi|\phi\rangle|^2.
$$

## 2.18. Protocolul reproductibil

Protocolul de referință utilizează, în absența unei specificații experimentale
mai restrictive:

- parametri deterministici;
- precizie dublă / `float64`;
- 20 iterații de warm-up;
- 1000 repetări măsurate;
- aceeași familie de operatori matematici;
- referință analitică independentă atunci când există;
- raportarea explicită a erorii și a conservării normei.

Timpii sunt măsurători ale implementării. Nu trebuie interpretați ca dovadă de
superioritate între platforme decât în condiții controlate și comparabile.

## 2.19. Metode de referință

| Familie | Problemă | Avantaj | Limitare | Rol |
| --- | --- | --- | --- | --- |
| Taylor | $e^{tA}v$ | simplitate | cost la ordin mare | baseline |
| Taylor scalată | $e^{tA}v$ | controlul normei | alegerea scalării | baseline |
| Arnoldi | $e^{tA}v$ | reducere de dimensiune | ortogonalizare | principală |
| Lanczos | caz Hermitian | structură compactă | condiții stricte | extensie |
| Chebyshev | operator cu spectru controlat | aproximare polinomială | necesită scalare spectrală | referință |
| Padé | $e^A$ | metodă consacrată | formează alt tip de aproximare | baseline |
| Krylov rațional | $e^{tA}v$ | flexibilitate spectrală | rezolvări liniare | comparație |
| MPS | stări cuantice | comprimare structurală | dependență de entanglement | SOTA contextual |

## 2.20. Golul de cercetare

Literatura oferă separat:

- structuri Petri pentru sisteme discrete;
- modele fuzzy pentru informație graduală;
- formalizări cuantice pentru stări și operatori;
- metode Krylov pentru funcții de matrice;
- tehnici sparse pentru calcul scalabil.

Golul abordat de teză este integrarea acestora într-un formalism **QFLPN
stratificat și auditabil**, cu:

$$
\text{semantică}
\rightarrow
\text{model}
\rightarrow
\text{operator}
\rightarrow
\text{algoritm}
\rightarrow
\text{software}
\rightarrow
\text{validare}.
$$

## 2.21. Figuri obligatorii

### Figura 2.1 — Harta conceptuală a domeniilor

Petri, fuzzy, quantum, operatori și HPC trebuie reprezentate ca niveluri distincte,
iar QFLPN ca interfață de integrare.

### Figura 2.2 — Taxonomia metodelor pentru $e^{tA}v$

Taylor → Taylor scalată → Krylov/Arnoldi → Lanczos/Chebyshev → metode raționale.

### Figura 2.3 — Lanțul de calcul sparse

```text
Operator
   ↓
CSR
   ↓
SpMV
   ↓
CPU / GPU
   ↓
latență / throughput / speedup
```

## 2.22. Tabele obligatorii

- sinteza fundamentelor Petri;
- sinteza fuzzy;
- sinteza quantum;
- comparația metodelor pentru $e^{tA}v$;
- comparația metodelor HPC;
- ipoteze și condiții de aplicabilitate;
- poziționarea QFLPN față de formalisme existente.

## 2.23. Criteriu de închidere

Capitolul este închis numai când fiecare afirmație bibliografică are sursă
verificabilă, fiecare metodă este poziționată corect, iar contribuțiile proprii
nu sunt prezentate ca rezultate ale literaturii.
