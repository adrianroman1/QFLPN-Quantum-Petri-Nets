# 04. Analiza matematică

## 1. Rolul capitolului

Acest capitol fixează cadrul matematic necesar pentru analiza QFLPN, pentru evoluția operatorială și pentru metodele numerice utilizate în capitolele 5 și 6. Rezultatele teoretice sunt separate explicit de observațiile experimentale.

Principiul de redactare este: **definiție → ipoteze → propoziție/teoremă → demonstrație sau justificare → consecință algoritmică → verificare experimentală**.

## 2. Convenții fundamentale

Pentru un sistem cu `q` qubiți se utilizează

$$
\mathcal H_q=(\mathbb C^2)^{\otimes q},
\qquad
N=\dim(\mathcal H_q)=2^q.
$$

Prin urmare, pentru reprezentarea completă a stării cuantice, `q` și `N` nu sunt parametri independenți.

| q | N = 2^q |
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

Dimensiunile HPC precum `10^6`, `5·10^6`, `10^7` și `3·10^7`, atunci când sunt utilizate, reprezintă volume de lucru sau dimensiuni ale structurilor sparse și nu trebuie prezentate ca dimensiuni Hilbert pentru `q` qubiți.

## 3. Spațiul Hilbert și norma

Pentru `x,y ∈ H_q`, produsul scalar este

$$
\langle x,y\rangle=x^*y,
$$

iar norma euclidiană este

$$
\|x\|_2=\sqrt{\langle x,x\rangle}.
$$

Norma indusă a unui operator este

$$
\|A\|_2=\sup_{x\ne0}\frac{\|Ax\|_2}{\|x\|_2}.
$$

Se utilizează proprietatea

$$
\|AB\|\leq\|A\|\,\|B\|.
$$

## 4. Operatori liniari și unitari

Un operator `A` este liniar dacă

$$
A(\alpha x+\beta y)=\alpha Ax+\beta Ay.
$$

Un operator `U` este unitar dacă

$$
U^*U=UU^*=I.
$$

**Propoziție 4.1.** Dacă `U` este unitar, atunci conservă norma.

**Demonstrație.**

$$
\|Ux\|_2^2
=\langle Ux,Ux\rangle
=\langle x,U^*Ux\rangle
=\langle x,x\rangle
=\|x\|_2^2.
$$

Această proprietate constituie un invariant numeric pentru implementările unitare.

## 5. Convenția tensorială

Se fixează convenția documentară

$$
|q_0q_1\ldots q_{q-1}\rangle
=
|q_0\rangle\otimes|q_1\rangle\otimes\cdots\otimes|q_{q-1}\rangle.
$$

Pentru patru qubiți:

$$
\mathcal H_4=(\mathbb C^2)^{\otimes4}.
$$

Operatorii locali sunt ridicați în spațiul global prin

$$
\widetilde U_i
=
I_2^{\otimes i}\otimes U_i\otimes I_2^{\otimes(q-i-1)}.
$$

Pentru operații independente, convenția globală este

$$
U=U_0\otimes U_1\otimes\cdots\otimes U_{q-1}.
$$

Dacă o implementare utilizează little-endian, conversia este tratată ca o permutare explicită și nu modifică definiția matematică de mai sus.

## 6. Evoluția liniară

Problema de evoluție este

$$
\frac{d}{dt}x(t)=Ax(t),
\qquad x(0)=x_0.
$$

Soluția este

$$
x(t)=e^{tA}x_0.
$$

În calculul numeric trebuie distinsă matricea completă `e^{tA}` de acțiunea ei asupra unui vector:

$$
y=e^{tA}v.
$$

Pentru dimensiuni mari, a doua problemă este obiectivul algoritmic principal.

## 7. Exponențiala de operator

Pentru un operator liniar mărginit,

$$
e^A=\sum_{k=0}^{\infty}\frac{A^k}{k!}.
$$

Pentru `tA`:

$$
e^{tA}=\sum_{k=0}^{\infty}\frac{t^kA^k}{k!}.
$$

Din submultiplicativitate,

$$
\left\|\frac{A^k}{k!}\right\|
\leq\frac{\|A\|^k}{k!},
$$

iar seria scalară majorantă este convergentă.

## 8. Aproximarea Taylor

Trunchierea de ordin `m` a acțiunii exponențialei este

