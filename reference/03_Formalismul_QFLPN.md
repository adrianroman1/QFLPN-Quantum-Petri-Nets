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

`𝒩_QFLPN = (P, T, E, M, μ, ℋ, ρ, 𝒰, ℛ)`

unde:

- `P` este mulțimea finită a locurilor;
- `T` este mulțimea finită a tranzițiilor;
- `E` este relația de intrare/ieșire;
- `M` este marcajul Petri;
- `μ` este familia valorilor sau funcțiilor fuzzy;
- `ℋ` este spațiul Hilbert al stratului cuantic;
- `ρ` este reprezentarea stării;
- `𝒰` este familia operatorilor admisibili;
- `ℛ` este familia regulilor de evoluție.

Definiția este stratificată intenționat: locul Petri este un obiect structural,
iar `ρ` este un obiect informațional.

## 3.3. Locuri, tranziții și marcaje

Un loc `p ∈ P` reprezintă o componentă structurală a rețelei.

O tranziție `t ∈ T` reprezintă un eveniment sau o regulă de evoluție.

Marcajul clasic poate fi:

`M : P → ℕ`

În stratul QFLPN se poate asocia unui loc o reprezentare informațională:

`ρ_p ∈ 𝒟(ℋ)`

unde:

`𝒟(ℋ) = {ρ : ρ ⪰ 0, Tr(ρ) = 1}`

Un token cuantic este o entitate semantică a modelului; el nu este identificat
automat cu un qubit fizic.

## 3.4. Activarea și firing-ul

Activarea unei tranziții este determinată de structura Petri și de condițiile
fuzzy:

`(M, μ) → t_activat`

Numai după activare se aplică transformarea operatorială:

`t_activat → 𝓔_t → ρ′`

Astfel:

> **marcaj + condiție fuzzy → firing → operator admisibil → stare nouă**

Separarea împiedică confundarea logicii de activare cu evoluția cuantică.

## 3.5. Componenta fuzzy

Pentru o variabilă fuzzy:

`μⱼ ∈ [0, 1]`

Pentru o tranziție `t`, o funcție de agregare poate produce:

`λ_t = g(μ₁, …, μ_r)`, `0 ≤ λ_t ≤ 1`

Funcția `g` nu este impusă universal. Poate fi aleasă dintre agregări admisibile
și trebuie documentată pentru fiecare instanță experimentală.

Este esențial:

`λ_t ≠ automat o probabilitate`

și:

`λ_t ≠ automat o amplitudine`.

## 3.6. Spațiul Hilbert

Pentru `q` qubiți:

`ℋ_q = (ℂ²)⊗q`, `N = 2^q`

Baza computațională este:

`𝓑_q = {|q₀q₁…q_{q−1}⟩ : qᵢ ∈ {0,1}}`

Pentru patru qubiți:

`dim(ℋ₄) = 16`

Convenția adoptată este:

`|q₀q₁q₂q₃⟩ = |q₀⟩⊗|q₁⟩⊗|q₂⟩⊗|q₃⟩`

## 3.7. Stări pure și mixte

O stare pură este:

`|ψ⟩ = Σⱼ₌₀^(N−1) cⱼ|j⟩`, `Σⱼ₌₀^(N−1) |cⱼ|² = 1`

Matricea densitate asociată este:

`ρ_ψ = |ψ⟩⟨ψ|`

Pentru o stare mixtă:

`ρ = Σᵢ pᵢ|ψᵢ⟩⟨ψᵢ|`

cu:

`pᵢ ≥ 0`, `Σᵢ pᵢ = 1`

Proprietățile fundamentale sunt:

`ρ† = ρ`, `ρ ⪰ 0`, `Tr(ρ) = 1`

## 3.8. Maparea fuzzy → cuantică

Pentru fiecare parametru fuzzy `λ ∈ [0,1]`, specificația QFLPN utilizează:

`θ(λ) = 2 arcsin(√λ)`

Operatorul local este:

```text
R_y(θ) = [ cos(θ/2)   −sin(θ/2) ]
         [ sin(θ/2)    cos(θ/2) ]
```

Aplicat lui `|0⟩`:

`R_y(θ(λ))|0⟩ = √(1−λ)|0⟩ + √λ|1⟩`

Rezultă:

`|⟨1|R_y(θ(λ))|0⟩|² = λ`

