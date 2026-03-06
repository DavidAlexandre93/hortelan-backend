# Revisão completa da aplicação Hortelan Backend

_Data da revisão: 2026-03-06_

## Escopo e método

Esta revisão foi executada por inspeção estática do código, documentação e pipeline, com validações locais mínimas:

- `pytest -q` (falhou na coleta por incompatibilidade de runtime local Python 3.10 x código Python 3.11+).
- `python -m compileall app api tests` (ok).

---

## 1) Arquitetura & Design

### Pontos fortes
- Estrutura em camadas alinhada à arquitetura hexagonal (`domain`, `application`, `infrastructure`, `api`, `core`).
- Ports/Adapters definidos por interfaces abstratas no domínio.
- Casos de uso separados (`ingest_telemetry`, `dispatch_command`, `register_ledger`).

### Lacunas
- **Acoplamento da camada API com detalhes analíticos internos**: `routes.py` importa símbolos “internos” (`_build_requirement_detail`, `_slugify_requirement`) do serviço de cobertura, quebrando encapsulamento.
- **Container de dependências manual e singleton global** (`get_container` com `lru_cache`) dificulta substituição por request e testes de integração mais isolados.
- **Responsabilidades misturadas em adapters**: parte de circuit breaker está implementada, mas com fluxo quebrado e código inalcançável (ver seção de Clean Code).

### Diagnóstico geral
Arquitetura base é boa e coerente, mas há inconsistências de implementação que reduzem os ganhos de design e testabilidade.

---

## 2) Clean Code & Qualidade

### Pontos fortes
- Nomes de classes/casos de uso e entidades são claros.
- Tipagem está bem difundida.
- Schemas Pydantic com exemplos e limites de entrada básicos.

### Problemas relevantes
- **Código inalcançável após `raise`** em múltiplos adapters (`aws_iot_adapter.py`, `kafka_adapter.py`, `redis_adapter.py`, `web3_adapter.py`), tornando parte da lógica de circuit breaker inefetiva.
- **Blocos `except` redundantes/mal posicionados** nos adapters (caminhos de sucesso/falha ficam incorretos).
- **Duplicação de fluxo de transação no adapter Web3**: tentativa inicial e nova tentativa com lógica quase idêntica no mesmo método.
- **Configuração de logging duplicada** (`logging.basicConfig` em `main.py` + `configure_logging`), risco de comportamento inconsistente em produção.

### Diagnóstico geral
A base é legível, porém há dívida técnica de confiabilidade no fluxo de erro/sucesso de integrações externas.

---

## 3) Boas práticas de API

### Pontos fortes
- Prefixo de versão (`/api/v1`) já aplicado.
- Validação de input com Pydantic (ex.: `limit`, faixas de campos).
- Endpoints de health e métricas disponíveis.

### Lacunas
- **Contratos de erro não padronizados** para erros de negócio/domínio (há handler genérico 500, mas não há envelope padronizado por família de erro 4xx/5xx).
- **Paginação limitada**: lista de telemetria usa apenas `limit`, sem `cursor/offset` e sem metadados de paginação.
- **Status codes simplificados**: endpoints de criação retornam ACK, mas sem status semântico mais específico em fluxos alternativos (ex.: degradação parcial).

---

## 4) Segurança (obrigatório)

### Pontos fortes
- Segredos via configuração (settings/env), sem hardcode explícito de credenciais no código.
- CORS configurável por ambiente.

### Riscos críticos
- **Sem autenticação/autorização** nos endpoints (incluindo ações operacionais como `/commands` e `/ledger`).
- **Ausência de rate limit/throttling**.
- **Sem headers de segurança HTTP adicionais** (CSP, HSTS, X-Frame-Options etc.).
- **Sem evidência de proteção CSRF para cenários com credenciais em browser** (hoje API parece stateless, mas ainda sem política documentada).
- **Sem evidência de SAST/SCA no pipeline** (CI atual executa compile + testes, sem auditoria de dependências).

### Riscos médios
- Logs incluem `query_params` em erro global; dependendo do endpoint, pode expor dados sensíveis.

