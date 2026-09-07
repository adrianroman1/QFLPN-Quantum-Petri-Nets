# Capitolul 3 — Formalismul QFLPN

## 3.1. Rolul capitolului

Capitolul 3 este nucleul matematic al tezei. El definește formalismul QFLPN,
separă obiectele semantice și stabilește interfețele dintre structura Petri,
componenta fuzzy și stratul cuantic.

Rezultatele bibliografice sunt distincte de:

- **L** — rezultat din literatură;
- **M** — alegere de model;
- **O** — contribuție originală;
- **V** — element de validare.

## 3.2. Definiția formală QFLPN

Definim o rețea QFLPN finită prin:

$$
\mathcal{N}_{QFLPN}
=
(P,T,E,M,\mu,\mathcal{H},\rho,\mathcal{U},\mathcal{R}),
$$

unde:

- $P$ este mulțimea finită a locurilor;
- $T$ este mulțimea finită a tranzițiilor;
- $E$ este relația de intrare/ieșire;
- $M$ este marcajul Petri;
- $\mu$ este familia valorilor sau funcțiilor fuzzy;
- $\mathcal{H}$ este spațiul Hilbert al stratului cuantic;
- $\rho$ este reprezentarea stării;
- $\mathcal{U}$ este familia operatorilor admisibili;
- $\mathcal{R}$ este familia regulilor de evoluție.

Definiția este stratificată intenționat: locul Petri este un obiect structural,
iar $\rho$ este un obiect informațional.

## 3.3. Locuri, tranziții și marcaje

Un loc $p\in P$ reprezintă o componentă structurală a rețelei.

O tranziție $t\in T$ reprezintă un eveniment sau o regulă de evoluție.

Marcajul clasic poate fi:

$$
M:P\rightarrow\mathbb{N}.
$$

În stratul QFLPN se poate asocia unui loc o reprezentare informațională:

$$
\rho_p\in\mathcal{D}(\mathcal{H}),
$$

unde:

$$
\mathcal{D}(\mathcal{H})
=
\{\rho:\rho\succeq0,\operatorname{Tr}(\rho)=1\}.
$$

Un token cuantic este o entitate semantică a modelului; el nu este identificat
automat cu un qubit fizic.

## 3.4. Activarea și firing-ul

Activarea unei tranziții este determinată de structura Petri și de condițiile
fuzzy:

$$
(M,\mu)
\longrightarrow
t_{\mathrm{activat}}.
$$

Numai după activare se aplică transformarea operatorială:

$$
t_{\mathrm{activat}}
\longrightarrow
\mathcal{E}_t
\longrightarrow
\rho'.
$$

Astfel:

$$
\boxed{
\text{marcaj}
+
\text{condiție fuzzy}
\rightarrow
\text{firing}
\rightarrow
\text{operator admisibil}
\rightarrow
\text{stare nouă}
}
$$

Separarea împiedică confundarea logicii de activare cu evoluția cuantică.

## 3.5. Componenta fuzzy

Pentru o variabilă fuzzy:

$$
\mu_j\in[0,1].
$$

Pentru o tranziție $t$, o funcție de agregare poate produce:

$$
\lambda_t
=
g(\mu_1,\ldots,\mu_r),
\qquad
0\le\lambda_t\le1.
$$

Funcția $g$ nu este impusă universal. Poate fi aleasă dintre agregări admisibile
și trebuie documentată pentru fiecare instanță experimentală.

Este esențial:

$$
\lambda_t
\neq
\text{automat o probabilitate}
$$

și:

$$
\lambda_t
\neq
\text{automat o amplitudine}.
$$

## 3.6. Spațiul Hilbert

Pentru $q$ qubiți:

$$
\mathcal{H}_q
=
(\mathbb{C}^2)^{\otimes q},
\qquad
N=2^q.
$$

Baza computațională este:

$$
\mathcal{B}_q
=
\{
|q_0q_1\ldots q_{q-1}\rangle:
q_i\in\{0,1\}
\}.
$$

Pentru patru qubiți:

$$
\dim(\mathcal{H}_4)=16.
$$

Convenția adoptată este:

$$
|q_0q_1q_2q_3\rangle
=
|q_0\rangle\otimes|q_1\rangle
\otimes|q_2\rangle\otimes|q_3\rangle.
$$

