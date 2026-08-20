# ADR 003: ACID local, idempotencia duravel e outbox

- Status: aceito
- Data: 2026-08-20

## Decisao

Telemetria e seu evento outbox sao inseridos na mesma transacao SQL. Kafka, Mongo e Redis sao
efeitos eventuais; falha de publicacao mantem o evento pendente para reconciliacao.

Comandos e ledger exigem uma chave idempotente persistida com unique constraint, operacao,
fingerprint canonico e estado `processing`, `completed` ou `unknown`. O mesmo resultado pode ser
reproduzido somente em `completed`. Payload divergente conflita; `processing`/`unknown` bloqueiam
uma segunda execucao automatica.

## Consequencias

- o efeito nao duplica em retries normais e concorrentes;
- um crash no limite de um sistema externo produz outcome incerto, nao uma promessa falsa;
- ACID termina no banco relacional local; nao se declara exactly-once distribuido;
- reconciliadores devem publicar outbox com metrica, retry limitado e dead-letter operacional.
