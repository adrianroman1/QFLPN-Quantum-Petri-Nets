# Capitolul 1 — Introducere

## 1.1 Rolul capitolului
Stabilește problema doctorală, motivația, obiectivele, contribuțiile originale,
metodologia și arhitectura tezei.

## 1.2 Problema de cercetare
Formularea unui formalism Quantum-Fuzzy Logical Petri Nets (QFLPN) care integrează
dinamica Petri, informația fuzzy, stări cuantice, operatori, compoziție tensorială,
evoluție operatorială și implementare numerică reproductibilă.

## 1.3 Motivație
### 1.3.1 Fundament matematic
Definirea riguroasă a obiectelor QFLPN, spațiului de stări, operatorilor și regulilor
de evoluție.

### 1.3.2 Fundament algoritmic
Calculul reproductibil al acțiunii `y = exp(tA)v`, prin metode Taylor și Krylov/Arnoldi
și metode de referință.

### 1.3.3 Fundament computațional
Reprezentare sparse, CSR, SpMV, paralelism și evaluarea scalării.

## 1.4 Întrebarea principală
Cum poate fi construit și validat un formalism QFLPN coerent matematic și implementabil
la scară, păstrând trasabilitatea dintre model, algoritm și rezultat?

## 1.5 Obiective
1. Definirea formală QFLPN.
2. Definirea spațiului de stări și a evoluției.
3. Formalizarea mapării fuzzy–cuantice.
4. Formalizarea transformărilor locale–globale.
5. Definirea operatorilor controlați și a referinței cu 4 qubiți.
6. Separarea evoluției ideale de degradare/decoerență.
7. Analiza proprietăților matematice.
8. Implementarea metodelor numerice.
9. Validarea pentru `q = 4,...,17`, `N = 2^q`.
10. Evaluarea performanței și reproductibilității.

## 1.6 Contribuții originale
- formalismul QFLPN propus;
- integrarea fuzzy–cuantică;
- construcția locală–globală prin Kronecker;
- operatorii controlați;
- metodologia numerică reproductibilă;
- arhitectura software multi-limbaj;
- metodologia de validare și scalare.

## 1.7 Metodologia cercetării
`definiție → model → analiză → algoritmi → implementare → validare → performanță → comparație`.

Trasabilitate obligatorie:
`obiectiv → ipoteză → ecuație → algoritm → implementare → metrică → rezultat`.

## 1.8 Convenții
- `q` = numărul de qubiți;
- `N = 2^q` = dimensiunea spațiului Hilbert;
- `|ψ⟩` = stare pură;
- `ρ` = matrice densitate;
- `U` = operator unitar;
- `A` = operator generator;
- `CSR`, `SpMV`, `NNZ` = notații HPC.

## 1.9 Figuri
- arhitectura cercetării;
- relația Petri–fuzzy–quantum;
- flux metodologic;
- trasabilitatea obiective–rezultate.

## 1.10 Tabele
- obiective și rezultate;
- contribuții și capitole;
- notații;
- obiective–metode–metrici.

### 1.10.1 Matricea obiectiv–rezultat

| Obiectiv | Capitol principal | Tip de verificare |
|---|---|---|
| Formalism QFLPN | 3 | definiții, propoziții, demonstrații |
| Analiză matematică | 4 | teoreme, ipoteze, estimări |
| Algoritmi și software | 5 | algoritmi și implementări |
| Validare numerică | 6 | metrici, erori, reproductibilitate |
| Sinteză și publicații | 7 | integrare și diseminare |

### 1.10.2 Matricea contribuțiilor

| Contribuție | Natură | Evidență |
|---|---|---|
| Formalism QFLPN | originală | definiții și construcții |
| Mapare fuzzy–cuantică | alegere de model | formulare și justificare |
| Construcție Kronecker | formală | ecuații și exemplu 4Q |
| Metodologie numerică | metodologică | algoritmi și protocol |
| Validare multi-limbaj | experimentală | rezultate reproductibile |

## 1.11 Ecuații introductive
`N = 2^q`

`y = exp(tA)v`

Ecuațiile introductive nu trebuie să anticipeze demonstrațiile din capitolele 3–4.

## 1.12 Criteriu de închidere
Fiecare obiectiv trebuie să aibă un loc precis de demonstrare, implementare sau validare.