Această mapare este **o alegere de model QFLPN**, nu o identitate universală
între apartenență fuzzy și probabilitate cuantică.

## 3.9. Operatori locali

Pentru qubitul `i`, operatorul localizat se construiește prin inserarea lui `U_i`
în poziția `i` a produsului tensorial și a identității pe celelalte poziții:

`Ũ_i = I₂ ⊗ … ⊗ I₂ ⊗ U_i ⊗ I₂ ⊗ … ⊗ I₂`

Pentru patru qubiți, în convenția canonică `|q₀q₁q₂q₃⟩`:

`Ũ₀ = U₀ ⊗ I₂ ⊗ I₂ ⊗ I₂`

`Ũ₁ = I₂ ⊗ U₁ ⊗ I₂ ⊗ I₂`

`Ũ₂ = I₂ ⊗ I₂ ⊗ U₂ ⊗ I₂`

`Ũ₃ = I₂ ⊗ I₂ ⊗ I₂ ⊗ U₃`

Pentru operatori independenți:

`U_loc = U₀ ⊗ U₁ ⊗ U₂ ⊗ U₃`

Orice implementare little-endian trebuie să introducă explicit permutarea de indici;
ea nu modifică definiția matematică a bazei.

## 3.10. Operatorul controlat `C³X`

Operatorul `C³X` are trei qubiți de control și un qubit țintă. În ordinea
corespunzătoare bazei, forma bloc este:

`C³X = I₈ ⊕ X`

unde:

```text
X = [ 0  1 ]
    [ 1  0 ]
```

Acțiunea este:

`|1110⟩ ↦ |1111⟩`

`|1111⟩ ↦ |1110⟩`

iar stările pentru care condiția celor trei controale nu este satisfăcută rămân
neschimbate.

Controlurile, ținta și ordinea bazei trebuie declarate în fiecare implementare.

## 3.11. Compoziția circuitului QFLPN-4Q

Dacă evoluția este împărțită în faze:

`U_QFLPN = U_m U_{m−1} … U₂ U₁`

Starea finală este:

`|ψ_final⟩ = U_QFLPN |ψ_initial⟩`

Pentru instanța de referință se poate utiliza forma:

`U_QFLPN = U_final C³X U_mid C³X U_prep`

cu sincronizarea exactă între această expresie și circuitul implementat.

Produsul Kronecker și produsul ordonat al fazelor nu sunt sinonime:
Kronecker construiește operatori compuși, iar înmulțirea ordonată determină
succesiunea temporală a evoluției.

## 3.12. Propoziție — conservarea normei

**Propoziție.** Dacă `U†U = I`, atunci pentru orice `|ψ⟩`:

`‖U|ψ⟩‖₂ = ‖|ψ⟩‖₂`

**Demonstrație.**

`‖U|ψ⟩‖₂² = ⟨ψ|U†U|ψ⟩ = ⟨ψ|I|ψ⟩ = ⟨ψ|ψ⟩`

Prin extragerea rădăcinii pătrate rezultă egalitatea normelor.

## 3.13. Canale CPTP

Pentru:

`𝓔(ρ) = Σₖ KₖρKₖ†`

condiția de conservare a urmei este:

`Σₖ Kₖ†Kₖ = I`

Atunci:

`Tr(𝓔(ρ)) = Σₖ Tr(KₖρKₖ†) = Σₖ Tr(Kₖ†Kₖρ) = Tr(ρ)`

Pozitivitatea este păstrată de forma Kraus, iar complet pozitivitatea este
inclusă în construcția canalului.

## 3.14. Dinamica Lindblad

Pentru un sistem deschis:

`dρ/dt = −i[H,ρ] + Σₖ (LₖρLₖ† − ½{Lₖ†Lₖ,ρ})`

Dacă se vectorizează matricea densitate, operatorul Liouvillian acționează
într-un spațiu de dimensiune:

`N² × N²`

Pentru `q = 4`, `N = 16`, deci dimensiunea operatorului vectorizat este:

`256 × 256`

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

`F(ρ,σ) = [Tr(√(√ρ σ √ρ))]²`

Pentru stări pure:

`F(ψ,φ) = |⟨ψ|φ⟩|²`

Fidelitatea este definită în formalism și utilizată ca metrică de validare în
Capitolul 6.

## 3.17. Acțiunea exponențialei

Pentru operatorul `A` și vectorul `v`:

`y = e^(tA)v`

Aproximarea Taylor:

