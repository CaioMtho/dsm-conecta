# Setup da Iteração 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estabelecer a fundação estrutural do monorepo, configuração de ferramentas base (uv, flutter, pytest) e pipeline de CI/CD para o DSM Conecta.

**Architecture:** Monorepo particionado em domínios (`apps/` e `packages/`), gerenciado via `uv workspace` no Python e `flutter` no frontend, orquestrado localmente via `Makefile` e validado via GitHub Actions.

**Tech Stack:** Python 3.12, uv, pytest, ruff, Flutter, GNU Make, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-26-setup-iteracao-1-design.md`

## Global Constraints

- O backend deve obrigatoriamente suportar testes guiados (TDD), utilizando `pytest`.
- A formatação/lint do backend usará `ruff`.
- A infraestrutura de testes do Flutter deve utilizar `flutter test`.
- O padrão de commit esperado é o Conventional Commits.

---

### Task 1: Criação do AGENTS.md

**Files:**
- Create: `AGENTS.md`

**Interfaces:**
- Produces: Diretrizes do projeto para o time e outros agentes.

- [ ] **Step 1: Escrever o arquivo de diretrizes**

```markdown
# Diretrizes de Desenvolvimento e Agentes - DSM Conecta

## 1. Padrões de Commit
Utilizamos **Conventional Commits** (ex: `feat:`, `fix:`, `chore:`, `docs:`, `test:`).
A verificação final é feita na pipeline de Pull Request.

## 2. Test-Driven Development (TDD)
É mandatório seguir o fluxo Red-Green-Refactor. 
- Escreva o teste que falha.
- Escreva a implementação mínima.
- Refatore se necessário.
A meta é manter a cobertura do backend superior a 70%.

## 3. Gestão de Dependências Python
O projeto utiliza **uv** no formato de **Workspaces**. 
Para adicionar dependências mútuas (ex: `gateway` dependendo de `schemas`), utilize a configuração nativa do workspace.

## 4. Revisões de Código (PRs)
Pull Requests direcionados à branch `main` exigem revisão aprovada por um integrante de outra equipe.
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: adiciona diretrizes do projeto e boas praticas"
```

### Task 2: Configuração do uv workspace e projetos Python

**Files:**
- Create: `pyproject.toml` (raiz)
- Create: `apps/gateway/pyproject.toml`
- Create: `apps/ingestor/pyproject.toml`
- Create: `apps/simulator/pyproject.toml`
- Create: `packages/schemas/pyproject.toml`

**Interfaces:**
- Produces: `pyproject.toml` workspace environment para testes nas próximas tasks.

- [ ] **Step 1: Criar estrutura de diretórios**

```bash
mkdir -p apps/gateway/src apps/gateway/tests
mkdir -p apps/ingestor/src apps/ingestor/tests
mkdir -p apps/simulator/src apps/simulator/tests
mkdir -p packages/schemas/src packages/schemas/tests
```

- [ ] **Step 2: Criar o pyproject.toml do workspace raiz**

```toml
[project]
name = "dsm-conecta-workspace"
version = "0.1.0"
description = "Workspace raiz do projeto DSM Conecta"
requires-python = ">=3.12"
dependencies = []

[tool.uv.workspace]
members = [
    "apps/*",
    "packages/*"
]

[tool.ruff]
line-length = 88
target-version = "py312"
```

- [ ] **Step 3: Criar pyproject.toml para os subprojetos**

Crie o arquivo `apps/gateway/pyproject.toml`:
```toml
[project]
name = "gateway"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "pytest",
]
```

Crie o arquivo `apps/ingestor/pyproject.toml`:
```toml
[project]
name = "ingestor"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pytest",
]
```

Crie o arquivo `apps/simulator/pyproject.toml`:
```toml
[project]
name = "simulator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pytest",
]
```

Crie o arquivo `packages/schemas/pyproject.toml`:
```toml
[project]
name = "schemas"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pytest",
]
```

- [ ] **Step 4: Sincronizar o workspace e validar lint**

Run: `uv sync`
Expected: Ambiente sincronizado sem erros.
Run: `uv run ruff check .`
Expected: Nenhuma violação relatada.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock apps/ packages/
git commit -m "build: configura uv workspace e projetos python base"
```

