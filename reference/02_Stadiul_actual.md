# Capitolul 2 — Stadiul actual al cercetării

## 2.1. Rolul capitolului

Capitolul stabilește fundamentul bibliografic pentru QFLPN și identifică golul de
cercetare. Prezentarea este critică: conceptele consacrate sunt separate de
alegerile de model și de contribuțiile originale dezvoltate ulterior.

Lanțul conceptual este:

> **Petri → Fuzzy → Quantum → Operatori → e^(tA)v → HPC**

## 2.2. Rețele Petri

O rețea Petri clasică poate fi reprezentată prin:

`𝒫 = (P, T, F)`

unde `P` este mulțimea locurilor, `T` mulțimea tranzițiilor, iar `F` relația
de flux.

Marcajul este o aplicație:

`M : P → ℕ`

Pentru reprezentarea matricială, matricea de incidență poate fi scrisă:

`C = C⁺ − C⁻`

iar o dinamică discretă poate avea forma:

`Mₖ₊₁ = Mₖ + Cσₖ`

Noțiunile de activare și firing constituie fundamentul semantic al stratului Petri.
Ele nu trebuie confundate cu transformarea operatorială a unei stări cuantice.

## 2.3. Fuzzy Petri nets și logică fuzzy

Un grad de apartenență este:

`μ ∈ [0, 1]`

Sunt relevante:

- funcțiile de apartenență;
- t-normele și agregarea;
- inferența fuzzy;
- gradele de activare;
- tratarea informației imprecise.

O distincție fundamentală este:

`μ ≠ p ≠ α`

unde `μ` este un grad fuzzy, `p` o probabilitate, iar `α` poate reprezenta
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

> **separare semantică → interfață explicită → compoziție controlată**

Nu se afirmă că un simulator clasic este echivalent cu un procesor cuantic fizic și
nu se deduce scalabilitatea dintr-un circuit de patru qubiți.

## 2.5. Fundamente cuantice

Pentru `q` qubiți:

`ℋ_q = (ℂ²)⊗q`, `dim(ℋ_q) = 2^q`

O stare pură este:

`|ψ⟩ = Σⱼ₌₀^(2^q−1) cⱼ|j⟩`, `Σⱼ |cⱼ|² = 1`

O stare mixtă este reprezentată prin:

`ρ = Σᵢ pᵢ|ψᵢ⟩⟨ψᵢ|`

cu:

`ρ ⪰ 0`, `Tr(ρ) = 1`

Evoluția unitară:

`|ψ′⟩ = U|ψ⟩`, `U†U = I`

Conservarea normei rezultă din:

`‖U|ψ⟩‖₂² = ⟨ψ|U†U|ψ⟩ = ‖ψ‖₂²`

## 2.6. Canale CPTP și sisteme deschise

Pentru un canal cuantic:

`𝓔(ρ) = Σₖ KₖρKₖ†`

cu:

`Σₖ Kₖ†Kₖ = I`

Această condiție asigură conservarea urmei:

`Tr(𝓔(ρ)) = Tr(ρ)`

Pentru dinamica Markoviană continuă, forma Lindblad este:

`dρ/dt = −i[H,ρ] + Σₖ (LₖρLₖ† − ½{Lₖ†Lₖ,ρ})`

În teză, cadrul Lindblad este tratat ca rezultat experimental numai dacă există
implementarea și măsurarea corespunzătoare; altfel rămâne un cadru teoretic.

## 2.7. Produse tensoriale și operatori

Pentru sisteme compuse:

`ℋ_q = ⊗ᵢ₌₀^(q−1) ℋᵢ`

Pentru patru qubiți:

`|q₀q₁q₂q₃⟩ = |q₀⟩⊗|q₁⟩⊗|q₂⟩⊗|q₃⟩`

Un operator localizat pe qubitul `i` este:

`Ũᵢ = I₂⊗i ⊗ Uᵢ ⊗ I₂⊗(q−i−1)`

unde notația indică plasarea lui `Uᵢ` în poziția `i`; în implementarea efectivă
operatorul trebuie construit explicit astfel încât ordinea tensorială să coincidă
cu baza declarată.

Pentru operații independente:

`U_loc = U₀⊗U₁⊗⋯⊗U_{q−1}`

Pentru cazul 4Q:

`U_loc = U₀⊗U₁⊗U₂⊗U₃`

Convenția de ordine tensorială trebuie sincronizată între matematică și software.

## 2.8. Analiză spectrală

Spectrul unui operator `A` este:

`σ(A) = {λ ∈ ℂ : A − λI nu este inversabil}`

Pentru un operator Hermitian:

`A = A†`

valorile proprii sunt reale, iar descompunerea spectrală poate fi scrisă:

`A = Σⱼ λⱼPⱼ`

Calculul funcțional conduce la:

`f(A) = Σⱼ f(λⱼ)Pⱼ`

Algebrele Artin–Wedderburn pot furniza o perspectivă structurală asupra
decompunerii algebrice, dar sunt utilizate numai acolo unde această structură
este relevantă pentru operatorii considerați.

Integralele de contur nu sunt introduse ca element decorativ; ele apar numai dacă
sunt utilizate efectiv în analiza sau implementarea finală.

## 2.9. Analiză funcțională

Într-un spațiu normat `(X, ‖·‖)`, un operator liniar continuu satisface
proprietățile standard de mărginitate și continuitate.

Pentru un operator `T : X → X`:

`‖T(x) − T(y)‖ ≤ q‖x − y‖`, `0 ≤ q < 1`

