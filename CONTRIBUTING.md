# Guia de Contribuição - DSM Conecta

Agradecemos o interesse em contribuir com o DSM Conecta! Este documento descreve os padrões técnicos, fluxos de trabalho e boas práticas adotados para garantir a qualidade, manutenibilidade e confiabilidade do código.

---

## 1. Padrões de Commit

Utilizamos o padrão **Conventional Commits**. Todas as mensagens de commit devem seguir a estrutura:

```
<tipo>[escopo opcional]: <descrição concisa no imperativo>

[corpo opcional detalhando as motivações da mudança]

[rodapé opcional com referências a issues, ex: Closes #123]
```

### Tipos Permitidos
- `feat`: Adiciona uma nova funcionalidade ao sistema.
- `fix`: Corrige um bug ou problema relatado.
- `chore`: Tarefas de manutenção, ferramentas ou configurações auxiliares.
- `docs`: Modificações exclusivamente na documentação.
- `test`: Criação ou ajuste de testes sem alterações no código produtivo.
- `refactor`: Refatoração de código sem alteração de comportamento externo.
- `style`: Ajustes puramente visuais ou de formatação que não alteram a lógica.

> A validação do título do Pull Request é feita automaticamente na esteira de integração contínua (CI).

---

## 2. Test-Driven Development (TDD)

O desenvolvimento deve seguir rigorosamente o ciclo **Red-Green-Refactor**:

1. **Red**: Escreva o teste que expressa o comportamento esperado e confirme que ele falha.
2. **Green**: Escreva a implementação mínima necessária para fazer o teste passar.
3. **Refactor**: Limpe o código, elimine duplicações e otimize a estrutura mantendo a suíte de testes verde.

### Cobertura Mínima
- A meta mandatória é manter a cobertura de testes do backend superior a **70%**.

---

## 3. Gestão de Dependências Python

O backend é organizado como um workspace monorepo utilizando o gerenciador **uv**.

- **Dependências Globais e Dev**: Definidas no `pyproject.toml` da raiz do projeto.
- **Aplicações e Pacotes**: Localizados em `apps/*` e `packages/*`.
- **Dependências Cruzadas**: Para adicionar dependências mútuas (por exemplo, `gateway` ou `ingestor` dependendo de `packages/schemas`), utilize a configuração nativa de workspace do `uv` declarada no `pyproject.toml` do pacote correspondente.

Para sincronizar todas as dependências localmente:

```bash
uv sync --all-packages
```

---

## 4. Gestão de Ambiente Flutter (`apps/client`)

É mandatório utilizar o **fvm** (Flutter Version Management) para qualquer comando ou execução relacionada ao projeto cliente Flutter. Nunca execute o binário `flutter` ou `dart` global do sistema diretamente.

Exemplos:
```bash
# Obter dependências
fvm flutter pub get

# Executar testes unitários e de integração
fvm flutter test

# Executar análise estática
fvm flutter analyze

# Executar a aplicação
fvm flutter run
```

---

## 5. Diretrizes de Comentários no Código

- **Proibido Narrar o Óbvio**: Comentários que apenas descrevem o que o código faz ou redundantes são estritamente proibidos. O código deve ser autoexplicativo e não ser usado como repositório de documentação.
- **Comentários Permitidos**: Devem existir unicamente para registrar contextos não triviais, decisões arquiteturais, restrições externas ou detalhes sutis indispensáveis para quem for ler e manter o código.

---

## 6. Comandos de Validação Local

Antes de abrir um Pull Request ou solicitar revisão, execute a suíte de verificações locais:

```bash
# Executa testes do backend (pytest) e do cliente Flutter (fvm flutter test)
make test

# Executa os linters (ruff no backend e fvm flutter analyze no frontend)
make lint

# (Opcional) Executa testes de integração com o broker MQTT ativo
make test-broker-auth
```

---

## 7. Fluxo de Pull Requests e Revisão

1. Crie uma branch a partir da `main` com nome semântico (ex: `feat/<issue-numero>-<descricao>`, `fix/<issue-numero>-<descricao>`).
2. Mantenha os commits organizados e atômicos seguindo o Conventional Commits.
3. Certifique-se de que todos os testes e linters passam localmente.
4. Abra o Pull Request direcionado para a branch `main`.
5. **Aprovação Obrigatória**: Pull Requests direcionados à `main` exigem obrigatoriamente a revisão e aprovação de ao menos um integrante de outra equipe.
6. Todos os checks do GitHub Actions devem estar verdes antes da conclusão do merge.