$$
T_m(tA)v
=
\sum_{k=0}^{m}\frac{t^kA^kv}{k!}.
$$

Restul este

$$
R_{m+1}(tA)v
=
\sum_{k=m+1}^{\infty}\frac{t^kA^kv}{k!}.
$$

O bornă generică este

$$
\|R_{m+1}(tA)v\|_2
\leq
\|v\|_2
\sum_{k=m+1}^{\infty}\frac{(|t|\|A\|_2)^k}{k!}.
$$

Aceasta este o bornă teoretică și nu este identică cu eroarea numerică măsurată.

### 8.1. Taylor scalat

Pentru `s` subpași,

$$
 e^{tA}v=
\left(e^{(t/s)A}\right)^s v.
$$

Scalarea reduce argumentul local al seriei, dar crește numărul de aplicări ale operatorului și poate crește acumularea erorii de rotunjire.

## 9. Subspațiul Krylov

Se definește

$$
\mathcal K_m(A,v)=
\operatorname{span}\{v,Av,A^2v,\ldots,A^{m-1}v\}.
$$

Dacă `m << N`, problema poate fi redusă la o reprezentare de dimensiune `m`.

## 10. Arnoldi

Baza ortonormală este

$$
V_m=[v_1,\ldots,v_m],
$$

iar relația Arnoldi este

$$
AV_m=V_mH_m+h_{m+1,m}v_{m+1}e_m^T.
$$

Aproximarea standard este

$$
 e^{tA}v
\approx
\|v\|_2V_me^{tH_m}e_1.
$$

Dimensiunea matricei reduse este `m × m`, nu `N × N`.

## 11. Ortogonalizarea

În aritmetică flotantă, ortogonalitatea poate fi pierdută. Modified Gram-Schmidt este exprimat prin

$$
 h_{ij}=\langle v_i,w\rangle,
\qquad
w\leftarrow w-h_{ij}v_i.
$$

Reortogonalizarea poate fi aplicată pentru reducerea pierderii de ortogonalitate.

Un indicator util este

$$
E_{\mathrm{orth}}=\|V_m^*V_m-I_m\|.
$$

## 12. Principiul contracției Banach

Fie `(X,d)` un spațiu metric complet și `T:X→X`. Dacă există `0≤c<1` astfel încât

$$
d(Tx,Ty)\leq c\,d(x,y),
$$

atunci `T` are un unic punct fix.

**Consecință importantă:** acest rezultat nu demonstrează automat lipsa deadlock-ului într-o rețea Petri. Deadlock-freedom este o proprietate separată, care necesită o demonstrație structurală sau un invariant adecvat.

## 13. Analiza spectrală

Dacă

$$
A=V\Lambda V^{-1},
$$

atunci

$$
 e^{tA}=Ve^{t\Lambda}V^{-1}.
$$

Pentru operatori normali, diagonalizarea poate fi realizată printr-o bază ortonormală. Analiza spectrală este utilizată pentru interpretare și pentru justificarea unor metode, nu ca substitut pentru măsurarea performanței.

## 14. Calcul funcțional

Pentru o funcție analitică `f` și un contur `Γ` care înconjoară spectrul,

$$
 f(A)=\frac{1}{2\pi i}\oint_\Gamma f(z)(zI-A)^{-1}\,dz.
$$

Formula este păstrată ca instrument teoretic. O metodă de contur poate fi declarată metodă experimentală numai dacă este implementată și evaluată prin același protocol ca metodele de comparație.

## 15. CSR și SpMV

Pentru un operator rar `A`, produsul

$$
 w=Av
$$

poate fi calculat în format CSR. Costul principal este proporțional cu

$$
O(\operatorname{NNZ}(A)).
$$

Memoria este, de asemenea, dominată de `NNZ`, de indicii CSR și de vectorii de lucru.

## 16. Complexitatea Arnoldi

O descriere de ordinul de mărime este

$$
C_{\mathrm{Arnoldi}}
=
O(mC_{\mathrm{SpMV}})+O(Nm^2)+C_{\mathrm{small}}(m).
$$

Primul termen corespunde produselor cu operatorul, al doilea ortogonalizării, iar ultimul operațiilor pe matricea redusă.

## 17. Erori numerice

Pentru rezultatul `y` și referința independentă `y^ref`:

