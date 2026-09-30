# DSM Conecta

[![CI Pipeline](https://github.com/CaioMtho/dsm-conecta/actions/workflows/ci.yml/badge.svg)](https://github.com/CaioMtho/dsm-conecta/actions/workflows/ci.yml)
[![Deploy to OCI VM](https://github.com/CaioMtho/dsm-conecta/actions/workflows/deploy.yml/badge.svg)](https://github.com/CaioMtho/dsm-conecta/actions/workflows/deploy.yml)

Sistema distribuído multiplataforma voltado à divulgação institucional do curso de **Desenvolvimento de Software Multiplataforma (DSM)** da FATEC Zona Sul, integrando aplicativo cliente interativo, captura de telemetria em tempo real, mensageria MQTT segura, ingestão de dados e painel administrativo.

---

## 🏛️ Visão Geral e Arquitetura

O **DSM Conecta** organiza-se em uma arquitetura distribuída orientada a eventos (*event-driven*), distribuída em quatro camadas:

1. **Borda (Edge / Clients):**
   * **Aplicativo Cliente (`apps/client`):** Desenvolvido em **Flutter** para Android, Web e Desktop. Implementa conformidade estrita com a **LGPD** (`ConsentGatekeeper`, diálogo de consentimento prévio, anonimização com UUID v4 e gestão de sessão e dados do usuário).
   * **Nó Sensor Simulado (`apps/simulator`):** Emissor de telemetria sintética e simulação de contagem de visitantes no estande físico.
2. **Transporte e Mensageria (Messaging):**
   * **Eclipse Mosquitto 2:** Broker MQTT com suporte duplo a TCP (`1883`) e WebSockets (`9001` / `/mqtt`), com controle de acesso granular baseado em ACLs (`deployments/docker/mosquitto.acl`) e autenticação de usuários segregados (`app_user`, `simulator_user`, `ingestor_user`, `admin_user`).
   * **Proxy Reverso (Nginx):** Roteamento unificado na porta `80` (HTTP API e WebSocket `/mqtt`) e portas diretas.
3. **Processamento e Ingestão:**
   * **Serviço de Ingestão (`apps/ingestor`):** Worker assíncrono em Python responsável pelo consumo do tópico `dsm/prod/#`, validação de contratos, deduplicação e persistência.
   * **API Gateway (`apps/gateway`):** Servidor HTTP e WebSocket construído com **FastAPI**, provendo endpoints documentados em OpenAPI 3 para catálogo institucional, quiz vocacional e métricas.
4. **Persistência (Database):**
   * **TimescaleDB (PostgreSQL 16):** Banco relacional com extensão de séries temporais para telemetria particionada.

---

## 📁 Estrutura do Monorepo

O projeto adota a estrutura de monorepo gerenciado por **uv workspaces** (Python) e **FVM / Flutter**:

```text
dsm-conecta/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Pipeline integrado de lint e testes (Python + Flutter)
│       ├── deploy.yml                 # Deploy contínuo para VM na Oracle Cloud (OCI) + GHCR
│       └── pr-title.yml               # Validação de títulos de PR (Conventional Commits)
├── apps/
│   ├── client/                        # Aplicativo Flutter (Mobile, Web, Desktop)
│   │   ├── lib/
│   │   │   ├── core/privacy/          # Gerenciamento de consentimento LGPD e armazenamento local
│   │   │   ├── core/session/          # Identificador de sessão anônima UUID v4
│   │   │   ├── core/telemetry/        # Gatekeeper de telemetria
│   │   │   └── features/              # Telas (ConsentDialog, SettingsScreen, etc.)
│   │   └── test/                      # Testes unitários e de widget em Flutter
│   ├── gateway/                       # API REST e WebSockets em FastAPI
│   ├── ingestor/                      # Worker assíncrono de ingestão MQTT
│   └── simulator/                     # Nó sensor simulado e gerador de telemetria
├── packages/
│   └── schemas/                       # Modelos de dados e validação de contratos (Pydantic)
│       ├── src/schemas/events.py      # TelemetryEvent e enums de categorias/origem
│       └── tests/                     # Testes de validação de esquemas (TDD)
├── deployments/
│   ├── docker/
│   │   ├── Dockerfile.gateway         # Container FastAPI Gateway
│   │   ├── Dockerfile.ingestor        # Container Ingestor
│   │   ├── entrypoint-broker.sh       # Script de inicialização com hash de senhas Mosquitto
│   │   ├── mosquitto.acl              # Listas de Controle de Acesso (ACL) por tópico
│   │   ├── mosquitto.conf             # Configurações de listeners TCP e WebSockets
│   │   └── nginx.conf                 # Configuração do proxy reverso
│   └── docker-compose.yml             # Orquestração local e produção dos serviços
├── tests/
│   └── test_broker_auth.py            # Testes de integração de autenticação e ACLs do Mosquitto
├── AGENTS.md                          # Diretrizes para desenvolvedores e agentes de IA
├── Makefile                           # Automação de tarefas (build, test, lint, infra)
├── pyproject.toml                     # Configuração raiz do uv workspace
└── README.md
```

---

## 🛠️ Tecnologias e Ferramentas

* **Linguagens e Runtimes:** Python 3.12+, Dart / Flutter 3.x
* **Gerenciadores de Pacote e Ambiente:** [uv](https://docs.astral.sh/uv/) (Python Workspace), [FVM](https://fvm.app/) (Flutter Version Management)
* **Mensageria:** Eclipse Mosquitto 2 (MQTT 3.1.1 / WebSockets)
* **Backend:** FastAPI, Pydantic, Paho-MQTT, Pytest, Ruff
* **Frontend:** Flutter, Riverpod, SharedPreferences
* **Infraestrutura e CI/CD:** Docker & Docker Compose, Nginx, GitHub Actions, Oracle Cloud Infrastructure (OCI Compute VM), GitHub Container Registry (GHCR)

---

## 🚀 Como Executar

### Pré-requisitos
* [Docker](https://docs.docker.com/get-docker/) e Docker Compose
* [uv](https://docs.astral.sh/uv/) instalado (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
* [FVM](https://fvm.app/) instalado para gerenciar o Flutter SDK

### 1. Clonar e Instalar Dependências

```bash
git clone https://github.com/CaioMtho/dsm-conecta.git
cd dsm-conecta

# Instala dependências do workspace Python e pacotes do Flutter
make install
```

### 2. Inicializar a Infraestrutura (Banco + Broker + Nginx)

Para subir os serviços de infraestrutura localmente via contêineres:

```bash
make up-infra
```

Para subir a stack completa (incluindo Gateway e Ingestor):

```bash
make up-all
```

### 3. Executar o Aplicativo Cliente (Flutter)

```bash
cd apps/client
fvm flutter run -d chrome    # Para execução Web
# ou
fvm flutter run              # Para execução Desktop/Dispositivo conectado
```

---

## 🧪 Testes e Qualidade

O projeto adota rigorosamente a prática de **Test-Driven Development (TDD)** e checagem de qualidade em esteira de CI:

```bash
# Executa todos os testes automatizados (pytest e flutter test)
make test

# Executa apenas a validação estática de código (ruff e flutter analyze)
make lint

# Executa a suíte de testes de integração com o broker MQTT (necessita do make up-infra ativo)
make test-broker-auth
```

---

## 🔒 Privacidade e Segurança (LGPD)

O DSM Conecta implementa privacidade por design (*Privacy by Design*):
* **Consentimento Prévio:** Nenhum evento de telemetria é coletado ou transmitido sem a autorização expressa do usuário no `ConsentDialog`.
* **Identificador Anônimo:** As sessões utilizam identificadores aleatórios UUID v4 desvinculados de qualquer dado pessoal ou cadastro.
* **Direito à Exclusão (RF12):** Na tela de configurações (`SettingsScreen`), o usuário pode revogar suas permissões e apagar instantaneamente o identificador e os dados locais armazenados.
* **Segregação de Tópicos:** Regras de ACL no broker impedem que clientes publiquem ou assinem tópicos fora de seu escopo restrito.
