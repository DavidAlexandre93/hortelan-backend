# Runbook: indisponibilidade e incidentes

## Triagem

1. Copie o `incident_id` mostrado pela interface ou pelo envelope HTTP.
2. Filtre o agregador de logs por `incident_id`; depois correlacione `request_id` e `trace_id`.
3. Verifique `/health/live`. Falha indica processo indisponivel; sucesso com `/health/ready` 503
   indica dependencia critica indisponivel.
4. Consulte `/metrics` por error rate/latencia da rota, erro SQL e integracao externa.

## Diagnostico

- `exception.class`, `file`, `function` e `line` localizam a origem;
- `exception.stack` contem a cadeia completa sanitizada;
- `error_code` e `retryable` separam falha esperada, transitoria e interna;
- `idempotency_records` com `unknown` nao devem ser reexecutados cegamente;
- `outbox_events` pendentes devem ser reconciliados antes de qualquer replay manual.

Nunca copie payload, API key, email ou private key para tickets. Se um log contiver PII, trate como
incidente de seguranca e corrija a allowlist/redaction antes de ampliar a coleta.

## Comunicacao ao usuario

A interface deve informar indisponibilidade temporaria, oferecer `Tentar novamente` e exibir apenas
a referencia segura do incidente. Stack, classe interna, host, query e causa nunca aparecem na tela.