---

## 5) Tratamento de erros & confiabilidade

### Pontos fortes
- Uso de exceções de infraestrutura/transiente (`InfrastructureError`, `TransientIntegrationError`).
- Estratégia de degradação controlada no use case de ingestão (persistência local antes de integração assíncrona).

### Lacunas
- **Circuit breaker parcialmente quebrado por fluxo inválido** (código inalcançável).
- **Sem timeouts explícitos** para chamadas externas (AWS IoT, Redis, Web3, Mongo em nível de operação).
- **Sem política de retry/backoff explícita** para integrações críticas.
- **Sem transação unificada entre persistência relacional e documental** (consistência eventual não documentada).
- **Sem idempotência explícita** para comandos/ledger (risco de duplicidade em reenvio de requisição).

---

## 6) Performance & escalabilidade

### Pontos fortes
- Índice em `device_id` na tabela de telemetria.
- Limite máximo no endpoint de listagem (`le=200`).
- Cache para leitura rápida de último comando/telemetria.

### Lacunas
- **Sem estratégia de paginação robusta para grande volume** (cursor + ordenação determinística).
- **Sem métricas de recursos (CPU/memória/fila)**, apenas métricas HTTP custom.
- **Sem jobs/fila para operações potencialmente lentas** no caminho de request (ex.: gravações múltiplas e integrações externas em sequência).

---

## 7) Banco de dados & migrações

### Pontos fortes
- Modelo relacional simples e objetivo para telemetria.

### Lacunas
- **Sem sistema de migração versionada** (Alembic ou equivalente).
- **Constraints de integridade básicas ausentes** (ex.: checks de faixas no DB, unique/idempotency keys quando aplicável).
- **Modelo relacional não persiste `metadata`**; divergência entre armazenamento SQL e documento.

---

## 8) Observabilidade

### Pontos fortes
- Middleware com `request_id`, `trace_id`, `span_id`.
- Endpoint `/metrics` em formato Prometheus.
- Healthcheck, liveness e readiness separados.
- Integração OpenTelemetry opcional.

### Lacunas
- **Métricas incompletas para operação** (não há percentis/histograma, erro por dependência externa, saturação de recursos).
- **Ausência de alertas/SLO documentados**.
- **Tracing distribuído depende de configuração externa e não tem guia operacional no repo**.

---

## 9) Testes

### Pontos fortes
- Existe suíte para cobertura funcional de endpoints analíticos e observabilidade.

### Lacunas
- **Falha de execução local em Python 3.10** por uso de `StrEnum` (projeto requer 3.11+, ambiente local não aderente).
- **Sem evidência de testes E2E, contrato com sistemas externos e testes de segurança**.
- **Sem gate de cobertura mínima na CI**.

---

## 10) Frontend

Não se aplica no escopo do repositório atual (backend-only).

---

## 11) CI/CD & qualidade automatizada

### Pontos fortes
- Pipeline com detecção de mudanças para reduzir custo de execução.
- Build básico com `compileall` + testes.
- Deploy condicional para Vercel em `main`.

### Lacunas
- **Sem lint/format obrigatório** na pipeline.
- **Sem SAST/SCA**.
- **Sem gate de cobertura**.
- **Sem estratégia de versionamento/release automatizada** (tags/changelog).

---

## 12) Docker/Infra

- Não há `Dockerfile`/`docker-compose` versionados no repositório.
- Falta documentação de execução local com serviços dependentes conteinerizados (Kafka/Redis/Mongo).

---

## 13) Documentação

### Pontos fortes
- README bem estruturado, com endpoints, setup básico e variáveis.
- Existem documentos complementares em `docs/`.

### Lacunas
- Falta `.env.example` versionado.
- Falta troubleshooting detalhado e guia de contribuição.
- Falta ADRs formais para decisões críticas (persistência dupla, cache fallback em memória, estratégia de resiliência).

---

## 14) Lista priorizada de problemas

