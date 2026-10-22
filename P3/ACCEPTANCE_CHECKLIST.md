# QFLPN P3 — ACCEPTANCE CHECKLIST
## Lista oficială de acceptare tehnică și experimentală

---

# 1. Regula de acceptare

Verdictul `P3_ACCEPTED` se acordă numai după demonstrarea tuturor criteriilor obligatorii.

Nu sunt suficiente:

- existența fișierelor;
- existența testelor;
- un workflow definit, dar neexecutat;
- un benchmark fără validare;
- un manifest fără hash-uri;
- hash-uri introduse manual;
- rezultate istorice;
- rezultate provenite din commituri diferite.

P1 și P2 reprezintă modelele de referință pentru automatizarea benchmarkurilor, generarea inventarelor și păstrarea dovezilor.

P3 trebuie să respecte același nivel de trasabilitate.

# 2. Identificarea versiunii finale

- [ ] Repository confirmat.
- [ ] Branch final identificat.
- [ ] Commit SHA complet înregistrat.
- [ ] Working tree curat sau modificările documentate.
- [ ] Toate testele aparțin aceluiași commit.
- [ ] Workflow run ID înregistrat.
- [ ] Benchmark RUN_ID înregistrat.
- [ ] Data validării înregistrată.

Dovezi:

- commit SHA;
- URL commit;
- URL workflow;
- identificator benchmark.

# 3. Build și compilare

- [ ] `mvn -B -f pom.xml validate` — PASS.
- [ ] `mvn -B -f pom.xml clean test` — PASS.
- [ ] `mvn -B -f P3/pom.xml validate` — PASS.
- [ ] `mvn -B -f P3/pom.xml clean test` — PASS.
- [ ] JDK 21 utilizat.
- [ ] Compilare fără erori.
- [ ] Zero teste eșuate.
- [ ] Rapoarte Surefire păstrate.

Dovezi:

- log Maven;
- rapoarte JUnit;
- versiunea JDK;
- commitul testat.

# 4. Reprezentarea CSR

- [ ] `rowPointers.length == rows + 1`.
- [ ] Primul pointer este zero.
- [ ] Pointerii sunt monoton crescători.
- [ ] Ultimul pointer este egal cu numărul elementelor nenule.
- [ ] Lungimea `values` este egală cu lungimea `columnIndices`.
- [ ] Indicii de coloană sunt în limite.
- [ ] Dimensiunile sunt validate.
- [ ] Rândurile goale sunt testate.
- [ ] Matricele dreptunghiulare sunt testate.
- [ ] Matricea goală este testată.
- [ ] Valorile NaN sunt tratate conform contractului.
- [ ] Valorile infinite sunt tratate conform contractului.

Dovadă: teste Java executate și rapoarte JUnit.

# 5. SpMV secvențial

- [ ] Implementarea respectă reprezentarea CSR.
- [ ] Dimensiunile matricei și vectorului sunt verificate.
- [ ] Există oracol dens independent.
- [ ] Testele compară rezultatul cu oracolul.
- [ ] Toleranța numerică este documentată.
- [ ] Rezultatul respectă toleranța.
- [ ] Cazurile-limită sunt acoperite.
- [ ] Intrările invalide sunt tratate.

Dovadă: teste automate și loguri.

# 6. SpMV paralel

- [ ] Toate rândurile sunt procesate.
- [ ] Nu există rânduri omise.
- [ ] Nu există suprapuneri incorecte.
- [ ] Rezultatul este comparat cu implementarea secvențială.
- [ ] Rezultatul este comparat cu oracolul dens.
- [ ] Sunt testate matricele dreptunghiulare.
- [ ] Sunt testate matricele cu rânduri goale.
- [ ] Parametrii paralelizării sunt validați.
- [ ] Testele de concurență sunt executate.

Dovadă: teste Java și rapoarte.

# 7. Teste Python

