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
\mathcal{N}QFLPN
=
(P,T,E,M,μ,ℋ,ρ,\mathcal{U},\mathcal{R}),
$$

unde:

- $P$ este mulțimea finită a locurilor;
- $T$ este mulțimea finită a tranzițiilor;
- $E$ este relația de intrare/ieșire;
- $M$ este marcajul Petri;
- $μ$ este familia valorilor sau funcțiilor fuzzy;
- $ℋ$ este spațiul Hilbert al stratului cuantic;
- $ρ$ este reprezentarea stării;
- $\mathcal{U}$ este familia operatorilor admisibili;
- $\mathcal{R}$ este familia regulilor de evoluție.

Definiția este stratificată intenționat: locul Petri este un obiect structural,
iar $ρ$ este un obiect informațional.

## 3.3. Locuri, tranziții și marcaje

Un loc $p∈ P$ reprezintă o componentă structurală a rețelei.

O tranziție $t∈ T$ reprezintă un eveniment sau o regulă de evoluție.

Marcajul clasic poate fi:

$$
M:P→ℕ.
$$

În stratul QFLPN se poate asocia unui loc o reprezentare informațională:

$$
ρ_p∈\mathcal{D}(ℋ),
$$

unde:

$$
\mathcal{D}(ℋ)
=
\{ρ:ρ\succeq0,Tr(ρ)=1\}.
$$

Un token cuantic este o entitate semantică a modelului; el nu este identificat
automat cu un qubit fizic.

## 3.4. Activarea și firing-ul

Activarea unei tranziții este determinată de structura Petri și de condițiile
fuzzy:

$$
(M,μ)
\longrightarrow
t_{\mathrm{activat}}.
$$

Numai după activare se aplică transformarea operatorială:

$$
t_{\mathrm{activat}}
\longrightarrow
\mathcal{E}_t
\longrightarrow
ρ'.
$$

Astfel:

$$
\boxed{
\text{marcaj}
+
\text{condiție fuzzy}
→
\text{firing}
→
\text{operator admisibil}
→
\text{stare nouă}
}
$$

Separarea împiedică confundarea logicii de activare cu evoluția cuantică.

## 3.5. Componenta fuzzy

Pentru o variabilă fuzzy:

$$
μ_j∈[0,1].
$$

Pentru o tranziție $t$, o funcție de agregare poate produce:

$$
λ_t
=
g(μ₁,\ldots,μ_r),
\qquad
0\leλ_t\le1.
$$

Funcția $g$ nu este impusă universal. Poate fi aleasă dintre agregări admisibile
și trebuie documentată pentru fiecare instanță experimentală.

Este esențial:

$$
λ_t
≠
\text{automat o probabilitate}
$$

și:

$$
λ_t
≠
\text{automat o amplitudine}.
$$

## 3.6. Spațiul Hilbert

Pentru $q$ qubiți:

$$
ℋ_q
=
(ℂ²)⊗ q,
\qquad
N=2^q.
$$

Baza computațională este:

$$
\mathcal{B}_q
=
\{
|q₀q₁\ldots qq-₁\rangle:
q_i∈\{0,1\}
\}.
$$

Pentru patru qubiți:

$$
\dim(ℋ₄)=16.
$$

Convenția adoptată este:

$$
|q₀q₁q₂q₃\rangle
=
|q₀\rangle⊗|q₁\rangle
⊗|q₂\rangle⊗|q₃\rangle.
$$

## 3.7. Stări pure și mixte

O stare pură este:

$$
|ψ\rangle
=
\sumj=₀N⁻¹c_j|j\rangle,
\qquad
\sumj=₀N⁻¹|c_j|²=1.
$$

Matricea densitate asociată este:

$$
ρ_ψ
=
|ψ\rangle\langleψ|.
$$

Pentru o stare mixtă:

$$
ρ
=
\sum_i p_i|ψ_i\rangle\langleψ_i|,
$$

cu:

$$
p_i\ge0,
\qquad
\sum_i p_i=1.
$$

Proprietățile fundamentale sunt:

