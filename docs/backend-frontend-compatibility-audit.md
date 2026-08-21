# Auditoria de Compatibilidade Backend ↔ Frontend

## Contexto da validação

Foi realizada uma verificação completa dos contratos HTTP expostos pelo backend (rotas, schemas, CORS, health checks e respostas), com foco em compatibilidade de consumo por frontend.

### Escopo da validação

O repositório do frontend está disponível localmente em `../hortelan-frontend` e foi comparado com as rotas e o OpenAPI deste backend. Também foram executados os quality gates dos dois projetos.

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

## Matriz real de consumo do frontend

| Módulo frontend | Caminhos chamados | Situação no backend |
| --- | --- | --- |
| `operationalApi` | `/monitoring`, `/alerts`, `/reports`, `/subscription`, `/integrations` | **Ausentes**; o backend retorna 404 e não possui contratos equivalentes |
| `authApi` | `/auth/login`, `/auth/register`, `/auth/social-login`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/validate-reset-token` | **Ausentes** |
| `accountSecurityApi` | `/auth/mfa/settings`, `/auth/consents`, `/auth/account/deletion-request`, `/auth/account/deactivate`, `/auth/account/export`, `/profile`, `/auth/trusted-devices/*` | **Ausentes** |
| Monitoramento live | `/monitoring` | **Desligado por padrão** via `VITE_ENABLE_LIVE_DATA=false`; a tela usa dados demo |
| Backend IoT disponível | `/api/v1/telemetry`, `/api/v1/commands`, `/api/v1/devices/*`, `/api/v1/ledger` | **Implementado**, mas o cliente frontend atual não chama esses paths |
| Health | `/health`, `/health/live`, `/health/ready` | **Implementado**, mas o cliente base não possui chamada específica de readiness |

### Divergências de contrato identificadas

1. **Prefixo:** o backend exige `/api/v1`; o frontend monta chamadas sem esse prefixo.
2. **Autenticação:** o frontend espera sessão/usuário em endpoints `/auth/*`; o backend implementa apenas `X-API-Key` para comandos e ledger.
3. **Formato:** o frontend espera campos camelCase como `generatedAt`, `updatedAt` e `deviceId`; os DTOs atuais do backend usam snake_case como `captured_at` e `device_id`.
4. **Domínio operacional:** as respostas esperadas pelo frontend (`monitoring`, `alerts`, `reports`, assinatura e integrações) não têm DTOs nem casos de uso correspondentes no backend.
5. **CORS para mutações:** o frontend usa `PUT` e `DELETE`; o backend agora permite esses métodos, além de `PATCH`, na configuração padrão de CORS.
6. **Integrações públicas:** a página de integrações do frontend informa que os controles são ilustrativos e não iniciam conexões externas. Não há chamadas efetivas a clima, pagamentos, logística, e-mail, push, WhatsApp ou SMS.

---

## Verificações de compatibilidade para frontend

### 1) Versionamento e previsibilidade de rotas

⚠️ O backend usa prefixo fixo `/api/v1`, mas o `apiClient` atual do frontend não o adiciona. A configuração de `VITE_API_BASE_URL` precisa apontar para a origem e o cliente precisa centralizar o prefixo, ou a variável precisa conter `/api/v1`.

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

## Resultado

O backend possui conexões configuradas para Redis, Kafka, MongoDB, AWS IoT e Web3, com timeout, circuit breaker e lifecycle. Essas conexões são infraestrutura disponível e não equivalem a endpoints consumíveis pelo frontend.

Para o frontend atual, a compatibilidade é **parcial**: os endpoints IoT e estratégicos existem, porém não são consumidos; os módulos de autenticação, conta e operações que o frontend chama ainda não existem no backend. Portanto, não é seguro afirmar que “muitos endpoints do frontend” já estão atendidos.

### Risco residual até validação final com frontend real

- implementar ou remover conscientemente os contratos `/auth/*`, `/profile` e operacionais esperados pelo frontend
- alinhar o prefixo `/api/v1` no `apiClient`
- definir o modelo de identidade: sessão/JWT/OAuth ou adaptar o frontend para `X-API-Key` somente em uso interno
- criar DTOs e casos de uso para monitoramento, alertas, relatórios e integrações antes de habilitar `VITE_ENABLE_LIVE_DATA`
- configurar o domínio de produção em `CORS_ORIGINS`

---

## Checklist de validação final (quando houver acesso ao frontend)

1. Alinhar `baseURL`/prefixo do frontend com `/api/v1`.
2. Implementar e validar os contratos de autenticação e conta antes de ativar o adapter backend do frontend.
3. Validar telas que consomem:
   - lista de telemetria,
   - último comando,
   - snapshot por dispositivo,
   - relatórios estratégicos.
4. Garantir fallback de UI para retorno `null` em endpoints `latest`.
5. Confirmar domínio do frontend em `CORS_ORIGINS` no ambiente alvo.
6. Testar fluxo completo com browser (network tab) e validar códigos HTTP/shape JSON.
