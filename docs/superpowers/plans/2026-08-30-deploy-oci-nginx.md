# Deploy Contínuo OCI e Nginx Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatizar o deploy contínuo via GitHub Actions para VM na OCI e expor serviços em porta única com Nginx.

**Architecture:** Adição do serviço Nginx ao docker-compose atuando como proxy reverso (HTTP 80 e TCP 1883), isolamento das portas internas e configuração de um pipeline CI/CD que realiza o build e push para GHCR e atualiza a VM remotamente via SSH/SCP.

**Tech Stack:** Docker Compose, Nginx, GitHub Actions.

**Spec:** docs/superpowers/specs/2026-08-30-deploy-oci-nginx-design.md

## Global Constraints
- Sem provisionamento de infra (a VM já existe).
- Proxy HTTP direto sem TLS/SSL nesta fase.
- Segredos do GitHub exigidos: OCI_GH_PAT, OCI_SSH_PRIVATE_KEY, OCI_VM_HOST, OCI_VM_USER.

---

### Task 1: Criar Configuração do Nginx

**Files:**
- Create: `deployments/docker/nginx.conf`

**Interfaces:**
- Consumes: N/A
- Produces: Um arquivo de configuração do Nginx que expõe a porta 80 roteando para `gateway:8000` e porta 1883 para `broker:1883`.

- [ ] **Step 1: Criar arquivo nginx.conf**

Crie o arquivo e adicione as regras de proxy HTTP e TCP (usando o módulo stream):

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

# Proxy TCP para o MQTT (Mosquitto)
stream {
    server {
        listen 1883;
        proxy_pass broker:1883;
        proxy_connect_timeout 10s;
        proxy_timeout 3600s;
    }
}

# Proxy HTTP para o Gateway
http {
    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://gateway:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add deployments/docker/nginx.conf
git commit -m "feat(infra): adiciona configuracao do proxy reverso nginx para rotas mqtt e http"
```

---

### Task 2: Atualizar o Docker Compose

**Files:**
- Modify: `deployments/docker-compose.yml`

**Interfaces:**
- Consumes: `deployments/docker/nginx.conf`
- Produces: Docker compose com serviço Nginx, portas isoladas e imagens configuradas para pull com GHCR.

- [ ] **Step 1: Remover portas expostas do gateway e broker**

Modifique o `deployments/docker-compose.yml`, removendo a chave `ports` dos serviços `broker` e `gateway`.

- [ ] **Step 2: Adicionar a propriedade image para o build local**

No serviço `gateway`, logo acima ou abaixo de `build:`, adicione: `image: ghcr.io/${GITHUB_REPOSITORY,,}/gateway:latest`
No serviço `ingestor`, logo acima ou abaixo de `build:`, adicione: `image: ghcr.io/${GITHUB_REPOSITORY,,}/ingestor:latest`

- [ ] **Step 3: Adicionar serviço Nginx**

Ao final de `services:` (ou no topo), adicione o serviço Nginx:

```yaml
  nginx:
    image: nginx:latest
    container_name: dsm_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "1883:1883"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - gateway
      - broker
```

- [ ] **Step 4: Validar configuração local**

Rodar o comando para validar se o compose file não contém erros de sintaxe:
```bash
docker compose -f deployments/docker-compose.yml config > /dev/null
```
Expected: Saída vazia (código 0).

- [ ] **Step 5: Commit**

```bash
git add deployments/docker-compose.yml
git commit -m "build: atualiza docker-compose com nginx e imagens do ghcr"
```

---

### Task 3: Criar Workflow de CI/CD (GitHub Actions)

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: Todo o ambiente.
- Produces: Um pipeline funcional para build e deploy na OCI.

- [ ] **Step 1: Criar arquivo deploy.yml**

```yaml
name: Deploy to OCI VM

on:
  push:
    branches:
      - main
      - 10-github-actions-oci-deploy # Branch atual para teste

permissions:
  contents: read
  packages: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Log in to the Container registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push Gateway
        run: |
          docker compose -f deployments/docker-compose.yml build gateway
          docker push ghcr.io/${GITHUB_REPOSITORY,,}/gateway:latest

      - name: Build and Push Ingestor
        run: |
          docker compose -f deployments/docker-compose.yml build ingestor
          docker push ghcr.io/${GITHUB_REPOSITORY,,}/ingestor:latest

      - name: Copy Deploy Files to VM
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.OCI_VM_HOST }}
          username: ${{ secrets.OCI_VM_USER }}
          key: ${{ secrets.OCI_SSH_PRIVATE_KEY }}
          source: "deployments/docker-compose.yml,deployments/docker/nginx.conf,deployments/docker/mosquitto.conf"
          target: "~/dsm-conecta"
          overwrite: true

      - name: Deploy Services on VM
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.OCI_VM_HOST }}
          username: ${{ secrets.OCI_VM_USER }}
          key: ${{ secrets.OCI_SSH_PRIVATE_KEY }}
          script: |
            echo "${{ secrets.OCI_GH_PAT }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
            cd ~/dsm-conecta/deployments
            export GITHUB_REPOSITORY=${{ github.repository }}
            docker compose pull
            docker compose up -d
```

- [ ] **Step 2: Verificar sintaxe do workflow**
Rodar verificação manual ou apenas observar se a formatação YAML está correta (não há ferramenta nativa no bash para validar schema completo sem actionlint, então validaremos o YAML puro).
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: cria pipeline de build e deploy no ghcr e oci vm"
```
