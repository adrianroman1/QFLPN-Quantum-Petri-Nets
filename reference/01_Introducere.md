# Capitolul 1 — Introducere

## 1.1. Rolul capitolului

Acest capitol stabilește problema științifică, motivația, întrebarea de cercetare,
obiectivele, contribuțiile originale, metodologia și arhitectura tezei. Introducerea
nu substituie formalizarea matematică din Capitolul 3 și nici validarea experimentală
din Capitolul 6; ea fixează însă lanțul de trasabilitate care le leagă.

## 1.2. Contextul cercetării

Rețelele Petri oferă un formalism consacrat pentru modelarea sistemelor cu evenimente
discrete, a concurenței, a marcajelor și a regulilor de evoluție. Extensiile fuzzy
permit reprezentarea informației graduale, iar formalismul cuantic introduce stări
în spații Hilbert, operatori liniari și evoluție prin transformări unitare sau canale
cuantice.

Teza dezvoltă **Quantum-Fuzzy Logical Petri Nets (QFLPN)** ca formalism stratificat
în care cele trei niveluri sunt păstrate distinct și apoi conectate prin interfețe
matematice explicite:

$$
\text{Petri}
+
\text{Fuzzy}
+
\text{Quantum}
\longrightarrow
\text{QFLPN}.
$$

Principiul central este **separarea semantică urmată de compoziție controlată**.
Un loc Petri, un marcaj, o valoare fuzzy, un qubit și o stare cuantică nu sunt
considerate automat obiecte identice.

## 1.3. Problema de cercetare

Problema doctorală este:

> Cum poate fi construit și validat un formalism QFLPN coerent matematic și
> implementabil numeric, în care structura Petri, activarea fuzzy și evoluția
> cuantică sunt conectate printr-o interfață operatorială explicită?

Problema este descompusă în:

1. definirea formală a structurii QFLPN;
2. definirea spațiului de stare și a regulilor de evoluție;
3. stabilirea unei mapări fuzzy–cuantice documentate;
4. construcția operatorilor locali și globali;
5. integrarea operatorilor controlați;
6. tratarea separată a dinamicii ideale și a modelelor de zgomot/degradare;
7. analiza matematică a proprietăților relevante;
8. implementarea numerică reproductibilă;
9. validarea pe scala cuantică $N=2^q$;
10. evaluarea performanței pentru reprezentări sparse și operații SpMV.

## 1.4. Întrebarea principală și ipoteza de lucru

Întrebarea principală este:

$$
\boxed{
\text{Cum poate QFLPN să ofere o interfață verificabilă între logică discretă,
informație fuzzy și evoluție cuantică?}
}
$$

Ipoteza de lucru este că o arhitectură stratificată, cu interfețe matematice
explicit definite și cu protocoale de calcul reproductibile, permite validarea
separată a semanticii, proprietăților operatoriale și implementării numerice.

Ipoteza nu afirmă că QFLPN este universal superior altor formalisme.

## 1.5. Obiectivele cercetării

| ID | Obiectiv | Evidență principală |
| --- | --- | --- |
| O1 | Definirea formală QFLPN | Capitolul 3 |
| O2 | Definirea spațiului de stări | Capitolul 3 |
| O3 | Formalizarea mapării fuzzy–cuantice | Capitolul 3 |
| O4 | Transformări locale–globale | Capitolul 3 |
| O5 | Operator controlat și referință 4Q | Capitolul 3 |
| O6 | Separarea ideal/zgomot/degradare | Capitolele 3–5 |
| O7 | Analiză matematică | Capitolul 4 |
| O8 | Algoritmi și software | Capitolul 5 |
| O9 | Validare numerică și experimentală | Capitolul 6 |
| O10 | Reproductibilitate și diseminare | Capitolele 6–7 |

## 1.6. Contribuții originale

| ID | Contribuție | Natură |
| --- | --- | --- |
| C1 | Formalismul QFLPN stratificat | contribuție originală |
| C2 | Interfața fuzzy–cuantică | alegere de model formalizată |
| C3 | Construcția locală–globală prin Kronecker | contribuție în cadrul QFLPN |
| C4 | Integrarea operatorilor controlați | contribuție în cadrul QFLPN |
| C5 | Separarea semantică a firing-ului de transformarea cuantică | contribuție de modelare |
| C6 | Lanțul numeric pentru acțiunea $etAv$ | contribuție algoritmică/implementare |
| C7 | Reprezentarea sparse și execuția SpMV | contribuție software/HPC |
| C8 | Protocolul multi-limbaj reproductibil | contribuție metodologică |
| C9 | Matricea de trasabilitate model–cod–rezultat | contribuție metodologică |
| C10 | Portofoliul de publicații derivat din rezultate | diseminare științifică |

## 1.7. Ecuațiile fundamentale

Pentru o familie QFLPN poate fi utilizată structura:

$$
\mathcal{N}QFLPN
=
(P,T,E,M,μ,ℋ,ρ,\mathcal{U},\mathcal{R}),
$$

unde $P$ reprezintă locurile, $T$ tranzițiile, $E$ relația de conectivitate,
$M$ marcajul, $μ$ componenta fuzzy, $ℋ$ spațiul Hilbert,
$ρ$ reprezentarea stării, $\mathcal{U}$ familia de operatori, iar
$\mathcal{R}$ regulile de evoluție.

Pentru $q$ qubiți:

$$
ℋ_q=(ℂ²)⊗ q,
\qquad
N_q=\dim(ℋ_q)=2^q.
$$

O stare pură satisface:

$$
|ψ\rangle∈ℋ_q,
\qquad
\langleψ|ψ\rangle=1.
$$

