# Plano de testes — full-sdd-production-hardening

## Objetivo e politica de cobertura

O objetivo e demonstrar comportamento, seguranca e confiabilidade, usando cobertura como evidencia complementar. O denominador inclui todo codigo first-party mantido em `app`, `api` e `scripts`; podem ser excluidos apenas arquivos declarativos, generated code ou entrypoints impossiveis de executar no test runner, sempre com justificativa versionada. Os modulos de contratos, erros, redacao, idempotencia, health e transacao exigem 100% imediato de statements, branches, functions e lines. O restante usa ratchet monotono ate 100% global.

## Baseline em 2026-08-20

| Projeto | Evidencia | Resultado inicial |
| --- | --- | --- |
| Backend | `pytest --cov=app --cov=api --cov-fail-under=100` | 27 passaram, 2 falharam; 74,09% total |
| Backend | `ruff check .` | passou |
| Backend | `ruff format --check .` | 46 arquivos fora do formato |
| Backend | `mypy app api tests scripts` | 10 erros em 7 arquivos |
| Frontend | `npm run quality:gate` | lint/build/audit/unit passaram; E2E 39/40 por espera flakey |
| Frontend | `npm run test:coverage` | Vitest 85,06% statements/75,57% branches; Node 67,47% lines |
| Landing | `npm run quality:gate` | passou; 84 testes, 98,49% statements/92,65% branches |
| Claude Code | busca first-party | nenhum `.claude` ou `CLAUDE.md`; achado apenas transitivo em `node_modules/resolve` |

## Matriz requirement-to-test

| Capacidade | Risco principal | Nivel e cenarios obrigatorios | Gate |
| --- | --- | --- | --- |
| `platform/api-contracts` | drift ou dado sensivel no cliente | unit DTO; contract por status; snapshot OpenAPI; frontend consumer | 100% + OpenAPI sem drift |
| `platform/observability` | PII/segredo ou trace inutil | unit redacao/stack; concorrencia ContextVar; OTEL fake; log JSON parseavel | 100% critico |
| `platform/runtime-reliability` | sucesso falso ou probe incorreto | auth timing-safe; 429; timeout; breaker; live 200/ready 503 | 100% critico |
| `data/transactional-integrity` | comando/ledger duplicado ou escrita parcial | replay/conflito; duas requests concorrentes; crash state; rollback; outbox replay | 100% critico |
| `delivery/backend-quality` | gate enganoso/reprodutibilidade | install clean; lint; mypy; coverage; audit; Docker/smoke; workflow check | todos verdes |
| `architecture/sdd-governance` | codigo sem contrato/evidencia | OpenSpec strict; rastreabilidade; scan Claude; task audit | zero falha |

## Suites detalhadas

### Unit

- DTOs: limites, extras, enums, UTC, serializacao e payloads maliciosos.
- Redacao: chaves sensiveis em qualquer casing, strings longas, objetos nao serializaveis e excecoes encadeadas.
- Fingerprint/idempotencia: ordem de chaves, mesmo intent, payload conflitante, estado completo/processando/incerto.
- Circuit breaker: closed/open/half-open, limite, recuperacao e chamadas concorrentes.
- Metricas: quantis, escape de labels, template de rota e erro/inflight balanceado.
- Settings: cada ambiente, URL invalida, limites e invariantes de producao.

### Contract/API

- Cada rota valida request e response pelo OpenAPI para todos os status declarados.
- 400/401/404/409/422/429/500/502/503 usam o mesmo envelope seguro.
- Validation errors nao ecoam `input`; unhandled errors nao expoem classe, stack, arquivo, linha ou query.
- Idempotency-Key ausente/invalida, replay igual, conflito e in-progress.
- Health/root/docs/favicon/metrics com headers, content types e schema corretos.

### Integration e ACID

