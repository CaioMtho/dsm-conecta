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