$$
ρ^†=ρ,
\qquad
ρ\succeq0,
\qquad
Tr(ρ)=1.
$$

## 3.8. Maparea fuzzy → cuantică

Pentru fiecare parametru fuzzy $λ∈[0,1]$, specificația QFLPN utilizează:

$$
θ(λ)
=
2\arcsin√{λ}.
$$

Operatorul local este:

$$
R_y(θ)
=
\begin{pmatrix}
\cos(θ/2)&-\sin(θ/2)\\
\sin(θ/2)&\cos(θ/2)
\end{pmatrix}.
$$

Aplicat lui $|0\rangle$:

$$
R_y(θ(λ))|0\rangle
=
√{1-λ}\,|0\rangle
+
√{λ}\,|1\rangle.
$$

Rezultă:

$$
|\langle1|R_y(θ(λ))|0\rangle|²
=
λ.
$$

Această mapare este **o alegere de model QFLPN**, nu o identitate universală
între apartenență fuzzy și probabilitate cuantică.

## 3.9. Operatori locali

Pentru qubitul $i$:

$$
\widetilde U_i
=
I₂⊗ i
⊗ U_i
⊗
I₂⊗(q⁻i⁻¹).
$$

Pentru patru qubiți:

$$
\widetilde U₀=U₀⊗ I₂⊗ I₂⊗ I₂,
$$

$$
\widetilde U₁=I₂⊗ U₁⊗ I₂⊗ I₂,
$$

$$
\widetilde U₂=I₂⊗ I₂⊗ U₂⊗ I₂,
$$

$$
\widetilde U₃=I₂⊗ I₂⊗ I₂⊗ U₃.
$$

Pentru operatori independenți:

$$
U_{\mathrm{loc}}
=
U₀⊗ U₁⊗ U₂⊗ U₃.
$$

Orice implementare little-endian trebuie să introducă explicit permutarea de indici;
ea nu modifică definiția matematică a bazei.

## 3.10. Operatorul controlat $C³X$

Operatorul $C³X$ are trei qubiți de control și un qubit țintă. În ordinea
corespunzătoare bazei, forma bloc este:

$$
C³X
=
I₈\oplus X,
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
U_mUm-₁·s U₂U₁.
$$

Starea finală este:

$$
|ψ_{\mathrm{final}}\rangle
=
U_{\mathrm{QFLPN}}
|ψ_{\mathrm{initial}}\rangle.
$$

Pentru instanța de referință se poate utiliza forma:

$$
U_{\mathrm{QFLPN}}
=
U_{\mathrm{final}}
C³X
U_{\mathrm{mid}}
C³X
U_{\mathrm{prep}},
$$

cu sincronizarea exactă între această expresie și circuitul implementat.

Produsul Kronecker și produsul ordonat al fazelor nu sunt sinonime:
Kronecker construiește operatori compuși, iar înmulțirea ordonată determină
succesiunea temporală a evoluției.

## 3.12. Propoziție — conservarea normei

**Propoziție.** Dacă:

$$
U^† U=I,
$$

atunci pentru orice $|ψ\rangle$:

$$
\|U|ψ\rangle\|₂
=
\||ψ\rangle\|₂.
$$

**Demonstrație.**

$$
\begin{aligned}
\|U|ψ\rangle\|₂²
&=
\langleψ|U^† U|ψ\rangle\\
&=
\langleψ|I|ψ\rangle\\
&=
\langleψ|ψ\rangle.
\end{aligned}
$$

Prin extragerea rădăcinii pătrate rezultă egalitatea normelor.

## 3.13. Canale CPTP

Pentru:

$$
\mathcal{E}(ρ)
=
\sum_kK_kρ K_k^†,
$$

condiția de conservare a urmei este:

$$
\sum_kK_k^† K_k=I.
$$

Atunci:

$$
\begin{aligned}
Tr(\mathcal{E}(ρ))
&=
\sum_kTr(K_kρ K_k^†)\\
&=
\sum_kTr(K_k^† K_kρ)\\
&=
Tr(ρ).
\end{aligned}
$$

Pozitivitatea este păstrată de forma Kraus, iar complet pozitivitatea este
inclusă în construcția canalului.