- SQLite/PostgreSQL compatível: create schema/migration, commit, rollback, constraint e isolamento de reserva concorrente.
- Redis/Kafka/Mongo/AWS/Web3 com fakes deterministicas para success/timeout/failure/circuit-open e resource close.
- Testcontainers opcionais para Redis, Kafka, Mongo e banco alvo no gate noturno; indisponibilidade deve gerar skip explicito somente fora do CI de integracao.
- Outbox: dado e evento no mesmo commit, relay retry, deduplicacao e poison event observavel.

### Seguranca e privacidade

- API key com `compare_digest`, producao sem segredo, CORS allowlist, request id limitado e header injection.
- Sem PII/secrets no stdout capturado, resposta HTTP, OpenAPI examples, build ou artefatos.
- Bandit, pip-audit, CodeQL, dependency review e secret scan como gates.
- Fuzz/property tests para DTOs, ids, redator e serializador quando o gerador agregar valor.

### Observabilidade e resiliencia

- Cada request produz eventos JSON parseaveis start/finish ou failure com correlacao consistente.
- Excecao interna registra classe/arquivo/linha/funcao/stack completa no log protegido.
- Collector OTLP ausente ou lento nao quebra startup/request/shutdown.
- Cardinalidade: ids de 100 dispositivos geram uma serie por template, nao 100 paths.
- Readiness testa timeout e falha paralela; liveness nunca toca dependencias.

### Frontend, acessibilidade e visual

- Consumer contract testa envelopes/health reais e desconhecidos.
- Global/route error boundary mostra tela elegante, pt-BR, incident id copiavel, retry e navegacao segura; sem diagnostico interno.
- Playwright desktop e 320px cobre offline, 503, timeout, rota lazy com falha, retry e reduced motion.
- Axe sem violacoes critical/serious; screenshots comparadas para claro/escuro em 320/768/1440.
- Landing executa release gate para impedir regressao entre os tres repositorios.

### Performance e operacao

- Baseline de `/health`, listagem e metricas com p50/p95/p99, throughput e erro.
- Carga concorrente de idempotencia prova um unico efeito e latencia limitada.
- Build Docker roda como usuario nao-root, healthcheck e shutdown gracioso; imagem e SBOM auditaveis.
- Smoke pos-deploy valida live, ready, OpenAPI e uma operacao read-only; rollback usa imagem imutavel anterior.

## Comandos de aceitacao

### Evidencia atualizada em 2026-08-20

- Backend: `pytest -q` passou com 71 testes; cobertura passou com 91,78% total e gate atual de 90%.
- Frontend: `npm run quality:gate` passou; 95 testes de componentes, 8 testes Node e 42 E2E passaram.
- Landing: `npm run quality:gate` passou; 84 testes passaram, cobertura de statements 98,49% e build principal/subpath validado.
- OpenSpec backend: `openspec validate --all --strict --no-interactive` passou.
- Backend adapter slice: Ruff e mypy passaram após a policy de resiliência e lifecycle explícito.
- Docker: não executado porque o comando `docker` não está disponível neste ambiente Windows.
- Gap residual: cobertura first-party global ainda não atingiu o requisito final de 100%; os módulos com linhas faltantes permanecem listados pelo relatório `term-missing`.

```text
npx openspec validate --all --strict --no-interactive
python -m ruff check .
python -m ruff format --check .
python -m mypy app api scripts tests
python -m pytest --cov=app --cov=api --cov=scripts --cov-branch --cov-report=term-missing --cov-fail-under=100
python -m pip check
python -m pip_audit
docker build --check .
docker build -t hortelan-backend:verify .
```

Nos repositorios irmaos:

```text
npm run quality:gate
npm run release:gate
```

## Criterio de saida

O change so pode ser arquivado quando todos os cenarios normativos possuem evidencia, nenhum dado sensivel aparece nos artefatos, os tres repositorios passam seus gates completos, os quatro indicadores de cobertura atingem 100% no escopo mantido (ou cada exclusao possui justificativa aprovada), o OpenAPI nao apresenta drift e os riscos residuais estao documentados com owner e prazo.