înseamnă că `T` este contracție.

Teorema punctului fix Banach oferă existență și unicitate în condițiile sale.
Aceasta nu constituie automat o demonstrație a absenței deadlock-ului într-o
rețea Petri; deadlock-ul este o proprietate distinctă care necesită analiză proprie.

## 2.10. Exponențiala operatorială

Exponențiala unui operator este:

`e^A = Σₖ₌₀^∞ A^k/k!`

În problemele de evoluție este esențială distincția:

`e^A` versus `e^A v`

Teza urmărește în principal a doua problemă, deoarece formarea explicită a lui
`e^A` poate fi prohibitivă pentru operatori mari și rari.

Aproximarea Taylor:

`T_m(A)v = Σₖ₌₀^m A^k v/k!`

Pentru scalare:

`e^A = (e^(A/2^s))^(2^s)`

Padé și scaling-and-squaring sunt tratate drept metode consacrate de referință,
nu drept contribuții originale QFLPN.

## 2.11. Metode Krylov și Arnoldi

Subspațiul Krylov este:

`𝒦_m(A,v) = span{v, Av, A²v, …, A^(m−1)v}`

Procesul Arnoldi construiește `V_m` și `H_m` astfel încât:

`AV_m = V_mH_m + h_{m+1,m}v_{m+1}e_mᵀ`

Acțiunea exponențialei poate fi aproximată prin:

`e^(tA)v ≈ V_m e^(tH_m)(βe₁)`, `β = ‖v‖₂`

Trebuie analizate:

- ortogonalizarea;
- reortogonalizarea;
- breakdown;
- costul produselor cu `A`;
- costul în funcție de `NNZ`;
- memoria;
- influența structurii spectrale.

## 2.12. Lanczos

Pentru operatori Hermitieni, Lanczos produce o bază Krylov cu structură
tridiagonală:

`AV_m ≈ V_mT_m`

unde `T_m` este Hermitiană tridiagonală.

Avantajul este reducerea memoriei și a costului de stocare față de o matrice
Hessenberg generală. Metoda este aplicabilă numai când ipotezele structurale
corespunzătoare sunt îndeplinite.

## 2.13. Aproximări Chebyshev

Pentru `x ∈ [−1,1]`:

`T_k(x) = cos(k arccos x)`

O funcție poate fi aproximată printr-o combinație:

`f(x) ≈ Σₖ₌₀^m aₖT_k(x)`

Aplicarea la operatori necesită scalarea spectrului într-un interval controlat.
Prin urmare, informația spectrală este parte a condițiilor de aplicare.

## 2.14. Krylov rațional

Krylov rațional utilizează vectori de forma:

`(A − ξⱼI)⁻¹v`

Metoda poate fi avantajoasă pentru spectre dificil de aproximat polinomial, dar
introduce costul rezolvărilor liniare și dependența de alegerea polilor `ξⱼ`.

## 2.15. Integratoare exponențiale

Pentru ecuații de evoluție:

`dy/dt = Ay + g(t,y)`

integratoarele exponențiale exploatează explicit operatorul `e^(tA)` și funcții
înrudite ale operatorului. Aceste metode constituie puntea dintre analiza
exponențialei și dinamica temporală mai generală.

## 2.16. Calcul sparse și HPC

Pentru:

`y = Ax`

cu `A` rară, costul SpMV este dominat de:

`O(NNZ(A))`

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

`T_mean`, `T_median`, `T_min`, `T_max`

Speedup-ul este:

`S = T_seq/T_par`

Throughput-ul poate fi definit prin:

`Throughput = N_work/T`

Eroarea absolută maximă:

`E_∞ = maxⱼ |xⱼ − x̂ⱼ|`

Conservarea normei:

`E_norm = |‖x‖₂ − 1|`

Pentru stări cuantice, fidelitatea trebuie definită conform tipului de stare;
pentru două stări pure:

`F(ψ,φ) = |⟨ψ|φ⟩|²`

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
| Taylor | `e^(tA)v` | simplitate | cost la ordin mare | baseline |
| Taylor scalată | `e^(tA)v` | controlul normei | alegerea scalării | baseline |
| Arnoldi | `e^(tA)v` | reducere de dimensiune | ortogonalizare | principală |
| Lanczos | caz Hermitian | structură compactă | condiții stricte | extensie |
| Chebyshev | operator cu spectru controlat | aproximare polinomială | necesită scalare spectrală | referință |
| Padé | `e^A` | metodă consacrată | formează alt tip de aproximare | baseline |
| Krylov rațional | `e^(tA)v` | flexibilitate spectrală | rezolvări liniare | comparație |
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

> **semantică → model → operator → algoritm → software → validare**

## 2.21. Figuri obligatorii

### Figura 2.1 — Harta conceptuală a domeniilor

Petri, fuzzy, quantum, operatori și HPC trebuie reprezentate ca niveluri distincte,
iar QFLPN ca interfață de integrare.

### Figura 2.2 — Taxonomia metodelor pentru `e^(tA)v`

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
- comparația metodelor pentru `e^(tA)v`;
- comparația metodelor HPC;
- ipoteze și condiții de aplicabilitate;
- poziționarea QFLPN față de formalisme existente.

## 2.23. Criteriu de închidere

Capitolul este închis numai când fiecare afirmație bibliografică are sursă
verificabilă, fiecare metodă este poziționată corect, iar contribuțiile proprii
nu sunt prezentate ca rezultate ale literaturii.