## 3.7. Stări pure și mixte

O stare pură este:

$$
|\psi\rangle
=
\sum_{j=0}^{N-1}c_j|j\rangle,
\qquad
\sum_{j=0}^{N-1}|c_j|^2=1.
$$

Matricea densitate asociată este:

$$
\rho_\psi
=
|\psi\rangle\langle\psi|.
$$

Pentru o stare mixtă:

$$
\rho
=
\sum_i p_i|\psi_i\rangle\langle\psi_i|,
$$

cu:

$$
p_i\ge0,
\qquad
\sum_i p_i=1.
$$

Proprietățile fundamentale sunt:

$$
\rho^\dagger=\rho,
\qquad
\rho\succeq0,
\qquad
\operatorname{Tr}(\rho)=1.
$$

## 3.8. Maparea fuzzy → cuantică

Pentru fiecare parametru fuzzy $\lambda\in[0,1]$, specificația QFLPN utilizează:

$$
\theta(\lambda)
=
2\arcsin\sqrt{\lambda}.
$$

Operatorul local este:

$$
R_y(\theta)
=
\begin{pmatrix}
\cos(\theta/2)&-\sin(\theta/2)\\
\sin(\theta/2)&\cos(\theta/2)
\end{pmatrix}.
$$

Aplicat lui $|0\rangle$:

$$
R_y(\theta(\lambda))|0\rangle
=
\sqrt{1-\lambda}\,|0\rangle
+
\sqrt{\lambda}\,|1\rangle.
$$

Rezultă:

$$
|\langle1|R_y(\theta(\lambda))|0\rangle|^2
=
\lambda.
$$

Această mapare este **o alegere de model QFLPN**, nu o identitate universală
între apartenență fuzzy și probabilitate cuantică.

## 3.9. Operatori locali

Pentru qubitul $i$:

$$
\widetilde U_i
=
I_2^{\otimes i}
\otimes U_i
\otimes
I_2^{\otimes(q-i-1)}.
$$

Pentru patru qubiți:

$$
\widetilde U_0=U_0\otimes I_2\otimes I_2\otimes I_2,
$$

$$
\widetilde U_1=I_2\otimes U_1\otimes I_2\otimes I_2,
$$

$$
\widetilde U_2=I_2\otimes I_2\otimes U_2\otimes I_2,
$$

$$
\widetilde U_3=I_2\otimes I_2\otimes I_2\otimes U_3.
$$

Pentru operatori independenți:

$$
U_{\mathrm{loc}}
=
U_0\otimes U_1\otimes U_2\otimes U_3.
$$

Orice implementare little-endian trebuie să introducă explicit permutarea de indici;
ea nu modifică definiția matematică a bazei.

## 3.10. Operatorul controlat $C^3X$

Operatorul $C^3X$ are trei qubiți de control și un qubit țintă. În ordinea
corespunzătoare bazei, forma bloc este:

$$
C^3X
=
I_8\oplus X,
$$

unde:

$$
X=
\begin{pmatrix}
0&1\\
1&0
\end{pmatrix}.
$$

Acțiunea este:

$$
|1110\rangle\mapsto|1111\rangle,
\qquad
|1111\rangle\mapsto|1110\rangle,
$$

iar stările pentru care condiția celor trei controale nu este satisfăcută rămân
neschimbate.

Controlurile, ținta și ordinea bazei trebuie declarate în fiecare implementare.

## 3.11. Compoziția circuitului QFLPN-4Q

Dacă evoluția este împărțită în faze:

$$
U_{\mathrm{QFLPN}}
=
U_mU_{m-1}\cdots U_2U_1.
$$

Starea finală este:

$$
|\psi_{\mathrm{final}}\rangle
=
U_{\mathrm{QFLPN}}
|\psi_{\mathrm{initial}}\rangle.
$$

Pentru instanța de referință se poate utiliza forma:

$$
U_{\mathrm{QFLPN}}
=
U_{\mathrm{final}}
C^3X
U_{\mathrm{mid}}
C^3X
U_{\mathrm{prep}},
$$

cu sincronizarea exactă între această expresie și circuitul implementat.

