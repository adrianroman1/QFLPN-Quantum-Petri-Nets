# P3 — VALIDATION PROTOCOL
## Protocol de compilare, testare, benchmark și acceptare

## 1. Scop

Acest protocol definește procedura reproductibilă de validare pentru P3.

Obiective:

1. compilarea proiectului;
2. executarea testelor Java;
3. executarea testelor Python;
4. verificarea integrității CSV;
5. executarea benchmarkului;
6. validarea independentă a rezultatelor;
7. verificarea provenienței;
8. verificarea checksum-urilor;
9. păstrarea dovezilor;
10. pregătirea acceptării finale.

Protocolul nu permite declararea unui rezultat PASS fără o dovadă verificabilă.

## 2. Cerințe de mediu

Mediul minim:

- Git;
- Java Development Kit 21;
- Maven;
- Python 3;
- pytest;
- Bash;
- `sha256sum`.

Verificare:

```bash
git --version
java -version
mvn --version
python3 --version
python3 -m pytest --version
sha256sum --version
