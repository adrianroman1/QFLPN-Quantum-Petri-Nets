# P3 — ACCEPTANCE CHECKLIST
## Lista oficială de verificare pentru acceptarea P3

## 1. Regula de acceptare

P3 poate fi declarat `P3_ACCEPTED` numai dacă toate criteriile obligatorii sunt îndeplinite și susținute de dovezi verificabile.

Nu se acordă acceptarea pe baza:
- existenței codului;
- testelor istorice;
- unui singur test izolat;
- unui benchmark fără validare independentă;
- unui workflow executat pe alt commit;
- unui raport completat manual fără artefacte.

## 2. Identificarea versiunii finale

- [ ] Repository identificat: `adrianroman1/QFLPN-Quantum-Petri-Nets`
- [ ] Branch final identificat.
- [ ] Commit SHA final înregistrat.
- [ ] Working tree curat sau modificările locale documentate.
- [ ] Toate dovezile aparțin aceleiași versiuni.
- [ ] Data validării înregistrată.
- [ ] Versiunea Java înregistrată.
- [ ] Versiunea Maven înregistrată.
- [ ] Versiunea Python înregistrată.

Dovadă obligatorie: commit SHA și raportul mediului de execuție.

## 3. Build și compilare

- [ ] `mvn -B -f pom.xml validate` — PASS
- [ ] `mvn -B -f pom.xml clean test` — PASS
- [ ] `mvn -B -f P3/pom.xml validate` — PASS
- [ ] `mvn -B -f P3/pom.xml clean test` — PASS
- [ ] Compilare Java 21 reușită.
- [ ] Nu există erori de compilare.
- [ ] Nu există teste eșuate.
- [ ] Rapoartele Surefire sunt păstrate.

Dovadă obligatorie: logurile Maven și rapoartele JUnit.

## 4. Corectitudinea CSR

- [ ] `rowPointers` are dimensiunea corectă.
- [ ] Primul pointer este zero.
- [ ] Pointerii sunt monoton crescători.
- [ ] Ultimul pointer corespunde numărului de valori.
- [ ] Lungimea `values` este egală cu lungimea `columnIndices`.
- [ ] Indicii de coloană sunt validați.
- [ ] Valorile numerice sunt finite.
- [ ] Sunt testate rândurile goale.
- [ ] Sunt testate matricile dreptunghiulare.
- [ ] Sunt testate dimensiunile incompatibile.
- [ ] Există comparație cu un oracol dens independent.
- [ ] Rezultatele SpMV sunt numeric corecte.

Dovadă obligatorie: teste Java executate și raport JUnit.

## 5. Corectitudinea paralelizării

- [ ] Decompoziția Fork/Join acoperă toate rândurile.
- [ ] Nu există suprapuneri incorecte între intervale.
- [ ] Nu există rânduri omise.
- [ ] Cazurile de matrice dreptunghiulară sunt acoperite.
- [ ] Testul de regresie D01 trece.
- [ ] Rezultatul paralel corespunde rezultatului secvențial.
- [ ] Configurația de parallelism este înregistrată.

Dovadă obligatorie: testele Fork/Join și rezultatul CI pe commitul final.

## 6. Validarea numerică

- [ ] Toleranța este documentată.
- [ ] Erorile sunt finite.
- [ ] Erorile nu sunt negative.
- [ ] Eroarea secvențială respectă toleranța.
- [ ] Eroarea paralelă respectă toleranța.
- [ ] Diferența absolută maximă respectă toleranța.
- [ ] Valorile NaN sunt respinse.
- [ ] Valorile infinite sunt respinse.
- [ ] Timpii nuli sau negativi sunt respinși.
- [ ] Speedup-ul este recalculat independent.
- [ ] Throughput-ul este recalculat independent.

Dovadă obligatorie: teste Java și Python executate.

## 7. Validatorul Python

- [ ] `P3/results/validate_benchmark.py` există.
- [ ] `P3/results/test_validate_benchmark.py` există.
- [ ] Schema CSV este definită de `EXPECTED_HEADER`.
- [ ] Antetul CSV este verificat exact.
- [ ] Coloanele lipsă sunt respinse.
- [ ] Coloanele suplimentare sunt respinse.
- [ ] Erorile numerice negative sunt respinse.
- [ ] Valorile nenumerice invalide sunt respinse.
- [ ] Configurația poate fi verificată explicit.
- [ ] Numărul de înregistrări poate fi verificat.
- [ ] Raportul JSON este generat.
- [ ] Testele pytest trec integral.

Dovadă obligatorie: log pytest și raport JSON.

## 8. Benchmarkul

Configurație obligatorie:

- [ ] N = 1.000.000
- [ ] NNZ = 2.000.000
- [ ] Warm-up = 5
- [ ] Iterații măsurate = 10
- [ ] Threshold = 4096
- [ ] Parallelism = 2
- [ ] Toleranță = 1.0e-12

Verificări:

- [ ] Argumentele CLI sunt acceptate de runnerul Java.
- [ ] Valorile efective corespund configurației solicitate.
- [ ] CSV-ul are schema autoritativă.
- [ ] Exact un rând nou a fost adăugat.
- [ ] Rândul nou este valid.
- [ ] Toate înregistrările istorice păstrate sunt valide.
- [ ] Timpii sunt pozitivi și finiți.
- [ ] Speedup-ul este consistent.
- [ ] Throughput-ul este consistent.
- [ ] Eroarea numerică respectă toleranța.

