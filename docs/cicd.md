# Pipeline de CI/CD do Backend

Este documento descreve o fluxo completo implementado no workflow `.github/workflows/cicd.yml`.

## Visão geral do fluxo

1. **Detectar escopo impactado** com `paths-filter`.
2. **Qualidade**: instalação, lint, formatação, type-check, testes unitários e integração, cobertura mínima.
3. **Segurança**: Bandit, `pip-audit`, `detect-secrets` e Gitleaks.
4. **Build**: geração de pacote Python (`sdist`/`wheel`) e metadados versionados.
5. **Container build/publish**: build de imagem e push no GHCR com tags rastreáveis.
6. **Deploy staging** automatizado via SSH (branch `develop` ou disparo manual).
7. **Deploy production controlado** com `environment: production` (permitindo approvals e regras de proteção do GitHub Environment).
8. **Observabilidade pós-deploy**: validação de `/health`, `/health/ready` e `/metrics`.
9. **Rollback** manual controlado via `workflow_dispatch` para uma tag específica de imagem.

## Gates de qualidade e cobertura

- **Lint:** `ruff check app api tests`
- **Formatação:** `ruff format --check app api tests`
- **Tipos:** `mypy app api --ignore-missing-imports`
- **Unitários:** `pytest -m 'not integration' --cov-fail-under=85`
- **Integração:** `pytest -m integration`

## Versionamento de artefatos

- Versão base lida de `pyproject.toml`.
- Artefato Python recebe versão expandida: `<version>+<sha7>`.
- Imagem de container recebe tag:
  - `vX.Y.Z` (quando o push é tag git), ou
  - `<version>-<sha7>` (demais casos).
- Metadados gerados em `build-metadata.json` e publicados como artifact.

## Gestão de segredos e variáveis por ambiente

Configurar nos **GitHub Environments** (`staging` e `production`) para isolamento:

### Secrets obrigatórios

- `DEPLOY_SSH_HOST`
- `DEPLOY_SSH_USER`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DEPLOY_SSH_PORT` (opcional, default 22)
- `GHCR_READ_USER`
- `GHCR_READ_TOKEN`

### Variables (`vars`) recomendadas

- `DEPLOY_ENV_FILE_PATH`: caminho no host remoto para arquivo `.env` do ambiente.
- `APP_PORT`: porta publicada no host.
- `OBSERVABILITY_BASE_URL`: URL base para smoke pós-deploy (ex.: `https://api.staging.hortelan.com`).

> Recomendação: ativar reviewers obrigatórios no Environment `production` para deploy controlado.

## Deploy automatizado e controlado

- **Staging:** automático em `develop`, ou manual via `workflow_dispatch`.
- **Production:** após staging + regras do environment, em push para `main/master` ou manual.
- **Infra alvo:** host com Docker instalado, acessível por SSH.

## Estratégia de rollback

Dispare o workflow manualmente com:

- `action=rollback`
- `target_environment=production`
- `rollback_image_tag=<tag-publicada-no-ghcr>`

O pipeline faz pull da imagem da tag informada e sobe novamente o container.

## Observabilidade pós-implantação

Após deploy com sucesso, o workflow valida automaticamente:

- `GET /health`
- `GET /health/ready`
- `GET /metrics`

Se qualquer validação falhar, o job de observabilidade falha, permitindo ação imediata.
