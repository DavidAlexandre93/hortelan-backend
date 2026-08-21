## 1. Baseline e governanca SDD

- [x] 1.1 Inventariar os tres repositorios Hortelan, registrar branches e mudancas pre-existentes e verificar com `git status --porcelain=v2` em cada raiz.
- [x] 1.2 Medir baseline de OpenSpec, lint, formato, tipagem, testes, cobertura, build, auditoria e E2E; registrar os resultados no `test-plan.md`.
- [x] 1.3 Inicializar OpenSpec 1.10 somente para Codex, criar proposal/specs/design/tasks em pt-BR e validar com `openspec validate --all --strict --no-interactive`.
- [x] 1.4 Varredura Claude Code first-party; verificar ausencia de `.claude`/`CLAUDE.md` versionados e preservar `.agents/skills/openspec-*` do Codex.

## 2. Dependencias, configuracao e qualidade estatica

- [x] 2.1 Consolidar runtime/dev dependencies em `pyproject.toml`, alinhar `requirements.txt` e verificar instalacao limpa mais `pip check`.
- [x] 2.2 Configurar Ruff, mypy, pytest-asyncio e coverage no `pyproject.toml`; formatar todo first-party e obter zero erro nos checks.
- [x] 2.3 Validar Settings por enum, limites, URLs e invariantes de producao; cobrir configuracoes validas e invalidas por testes.
- [x] 2.4 Adicionar gate OpenSpec, Conventional Commits, OpenAPI drift e cobertura a CI; validar sintaxe dos workflows por teste estatico.

## 3. Contratos HTTP e seguranca de erros

- [x] 3.1 Criar DTO base estrito, enums e modelos de ack, erro, health, snapshot e paginacao; verificar schemas e rejeicao de extras.
- [x] 3.2 Refatorar handlers para nunca retornar traceback, input invalido, tipo interno ou causa; testar envelopes 4xx/5xx e correlacao.
- [x] 3.3 Documentar respostas de erro, security scheme, headers e exemplos no OpenAPI 3.1; gerar artefato deterministico e validar drift.
- [x] 3.4 Endurecer API key com comparacao constante, identificadores/headers limitados e CORS explicito; cobrir abusos e producao insegura.

## 4. Observabilidade e health

- [x] 4.1 Implementar formatter JSON allowlist-first com ambiente/servico/evento/extras aprovados e diagnostico completo de excecao; provar redacao por testes.
- [x] 4.2 Correlacionar logs/respostas com incident, request e contexto OTEL real, restaurando ContextVars ao final; testar concorrencia e fallback.
- [x] 4.3 Normalizar labels de rota/metricas, escapar labels e aplicar headers tambem em 429/erros; verificar baixa cardinalidade.
- [x] 4.4 Tornar liveness e readiness tipados, com timeout, 503 em indisponibilidade e detalhes seguros; cobrir sucesso, falha e timeout.

## 5. Idempotencia e integridade de dados

- [x] 5.1 Modelar repository de idempotencia com unique constraint, fingerprint canonico e estados processing/completed/unknown; testar concorrencia e rollback.
- [x] 5.2 Aplicar Idempotency-Key a comandos e ledger, incluindo replay, conflito e outcome incerto; contract tests devem provar que o efeito nao duplica.
- [x] 5.3 Propagar a chave ao comando externo e registrar resultado tipado sem payload sensivel; testar adapter AWS com fake.
- [x] 5.4 Persistir telemetria e outbox na mesma transacao SQL e expor reconciliacao observavel; testar rollback e reprocessamento sem duplicidade.
- [x] 5.5 Documentar matriz ACID/consistencia por sistema e validar que nenhuma resposta declara garantia distribuida inexistente.

## 6. Adapters e resiliência

- [x] 6.1 Extrair policy pequena de timeout/circuit breaker/metrica e aplicar a Redis, Kafka, AWS IoT e Web3 sem heranca; testar sucesso, falha e circuito aberto.
- [x] 6.2 Adicionar timeouts finitos a Redis/Mongo/Kafka e fechar recursos pelo lifecycle; testar shutdown parcial sem mascarar falhas criticas.
- [x] 6.3 Corrigir timezone-aware UTC e retornos tipados em entidades/casos de uso/adapters; mypy deve passar sem `ignore-missing-imports` global.
- [x] 6.4 Corrigir testes de rotas para substituir use cases/ports e remover acoplamento a campos concretos do container.

## 7. Frontend e landing integrados

- [x] 7.1 Corrigir o E2E flakey do dashboard com espera por estado semanticamente estavel e confirmar 40/40 cenarios em desktop/mobile.
- [x] 7.2 Validar a tela global de indisponibilidade/incident contra o novo envelope e health 503 sem expor diagnosticos.
- [x] 7.3 Executar gates completos do frontend e landing; registrar cobertura honesta e manter o plano progressivo ate 100% sem reduzir o denominador.
- [x] 7.4 Inspecionar visualmente rotas e estados de erro em 320/768/1440, tema claro/escuro e reduced motion; registrar evidencia e defeitos residuais.

## 8. Testes, documentacao e entrega

- [ ] 8.1 Implementar matriz do `test-plan.md` para contratos, redacao, health, idempotencia, transacao, adapters e concorrencia; atingir 100% nos modulos criticos.
- [ ] 8.2 Elevar o gate global a 100% de statements/branches/functions/lines do first-party mantido ou documentar cada exclusao revisada.
- [x] 8.3 Atualizar README, `.env.example`, Swagger, runbooks e ADRs de consistencia/observabilidade/idempotencia; verificar links e exemplos.
- [ ] 8.4 Executar OpenSpec estrito, lint, format, mypy, pytest/coverage, audit, build Docker e smoke health; anexar comandos/resultados a `test-plan.md`.
- [ ] 8.5 Revisar diff e status dos tres repositorios, confirmar preservacao de mudancas do usuario e deixar o change ativo ate todos os itens estarem comprovados.
