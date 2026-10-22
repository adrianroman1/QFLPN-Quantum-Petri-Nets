# QFLPN P3 — RAPORT DE AUDIT TEHNIC
## Audit integrat, corelare P1/P2 și criterii de acceptare

**Proiect:** QFLPN — Quantum-Fuzzy Logical Petri Nets  
**Componentă:** P3 — Sparse Quantum-Fuzzy Logical Petri Nets  
**Repository:** adrianroman1/QFLPN-Quantum-Petri-Nets  
**Branch auditat:** main  
**Revizie documentară:** 2026-10-22

---

# 1. Obiectiv

Acest raport stabilește cerințele de audit și acceptare pentru P3.

Auditul trebuie să demonstreze concordanța dintre:

1. modelul matematic;
2. implementarea Java;
3. testele Java;
4. validatorul Python;
5. benchmark;
6. rezultatele experimentale;
7. manifest și SHA-256;
8. GitHub Actions;
9. documentația de reproductibilitate;
10. criteriile finale de acceptare.

Existența unui fișier nu reprezintă dovada funcționării sale.

Existența unui workflow nu reprezintă dovada executării sale.

Un rezultat istoric nu reprezintă automat dovada comportamentului commitului curent.

Toate criteriile obligatorii trebuie demonstrate pe aceeași versiune Git.

# 2. Corelarea P3 cu P1 și P2

## 2.1. Modelul P1

P1 folosește generatorul:

`P1/tools/compute_checksums.py`

Acesta generează:

- `P1/MANIFEST.txt`
- `P1/SHA256SUMS.txt`

Generatorul P1:

- inventariază fișierele eligibile din P1 și workflow-urile GitHub;
- sortează determinist căile;
- utilizează căi relative la repository;
- exclude manifestul și lista SHA autoreferențiale;
- exclude cache-uri și linkuri simbolice;
- calculează SHA-256 automat;
- folosește scriere atomică.

Workflow-ul P1:

- rulează validarea matematică;
- generează rapoarte;
- rulează benchmarkul;
- agregă rezultatele testelor;
- generează manifestul și checksum-urile;
- verifică pachetul final;
- publică rezumatul;
- încarcă artefactele;
- comite automat dovezile după succes.

Benchmarkul P1 este configurat cu 5 warm-up-uri și 30 de repetări.

Benchmarkul este tratat ca dovadă suplimentară de performanță. Eșecul său nu trebuie confundat cu eșecul validării matematice.

## 2.2. Modelul P2

P2 utilizează generatoare și verificatoare separate:

- `P2/tools/generate_manifest.py`
- `P2/tools/verify_sha256.py`
- `P2/tools/generate_sha256sums.py`
- `P2/tools/verify_sha256sums.py`

P2 are teste dedicate integrității și verificării inventarului.

Workflow-ul P2:

- compilează și testează codul;
- verifică configurația canonică;
- execută testele matematice;
- generează artefacte de referință;
- rulează benchmarkul;
- validează rezultatele benchmarkului;
- generează manifestul;
- verifică manifestul;
- generează SHA256SUMS;
- verifică lista completă;
- publică raportul;
- încarcă artefactele;
- comite dovezile numai după succesul etapelor cerute.

Configurația benchmarkului P2 include:

| Parametru | Valoare |
|---|---:|
| Warm-ups | 5 |
| Repetări | 30 |
| Toleranță numerică | 1e-12 |
| Timer | `time.perf_counter_ns` |

Benchmarkul P2 este suplimentar față de verdictul matematic. Workflow-ul condiționează commitul automat al dovezilor de succesul benchmarkului și al validării sale.

## 2.3. Situația P3

P3 are deja:

- `P3/results/run_benchmark.sh`
- `P3/results/validate_benchmark.py`
- `P3/results/test_validate_benchmark.py`
- `P3/benchmarks/benchmark_results.csv` ca destinație a runnerului;
- `P3/results/raw/<RUN_ID>/` pentru dovezile individuale;
- `.github/workflows/p3-validation.yml`.

Workflow-ul P3 utilizează:

- JDK 21;
- Python 3.12;
- Maven;
- pytest;
- benchmark la `workflow_dispatch`.

Configurația transmisă benchmarkului:

