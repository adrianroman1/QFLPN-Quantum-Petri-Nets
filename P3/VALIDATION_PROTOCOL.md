# QFLPN P3 — VALIDATION PROTOCOL
## Protocol de validare, benchmark, integritate și acceptare

---

# 1. Scop

Acest protocol definește procesul reproductibil de validare P3.

Obiectivul este demonstrarea concordanței dintre:

- manuscris;
- implementare;
- teste;
- rezultate matematice;
- benchmark;
- dovezi experimentale;
- manifest;
- checksum-uri;
- GitHub Actions;
- commitul final.

P1 și P2 reprezintă modelele existente de automatizare și verificare.

P3 trebuie să adopte același nivel de rigoare, păstrând particularitățile benchmarkului CSR/SpMV.

# 2. Identificarea commitului

Înaintea validării:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

Se înregistrează:

- branch;
- commit SHA complet;
- working tree;
- data;
- identificatorul workflow-ului.

Nu se combină rezultate de pe commituri diferite.

Un rezultat CI istoric nu validează automat codul actual.

# 3. Mediul de execuție

Cerințe:

- Git;
- JDK 21;
- Maven;
- Python 3.12 în CI;
- pytest;
- Bash;
- sha256sum.

Verificare:

```bash
git --version
java -version
mvn --version
python3 --version
python3 -m pytest --version
sha256sum --version
```

Versiunile efective trebuie înregistrate în dovezile benchmarkului.

# 4. Validarea Maven

Din rădăcina repository-ului:

```bash
mvn -B -f pom.xml validate
mvn -B -f pom.xml clean test
```

Pentru P3:

```bash
mvn -B -f P3/pom.xml validate
mvn -B -f P3/pom.xml clean test
```

Cerințe:

- compilare fără erori;
- teste executate;
- zero teste eșuate;
- rapoarte Surefire păstrate.

`mvn validate` nu înlocuiește `mvn clean test`.

# 5. Testarea Python

Comanda de bază:

```bash
python3 -m pytest \
  P3/results/test_validate_benchmark.py \
  P3/tests/test_generate_integrity.py \
  -v
```

După implementarea completă a verificatoarelor P3, suita trebuie să acopere:

- generarea manifestului;
- verificarea manifestului;
- generarea SHA256SUMS;
- verificarea SHA256SUMS;
- hash invalid;
- cale absolută;
- cale cu `..`;
- duplicate;
- fișiere lipsă;
- fișiere suplimentare;
- linkuri simbolice;
- fișiere temporare;
- modificări după generare;
- inventar gol;
- excluderi.

Testele trebuie să folosească directoare temporare.

Nu trebuie să modifice inventarul real al repository-ului.

# 6. Validarea matematică CSR

Se verifică:

- `rowPointers.length == rows + 1`;
- `rowPointers[0] == 0`;
- pointerii monoton crescători;
- ultimul pointer egal cu numărul elementelor nenule;
- `values.length == columnIndices.length`;
- indicii de coloană în interval;
- dimensiuni valide;
- rânduri goale;
- matrice dreptunghiulare;
- valori invalide.

# 7. Validarea SpMV

## 7.1. Secvențial

Rezultatul CSR trebuie comparat cu un oracol dens independent.

Toleranța numerică trebuie să fie explicită.

## 7.2. Paralel

Rezultatul paralel trebuie comparat cu:

- oracolul dens;
- implementarea secvențială.

Trebuie verificate:

- toate rândurile;
- lipsa suprapunerilor incorecte;
- lipsa rândurilor omise;
- comportamentul pentru matrice goale;
- comportamentul pentru dimensiuni-limită.

# 8. Benchmark P3

Runnerul oficial este:

`P3/results/run_benchmark.sh`

Validatorul oficial este:

`P3/results/validate_benchmark.py`

Testele validatorului:

`P3/results/test_validate_benchmark.py`

Configurația standard pentru workflow-ul manual:

```text
N=1000000
WARMUP=5
ITERATIONS=10
THRESHOLD=4096
PARALLELISM=2
NNZ=2000000
TOLERANCE=1.0e-12
```

Runnerul trebuie să:

1. verifice parametrii;
2. verifice executabilele;
3. înregistreze commitul;
4. înregistreze mediul;
5. ruleze testele Java;
6. ruleze testele validatorului;
7. valideze CSV-ul existent;
8. execute benchmarkul Java;
9. solicite exact un rând nou;
10. valideze toate rândurile CSV;
11. extragă ultimul rând;
12. valideze ultimul rând cu configurația solicitată;
13. genereze raport JSON;
14. genereze checksum-urile run-specific;
15. verifice checksum-urile.

Nu se editează manual CSV-ul.

Nu se introduc manual timpi, speedup sau throughput.

# 9. Dovezi benchmark P3

Fiecare execuție trebuie să aibă un RUN_ID unic.

Structura:

```text
P3/results/raw/<RUN_ID>/
├── benchmark.log
├── environment.txt
├── validation-report.json
├── latest_benchmark_result.csv
└── SHA256SUMS.txt
```

Runnerul actual generează aceste dovezi.

Lista SHA-256 run-specific trebuie să includă:

- CSV-ul complet;
- CSV-ul ultimei înregistrări;
- logul;
- mediul;
- raportul JSON.

