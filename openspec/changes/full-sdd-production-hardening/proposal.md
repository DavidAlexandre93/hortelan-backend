## Why

O backend possui uma boa base hexagonal, mas a linha de base reproduzivel falha: dois testes estao quebrados, a cobertura global e 74,09%, ha dez erros de tipagem, dependencias divergentes e contratos de erro/saude que podem expor diagnosticos sensiveis. A mudanca e necessaria agora para oferecer ao frontend contratos confiaveis, falhas recuperaveis e evidencia automatizada de seguranca e qualidade.

## What Changes

- Padronizar DTOs de entrada, saida, erro, health e paginacao com enums e OpenAPI 3.1 deterministico.
- Emitir logs JSON allowlist-first com classe, arquivo, linha, stack interna completa e correlacao OTEL, sem PII, segredos, corpos ou query strings.
- Separar liveness, readiness e dependency health, retornando status HTTP operacionalmente correto e informacao segura para a tela de indisponibilidade do frontend.
- Garantir idempotencia para comandos e ledger com chave validada, fingerprint da requisicao, replay deterministico, conflito explicito e armazenamento atomico compartilhado.
- Tornar a persistencia relacional ACID por transacao e declarar explicitamente consistencia eventual para Mongo/Kafka/cache; preparar outbox sem prometer atomicidade distribuida inexistente.
- Corrigir UTC timezone-aware, comparacao segura de credenciais, limites de entrada, rate limit tipado, headers e CORS configuravel.
- Consolidar dependencias e configurar Ruff, mypy, pytest/coverage, Conventional Commits, auditoria, CI e plano de testes com gate progressivo ate 100% do codigo mantido.
- Manter a arquitetura hexagonal existente; aplicar Adapter, Strategy/Policy e Repository onde ja ha variacao real, sem reescrita cerimonial.
- Remover somente artefatos Claude Code pertencentes ao projeto. A varredura confirmou que nao existe `.claude` versionado; `.agents/skills/openspec-*` e a integracao OpenSpec para Codex e sera preservada.

### Non-goals

- Nao adicionar um segundo framework web, um container de injecao de dependencias ou microservicos sem necessidade demonstrada.
- Nao afirmar ACID entre SQL, MongoDB, Kafka, Redis, AWS IoT e blockchain; esses limites permanecem assíncronos e observaveis.
- Nao expor stack trace, detalhes de dependencia, PII ou segredos a clientes, inclusive em desenvolvimento por padrao.
- Nao substituir o sistema visual Material UI do frontend nem adicionar bibliotecas apenas por novidade.

## Capabilities

### New Capabilities

- `platform/api-contracts`: DTOs estritos, enums, envelopes de erro, health e documentacao OpenAPI consumivel pelo frontend.
- `platform/observability`: logs JSON seguros, correlacao W3C/OTEL, diagnosticos internos e metricas de operacao.
- `platform/runtime-reliability`: autenticacao, rate limit, timeouts, circuit breaker, degradacao e health checks coerentes.
- `data/transactional-integrity`: idempotencia persistente, transacoes ACID locais e limites documentados de consistencia eventual.
- `delivery/backend-quality`: toolchain estatica, cobertura, testes, dependencias, Conventional Commits e gates de CI.
- `architecture/sdd-governance`: governanca OpenSpec e rastreabilidade entre requisitos, design, tarefas e verificacao.

### Modified Capabilities

Nenhuma. Este e o primeiro baseline OpenSpec canonico do backend.

## Impact

- Afeta contratos HTTP, middleware, tratamento de erros, composition root, casos de uso de mutacao, portas/adapters, persistencia SQL/Redis, configuracao, CI, Docker e documentacao.
- O frontend podera tratar health, indisponibilidade, conflito idempotente e incidentes por contratos estaveis; clientes existentes preservam as rotas e campos de sucesso atuais sempre que possivel.
- Novas dependencias de runtime somente serao aceitas quando substituirem implementacao insegura ou habilitarem um requisito verificavel; ferramentas de qualidade ficam no grupo de desenvolvimento.
- A ativacao de exportacao OTLP e integracoes externas continua controlada por ambiente e deve falhar de modo seguro.