`y_m = Σₖ₌₀^m (t^k A^k v)/k!`

Aproximarea Krylov/Arnoldi:

`y_m ≈ V_m e^(tH_m)(βe₁)`, `β = ‖v‖₂`

Aceste expresii constituie interfața formală către algoritmii din Capitolul 5.

## 3.18. Reprezentare sparse

Pentru o matrice rară `A`:

`y = Ax`

costul aritmetic al SpMV este:

`O(NNZ(A))`

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

`N = 2^q`, `q = 4, 5, …, 17`

| `q` | `N` |
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

Instanța QFLPN-4Q este punctul de referință `q = 4`, `N = 16` al familiei scalabile.

## 3.20. Proprietăți matematice și condiții de validare

| Proprietate | Condiție | Verificare |
| --- | --- | --- |
| Normalizare | `⟨ψ|ψ⟩ = 1` | eroare de normă |
| Unitate | `U†U = I` | abatere operatorială |
| Pozitivitate | `ρ ⪰ 0` | spectru |
| Conservarea urmei | `Tr(ρ) = 1` | eroare de urmă |
| Compoziție | ordine tensorială fixată | comparație cross-platform |
| Mapare fuzzy | `λ ∈ [0,1]` | parametrizare |
| Fidelitate | `0 ≤ F ≤ 1` | metrică |
| Numeric | `e^(tA)v` | eroare față de referință |
| Sparse | structură CSR validă | NNZ și rezultat SpMV |

## 3.21. Trasabilitatea formalismului

| Element | Matematică | Software | Validare |
| --- | --- | --- | --- |
| QFLPN | definiția tuplei | nucleu model | consistență structurală |
| fuzzy | `λ ∈ [0,1]` | parametri | domeniu |
| RY | `R_y(θ)` | Python/MATLAB | stare/probabilități |
| Kronecker | `⊗` | operator global | ordinea bazei |
| `C³X` | `I₈ ⊕ X` | circuit 4Q | acțiune pe baze |
| unitar | `U†U = I` | operator | normă |
| CPTP | Kraus | canal | urmă/pozitivitate |
| `e^(tA)v` | exponențială | algoritmi | eroare |
| CSR | SpMV | engine sparse | rezultat/performance |

## 3.22. Figuri obligatorii

1. **Figura 3.1 — Arhitectura formală QFLPN**
   - Petri;
   - fuzzy;
   - Hilbert;
   - operatori;
   - evoluție.

2. **Figura 3.2 — Interfața fuzzy–cuantică**
   - `λ`;
   - `θ(λ)`;
   - `R_y(θ)`;
   - starea rezultată.

3. **Figura 3.3 — Ordonarea celor patru qubiți**
   - baza computațională;
   - ordinea tensorială;
   - convenția software.

4. **Figura 3.4 — Construcția operatorului global**
   - `U₀, U₁, U₂, U₃`;
   - tensorizare;
   - operator global;
   - control.

5. **Figura 3.5 — Operatorul `C³X`**
   - controale;
   - țintă;
   - subspațiul activ.

6. **Figura 3.6 — Circuitul QFLPN-4Q**
   - `U_prep`;
   - `C³X`;
   - `U_mid`;
   - `C³X`;
   - `U_final`.

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

9. **Figura 3.9 — Scala `q = 4, …, 17`**
   - `q`;
   - `N = 2^q`;
   - cost/memorie.

## 3.23. Tabele obligatorii

- definiția formală QFLPN;
- notații;
- maparea fuzzy–cuantică;
- operatori locali/globali;
- `C³X`;
- proprietăți și demonstrații;
- scala `q/N`;
- separarea ideal/noisy/degradare;
- trasabilitate matematică–software–validare.

## 3.24. Criteriu de închidere

Formalismul este considerat închis numai când:

- toate componentele tuplei sunt definite;
- activarea fuzzy este separată de firing și de transformarea cuantică;
- convenția bazei este unică și identică în matematică și software;
- maparea fuzzy–cuantică este declarată ca alegere de model;
- operatorii Kronecker sunt definiți fără ambiguitate;
- `C³X` are controluri și țintă explicite;
- conservarea normei și conservarea urmei sunt demonstrate;
- ideal, zgomot, decoerență, degradare și eroare numerică sunt separate;
- relația `N = 2^q` este respectată;
- fiecare afirmație poate fi urmărită către implementare sau validare.