- [ ] Validatorul benchmarkului este testat.
- [ ] Generatorul manifestului este testat.
- [ ] Verificatorul manifestului este testat.
- [ ] Generatorul SHA256SUMS este testat.
- [ ] Verificatorul SHA256SUMS este testat.
- [ ] Hash invalid respins.
- [ ] Cale absolută respinsă.
- [ ] Cale cu `..` respinsă.
- [ ] Duplicate respinse.
- [ ] Fișiere lipsă detectate.
- [ ] Fișiere suplimentare detectate.
- [ ] Linkuri simbolice tratate conform politicii.
- [ ] Modificările după generare sunt detectate.
- [ ] Cache-urile sunt excluse conform politicii.
- [ ] Testele folosesc fixture-uri temporare.

Dovadă: raport pytest.

# 8. Benchmark P3

Configurația solicitată:

| Parametru | Valoare |
|---|---:|
| N | 1.000.000 |
| NNZ | 2.000.000 |
| Warm-up | 5 |
| Iterații | 10 |
| Threshold | 4096 |
| Parallelism | 2 |
| Toleranță | 1e-12 |

- [ ] Benchmarkul a fost executat.
- [ ] Execuția aparține commitului final.
- [ ] RUN_ID este unic.
- [ ] Parametrii au fost transmiși efectiv.
- [ ] Mediul a fost înregistrat.
- [ ] CSV-ul istoric a fost validat.
- [ ] Exact un rând nou a fost produs.
- [ ] CSV-ul complet a fost validat.
- [ ] Ultimul rând a fost extras.
- [ ] Ultimul rând a fost validat separat.
- [ ] Configurația raportată corespunde configurației cerute.
- [ ] Rezultatele numerice respectă toleranța.
- [ ] Timpii sunt finiți și pozitivi.
- [ ] Speedup-ul și throughput-ul sunt validați conform schemei.
- [ ] Raportul JSON există.
- [ ] Logul benchmarkului există.
- [ ] Environment există.

Dovezi:

- CSV;
- raport JSON;
- log;
- environment;
- RUN_ID;
- commit SHA.

# 9. Automatizarea benchmarkurilor P1/P2/P3

## P1

- [ ] Workflow-ul P1 rulează benchmarkul.
- [ ] Configurația este 5 warm-ups și 30 de repetări.
- [ ] Rezultatele sunt păstrate în `P1/benchmarks/`.
- [ ] Rezumatul benchmarkului este generat.
- [ ] Artefactele sunt încărcate.
- [ ] Eșecul benchmarkului este raportat distinct de validarea matematică.

## P2

- [ ] Workflow-ul P2 rulează benchmarkul din configurația JSON.
- [ ] Configurația are 5 warm-ups și 30 de repetări.
- [ ] Rezultatele JSON/CSV/Markdown/environment sunt generate.
- [ ] Validatorul benchmarkului este executat.
- [ ] Rezumatul benchmarkului este publicat.
- [ ] Artefactele sunt încărcate.
- [ ] Commitul automat este condiționat de succesul benchmarkului și al validatorului.

## P3

- [ ] Workflow-ul are `workflow_dispatch`.
- [ ] Benchmarkul se execută prin `P3/results/run_benchmark.sh`.
- [ ] Parametrii sunt transmiși explicit.
- [ ] Rezultatele CSV sunt validate.
- [ ] Dovezile run-specific sunt generate.
- [ ] Checksum-urile run-specific sunt verificate.
- [ ] Artefactele benchmarkului sunt încărcate.
- [ ] Commitul automat este configurat sau este documentat explicit ca neactiv.
- [ ] Manifestul global este generat și verificat.
- [ ] SHA256SUMS global este generat și verificat.

Dovadă: workflow run și artefactele sale.

# 10. Manifest global P3

