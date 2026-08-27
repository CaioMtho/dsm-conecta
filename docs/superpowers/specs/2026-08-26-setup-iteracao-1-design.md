# Spec: Setup da Iteração 1 (Ambiente e Repositório)

## 1. Visão Geral
Este documento especifica a implementação das tarefas da Iteração 1 do projeto **DSM Conecta**, focando em estabelecer a fundação estrutural do monorepo, a configuração das pipelines de integração contínua (CI/CD), automação do ambiente local de desenvolvimento e definição das práticas e padrões.

## 2. Estrutura de Diretórios do Monorepo
O repositório será organizado mapeando os domínios levantados na documentação de arquitetura, provendo clara separação entre componentes e simplificando o escopo de testes de cada um:

* `apps/client/`: Aplicativo em Flutter com configuração base e testes.
* `apps/gateway/`: API baseada em FastAPI (Python com `uv`).
* `apps/ingestor/`: Worker de processamento e deduplicação (Python com `uv`).
* `apps/simulator/`: Gerador de carga simulando os sensores físicos (Python com `uv`).
* `packages/schemas/`: Pacote contendo os modelos de dados e contratos compartilhados entre os serviços Python.
* `deployments/`: Artefatos para orquestração da infra (e.g. `docker-compose.yml`, `mosquitto.conf`).
* `.github/workflows/`: Pipelines automatizadas.
* `AGENTS.md`: Arquivo consolidando práticas de desenvolvimento e orientações.

## 3. Configuração do Ecossistema Python
* A gestão de dependências utilizará o gerenciador **uv**, implementando a funcionalidade de **uv workspaces** para centralizar dependências cruzadas (ex: as APIs usando `packages/schemas`). 
* Ferramentas base incluídas em cada app/pacote:
  * `pytest`: Framework de testes suportando a abordagem Red-Green-Refactor.
  * `ruff`: Validação estática, linting e formatação de código altamente performática.
* Exemplos triviais de testes (asserts booleanos ou mocks básicos) serão incluídos em cada projeto para atestar a comunicação da esteira de CI.

## 4. Configuração do Ecossistema Flutter
* Inicialização do projeto cliente usando a CLI do Flutter.
* Configuração dos arquivos básicos ativando a suíte nativa `flutter test`.
* Manutenção do teste exemplo criado pelo SDK para permitir sucesso limpo (green build) na pipeline inicial.

## 5. Automação e Integração Contínua (CI/CD)
* **Makefile:** Centralizará e simplificará o acesso às ferramentas. Targets planejados:
  * `install`: Sincroniza o `uv workspace` e executa o `flutter pub get`.
  * `up-all`, `up-infra`: Wrappers em torno do comando `docker compose up`.
  * `run-simulator`: Comando isolado para acionar apenas o gerador de carga.
  * `test`: Aciona as rotinas de verificação do `pytest` em todos os projetos Python e o `flutter test`.
* **GitHub Actions:** 
  * Será criada uma esteira para rodar em Pull Requests e na branch `main`.
  * As *jobs* realizarão, de forma paralela:
    1. Execução do analisador sintático (Ruff / Flutter Analyze).
    2. Execução da suíte de testes unitários.
    3. Verificação do título do Pull Request em conformidade com o padrão **Conventional Commits**.

## 6. Padronização e Boas Práticas (AGENTS.md)
* Não serão incluídos *pre-commit hooks* invasivos localmente para a verificação de commit, garantindo agilidade no TDD. Essa responsabilidade foi delegada à CI.
* O arquivo `AGENTS.md` será redigido orientando desenvolvedores sobre:
  * Mensagens sob o padrão do *Conventional Commits* (ex: `feat:`, `fix:`, `chore:`).
  * Obrigação da prática de **TDD** visando cobertura mínima futura de 70%.
  * Orientação sobre o uso do ambiente unificado do `uv workspace`.
  * Regra sobre Pull Requests e branch protegida.