$$
E_{\max}=\max_i|y_i-y_i^{\mathrm{ref}}|.
$$

Eroarea relativă:

$$
E_{\mathrm{rel}}
=
\frac{\|y-y^{\mathrm{ref}}\|_2}
{\max(\|y^{\mathrm{ref}}\|_2,\varepsilon)}.
$$

Conservarea normei:

$$
E_{\mathrm{norm}}
=|\|y\|_2-\|v\|_2|.
$$

## 18. Decompoziția erorii

Eroarea observată poate include mai multe contribuții:

$$
E_{\mathrm{total}}
\lesssim
E_{\mathrm{trunc}}
+E_{\mathrm{round}}
+E_{\mathrm{model}}
+E_{\mathrm{reference}}.
$$

Nu este justificată atribuirea integrală a erorii către trunchiere fără o analiză separată.

## 19. Scalare și memorie

În reprezentarea completă,

$$
N=2^q.
$$

Prin urmare, creșterea lui `q` produce creștere exponențială a numărului de amplitudini.

| Mărime | Dependență relevantă |
|---|---|
| starea densă | O(N) memorie |
| matrice densă | O(N²) memorie |
| SpMV sparse | O(NNZ) aritmetică aproximativă |
| baza Arnoldi | O(Nm) memorie |
| matricea redusă | O(m²) memorie |

## 20. Matricea de închidere matematică

| Componentă | Ecuație | Condiție | Verificare |
|---|---|---|---|
| Hilbert | `H_q=(C²)^⊗q` | q finit | q/N |
| Dimensiune | `N=2^q` | stare completă | tabel scalare |
| Unitaritate | `U*U=I` | U unitar | normă |
| Evoluție | `x(t)=e^{tA}x0` | A definit | algoritm |
| Taylor | `T_m(tA)v` | truncare | eroare |
| Krylov | `K_m(A,v)` | m≪N, dacă este eficient | timp/eroare |
| Arnoldi | `AV_m=V_mH_m+...` | ortogonalizare | rezidual |
| Banach | `d(Tx,Ty)≤cd(x,y)` | c<1 | analiză |
| CSR | `O(NNZ)` | A rară | profilare |
| Fidelitate | metrică de stare | stări valide | Capitolul 6 |

## 21. Figuri obligatorii

### Figura 4.1 — Arhitectura matematică QFLPN

**Tip:** diagramă vectorială finală.

**Conținut:** QFLPN → stare în `H_q` → operator `A/U` → `e^{tA}v` → observabile → metrici.

**Ecuații afișate:** `H_q=(C²)^⊗q`, `N=2^q`, `y=e^{tA}v`.

### Figura 4.2 — Reducerea Krylov

**Conținut:** vectorii `v,Av,...,A^{m-1}v`, baza `V_m`, proiecția către `H_m` și revenirea în spațiul original.

### Figura 4.3 — CSR–SpMV

**Conținut:** structurile `data`, `indices`, `indptr`, vectorul `v` și rezultatul `Av`.

### Figura 4.4 — Scalarea dimensională

**Conținut:** `q → N=2^q → NNZ/memorie → timp`.

## 22. Tabele obligatorii

1. Tabelul `q/N`.
2. Tabelul simbolurilor.
3. Tabelul metodelor și domeniilor de utilizare.
4. Tabelul complexităților.
5. Tabelul metricilor numerice.
6. Matricea de închidere matematică.
7. Tabelul trasabilității către cod și experimente.

## 23. Trasabilitate

| Element matematic | Implementare | Validare |
|---|---|---|
| `N=2^q` | generarea dimensiunii | Capitolul 6 |
| operator local | construcție tensorială | stare/operator |
| `e^{tA}v` | Taylor/Krylov | eroare |
| Arnoldi | baza `V_m`, `H_m` | eroare/rezidual |
| CSR | SpMV | timp și NNZ |
| unitaritate | operator U | eroare de normă |
| fidelitate | metrică de stare | Capitolul 6 |

## 24. Criteriu de închidere

Capitolul este considerat final numai când toate ecuațiile utilizate în capitolele 5–6 sunt definite, ipotezele sunt explicite, convenția tensorială este unică, figurile au specificații complete, iar afirmațiile teoretice nu sunt prezentate ca rezultate experimentale.