## Alta prioridade
1. Corrigir fluxos de erro/sucesso e código inalcançável nos adapters (circuit breaker efetivamente quebrado).
2. Implementar autenticação/autorização para endpoints sensíveis (`commands`, `ledger`, leitura operacional).
3. Adicionar proteção de API: rate limit, política de CORS por ambiente, headers de segurança.
4. Definir estratégia de timeout/retry/backoff para integrações externas.
5. Introduzir migrações versionadas (Alembic) e política de evolução de schema.

## Média prioridade
1. Padronizar envelope de erros (código, mensagem, correlação, causa externa).
2. Melhorar paginação (cursor + metadados).
3. Adicionar lint/format + coverage gate + SAST/SCA no CI.
4. Criar `docker-compose` para ambiente de desenvolvimento com dependências.
5. Endurecer logs para evitar vazamento de dados sensíveis.

## Baixa prioridade
1. Consolidar configuração de logging (evitar duplicidade).
2. Publicar ADRs e runbooks de observabilidade.
3. Refinar contratos de snapshot/telemetry para consistência de serialização.

---

## Recomendações com justificativa e impacto

1. **Refatorar adapters com template comum de resiliência** (permit/check + operação + sucesso/falha).  
   **Impacto:** reduz falhas silenciosas e melhora previsibilidade operacional.

2. **Adicionar camada de segurança transversal** (auth middleware + autorização por escopo/role + rate limiting).  
   **Impacto:** reduz risco de abuso e acesso indevido.

3. **Padronizar erro de API** com modelo único (ex.: `code`, `message`, `details`, `trace_id`).  
   **Impacto:** melhora DX, monitoramento e suporte.

4. **Instrumentar testes de integração para Redis/Kafka/Mongo em ambiente controlado**.  
   **Impacto:** captura regressões reais de integração antes do deploy.

5. **Adotar Alembic e constraints no banco**.  
   **Impacto:** evoluções de schema reproduzíveis e mais segurança de dados.

---

## Sugestões de refatoração (antes/depois)

### Exemplo 1 — fluxo de circuit breaker em adapter

**Antes (problema):** `raise` seguido de `on_success()`/`on_failure()` inalcançáveis em blocos `except`.

**Depois (proposta):**

```python
try:
    breaker.call_permitted()
    do_external_call()
except CircuitBreakerOpenError:
    return degraded_response
except Exception as exc:
    breaker.on_failure()
    raise TransientIntegrationError("...") from exc
else:
    breaker.on_success()
```

### Exemplo 2 — padronização de erro de API

**Antes (problema):** resposta de erro varia por origem e não há contrato único para 4xx/5xx.

**Depois (proposta):**

```json
{
  "error": {
    "code": "INTEGRATION_TIMEOUT",
    "message": "Falha temporária ao publicar telemetria",
    "trace_id": "...",
    "details": {"dependency": "kafka"}
  }
}
```

### Exemplo 3 — paginação robusta

**Antes (problema):** apenas `limit`.

**Depois (proposta):** `GET /telemetry?cursor=<token>&limit=50&device_id=...` com payload:

```json
{
  "items": [...],
  "next_cursor": "...",
  "has_more": true
}
```

---

## Plano de ação sugerido

## Quick wins (1–2 sprints)
1. Corrigir fluxos dos adapters e cobrir com testes unitários focados em falha/sucesso/circuit aberto.
2. Adicionar lint (`ruff`/`black`) e coverage gate na CI.
3. Criar `.env.example` e atualizar README com troubleshooting.
4. Definir e implementar error shape padrão na API.

## Refactor maior (3–6 sprints)
1. Introduzir autenticação/autorização por token e políticas de acesso por endpoint.
2. Adotar Alembic + constraints + idempotency key para operações críticas.
3. Evoluir observabilidade com métricas de dependências externas + alertas SLO.
4. Implementar suíte de integração com dependências reais via containers.

---

## Veredito executivo

A aplicação apresenta **boa base arquitetural** e documentação acima da média para estágio inicial. Entretanto, há **gaps críticos de segurança e confiabilidade operacional** que impedem classificação de prontidão para produção sem mitigação prévia. Recomenda-se tratar primeiro os itens de **Alta prioridade** para estabilização e hardening da plataforma.