## 3.14. Dinamica Lindblad

Pentru un sistem deschis:

$$
\frac{dρ}{dt}
=
-i[H,ρ]
+
\sum_k
(
L_kρ L_k^†
-
\frac12
\{L_k^† L_k,ρ\}
).
$$

Dacă se vectorizează matricea densitate, operatorul Liouvillian acționează
într-un spațiu de dimensiune:

$$
N²× N².
$$

Pentru $q=4$, $N=16$, deci dimensiunea operatorului vectorizat este:

$$
256×256.
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
F(ρ,\sigma)
=
[
Tr
√{√{ρ}\sigma√{ρ}}
]².
$$

Pentru stări pure:

$$
F(ψ,φ)
=
|\langleψ|φ\rangle|².
$$

Fidelitatea este definită în formalism și utilizată ca metrică de validare în
Capitolul 6.

## 3.17. Acțiunea exponențialei

Pentru operatorul $A$ și vectorul $v$:

$$
y=etAv.
$$

Aproximarea Taylor:

$$
y_m
=
\sumk=₀m\frac{t^kA^kv}{k!}.
$$

Aproximarea Krylov/Arnoldi:

$$
y_m
≈
V_m etH_m(\beta e₁),
\qquad
\beta=\|v\|₂.
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
| Normalizare | $\langleψ|ψ\rangle=1$ | eroare de normă |
| Unitate | $U^† U=I$ | abatere operatorială |
| Pozitivitate | $ρ\succeq0$ | spectru |
| Conservarea urmei | $Tr(ρ)=1$ | eroare de urmă |
| Compoziție | ordine tensorială fixată | comparație cross-platform |
| Mapare fuzzy | $λ∈[0,1]$ | parametrizare |
| Fidelitate | $0\le F\le1$ | metrică |
| Numeric | $etAv$ | eroare față de referință |
| Sparse | structură CSR validă | NNZ și rezultat SpMV |

## 3.21. Trasabilitatea formalismului

| Element | Matematică | Software | Validare |
| --- | --- | --- | --- |
| QFLPN | definiția tuplei | nucleu model | consistență structurală |
| fuzzy | $λ∈[0,1]$ | parametri | domeniu |
| RY | $R_y(θ)$ | Python/MATLAB | stare/probabilități |
| Kronecker | $⊗$ | operator global | ordinea bazei |
| $C³X$ | $I₈\oplus X$ | circuit 4Q | acțiune pe baze |
| unitar | $U^† U=I$ | operator | normă |
| CPTP | Kraus | canal | urmă/pozitivitate |
| $etAv$ | exponențială | algoritmi | eroare |
| CSR | SpMV | engine sparse | rezultat/performance |

## 3.22. Figuri obligatorii

1. **Figura 3.1 — Arhitectura formală QFLPN**
   - Petri;
   - fuzzy;
   - Hilbert;
   - operatori;
   - evoluție.

2. **Figura 3.2 — Interfața fuzzy–cuantică**
   - $λ$;
   - $θ(λ)$;
   - $R_y(θ)$;
   - starea rezultată.

3. **Figura 3.3 — Ordonarea celor patru qubiți**
   - baza computațională;
   - ordinea tensorială;
   - convenția software.

4. **Figura 3.4 — Construcția operatorului global**
   - $U₀,U₁,U₂,U₃$;
   - tensorizare;
   - operator global;
   - control.

5. **Figura 3.5 — Operatorul $C³X$**
   - controale;
   - țintă;
   - subspațiul activ.

6. **Figura 3.6 — Circuitul QFLPN-4Q**
   - $U_{\mathrm{prep}}$;
   - $C³X$;
   - $U_{\mathrm{mid}}$;
   - $C³X$;
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
- $C³X$;
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
- $C³X$ are controluri și țintă explicite;
- conservarea normei și conservarea urmei sunt demonstrate;
- ideal, zgomot, decoerență, degradare și eroare numerică sunt separate;
- relația $N=2^q$ este respectată;
- fiecare afirmație poate fi urmărită către implementare sau validare.
