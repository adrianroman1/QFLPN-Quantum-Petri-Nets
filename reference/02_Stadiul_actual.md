# Capitolul 2 — Stadiul actual al cercetării

## 2.1 Rolul capitolului
Construiește fundamentul bibliografic și identifică explicit golul de cercetare.
Nu este o enumerare de referințe, ci o analiză critică.

## 2.2 Rețele Petri
- locuri;
- tranziții;
- marcaje;
- activare și firing;
- matrici de incidență;
- reprezentări matriciale;
- limite computaționale;
- CSR și SpMV.

Semantica Petri trebuie separată de implementarea numerică.

## 2.3 Logică fuzzy
- grade de apartenență;
- funcții de apartenență;
- agregare și inferență;
- incertitudine;
- diferența dintre valoare fuzzy, probabilitate și amplitudine cuantică.

Maparea fuzzy–cuantică trebuie prezentată ca alegere de model, nu ca identitate universală.

## 2.4 Fundamente cuantice
- spațiu Hilbert;
- baza computațională;
- produs tensorial;
- operatori liniari și unitari;
- matrice densitate;
- canale CPTP;
- fidelitate.

Fidelitatea este introdusă teoretic și utilizată ulterior în validare.

## 2.5 Analiză spectrală
- valori și vectori proprii;
- decompoziții spectrale;
- funcții de operator;
- teoreme spectrale;
- Artin–Wedderburn unde este justificat;
- integrale de contur numai dacă sunt folosite efectiv.

## 2.6 Analiză funcțională
- spații normate;
- operatori liniari;
- norme;
- continuitate;
- stabilitate;
- convergență;
- spații Banach;
- principiul contracției.

Contracția nu trebuie prezentată ca dovadă automată a absenței deadlock-ului.

## 2.7 Exponențiala operatorială
Compararea conceptuală a:
- Taylor;
- Taylor scalată;
- scaling-and-squaring;
- Padé;
- Chebyshev;
- Krylov/Arnoldi;
- Lanczos;
- rational Krylov;
- exponential integrators.

Se separă `exp(A)` de acțiunea `exp(A)v`.

## 2.8 Metode Krylov
`K_m(A,v) = span{v, Av, ..., A^(m-1)v}`

`A V_m ≈ V_m H_m`

`exp(tA)v ≈ V_m exp(tH_m)(βe₁)`

Se analizează ortogonalizarea, reortogonalizarea, breakdown-ul, costul în funcție
de `NNZ`, memoria și influența structurii spectrale.

## 2.9 Performanță și calcul de înaltă performanță
- CSR;
- SpMV;
- localitatea memoriei;
- paralelism;
- CPU/GPU;
- latență;
- throughput;
- speedup;
- scalare;
- reproductibilitate.

Pragul de `15 ms` este tratat ca obiectiv/reper al proiectului, nu ca limită universală.

### 2.9.1 Metrici de performanță

Pentru evaluarea computațională se vor păstra distinct:

- latență;
- timp mediu, median, minim și maxim;
- speedup;
- throughput;
- memorie;
- eroare absolută maximă;
- eroarea de conservare a normei;
- reproductibilitate.

Pentru scalare, dimensiunea Hilbert este:

`N = 2^q`.

Pentru o operație sparse, costul SpMV este exprimat în funcție de `NNZ`, nu doar
în funcție de `N`.

## 2.10 Comparație metodologică
| Familie | Problemă | Avantaj | Limitare | Rol |
| --- | --- | --- | --- | --- |
| Taylor | `exp(tA)v` | simplă | cost la precizie/scalare | bază |
| Krylov/Arnoldi | `exp(tA)v` | eficientă | ortogonalizare | principală |
| Lanczos | caz Hermitian | eficient | condiții structurale | extensie |
| Chebyshev | operatori potriviți | stabilitate | informație spectrală | referință |
| Padé | `exp(A)` | consacrată | altă problemă numerică | baseline |
| Rational Krylov | `exp(tA)v` | flexibilitate | complexitate | comparație |
| MPS | stări cuantice | scalare structurală | dependență de entanglement | SOTA |

## 2.11 Golul de cercetare
Integrarea coerentă a componentelor Petri, fuzzy, cuantice, operatoriale și HPC,
într-un formalism QFLPN cu analiză matematică și validare reproductibilă, constituie
problema abordată de teză.

## 2.12 Figuri și tabele
- hartă conceptuală a domeniilor;
- taxonomia metodelor numerice;
- poziționarea QFLPN;
- sinteza literaturii;
- comparația metodelor;
- ipoteze și condiții de aplicabilitate.

## 2.13 Criteriu de închidere
Fiecare afirmație despre stadiul actual trebuie susținută bibliografic, iar contribuția
proprie trebuie separată explicit de rezultatele existente.
