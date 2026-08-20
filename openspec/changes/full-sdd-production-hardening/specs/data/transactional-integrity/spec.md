## Purpose

Estabelece garantias verificaveis de atomicidade local, idempotencia e consistencia para operacoes que podem ser repetidas ou atravessam mais de um sistema.

## ADDED Requirements

### Requirement: Idempotencia persistente de mutacoes criticas
Comandos e registros de ledger SHALL exigir Idempotency-Key valida, associar a chave ao fingerprint canonico da operacao e armazenar reserva e resultado em repositorio compartilhado com unicidade atomica.

#### Scenario: Replay do mesmo comando
- **WHEN** o cliente repete a mesma operacao com a mesma chave e payload
- **THEN** a API retorna o resultado confirmado anteriormente sem repetir o efeito externo

#### Scenario: Reuso conflitante de chave
- **WHEN** a mesma chave e usada com payload ou operacao diferente
- **THEN** a API retorna 409 e nao executa nenhum efeito

#### Scenario: Resultado externo incerto
- **WHEN** a operacao reservada nao possui resultado confirmado devido a interrupcao
- **THEN** a API informa outcome unknown/in progress e MUST NOT executar automaticamente o efeito outra vez

### Requirement: Transacoes ACID no banco relacional
Cada mudanca relacional SHALL executar em transacao com commit atomico, rollback em falha e constraints de integridade; testes concorrentes MUST comprovar isolamento suficiente para unicidade e idempotencia.

#### Scenario: Falha durante escrita
- **WHEN** uma operacao relacional falha antes do commit
- **THEN** nenhuma parte da transacao fica visivel e a conexao permanece reutilizavel

### Requirement: Limites explicitos de consistencia distribuida
A API MUST declarar que SQL, documento, mensageria, cache, IoT e blockchain nao compartilham uma transacao ACID; efeitos pos-commit SHALL usar outbox ou estado de reconciliacao quando a perda nao for aceitavel.

#### Scenario: Publicacao indisponivel apos persistencia
- **WHEN** a telemetria foi confirmada no SQL e Kafka esta indisponivel
- **THEN** o dado confirmado permanece consultavel e a entrega pendente fica observavel e reprocessavel sem duplicar o registro