Produsul Kronecker și produsul ordonat al fazelor nu sunt sinonime:
Kronecker construiește operatori compuși, iar înmulțirea ordonată determină
succesiunea temporală a evoluției.

## 3.12. Propoziție — conservarea normei

**Propoziție.** Dacă:

$$
U^\dagger U=I,
$$

atunci pentru orice $|\psi\rangle$:

$$
\|U|\psi\rangle\|_2
=
\||\psi\rangle\|_2.
$$

**Demonstrație.**

$$
\begin{aligned}
\|U|\psi\rangle\|_2^2
&=
\langle\psi|U^\dagger U|\psi\rangle\\
&=
\langle\psi|I|\psi\rangle\\
&=
\langle\psi|\psi\rangle.
\end{aligned}
$$

Prin extragerea rădăcinii pătrate rezultă egalitatea normelor.

## 3.13. Canale CPTP

Pentru:

$$
\mathcal{E}(\rho)
=
\sum_kK_k\rho K_k^\dagger,
$$

condiția de conservare a urmei este:

$$
\sum_kK_k^\dagger K_k=I.
$$

Atunci:

$$
\begin{aligned}
\operatorname{Tr}(\mathcal{E}(\rho))
&=
\sum_k\operatorname{Tr}(K_k\rho K_k^\dagger)\\
&=
\sum_k\operatorname{Tr}(K_k^\dagger K_k\rho)\\
&=
\operatorname{Tr}(\rho).
\end{aligned}
$$

Pozitivitatea este păstrată de forma Kraus, iar complet pozitivitatea este
inclusă în construcția canalului.

## 3.14. Dinamica Lindblad

Pentru un sistem deschis:

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

Dacă se vectorizează matricea densitate, operatorul Liouvillian acționează
într-un spațiu de dimensiune:

$$
N^2\times N^2.
$$

Pentru $q=4$, $N=16$, deci dimensiunea operatorului vectorizat este:

$$
256\times256.
$$

Această formulare rămâne teoretică dacă nu este însoțită de implementare și
validare experimentală corespunzătoare.

## 3.15. Ideal, zgomot, degradare și eroare

Teza separă explicit:

| Termen | Semnificație |
| --- | --- |
| Ideal | evoluție fără model de zgomot |
| Zgomot/decoerență | pierdere sau perturbare a informației cuantice |
| Degradare | variație a stării/performanței unui sistem în timp |
| Eroare numerică | abatere introdusă de aproximare și aritmetică |
| Eroare de implementare | abatere între modelul declarat și cod |

Degradarea nu este sinonimă cu decoerența.

## 3.16. Fidelitatea

Pentru două matrice densitate:

$$
F(\rho,\sigma)
=
\left[
\operatorname{Tr}
\sqrt{\sqrt{\rho}\sigma\sqrt{\rho}}
\right]^2.
$$

Pentru stări pure:

$$
F(\psi,\phi)
=
|\langle\psi|\phi\rangle|^2.
$$

Fidelitatea este definită în formalism și utilizată ca metrică de validare în
Capitolul 6.

## 3.17. Acțiunea exponențialei

Pentru operatorul $A$ și vectorul $v$:

$$
y=e^{tA}v.
$$

Aproximarea Taylor:

$$
y_m
=
\sum_{k=0}^{m}\frac{t^kA^kv}{k!}.
$$

Aproximarea Krylov/Arnoldi:

$$
y_m
\approx
V_m e^{tH_m}(\beta e_1),
\qquad
\beta=\|v\|_2.
$$

Aceste expresii constituie interfața formală către algoritmii din Capitolul 5.

## 3.18. Reprezentare sparse

Pentru o matrice rară $A$:

$$
y=Ax,
$$

costul aritmetic al SpMV este:

$$
O(\operatorname{NNZ}(A)).
$$

Reprezentarea CSR utilizează:

```text
data
indices
indptr
```

Această reprezentare nu presupune că orice operator QFLPN este rar; proprietatea
de sparsitate trebuie verificată pentru fiecare familie de operatori.

## 3.19. Scalarea familiei QFLPN

Familia de referință este:

$$
N=2^q,
\qquad
q=4,5,\ldots,17.
$$

| $q$ | $N$ |
| ---: | ---: |
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

