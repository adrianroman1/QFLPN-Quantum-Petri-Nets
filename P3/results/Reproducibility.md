# P3 — Reproducibility Protocol

## 1. Purpose

This document defines the procedure for reproducing the P3
build, tests, mathematical validation, benchmark, and integrity checks.

A command listed in this document is a reproducibility instruction.
Its presence does not prove that the command has been executed
successfully.

Execution evidence must be associated with a commit and a
GitHub Actions run.

## 2. Required environment

The validation environment must record:

- operating system and version;
- CPU model and available processors;
- memory capacity;
- Java runtime version;
- Maven version;
- Python version;
- installed Python dependencies;
- Git commit SHA;
- GitHub Actions run identifier;
- benchmark configuration.

Expected major runtime requirements:

- Java 21;
- Maven;
- Python 3.12;
- pytest.

The actual versions used must be recorded in the generated
reproducibility report.

## 3. Repository provenance

Every accepted execution must identify:

- repository;
- branch;
- commit SHA;
- workflow name;
- workflow run ID;
- run timestamp;
- execution environment.

Results from different commits must not be combined into
one acceptance record unless the relationship is explicitly
documented.

## 4. Build and test commands

Run the root project validation:

```bash
mvn -B -f pom.xml validate