| Parametru | Valoare |
|---|---:|
| N | 1.000.000 |
| NNZ | 2.000.000 |
| Warm-up | 5 |
| Iterații | 10 |
| Threshold | 4096 |
| Parallelism | 2 |
| Toleranță | 1e-12 |

Runnerul verifică CSV-ul istoric, execută benchmarkul Java, cere exact un rând nou, validează toate înregistrările și validează separat ultima înregistrare cu parametrii solicitați.

Dovezile run-specific includ:

- `benchmark.log`;
- `environment.txt`;
- `validation-report.json`;
- `latest_benchmark_result.csv`;
- `SHA256SUMS.txt`.

Scriptul verifică SHA-256 prin `sha256sum -c`.

## 2.4. Diferențe care trebuie remediate în P3

P3 nu trebuie declarat echivalent cu P1/P2 înainte de următoarele remedieri:

1. Generatorul P3 trebuie să producă manifest cu hash și cale, nu doar listă de căi.
2. Trebuie eliminată eroarea de ordine a câmpurilor din generatorul 3M.
3. Trebuie implementată verificarea independentă a inventarului.
4. Trebuie verificate fișierele suplimentare, lipsă și duplicate.
5. Trebuie verificată politica de excludere.
6. Workflow-ul trebuie să păstreze și să publice toate dovezile.
7. Trebuie stabilit dacă P3 va comite automat dovezile, după modelul P1/P2.
8. Permisiunile GitHub trebuie configurate explicit dacă se dorește commit automat.

# 3. Arhitectura tehnică P3

## 3.1. CSR

Se verifică:

- dimensiunea `rowPointers`;
- valoarea inițială zero;
- monotonia pointerilor;
- ultimul pointer egal cu numărul elementelor nenule;
- egalitatea lungimilor `values` și `columnIndices`;
- indicii de coloană;
- dimensiunile matricei;
- rânduri goale;
- matrice dreptunghiulare;
- valori invalide.

## 3.2. SpMV secvențial

Se verifică:

- corectitudinea operației;
- compatibilitatea dimensiunilor;
- comparația cu un oracol dens independent;
- toleranța numerică;
- matrice goală;
- vectori invalizi.

## 3.3. SpMV paralel

Se verifică:

- acoperirea tuturor rândurilor;
- lipsa suprapunerilor incorecte;
- lipsa rândurilor omise;
- independența de ordinea taskurilor;
- concordanța cu implementarea secvențială;
- concordanța cu oracolul dens;
- comportamentul Fork/Join.

## 3.4. Benchmark

Benchmarkul trebuie să separe:

- validarea numerică;
- măsurarea timpului;
- speedup;
- throughput;
- configurarea execuției;
- proveniența rezultatelor;
- validarea CSV;
- calculul checksum-urilor.

Performanța nu poate compensa o eroare de corectitudine numerică.

# 4. Contractul de integritate P3

Locația canonică:

```text
P3/
├── MANIFEST.txt
└── SHA256SUMS.txt
```

Nu se creează o a doua pereche redundantă în rădăcina generală a repository-ului.

## 4.1. Manifest

Manifestul trebuie să conțină:

- hash SHA-256;
- cale relativă;
- ordine deterministă;
- intrări unice;
- număr verificabil de fișiere.

Formatul recomandat:

```text
<sha256>  <relative/path>
```

## 4.2. SHA256SUMS

Lista SHA-256 trebuie generată automat.

Nu se introduc hash-uri manual.

Manifestul și lista SHA trebuie să fie construite din același inventar logic.

Fișierele autoreferențiale trebuie excluse.

## 4.3. Verificare strictă

Verificatorul trebuie să respingă:

- hash invalid;
- cale absolută;
- secvență `..`;
- cale duplicată;
- fișier lipsă;
- fișier suplimentar eligibil;
- fișier modificat;
- link simbolic;
- fișier care nu este regulat;
- inventar gol;
- număr incorect de intrări.

Generatorul și verificatorul trebuie să utilizeze aceeași politică documentată de inventariere.

## 4.4. Excluderi și rezultate benchmark

Nu se exclude întregul director `results/` fără o justificare tehnică.