Dovadă obligatorie: CSV și logul complet al benchmarkului.

## 9. Reproductibilitate și mediu

- [ ] RUN_ID unic.
- [ ] Commit SHA înregistrat.
- [ ] Timestamp UTC înregistrat.
- [ ] Versiunea Java înregistrată.
- [ ] Versiunea Maven înregistrată.
- [ ] Versiunea Python înregistrată.
- [ ] Sistemul de operare înregistrat.
- [ ] CPU documentat.
- [ ] Metadatele de memorie sunt documentate.
- [ ] Logul complet este păstrat.
- [ ] Mediul este păstrat.
- [ ] Raportul validatorului este păstrat.

Dovadă obligatorie: directorul `P3/results/raw/<RUN_ID>/`.

## 10. Integritatea artefactelor

- [ ] CSV inclus în checksum.
- [ ] Log inclus în checksum.
- [ ] Raportul de mediu inclus în checksum.
- [ ] Raportul JSON inclus în checksum.
- [ ] Fișierul SHA256SUMS este prezent.
- [ ] `sha256sum -c` trece integral.
- [ ] Nu au fost modificate artefactele după calcularea checksum-urilor.
- [ ] Manifestul global este sincronizat cu fișierele finale.

Dovadă obligatorie: logul verificării SHA-256.

## 11. GitHub Actions

- [ ] Workflow-ul P3 există.
- [ ] Permisiunile sunt limitate la necesar.
- [ ] Checkout-ul nu persistă credențiale.
- [ ] JDK 21 este configurat.
- [ ] Testele Maven principale sunt executate.
- [ ] Testele Java P3 sunt executate.
- [ ] Testele Python sunt executate.
- [ ] Benchmarkul manual este disponibil.
- [ ] Artefactele JUnit sunt încărcate.
- [ ] Artefactele benchmarkului sunt încărcate.
- [ ] Runul final este `completed`.
- [ ] Conclusion este `success`.
- [ ] Commitul CI este commitul final.

Dovadă obligatorie: run ID, commit SHA și logurile jobului.

## 12. Alinierea documentară

- [ ] `P3/P3_AUDIT_REPORT.md` reflectă codul actual.
- [ ] `P3/VALIDATION_ALIGNMENT.md` reflectă codul și schema CSV actuale.
- [ ] `P3/VALIDATION_PROTOCOL.md` descrie pașii reali.
- [ ] `P3/ACCEPTANCE_CHECKLIST.md` conține criteriile obligatorii.
- [ ] `P3/MANIFEST.txt` reflectă structura reală.
- [ ] `P3/results/Results.md` este aliniat cu datele experimentale.
- [ ] `P3/results/Reproducibility.md` este aliniat cu execuția reală.
- [ ] `P3/results/Traceability.md` leagă afirmațiile de implementare și teste.
- [ ] Rezultatele istorice sunt diferențiate de rezultatele noi.
- [ ] Nu există valori experimentale inventate.
- [ ] Nu există contradicții între numărul de coloane CSV și manifest.

## 13. Reconcilierea copiilor de cod

- [ ] Toate copiile Java relevante au fost inventariate.
- [ ] Rolul fiecărei copii este documentat.
- [ ] Copiile care trebuie să fie identice au fost comparate integral.
- [ ] Diferențele sunt remediate sau justificate.
- [ ] Maven compilează sursele declarate.
- [ ] Nu există surse vechi prezentate ca implementare activă.
- [ ] Nicio copie nu a fost ștearsă fără analiză.

Dovadă obligatorie: tabel cu căi, SHA-256 și rezultat de comparație.

## 14. Verdict final

Se completează numai după obținerea dovezilor.

| Domeniu | Verdict | Referință dovadă |
|---|---|---|
| Build principal | PENDING | |
| Teste principale | PENDING | |
| Build P3 | PENDING | |
| Teste Java P3 | PENDING | |
| Teste Python | PENDING | |
| CSR și SpMV | PENDING | |
| Fork/Join | PENDING | |
| Benchmark 5/10 | PENDING | |
| Validare independentă | PENDING | |
| Reproductibilitate | PENDING | |
| SHA-256 | PENDING | |
| CI final | PENDING | |
| Documentație | PENDING | |
| Copii de cod | PENDING | |

Valori permise pentru verdict:

- `PASS`
- `FAIL`
- `PENDING`
- `NOT APPLICABLE`

Nu se completează PASS fără dovadă.

## 15. Decizia de acceptare

**P3_ACCEPTED = TRUE** numai dacă toate criteriile obligatorii sunt PASS.

Dacă cel puțin un criteriu obligatoriu este FAIL sau PENDING:

**P3_ACCEPTED = FALSE**

Verdictul actual, înaintea validării finale:

**P3_ACCEPTED — NOT GRANTED.**

Data acceptării: ____________________

Commit SHA acceptat: ____________________

Run ID CI: ____________________

RUN_ID benchmark: ____________________

Responsabil validare: ____________________
