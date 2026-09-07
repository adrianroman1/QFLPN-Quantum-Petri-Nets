# Capitolul 3 — Formalismul QFLPN

## 3.1 Rolul capitolului
Nucleul matematic al tezei. Definește formalismul QFLPN și separă rezultatele din
literatură de alegerile de model și contribuțiile originale.

## 3.2 Definiția formală QFLPN
Se vor defini explicit:
- locuri;
- tranziții;
- relații de intrare/ieșire;
- marcaje;
- valori fuzzy;
- spațiul de stare cuantic;
- operatori;
- condiții de activare;
- regula de firing;
- observabile și ieșiri;
- condiții de validitate.

### 3.2.1 Structura formală

| Componentă | Simbol | Rol |
|---|---|---|
| Locuri | `P` | stocarea marcajelor |
| Tranziții | `T` | evoluția discretă |
| Arce | `A` | conectivitate |
| Marcaj | `M` | stare Petri |
| Grad fuzzy | `μ` | informație fuzzy |
| Spațiu cuantic | `H_q` | stare cuantică |
| Operator | `U`, `A` | transformare/evoluție |
| Canal | `{K_k}` | evoluție zgomotoasă |

## 3.3 Spațiul Hilbert
Pentru `q` qubiți:

`H_q = (C²)^(⊗q)`

`dim H_q = N = 2^q`

Pentru 4 qubiți:

`N = 16`.

Ordinea bazei computaționale trebuie declarată o singură dată și respectată în matematică
și software.

### 3.3.1 Consecințe dimensionale

`dim((C²)^(⊗q)) = 2^q`.

Prin urmare, pentru creșterea cu un qubit:

`N(q+1) = 2N(q)`.

Această relație trebuie respectată în toate implementările și graficele de scalare.

## 3.4 Starea cuantică
Pentru stare pură:

`|ψ⟩ ∈ H_q`

`⟨ψ|ψ⟩ = 1`

Pentru matrice densitate:

`ρ = |ψ⟩⟨ψ|`

`ρ ⪰ 0`, `Tr(ρ) = 1`.

## 3.5 Componenta fuzzy
`μ ∈ [0,1]`

Trebuie precizat că `μ` nu este automat probabilitate și nu este automat amplitudine
cuantică.

## 3.6 Maparea fuzzy → cuantică
Construcție de referință:

`θ = πμ`

`R_y(θ) = [[cos(θ/2), -sin(θ/2)], [sin(θ/2), cos(θ/2)]]`

Se documentează domeniul, convenția, interpretarea și limitele. Este o alegere de model.

## 3.7 Activare și firing
Activarea tranziției și transformarea cuantică sunt procese distincte:

`marcaj + condiție fuzzy → tranziție activată → operator admisibil → stare nouă`.

## 3.8 Operatori locali și globali
Pentru:

`|q₀q₁q₂q₃⟩ = |q₀⟩ ⊗ |q₁⟩ ⊗ |q₂⟩ ⊗ |q₃⟩`

operatorul global local este:

`U = U₀ ⊗ U₁ ⊗ U₂ ⊗ U₃`.

Pentru qubitul `i`:

`Ũ_i = I₂^(⊗i) ⊗ U_i ⊗ I₂^(⊗(q-i-1))`.

Convenția de endianitate din software trebuie să fie explicită.

## 3.9 Operatorul controlat C³X
Se definește cu trei qubiți de control și un qubit țintă.

În ordinea de bază adecvată:

`C³X = I₈ ⊕ X`.

Trebuie precizate controlurile, ținta, ordinea bazei și acțiunea asupra stărilor de bază.

## 3.10 Circuitul QFLPN-4Q
`U_total = U_k ... U_2 U_1`

`|ψ_final⟩ = U_total |ψ_initial⟩`

Ordinea operatorilor trebuie justificată algebric și sincronizată cu implementarea.

## 3.11 Propoziție — conservarea normei
Dacă:

`U†U = I`

atunci:

`||U|ψ⟩||₂ = |||ψ⟩||₂`.

Demonstrația completă va fi inclusă în versiunea LaTeX.

## 3.12 Canale CPTP
`ρ' = Σ_k K_k ρ K_k†`

`Σ_k K_k†K_k = I`.

Trebuie demonstrată conservarea urmei și menținută pozitivitatea.

## 3.13 Dinamica Lindblad
Dacă este implementată și validată:

`dρ/dt = -i[H,ρ] + Σ_k(L_kρL_k† - 1/2{L_k†L_k,ρ})`.

Dacă rămâne numai cadru teoretic, trebuie declarat explicit.

## 3.14 Ideal, zgomot, degradare și eroare
Se separă:
- evoluție ideală;
- zgomot/decoerență;
- degradare;
- eroare numerică;
- eroare de implementare.

## 3.15 Fidelitate
`F(ρ,σ) = [Tr √(√ρ σ √ρ)]²`

Este definită aici și utilizată ca metrică în Capitolul 6.

## 3.16 Scalare
`q = 4,...,17`

`N = 2^q`

| q | N |
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

## 3.17 Legătura cu metodele numerice
`y = exp(tA)v`

Această formulare conduce către Taylor și Krylov/Arnoldi din Capitolul 5.

## 3.18 Reprezentare sparse
Se documentează:
- CSR;
- SpMV;
- costul în funcție de `NNZ`;
- memoria;
- paralelizarea.

Nu se presupune că orice operator QFLPN este sparse.

## 3.19 Proprietăți de verificat
- normalizare;
- unitate;
- conservarea urmei;
- pozitivitate;
- compoziție tensorială;
- ordinea bazei;
- consistența mapării fuzzy–cuantice;
- compatibilitatea model–implementare.

## 3.20 Trasabilitate
Etichete de lucru:
- **L** — literatură;
- **M** — alegere de model;
- **O** — contribuție originală;
- **V** — validare.

Etichetele sunt pentru documentația internă și pot fi eliminate din versiunea finală.

## 3.21 Figuri
1. Arhitectura formală QFLPN.
2. Interfața fuzzy–cuantică.
3. Ordonarea celor 4 qubiți.
4. Transformarea locală → globală prin Kronecker.
5. Operatorul C³X.
6. Evoluția ideală versus degradare.
7. Fluxul de validare.
8. Reproductibilitatea Python ↔ MATLAB/Octave ↔ Java.
9. Scalarea `q = 4,...,17`.

## 3.22 Tabele
- definiția formală;
- notații;
- operatori locali/globali;
- maparea fuzzy–cuantică;
- proprietăți și demonstrații;
- scala `q/N`;
- trasabilitatea definiție → implementare → validare.

## 3.23 Criteriu de închidere
Formalismul este considerat închis numai când definițiile, convenția qubiților,
maparea fuzzy–cuantică, operatorii Kronecker, C³X, separarea ideal/zgomot și
proprietățile matematice sunt fără ambiguități și pot fi urmărite până la implementare
și validare.
