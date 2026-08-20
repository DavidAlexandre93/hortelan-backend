# ADR 002: diagnostico interno completo e erro publico seguro

- Status: aceito
- Data: 2026-08-20

## Decisao

Logs sao JSON allowlist-first e correlacionados por request, trace, span e incident. Excecoes 5xx
registram internamente classe, modulo, arquivo, funcao, linha, mensagem e stack depois de redaction.
O envelope HTTP contem apenas codigo estavel, mensagem segura, retryable, detalhes sanitizados e
identificadores de correlacao.

OTEL exporta spans apenas quando um endpoint OTLP for explicitamente configurado. Health, metrics
e logs continuam funcionais sem collector.

## Consequencias

- suporte pesquisa pelo `incident_id` sem expor implementacao ao cliente;
- PII, secrets, input invalido e headers arbitrarios nao atravessam a fronteira publica;
- labels usam templates de rota e nao IDs de recursos;
- o frontend pode mostrar uma referencia segura e uma acao de retry.