Instanța QFLPN-4Q este punctul de referință $q=4$, $N=16$ al familiei scalabile.

## 3.20. Proprietăți matematice și condiții de validare

| Proprietate | Condiție | Verificare |
| --- | --- | --- |
| Normalizare | $\langle\psi|\psi\rangle=1$ | eroare de normă |
| Unitate | $U^\dagger U=I$ | abatere operatorială |
| Pozitivitate | $\rho\succeq0$ | spectru |
| Conservarea urmei | $\operatorname{Tr}(\rho)=1$ | eroare de urmă |
| Compoziție | ordine tensorială fixată | comparație cross-platform |
| Mapare fuzzy | $\lambda\in[0,1]$ | parametrizare |
| Fidelitate | $0\le F\le1$ | metrică |
| Numeric | $e^{tA}v$ | eroare față de referință |
| Sparse | structură CSR validă | NNZ și rezultat SpMV |

## 3.21. Trasabilitatea formalismului

| Element | Matematică | Software | Validare |
| --- | --- | --- | --- |
| QFLPN | definiția tuplei | nucleu model | consistență structurală |
| fuzzy | $\lambda\in[0,1]$ | parametri | domeniu |
| RY | $R_y(\theta)$ | Python/MATLAB | stare/probabilități |
| Kronecker | $\otimes$ | operator global | ordinea bazei |
| $C^3X$ | $I_8\oplus X$ | circuit 4Q | acțiune pe baze |
| unitar | $U^\dagger U=I$ | operator | normă |
| CPTP | Kraus | canal | urmă/pozitivitate |
| $e^{tA}v$ | exponențială | algoritmi | eroare |
| CSR | SpMV | engine sparse | rezultat/performance |

## 3.22. Figuri obligatorii

1. **Figura 3.1 — Arhitectura formală QFLPN**
   - Petri;
   - fuzzy;
   - Hilbert;
   - operatori;
   - evoluție.

2. **Figura 3.2 — Interfața fuzzy–cuantică**
   - $\lambda$;
   - $\theta(\lambda)$;
   - $R_y(\theta)$;
   - starea rezultată.

3. **Figura 3.3 — Ordonarea celor patru qubiți**
   - baza computațională;
   - ordinea tensorială;
   - convenția software.

4. **Figura 3.4 — Construcția operatorului global**
   - $U_0,U_1,U_2,U_3$;
   - tensorizare;
   - operator global;
   - control.

5. **Figura 3.5 — Operatorul $C^3X$**
   - controale;
   - țintă;
   - subspațiul activ.

6. **Figura 3.6 — Circuitul QFLPN-4Q**
   - $U_{\mathrm{prep}}$;
   - $C^3X$;
   - $U_{\mathrm{mid}}$;
   - $C^3X$;
   - $U_{\mathrm{final}}$.

7. **Figura 3.7 — Ideal versus zgomot/decoerență**
   - evoluție unitară;
   - canal CPTP/Lindblad;
   - degradare ca strat separat.

8. **Figura 3.8 — Lanțul de validare**
   - definiție;
   - proprietate;
   - implementare;
   - metrică;
   - rezultat.

9. **Figura 3.9 — Scala $q=4,\ldots,17$**
   - $q$;
   - $N=2^q$;
   - cost/memorie.

## 3.23. Tabele obligatorii

- definiția formală QFLPN;
- notații;
- maparea fuzzy–cuantică;
- operatori locali/globali;
- $C^3X$;
- proprietăți și demonstrații;
- scala $q/N$;
- separarea ideal/noisy/degradare;
- trasabilitate matematică–software–validare.

## 3.24. Criteriu de închidere

Formalismul este considerat închis numai când:

- toate componentele tuplei sunt definite;
- activarea fuzzy este separată de firing și de transformarea cuantică;
- convenția bazei este unică și identică în matematică și software;
- maparea fuzzy–cuantică este declarată ca alegere de model;
- operatorii Kronecker sunt definiți fără ambiguitate;
- $C^3X$ are controluri și țintă explicite;
- conservarea normei și conservarea urmei sunt demonstrate;
- ideal, zgomot, decoerență, degradare și eroare numerică sunt separate;
- relația $N=2^q$ este respectată;
- fiecare afirmație poate fi urmărită către implementare sau validare.