- [ ] `P3/MANIFEST.txt` există.
- [ ] Este generat automat.
- [ ] Conține hash și cale relativă.
- [ ] Căile sunt sortate.
- [ ] Nu există duplicate.
- [ ] Nu există căi absolute.
- [ ] Nu există `..`.
- [ ] Fișierele autoreferențiale sunt excluse.
- [ ] Politica de excludere este documentată.
- [ ] Fișierele eligibile lipsă sunt detectate.
- [ ] Fișierele suplimentare sunt detectate.
- [ ] Inventarul nu este gol.
- [ ] Verificatorul independent raportează PASS.

Dovadă: manifest și logul verificatorului.

# 11. SHA256SUMS P3

- [ ] `P3/SHA256SUMS.txt` există.
- [ ] Este generat automat.
- [ ] Hash-urile sunt SHA-256 valide.
- [ ] Intrările corespund inventarului.
- [ ] Nu există duplicate.
- [ ] Nu există intrări autoreferențiale.
- [ ] Fișierele modificate sunt detectate.
- [ ] Fișierele lipsă sunt detectate.
- [ ] Verificarea independentă raportează PASS.

Dovadă: SHA256SUMS și logul verificării.

# 12. GitHub Actions

- [ ] Workflow-ul P3 rulează la push.
- [ ] Workflow-ul P3 rulează la pull request.
- [ ] Workflow-ul P3 poate fi declanșat prin `workflow_dispatch`.
- [ ] Maven principal este validat.
- [ ] Testele principale sunt executate.
- [ ] Maven P3 este validat.
- [ ] Testele Java P3 sunt executate.
- [ ] Testele Python sunt executate.
- [ ] Benchmarkul este executat la dispatch.
- [ ] Rezultatele benchmarkului sunt validate.
- [ ] Manifestul este generat.
- [ ] SHA256SUMS este generat.
- [ ] Integritatea este verificată.
- [ ] Artefactele sunt încărcate.
- [ ] Rezumatul workflow-ului este publicat.
- [ ] Nu există etape obligatorii ignorate.

Dovadă: GitHub Actions run cu toate joburile și pașii.

# 13. Commit automat și permisiuni

- [ ] Este documentat dacă P3 folosește commit automat.
- [ ] Dacă da, `contents: write` este configurat.
- [ ] Checkout-ul păstrează credențialele necesare.
- [ ] Identitatea botului este configurată.
- [ ] Pull request-urile sunt excluse din commit automat.
- [ ] Sunt comise numai fișierele generate aprobate.
- [ ] Commitul automat se execută numai după succes.
- [ ] Nu se generează bucle de workflow.

Dacă nu există drepturi de scriere, artefactele trebuie păstrate fără a pretinde că au fost comise.

# 14. Corelarea documentației

- [ ] `P3/P3_AUDIT_REPORT.md` reflectă implementarea reală.
- [ ] `P3/VALIDATION_PROTOCOL.md` descrie comenzile reale.
- [ ] `P3/ACCEPTANCE_CHECKLIST.md` conține toate porțile obligatorii.
- [ ] Parametrii benchmarkului sunt consecvenți.
- [ ] Politica de integritate este consecventă.
- [ ] Locațiile artefactelor sunt consecvente.
- [ ] Nu există rezultate inventate.
- [ ] Nu există PASS fără dovadă.

# 15. Verdict final

Completează numai după validarea efectivă:

```text
P3_ACCEPTED:
FINAL_COMMIT_SHA:
CI_RUN_ID:
BENCHMARK_RUN_ID:
JAVA_TESTS:
PYTHON_TESTS:
CSR_VALIDATION:
SEQUENTIAL_SPMV:
PARALLEL_SPMV:
BENCHMARK:
MANIFEST:
SHA256:
ARTIFACTS:
DOCUMENTATION:
ACCEPTANCE_DATE:
```

Reguli:

- toate porțile obligatorii PASS → `P3_ACCEPTED`;
- orice criteriu PENDING → acceptare neacordată;
- orice criteriu FAIL → `P3_REJECTED`.

Nu se acordă nota 10 și nu se declară acceptarea înainte de verificarea tuturor dovezilor pe același commit.
