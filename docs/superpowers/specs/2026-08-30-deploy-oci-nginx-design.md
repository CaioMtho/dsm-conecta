# Design: Deploy Contínuo (OCI) e Nginx (Porta Única)

## 1. Objetivo
Automatizar o deploy contínuo da aplicação DSM Conecta para uma VM na Oracle Cloud Infrastructure (OCI) através do GitHub Actions. Além disso, expor os serviços de backend externamente através de uma única porta de entrada (Nginx), removendo a exposição direta das portas da API e do Broker MQTT por questões de boas práticas e segurança.

## 2. Arquitetura e Proxy (Nginx)

Um novo serviço de proxy será introduzido no `docker-compose.yml` utilizando o Nginx. Ele atuará como o ponto de entrada único para os serviços internos.

### 2.1 Mudanças no Docker Compose
- **Adição do serviço Nginx**: Irá expor a porta HTTP `80:80` e a porta MQTT `1883:1883`.
- **Isolamento de portas**: Remover a declaração `ports` dos serviços `gateway` (8000) e `broker` (1883 e 9001). Eles passarão a se comunicar com o mundo externo apenas por intermédio do Nginx (via rede interna do Docker).
- **Referência a Imagens**: Os serviços customizados (`gateway`, `ingestor`) receberão a tag `image: ghcr.io/${GITHUB_REPOSITORY,,}/<nome>:latest` para possibilitar o pull da imagem já buildada pela VM. A chave `build` será mantida para uso no desenvolvimento local.

### 2.2 Roteamento (nginx.conf)
- O arquivo será criado em `deployments/docker/nginx.conf`.
- Roteamento HTTP (bloco `http`): Redireciona o tráfego da porta 80 para `gateway:8000`.
- Roteamento TCP (bloco `stream`): Redireciona o tráfego da porta 1883 para `broker:1883`.

## 3. Pipeline de CI/CD (GitHub Actions)

Um novo arquivo será adicionado em `.github/workflows/deploy.yml`. O gatilho de execução ocorrerá em pushes na branch principal (`main`).

### 3.1 Etapa 1: Build e Push
- O pipeline autentica-se nativamente no GitHub Container Registry (`ghcr.io`) usando o `secrets.GITHUB_TOKEN`.
- Ocorre o build das imagens dos contêineres do `gateway` e do `ingestor`.
- As imagens geradas recebem a tag `latest` (e alternativamente do SHA do commit) e são enviadas para o `ghcr.io`.

### 3.2 Etapa 2: Deploy na VM (OCI)
- O workflow usará `appleboy/scp-action` para copiar apenas o `docker-compose.yml` e a pasta `deployments/docker/` para a VM, garantindo que as configurações de proxy mais recentes estejam presentes.
- O workflow usará `appleboy/ssh-action` para executar comandos na VM remotamente.
- A VM se autenticará no `ghcr.io` usando o token `OCI_GH_PAT`.
- A VM fará o `docker compose pull` para baixar as imagens novas, e então rodará `docker compose up -d` para recriar os serviços afetados.

## 4. Segredos e Variáveis
O deploy assumirá que as seguintes chaves secretas estão configuradas no repositório do GitHub:
- `OCI_VM_HOST`: Endereço IP da VM.
- `OCI_VM_USER`: Usuário de conexão SSH.
- `OCI_SSH_PRIVATE_KEY`: Chave SSH de acesso à VM.
- `OCI_GH_PAT`: Token pessoal do GitHub com permissão estrita `read:packages` para a máquina conseguir fazer pull no Container Registry.

## 5. Limites e Escopo
- Provisionamento de Infraestrutura não faz parte deste documento (a VM já existe previamente).
- A comunicação Nginx <-> Gateway usará HTTP (sem TLS/SSL interno). O encerramento SSL, caso venha a existir, será tratado no futuro, mas foge ao escopo restrito de unificação de portas e automação desta fase inicial.