O matrice densitate satisface:

$$
ρ\succeq0,
\qquad
ρ^†=ρ,
\qquad
Tr(ρ)=1.
$$

Evoluția unitară este:

$$
|ψ'\rangle=U|ψ\rangle,
\qquad
U^† U=I.
$$

Pentru dinamica generală:

$$
ρ'
=
\mathcal{E}(ρ)
=
\sum_kK_kρ K_k^†,
\qquad
\sum_kK_k^† K_k=I.
$$

Pentru acțiunea exponențialei asupra unui vector:

$$
y=etAv.
$$

Această problemă este distinctă de formarea explicită a matricei $etA$.

## 1.8. Convenții de notație

| Simbol | Semnificație |
| --- | --- |
| $P$ | mulțimea locurilor |
| $T$ | mulțimea tranzițiilor |
| $M$ | marcaj Petri |
| $μ$ | grad fuzzy |
| $ℋ_q$ | spațiul Hilbert pentru $q$ qubiți |
| $N=2^q$ | dimensiunea spațiului de stare |
| $|ψ\rangle$ | stare pură |
| $ρ$ | matrice densitate |
| $U$ | operator unitar |
| $A$ | operator/generator numeric |
| $K_k$ | operator Kraus |
| $\operatorname{NNZ}$ | numărul de elemente nenule |
| CSR | Compressed Sparse Row |
| SpMV | sparse matrix–vector multiplication |

Convenția bazei computaționale este:

$$
|q₀q₁\ldots qq-₁\rangle
=
|q₀\rangle⊗|q₁\rangle⊗·s
⊗|qq-₁\rangle.
$$

Orice convenție de endianitate implementată în software trebuie documentată separat.

## 1.9. Metodologia cercetării

Metodologia este organizată în următoarele etape:

1. delimitarea problemei și analiza critică a literaturii;
2. definirea matematică a QFLPN;
3. definirea interfeței fuzzy–cuantice;
4. construirea operatorilor locali și globali;
5. definirea circuitului QFLPN-4Q;
6. separarea modelelor ideal și noisy;
7. analiza matematică;
8. proiectarea algoritmilor numerici;
9. implementarea multi-limbaj;
10. validarea numerică;
11. evaluarea performanței;
12. compararea controlată cu metode de referință;
13. integrarea rezultatelor în publicații.

Lanțul de trasabilitate este:

$$
\boxed{
\text{obiectiv}
→
\text{ipoteză}
→
\text{ecuație}
→
\text{algoritm}
→
\text{cod}
→
\text{metrică}
→
\text{rezultat}
}
$$

## 1.10. Scalare și delimitarea dimensiunilor

Pentru componenta cuantică:

$$
N=2^q.
$$

În familia validată:

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

Workload-urile HPC de ordinul milioanelor de stări/elemente sunt raportate ca
probleme de calcul sparse și nu sunt reinterpretate ca dimensiuni ale unui
spațiu Hilbert cuantic cu număr arbitrar de qubiți.

Obiectivul de latență de **15 ms** este un prag de proiect pentru configurația
definită și nu o limită universală.

## 1.11. Criterii de succes

| Domeniu | Criteriu |
| --- | --- |
| Formal | definiții fără ambiguități |
| Matematic | ipoteze și demonstrații explicitate |
| Numeric | erori și conservarea normei documentate |
| Software | cod și configurație trasabile |
| HPC | CSR/SpMV și cost în funcție de NNZ |
| Scalare | $q$ și $N=2^q$ consecvente |
| Reproductibilitate | protocol și parametri fixați |
| Experimental | rezultate efectiv măsurate, fără extrapolare |
| Științific | separarea rezultatelor proprii de literatură |

## 1.12. Figuri obligatorii

### Figura 1.1 — Arhitectura stratificată QFLPN

Trebuie să conțină explicit cele trei niveluri:

```text
Structură Petri
      ↓
Activare fuzzy
      ↓
Interfață fuzzy–cuantică
      ↓
Stare în Hilbert / matrice densitate
      ↓
Operatori locali și globali
      ↓
Evoluție QFLPN
```

### Figura 1.2 — Fluxul metodologic

```text
Problemă
   ↓
Literatură
   ↓
Formalizare
   ↓
Analiză matematică
   ↓
Algoritmi
   ↓
Implementare
   ↓
Validare
   ↓
Rezultate
   ↓
Publicații
```

### Figura 1.3 — Lanțul de trasabilitate

```text
Obiectiv
   ↓
Definiție / ipoteză
   ↓
Ecuație
   ↓
Algoritm
   ↓
Fișier sursă
   ↓
Experiment
   ↓
Metrică
   ↓
Rezultat
```

## 1.13. Tabele obligatorii

- obiective și evidențe;
- contribuții și natură;
- notații;
- scala $q/N$;
- obiective–metode–metrici;
- trasabilitate model–software–experiment.

## 1.14. Poziționarea științifică

Teza nu revendică înlocuirea tuturor formalismelor Petri, fuzzy sau cuantice.
Contribuția este un cadru QFLPN explicit, auditabil și implementabil, în care
interfețele dintre niveluri sunt declarate matematic și verificate independent.

## 1.15. Criteriu de închidere

Capitolul este închis când:

- problema și întrebarea de cercetare sunt formulate fără ambiguități;
- O1–O10 sunt trasabile;
- C1–C10 sunt delimitate de fundamentele bibliografice;
- notația este identică cu cea din capitolele 2–6;
- scala $N=2^q$ este utilizată consecvent;
- figurile și tabelele sunt definite;
- niciun rezultat experimental nu este prezentat fără dovadă corespunzătoare.
