# DSM Conecta

Aplicativo multiplataforma para divulgação e captura de telemetria do curso de Desenvolvimento de Software Multiplataforma (DSM).

---

## 🛠️ Pré-requisitos

- [Docker](https://docs.docker.com/engine/install/) e Docker Compose
- [uv](https://docs.astral.sh/uv/) (gerenciador de dependências e ambientes Python)
- [FVM](https://fvm.app/) (Flutter Version Management)

Para instalar as dependências do workspace e do cliente:

```bash
make install
```

---

## 🚀 Ambiente de Desenvolvimento e Backend

O projeto disponibiliza diferentes modos de execução para paridade e produtividade no desenvolvimento local.

### 1. Configuração de Variáveis de Ambiente

Copie o arquivo de exemplo para inicializar as credenciais locais:

```bash
cp .env.example .env
```

As variáveis controlam:
- Banco de dados TimescaleDB (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).
- Credenciais de autenticação no broker MQTT Mosquitto (`MQTT_*`).

O banco de dados é inicializado automaticamente com o script em `deployments/docker/initdb/01_init.sql`, habilitando a extensão TimescaleDB.

### 2. Modos de Inicialização do Docker Compose

- **Modo Desenvolvimento com Hot-Reload (`make up-dev`)**:
  Aplica a sobreposição `deployments/docker-compose.dev.yml`, montando o código fonte (`apps/gateway`, `apps/ingestor`, `packages/schemas`) via volumes no container e habilitando o `--reload` no Uvicorn. Alterações salvas no código são refletidas instantaneamente sem necessidade de rebuild.
  ```bash
  make up-dev
  ```

- **Modo Infraestrutura Isolada (`make up-infra`)**:
  Inicia unicamente os serviços base (`db`, `broker`, `nginx`) sem disparar o build das aplicações Python. Recomendado quando o desenvolvedor deseja executar o Gateway ou Ingestor nativamente no host com `uv run`.
  ```bash
  make up-infra
  ```

- **Modo Produção / Paridade OCI (`make up-all`)**:
  Inicia a stack completa utilizando as imagens e configurações imutáveis do `deployments/docker-compose.yml`, idêntico ao deploy realizado na Oracle Cloud Infrastructure (OCI).
  ```bash
  make up-all
  ```

Para desligar os containers:

```bash
docker compose -f deployments/docker-compose.yml down
```

---

## 📱 Execução do Aplicativo Flutter (`apps/client`)

> [!IMPORTANT]
> Todos os comandos Flutter devem ser executados através do `fvm` (ex.: `fvm flutter run`, `fvm flutter test`).

O cliente Flutter oferece configurações pré-definidas para alternar entre ambientes via `--dart-define-from-file`.

### 1. Apontamento Local (Docker / Emulador)

Para executar o app apontando para a infraestrutura local:

```bash
make run-client-dev
```

Este comando utiliza o arquivo de configuração `apps/client/config/dev.json`. O app resolve o host de desenvolvimento automaticamente:
- **Emulador Android**: conecta em `10.0.2.2`.
- **Desktop (Linux/macOS/Windows) e Web**: conecta em `localhost`.
- **Credenciais**: `app_user` / `app_pass_dev`.

### 2. Apontamento Remoto (VM na OCI)

Para executar o app apontando para o servidor de produção/homologação na Oracle Cloud Infrastructure:

1. Abra `apps/client/config/remote.json`.
2. Substitua o valor de `MQTT_HOST` pelo endereço IP ou DNS da VM na OCI:
   ```json
   {
     "MQTT_HOST": "<IP_OU_HOST_DA_VM_OCI>",
     "MQTT_TCP_PORT": "1883",
     "MQTT_WS_PORT": "80",
     "MQTT_WS_PATH": "/mqtt",
     "MQTT_USERNAME": "app_user",
     "MQTT_PASSWORD": "app_pass_dev",
     "MQTT_CLIENT_PREFIX": "client_app_remote_"
   }
   ```
3. Execute:
   ```bash
   make run-client-remote
   ```

No Flutter Web, a conexão utiliza a rota WebSocket `/mqtt` na porta HTTP 80 por meio do proxy reverso Nginx, mantendo total paridade com as regras de exposição de produção.

---

## 🧪 Testes e Qualidade de Código

### Executar Testes Unitários e de Integração

```bash
make test
```

### Executar Linters e Análise Estática

```bash
make lint
```

---

## 🤝 Contribuição

Para padrões de commits, fluxo de Test-Driven Development (TDD), regras de revisão de Pull Requests e governança do repositório, consulte o guia completo em [CONTRIBUTING.md](CONTRIBUTING.md).

