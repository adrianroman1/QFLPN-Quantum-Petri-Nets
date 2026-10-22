# P3 — RAPORT DE AUDIT TEHNIC

## 1. Identificarea proiectului

**Proiect:** QFLPN — Quantum-Fuzzy Logical Petri Nets  
**Componentă:** P3 — Sparse Quantum-Fuzzy Logical Petri Nets: CSR/SpMV Algorithms and Large-Scale State Evolution  
**Repository:** `adrianroman1/QFLPN-Quantum-Petri-Nets`  
**Branch auditat:** `main`  
**Data documentului:** 2026-10-22

Acest raport separă explicit:
- existența implementării;
- rezultatele testelor;
- rezultatele CI;
- măsurătorile experimentale;
- validarea independentă;
- acceptarea finală.

Prezența unui fișier în repository nu demonstrează că acesta a fost executat cu succes.

## 2. Domeniul auditului

Auditul P3 acoperă:

1. reprezentarea matricelor în format CSR;
2. înmulțirea secvențială sparse matrix-vector (SpMV);
3. înmulțirea paralelă SpMV;
4. decompoziția Fork/Join;
5. matrice dreptunghiulare;
6. corectitudinea numerică;
7. benchmarkul Java;
8. scrierea și citirea rezultatelor CSV;
9. validarea independentă Python;
10. testele automate;
11. workflow-ul GitHub Actions;
12. proveniența rezultatelor;
13. reproducibilitatea experimentelor;
14. alinierea manuscris–cod–teste–rezultate;
15. integritatea artefactelor prin SHA-256.

## 3. Reguli de clasificare a dovezilor

Se folosesc următoarele stări:

| Stare | Semnificație |
|---|---|
| IMPLEMENTED | Codul sau documentul există |
| TESTED | Testul a fost executat și rezultatul este disponibil |
| CI PASS | Workflow-ul a trecut pe commitul identificat |
| EXPERIMENT PASS | Benchmarkul a fost executat și verificat independent |
| PENDING | Există o verificare necesară, dar fără dovadă suficientă |
| OPEN | Criteriul nu este încă demonstrat |
| BLOCKED | Există o eroare confirmată care împiedică validarea |
| ACCEPTED | Toate criteriile obligatorii au dovezi complete |

Un rezultat istoric nu este considerat automat rezultat al versiunii curente.

Un rezultat CI este valabil numai pentru commitul pe care a fost executat.

Un rezultat de benchmark este valabil numai pentru configurația și mediul în care a fost măsurat.

## 4. Structura Maven și configurația tehnică

Proiectul P3 utilizează:

- Java release 21;
- Maven;
- JUnit 5;
- Python 3;
- pytest.

Configurația Maven din `P3/pom.xml` declară:

```text
sourceDirectory      = P3/code
testSourceDirectory  = P3/tests
Java release         = 21
JUnit Jupiter        = 5.10.2