Dacă rezultatele volatile sunt excluse din inventarul global, ele trebuie acoperite de checksum-urile run-specific.

Dovezile benchmarkului trebuie să fie verificabile chiar dacă nu sunt incluse în manifestul global.

# 5. GitHub Actions

Workflow-ul P3 trebuie să păstreze următoarea ordine logică:

1. checkout;
2. configurare JDK;
3. configurare Python;
4. instalare dependențe;
5. validare Maven principală;
6. teste Maven principale;
7. validare Maven P3;
8. teste Java P3;
9. teste Python;
10. validare numerică;
11. benchmark la `workflow_dispatch`;
12. validare benchmark;
13. generare dovezi;
14. generare manifest;
15. verificare manifest;
16. generare SHA256SUMS;
17. verificare SHA256SUMS;
18. publicare rezumat;
19. încărcare artefacte;
20. commit automat, numai dacă este configurat și permis.

## 5.1. Permisiuni

Workflow-ul actual P3 are:

`permissions: contents: read`

Aceasta nu permite commit automat în branch.

Dacă P3 trebuie să adopte modelul P1/P2, sunt necesare:

- `contents: write`;
- checkout cu credențiale persistente;
- identitate GitHub Actions bot;
- condiții stricte pentru commit;
- excluderea pull request-urilor din commitul automat;
- evitarea buclelor de workflow.

Dacă drepturile nu sunt disponibile, artefactele trebuie încărcate fără a pretinde că au fost comise.

# 6. Defecte identificate în 3M

## D01 — Formatul manifestului

Generatorul 3M actual produce numai căi, nu perechi hash/cale.

**Remediere:** aliniere la contractul P1/P2.

## D02 — Ordinea câmpurilor

Generatorul 3M construiește intrările în ordinea `(cale, hash)`, dar le serializează ca și cum ar fi `(hash, cale)`.

**Remediere:** corectarea structurii interne și a formatului de ieșire.

## D03 — Verificare independentă

Verificarea `--check` regenerează conținutul folosind aceeași logică de inventariere.

**Remediere:** introducerea verificatorului strict, care validează structura, completitudinea și hash-urile.

## D04 — Căi și duplicate

Trebuie respinse căile nesigure, duplicatele și intrările neconforme.

## D05 — Fișiere lipsă și suplimentare

Trebuie demonstrată completitudinea inventarului.

## D06 — Automatizarea CI

Workflow-ul trebuie să păstreze manifestul, checksum-urile, rezultatele benchmarkului și rapoartele.

## D07 — Commit automat

Trebuie decis explicit dacă P3 va adopta modelul de commit automat P1/P2.

## D08 — Documentație

Toate documentele trebuie să descrie implementarea reală, nu o funcționalitate planificată.

# 7. Criterii de acceptare

Acceptarea necesită PASS pentru:

- corectitudinea CSR;
- corectitudinea SpMV;
- corectitudinea paralelizării;
- testele Java;
- testele Python;
- validarea numerică;
- benchmark și proveniență;
- manifest;
- SHA-256;
- workflow;
- artefacte;
- reproductibilitate;
- documentație;
- identificarea commitului final.

# 8. Verdictul auditului

La data reviziei documentare:

`P3_ACCEPTED = FALSE`

Motiv: integritatea globală și alinierea completă cu modelul P1/P2 nu sunt încă demonstrate.

Această stare nu afirmă că algoritmii CSR sau SpMV sunt incorecți.

Înseamnă că acceptarea completă nu este demonstrată prin dovezi.

# 9. Înregistrarea verdictului final

Se completează după validarea efectivă:

```text
P3_ACCEPTED:
FINAL_COMMIT_SHA:
CI_RUN_ID:
BENCHMARK_RUN_ID:
JAVA_VERSION:
MAVEN_VERSION:
PYTHON_VERSION:
JAVA_TESTS:
PYTHON_TESTS:
BENCHMARK_VERDICT:
MANIFEST_VERDICT:
SHA256_VERDICT:
ARTIFACTS_VERDICT:
DOCUMENTATION_VERDICT:
ACCEPTANCE_DATE:
```

Verdictul `P3_ACCEPTED` poate fi acordat numai când toate porțile obligatorii sunt PASS pe același commit.