### Task 3: Criação de Testes Base (Python)

**Files:**
- Create: `apps/gateway/tests/test_base.py`
- Create: `apps/ingestor/tests/test_base.py`
- Create: `apps/simulator/tests/test_base.py`
- Create: `packages/schemas/tests/test_base.py`

**Interfaces:**
- Produces: Testes triviais para validar CI.

- [ ] **Step 1: Criar testes temporários que falham intencionalmente (Red)**

Em cada pasta `tests/` acima, crie um `test_base.py` com:
```python
def test_initial_setup():
    assert False
```

- [ ] **Step 2: Executar testes para garantir falha**

Run: `uv run pytest`
Expected: 4 failures

- [ ] **Step 3: Corrigir testes para sucesso (Green)**

Modifique os 4 arquivos `test_base.py` para:
```python
def test_initial_setup():
    assert True
```

- [ ] **Step 4: Executar testes para garantir sucesso**

Run: `uv run pytest`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add apps/ packages/
git commit -m "test: adiciona suites de teste base aos pacotes python"
```

### Task 4: Configuração da Base Cliente (Flutter)

**Files:**
- Create: `apps/client/` (via `flutter create`)

**Interfaces:**
- Produces: Projeto client Flutter que será consumido no Makefile e CI.

- [ ] **Step 1: Criar projeto Flutter base**

```bash
cd apps
flutter create --project-name client --org br.gov.sp.fatec client
```
Expected: O framework irá gerar a estrutura do projeto cliente com `test/widget_test.dart` já incluído.

- [ ] **Step 2: Executar teste de validação**

```bash
cd client
flutter test
```
Expected: All tests passed.

- [ ] **Step 3: Analisar o projeto**

```bash
cd client
flutter analyze
```
Expected: No issues found.

- [ ] **Step 4: Commit**

```bash
cd ..
git add apps/client/
git commit -m "build: cria aplicacao base em flutter"
```

### Task 5: Implementação do Makefile

**Files:**
- Create: `Makefile`

**Interfaces:**
- Produces: Atalhos de linha de comando para setup e CI.

- [ ] **Step 1: Criar o Makefile**

```makefile
.PHONY: install up-all up-infra run-simulator test lint

install:
	uv sync
	cd apps/client && flutter pub get

up-all:
	docker compose up -d

up-infra:
	docker compose up -d db broker

run-simulator:
	cd apps/simulator && uv run python -m src.main

test:
	uv run pytest
	cd apps/client && flutter test

lint:
	uv run ruff check .
	cd apps/client && flutter analyze
```

- [ ] **Step 2: Testar comandos localmente**

Run: `make test`
Expected: Pytest reporta sucesso e flutter test reporta sucesso.
Run: `make lint`
Expected: Sem violações (Ruff e Flutter).

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "build: implementa rotinas do makefile"
```

### Task 6: Configuração de Integração Contínua (CI/CD)

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/pr-title.yml`

**Interfaces:**
- Consumes: Makefile (para execução de lint e tests no CI).

- [ ] **Step 1: Configurar pipeline de testes**

Crie `.github/workflows/ci.yml`:
```yaml
name: CI Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      - name: Install dependencies
        run: uv sync
      - name: Lint Python
        run: uv run ruff check .
      - name: Test Python
        run: uv run pytest

  test-flutter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          channel: 'stable'
      - name: Install dependencies
        run: cd apps/client && flutter pub get
      - name: Lint Flutter
        run: cd apps/client && flutter analyze
      - name: Test Flutter
        run: cd apps/client && flutter test
```

- [ ] **Step 2: Configurar verificação de Conventional Commits**

Crie `.github/workflows/pr-title.yml`:
```yaml
name: "Lint PR"

on:
  pull_request_target:
    types:
      - opened
      - edited
      - synchronize

jobs:
  main:
    name: Validate PR title
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci: configura fluxos do github actions para lint e tests"
```