Verificarea se execută cu:

```bash
sha256sum -c P3/results/raw/<RUN_ID>/SHA256SUMS.txt
```

Dovezile trebuie să fie asociate commitului care a produs rezultatul.

# 10. Corelarea benchmarkurilor P1/P2/P3

Benchmarkurile nu trebuie confundate.

## P1

P1 rulează benchmarkul cu:

```bash
python P1/benchmarks/benchmark_runner.py \
  --warmups 5 \
  --repetitions 30
```

Rezultatele sunt păstrate în `P1/benchmarks/`.

Eșecul benchmarkului este tratat ca avertisment pentru validarea matematică, dar trebuie consemnat.

## P2

P2 rulează:

```bash
python P2/benchmarks/benchmark_runner.py \
  --config P2/benchmarks/benchmark_config.json \
  --output P2/benchmarks
```

Apoi validează:

```bash
python P2/benchmarks/validate_benchmark.py \
  --results P2/benchmarks
```

Benchmarkul este suplimentar pentru verdictul matematic.

Commitul automat al dovezilor P2 este condiționat de succesul benchmarkului și al validării sale.

## P3

P3 rulează benchmarkul la `workflow_dispatch`.

Workflow-ul transmite parametrii expliciți prin variabile de mediu și execută:

```bash
bash P3/results/run_benchmark.sh
```

Benchmarkul P3 este o etapă obligatorie a execuției manuale.

Nu trebuie prezentat ca fiind executat la fiecare push dacă workflow-ul nu face acest lucru.

# 11. Manifestul global P3

Locația canonică:

```text
P3/MANIFEST.txt
```

Contract:

- inventar determinist;
- căi relative;
- SHA-256;
- sortare stabilă;
- fără duplicate;
- fără căi absolute;
- fără `..`;
- fără linkuri simbolice;
- fără intrări autoreferențiale.

Manifestul trebuie să descrie fișierele eligibile ale proiectului P3.

Politica de excludere trebuie documentată și comună generatorului și verificatorului.

Rezultatele volatile ale benchmarkului pot avea un inventar separat run-specific, dar nu pot rămâne fără checksum.

# 12. SHA256SUMS P3

Locația:

```text
P3/SHA256SUMS.txt
```

Fișierul trebuie generat automat.

Nu se editează manual.

Nu se include propriul hash.

Nu se creează o dependență circulară între manifest și checksum.

Generatorul trebuie să producă rezultate deterministe.

# 13. Verificarea independentă

Verificatorul trebuie să:

1. confirme rădăcina P3;
2. citească manifestul;
3. valideze formatul hash-urilor;
4. valideze căile;
5. respingă duplicatele;
6. reconstruiască inventarul așteptat;
7. detecteze fișiere lipsă;
8. detecteze fișiere suplimentare;
9. recalculeze hash-urile;
10. compare rezultatele;
11. publice verdictul.

Generatorul și verificatorul nu trebuie să se limiteze la confirmarea propriului rezultat fără controlul inventarului complet.

# 14. Ordinea GitHub Actions

Ordinea logică obligatorie:

1. checkout;
2. configurare JDK;
3. configurare Python;
4. instalare dependențe;
5. validare Maven principală;
6. teste Maven principale;
7. validare Maven P3;
8. teste Java P3;
9. teste Python;
10. benchmark la `workflow_dispatch`;
11. validare benchmark;
12. capturare dovezi;
13. generare manifest;
14. verificare manifest;
15. generare SHA256SUMS;
16. verificare SHA256SUMS;
17. publicare rezumat;
18. încărcare artefacte;
19. commit automat, dacă este configurat și permis.

Etapele obligatorii trebuie să oprească verdictul de acceptare dacă eșuează.

# 15. Commit automat

P1 și P2 folosesc `contents: write` și comit dovezile generate după succesul etapelor cerute.

Workflow-ul P3 actual folosește `contents: read` și `persist-credentials: false`.

Prin urmare, workflow-ul P3 actual nu poate efectua commit automat.

Dacă se adoptă modelul P1/P2, trebuie:

- acordat `contents: write`;
- configurat checkout-ul pentru push;
- configurată identitatea botului;
- limitate fișierele comise;
- excluse pull request-urile;
- condiționat commitul de succes;
- prevenite buclele de workflow.

Dacă nu există permisiuni, artefactele trebuie încărcate fără commit automat.

# 16. Artefacte obligatorii

La finalul unei execuții trebuie păstrate:

- commit SHA;
- workflow run ID;
- benchmark RUN_ID;
- log benchmark;
- environment;
- CSV;
- raport JSON;
- SHA256SUMS run-specific;
- rapoarte JUnit;
- log pytest;
- MANIFEST;
- SHA256SUMS global;
- rezumatul GitHub Actions.

# 17. Acceptarea finală

P3 este acceptat numai dacă:

- buildul este PASS;
- testele Java sunt PASS;
- testele Python sunt PASS;
- validarea numerică este PASS;
- benchmarkul este valid;
- dovezile sunt prezente;
- checksum-urile sunt verificate;
- manifestul este complet;
- workflow-ul este PASS;
- documentația este aliniată;
- toate dovezile aparțin aceluiași commit.

Orice criteriu PENDING blochează acceptarea.

Orice criteriu FAIL respinge acceptarea.
