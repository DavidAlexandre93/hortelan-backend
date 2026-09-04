# Auditoria e arquitetura-alvo — full-sdd-production-hardening

## Evidencias verificadas em 2026-09-04

- `pytest -q`: 72 testes passaram.
- Ruff, formatacao Ruff e MyPy: passaram.
- `pip check` e `pip-audit --local --skip-editable`: passaram sem vulnerabilidades conhecidas.
- OpenSpec estrito: passou.
- O container e nao-root, possui healthcheck e usa FastAPI com camadas hexagonais.

## Achados priorizados

### Alta prioridade

1. **Schema sem migracoes versionadas**: `app/infrastructure/persistence/relational_repository.py` executa `Base.metadata.create_all()` no startup. Isso nao versiona alteracoes, nao detecta drift nem oferece rollback controlado. O banco de producao pode divergir silenciosamente do modelo.
2. **Rate limit nao escala horizontalmente**: `RateLimiter` guarda contadores em memoria do processo e usa apenas o host do cliente. Com varias replicas, o limite efetivo e multiplicado e proxies podem concentrar ou mascarar identidades. O contrato deve distinguir modo local de backend compartilhado e recusar configuracao de producao sem coordenacao distribuida.
3. **Outbox sem relay operacional**: existem tabelas e operacoes de leitura/marcacao, mas nao ha worker/endpoint/job que publique eventos pendentes, aplique retry/backoff ou trate poison events. A garantia de reprocessamento esta documentada, mas incompleta na implementacao.
4. **Autorizacao coarse-grained**: comandos e ledger usam uma API key global; leituras e endpoints de cobertura sao publicos. Nao ha identidade, escopo ou auditoria por ator. A API key e adequada para integracao interna simples, mas deve ser explicitamente limitada a esse modelo e nunca apresentada como autorizacao por usuario.

### Media prioridade

5. **Inicializacao global do container**: `get_container()` usa `lru_cache`, tornando lifecycle e substituicao por teste dependentes de estado global. O risco e maior em testes paralelos, reload e processos long-lived; a composicao deve continuar simples, mas permitir override/factory no app.
6. **Escritas externas no caminho de request**: AWS IoT e Web3 sao chamados sincronicamente dentro dos casos de uso. Timeout e circuit breaker existem, mas nao ha retry seguro padronizado; retry automatico so deve ser habilitado para operacoes demonstradamente idempotentes.
7. **Consultas sem ordenacao deterministica completa**: a listagem de telemetria ordena apenas por `captured_at`; empates podem mudar entre paginas futuras. O endpoint atual ainda usa `limit`, sem cursor e sem metadados.
8. **`create_all` e health acoplados ao processo**: o startup falha ou altera schema em runtime, misturando deploy da aplicacao com administracao do banco.

### Baixa prioridade

9. **Contrato de erro e headers**: handlers e middleware cobrem os caminhos atuais, mas a matriz normativa de todos os status precisa de testes de contrato, especialmente 405/429/503 e respostas geradas antes da rota.
10. **Observabilidade**: metricas sao in-process; nao ha exportador Prometheus externo nem SLO/alertas versionados. Isso e aceitavel nesta fronteira, desde que o runbook trate scraping e limites de cardinalidade.

## Arquitetura-alvo simples

- **Entrada**: FastAPI, DTOs Pydantic estritos, middleware de correlacao/rate limit/headers e handlers de erro seguros.
- **Aplicacao**: casos de uso finos, policies de idempotencia e resiliencia, sem dependencias de FastAPI ou SDKs externos.
- **Dominio**: entidades, invariantes e ports pequenos; nenhum acesso a rede ou banco.
- **Persistencia**: SQLAlchemy async para estado transacional local, Alembic para evolucao versionada e indices/constraints declarados; outbox na mesma transacao.
- **Integracoes**: adapters com timeout finito, circuit breaker e classificacao de falha; retry somente quando a operacao for segura/idempotente. Mongo, Redis, Kafka, AWS e Web3 permanecem consistencia eventual.
- **Composicao**: factory explicita do container com override para testes; lifecycle fecha recursos e nao executa migracao implicitamente.
- **Operacao**: migration job separado do processo web, readiness sem efeitos colaterais, worker de outbox somente quando houver publisher configurado.

## Limites e decisoes

- Nao adicionar broker, CQRS, Event Sourcing, RAG ou camada de LLM: nao existe requisito funcional concreto neste backend.
- Nao inventar autenticacao de usuario/JWT sem consumidor e contrato definidos; manter API key para integracao interna, documentando seus limites e exigindo escopos quando surgir identidade.
- Nao trocar Redis por outro mecanismo: ele e opcional para cache e pode ser o coordenador compartilhado de rate limit quando habilitado.
- Toda mudanca de schema deve ser aditiva e reversivel por migracao; deploy aplica migracoes antes de habilitar a nova versao.

## Riscos residuais

- Sem um backend compartilhado de rate limit, o modo local nao oferece garantia global entre replicas.
- Sem contrato downstream de deduplicacao, AWS IoT e Web3 nao oferecem exatamente-uma-vez fora da fronteira local.
- O relay de outbox precisa de ownership operacional, destino Kafka e politica de poison event definidos pelo ambiente.
