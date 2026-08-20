# Hortelan Backend

API FastAPI da plataforma Hortelan, organizada em arquitetura hexagonal para telemetria IoT,
comandos de irrigacao, ledger e visoes operacionais. O projeto usa contratos estritos, OpenAPI
3.1, idempotencia persistente, outbox transacional, logs JSON e OpenTelemetry.

## Arquitetura

```text
HTTP / DTOs -> Application / use cases -> Domain ports -> Infrastructure adapters
                                                    |-> SQLAlchemy + SQLite/PostgreSQL
                                                    |-> PyMongo Async / MongoDB
                                                    |-> Redis, Kafka, AWS IoT e Web3
```

- `app/domain`: entidades e ports, sem dependencia de framework.
- `app/application`: casos de uso e politicas de aplicacao.
- `app/infrastructure`: adapters substituiveis e persistencia.
- `app/api`: DTOs Pydantic estritos, rotas e handlers seguros.
- `app/core`: settings, composicao, resiliência e observabilidade.
- `openspec`: fonte SDD; mudancas ficam ativas ate a verificacao final.

A decisao de manter a arquitetura hexagonal existente e introduzir apenas Repository,
Adapter e pequenas policies segue KISS/YAGNI: novos patterns precisam resolver um problema
observado, nao apenas aumentar a quantidade de abstracoes.

## Inicio rapido

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -e ".[dev]"
copy .env.example .env
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

Em Linux/macOS, use `.venv/bin/` e `cp`. A instalacao tambem funciona com `poetry install`.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI versionado: `docs/openapi.json`
- Liveness: `GET /health/live`
- Readiness: `GET /health/ready` (retorna 503 se a dependencia critica falhar)
- Metricas: `GET /metrics`

## Contratos e seguranca

Todos os DTOs rejeitam campos desconhecidos, validam identificadores/limites e normalizam datas
para UTC. Comandos e ledger exigem `Idempotency-Key` de 8 a 128 caracteres. Quando `API_KEY`
estiver configurada, envie tambem `X-API-Key`; producao falha no startup sem chave por padrao.

```bash
curl -X POST http://localhost:8000/api/v1/commands \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: irrigation-2026-08-20-001" \
  -d '{"device_id":"sensor-01","action":"irrigate","duration_seconds":120}'
```

Repetir a mesma chave e payload devolve o resultado salvo com `replayed: true`, sem repetir o
efeito. Reutilizar a chave com outro payload retorna 409. Falha depois da reserva marca o outcome
como incerto e impede uma repeticao cega.

Erros publicos nunca incluem stack, classe interna, causa, credencial ou o valor de entrada
invalido:

```json
{
  "error": {
    "code": "INFRASTRUCTURE_FAILURE",
    "message": "Nao foi possivel concluir a operacao externa.",
    "retryable": true,
    "details": {},
    "diagnostics": {
      "timestamp": "2026-08-20T12:00:00Z",
      "status_code": 502,
      "incident_id": "referencia-segura",
      "request_id": "request-seguro",
      "trace_id": null,
      "span_id": null
    }
  }
}
```

## Observabilidade

Cada linha de log e um objeto JSON allowlist-first com servico, ambiente, evento, severidade,
request/trace/span/incident. Excecoes internas incluem classe, modulo, arquivo, funcao, linha,
mensagem e stack completos depois de redaction de email, tokens, secrets, paths de usuario e query
strings. Payloads e headers arbitrarios nao entram no log.

OTEL so instala o exporter quando `OTEL_ENABLED=true` e `OTEL_EXPORTER_OTLP_ENDPOINT` esta
configurado. Sem endpoint, nao existe exporter de console nem tentativa silenciosa de rede.
As metricas Prometheus usam templates de rota para evitar cardinalidade por identificador.

Consulte [runbook de incidentes](docs/runbook-observability.md) e
[ADR de observabilidade](docs/adr/002-observability-and-safe-errors.md).

## ACID e consistencia

| Fluxo | Garantia |
|---|---|
| Telemetria SQL + evento outbox | ACID na mesma transacao local |
| Publicacao Kafka | Eventual; outbox pendente permite reconciliacao |
| Projecao Mongo e cache Redis | Eventual e degradavel |
| Comandos AWS IoT | At-most-one effect por chave enquanto o store SQL estiver disponivel; outcome incerto e bloqueado |
| Ledger Web3 | Resultado externo idempotentemente reservado; sem alegacao de transacao distribuida |

Nao existe uma alegacao falsa de ACID entre SQL, Kafka, Mongo, Redis, AWS e blockchain. Veja
[ADR de consistencia](docs/adr/003-acid-idempotency-and-outbox.md).

## Configuracao

As principais variaveis estao em `.env.example`:

- aplicacao: `APP_NAME`, `APP_VERSION`, `APP_ENV`, `APP_PORT`, `LOG_LEVEL`;
- seguranca: `API_KEY`, `ENFORCE_API_KEY_IN_PRODUCTION`, CORS e rate limit;
- persistencia: `RELATIONAL_DB_URL`, `MONGO_URL`, `REDIS_URL`;
- integracoes: Kafka, AWS IoT e Web3;
- telemetria: `OTEL_*` e `ENABLE_METRICS`;
- resiliência: timeout externo/health e parametros do circuit breaker.

Secrets sao `SecretStr`, nunca devem ser commitados e devem vir do secret manager do ambiente.

## Qualidade e testes

```bash
.venv/Scripts/ruff check app api scripts tests
.venv/Scripts/ruff format --check app api scripts tests
.venv/Scripts/mypy app api scripts
.venv/Scripts/pytest -q --cov=app --cov=api --cov=scripts --cov-report=term-missing
.venv/Scripts/bandit -q -r app api scripts
.venv/Scripts/python -m pip_audit --local --skip-editable --progress-spinner off
npx --yes @fission-ai/openspec@1.10.0 validate --all --strict --no-interactive
```

O gate atual exige no minimo 90% global e os modulos criticos novos de idempotencia/contratos
estao em 100%. O plano progressivo para statements, branches, functions e lines em 100% esta em
[test-plan.md](openspec/changes/full-sdd-production-hardening/test-plan.md); cobertura nao e
inflada removendo adapters ou scripts do denominador.

O workflow `quality.yml` valida Conventional Commits, OpenSpec, Ruff, formato, MyPy, Bandit,
OpenAPI drift, testes/cobertura, dependencias e build Docker. Subjects aceitos seguem
`tipo(escopo): descricao`, por exemplo `feat(api): add idempotent command dispatch`.

## SDD com OpenSpec

```bash
npx --yes @fission-ai/openspec@1.10.0 list
npx --yes @fission-ai/openspec@1.10.0 validate --all --strict --no-interactive
```

A mudanca ativa e `full-sdd-production-hardening`, com proposal, design, specs por capability,
tasks e test plan. A pasta `.agents/skills/openspec-*` e a integracao oficial do OpenSpec para
Codex. Nao ha estrutura first-party do Claude Code neste repositorio.

## Docker

```bash
docker build -t hortelan-backend .
docker run --rm -p 8000:8000 --env-file .env hortelan-backend
```

A imagem e multi-stage, executa como UID/GID 10001 e possui healthcheck sem depender de `curl`.

## Licenca

MIT. Consulte [LICENSE](LICENSE).
