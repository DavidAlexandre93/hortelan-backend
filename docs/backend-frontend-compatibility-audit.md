# Auditoria de Compatibilidade Backend ↔ Frontend

## Contexto da validação

Foi realizada uma verificação completa dos contratos HTTP expostos pelo backend (rotas, schemas, CORS, health checks e respostas), com foco em compatibilidade de consumo por frontend.

### Limitação de ambiente

Não foi possível clonar/inspecionar diretamente o repositório informado do frontend (`https://github.com/DavidAlexandre93/hortelan-frontend`) neste ambiente, por bloqueio de conectividade de rede (`403 CONNECT tunnel failed`).

Com isso, esta auditoria valida:

1. **Consistência interna dos contratos do backend** (OpenAPI implícito por FastAPI + schemas Pydantic).
2. **Prontidão para integração com frontend** com base em padrões de consumo REST.
3. **Possíveis pontos de atenção** que normalmente causam quebra no frontend.

---

## Contrato de API exposto pelo backend

Base path versionado: **`/api/v1`**.

### Endpoints operacionais

- `POST /api/v1/telemetry`
- `GET /api/v1/telemetry`
- `GET /api/v1/telemetry/latest/{device_id}`
- `POST /api/v1/commands`
- `GET /api/v1/commands/latest/{device_id}`
- `POST /api/v1/ledger`
- `GET /api/v1/devices/{device_id}/snapshot`

### Endpoints institucionais/observabilidade

- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`
- `GET /docs`
- `GET /redoc`

### Endpoints estratégicos (cobertura de requisitos)

- `GET /api/v1/requirements`
- `GET /api/v1/strategic/coverage`
- `GET /api/v1/product/readiness`
- `GET /api/v1/product/modules/{module_slug}`
- `GET /api/v1/requirements/{slug}` (dinâmico por catálogo)

---

## Verificações de compatibilidade para frontend

### 1) Versionamento e previsibilidade de rotas

✅ O backend usa prefixo fixo `/api/v1`, o que facilita configurar uma camada de `apiClient` no frontend sem hardcode disperso.

### 2) Contratos de payload de entrada

✅ `TelemetryIn`, `IrrigationCommandIn` e `LedgerRecordIn` têm campos obrigatórios e validações claras (faixas numéricas e limites), reduzindo ambiguidades no frontend.

### 3) Contratos de payload de saída

✅ Os endpoints de leitura pontual agora retornam resposta tipada opcional, sem uso de objeto vazio (`{}`):

- `GET /api/v1/telemetry/latest/{device_id}` → `TelemetryOut | null`
- `GET /api/v1/commands/latest/{device_id}` → `CommandSnapshotOut | null`

Isso reduz ambiguidade no frontend: o estado "sem dados" passa a ser `null` explícito.

### 4) CORS

⚠️ O backend permite, por padrão, apenas:

- `http://localhost:3000`
- `http://localhost:5173`

Se o frontend em produção usar outro domínio, será necessário configurar `CORS_ORIGINS` no deploy para evitar bloqueio no navegador.

### 5) Datas/horários

✅ O contrato foi alinhado para tipagem temporal consistente no comando:

- `AckResponse.timestamp`: `datetime` (ISO)
- `CommandSnapshotOut.sent_at`: `datetime` (ISO)

Também foi mantida compatibilidade retroativa no backend para cache legado com chave `created_at`, convertendo internamente para `sent_at`.

### 6) Estado de saúde para boot do frontend

✅ Endpoints de health/liveness/readiness estão disponíveis e podem ser usados por tela de status operacional ou por mecanismo de fallback/retry do frontend.

---

## Conclusão

Sem acesso direto ao código do frontend neste ambiente, **não é possível afirmar aderência 1:1** entre chamadas reais do frontend e este backend.

Entretanto, o backend está **estruturalmente pronto para consumo por frontend SPA** e possui contratos consistentes para os fluxos principais.

### Risco residual até validação final com frontend real

- rota/baseURL divergente no cliente
- domínio de produção não incluído em `CORS_ORIGINS`

---

## Checklist de validação final (quando houver acesso ao frontend)

1. Confirmar `baseURL` do frontend apontando para backend com prefixo `/api/v1`.
2. Validar telas que consomem:
   - lista de telemetria,
   - último comando,
   - snapshot por dispositivo,
   - relatórios estratégicos.
3. Garantir fallback de UI para retorno `null` em endpoints `latest`.
4. Confirmar domínio do frontend em `CORS_ORIGINS` no ambiente alvo.
5. Testar fluxo completo com browser (network tab) e validar códigos HTTP/shape JSON.
