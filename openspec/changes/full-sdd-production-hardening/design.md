## Context

Ver `proposal.md` para a motivacao. O backend ja separa dominio, casos de uso, portas e adapters; os problemas estao principalmente nos contratos de borda, no composition root global, na seguranca de diagnosticos e na ausencia de garantias persistentes para repeticao e efeitos distribuidos. Os frontends irmaos ja possuem OpenSpec e esperam health, correlacao e idempotencia que hoje o backend nao garante.

## Goals / Non-Goals

**Goals:**

- Endurecer as fronteiras existentes sem trocar FastAPI ou reescrever regras estaveis.
- Tornar garantias de seguranca, idempotencia, ACID local e consistencia eventual explicitas e testaveis.
- Entregar um gate unico e reproduzivel, com artefatos SDD auditaveis.

**Non-Goals:**

- Criar exatamente-uma-vez entre sistemas que nao compartilham coordenador transacional.
- Adicionar framework de DI, service mesh, broker alternativo ou UI dentro deste repositorio.
- Converter catálogos estaticos de cobertura em um dominio complexo sem demanda funcional.

## Decisions

### 1. Evoluir a arquitetura hexagonal existente

Casos de uso continuam dependendo de portas pequenas e o composition root instancia adapters. Protocolos tipados e factories simples substituem singletons apenas nos pontos que precisam de teste ou lifecycle explicito. Esta decisao aplica Dependency Inversion e Adapter ja presentes. Uma migracao total para outra estrutura foi rejeitada por alto churn e baixo ganho, em respeito a KISS/YAGNI.

### 2. DTO base estrito e enums nos limites HTTP

Contratos operacionais herdam configuracao comum que rejeita campos extras e serializa UTC. Enums cobrem estados, acoes e codigos limitados; identificadores continuam value strings validadas para nao criar classes sem comportamento. O OpenAPI gerado pelo FastAPI e normalizado e verificado em CI. Manter dicionarios `Any` foi rejeitado porque transfere falha de contrato para runtime e para o frontend.

### 3. Erros publicos e diagnosticos internos sao modelos diferentes

O cliente recebe somente um envelope seguro com incident/request/trace id e retryability. O logger JSON registra, por allowlist, classe, arquivo, linha, funcao, causa e stack completa via `exc_info`. Redacao ocorre antes da serializacao e nunca registra body ou query. Este desenho evita a falsa escolha entre observabilidade e privacidade; retornar traceback em ambiente de desenvolvimento foi rejeitado porque respostas podem ser copiadas ou capturadas por proxies.

### 4. OTEL usa contexto real e falha aberto

O middleware le o span OpenTelemetry ativo apos instrumentacao, aceita apenas `traceparent` valido pela instrumentacao e usa ids locais somente como fallback. OTLP e habilitado apenas com endpoint; sem endpoint, tracing exportado fica desativado em vez de imprimir spans misturados aos logs JSON. Instrumentacoes adicionais ficam fora deste change ate haver collector e budget operacional definidos.

### 5. Idempotencia usa reserva duravel com estado explicito

Um Repository de idempotencia persiste chave, operacao, fingerprint canonico, estado e resposta sob unique constraint. A aplicacao reserva antes do efeito, rejeita fingerprints conflitantes, reproduz resultado concluido e nao repete estado `processing/unknown`. O mesmo id e propagado ao comando externo para permitir deduplicacao downstream. Redis `SET NX` isolado foi rejeitado porque eviction e fallback local nao fornecem durabilidade; reexecutar apos timeout foi rejeitado porque pode duplicar irrigacao ou ledger.

### 6. ACID e local; efeitos externos usam consistencia explicita

SQLAlchemy controla transacoes relacionais com commit/rollback e constraints. Mongo, Kafka, Redis, AWS IoT e Web3 nao participam dessa transacao. Telemetria persiste primeiro no SQL e registra outbox na mesma transacao; relay/reconciliacao entrega efeitos externos. Nesta iteracao, qualquer etapa ainda nao migrada fica explicitamente marcada como best-effort e observavel, sem alegacao de ACID distribuido. Two-phase commit foi rejeitado por incompatibilidade e complexidade operacional.

### 7. Resiliencia e implementada como policy compartilhada somente no limite externo

Timeout, circuit breaker, metrica e classificacao de excecao seguem uma pequena policy reutilizavel, evitando duplicacao entre adapters. O pattern Strategy permite comportamento fatal ou degradavel por operacao. Retry automatico nao e default: so leituras seguras ou mutacoes idempotentes podem utiliza-lo. Uma hierarquia de templates foi rejeitada para evitar acoplamento por heranca.

### 8. Health e rate limit usam os mesmos contratos de erro e headers

Liveness nao toca dependencias. Readiness executa apenas checks obrigatorios com timeout e retorna 503 degradado. O rate limiter permanece simples no desenvolvimento, mas producao exige armazenamento compartilhado; todos os retornos passam pelo mesmo finalizador de headers/correlacao. Health detalhado autenticado pode ser acrescentado depois; o endpoint publico nunca inclui host ou excecao.

### 9. Toolchain declarada em `pyproject.toml`

Dependencias runtime e dev, Ruff, mypy, pytest e coverage ficam em uma fonte de verdade. `requirements.txt` passa a ser arquivo compatível gerado ou espelho validado, nao um manifesto divergente. O gate inicia pelo baseline real, corrige testes quebrados e exige 100% nos modulos criticos; o plano define o caminho para 100% global sem manipular denominador.

### 10. OpenSpec e inicializado apenas para Codex

`.agents/skills/openspec-*` e mantido porque e o delivery target oficial do Codex. A busca ignora dependencias instaladas e bloqueia `.claude`/`CLAUDE.md` first-party. Nenhum arquivo Claude versionado foi encontrado, portanto nao ha migracao de conteudo nem delecao destrutiva a executar.

## Risks / Trade-offs

- **Mudanca de shape de erro pode afetar clientes informais** -> preservar campos estaveis, publicar OpenAPI e adicionar contract tests frontend/backend.
- **Reserva idempotente pode ficar presa apos crash** -> representar outcome unknown, expor status seguro e reconciliar por operacao, nunca reexecutar cegamente.
- **100% global pode incentivar testes de pouco valor** -> medir todo first-party, permitir somente exclusoes declarativas revisadas e combinar cobertura com cenarios de risco.
- **Checks de dependencia podem aumentar latencia de readiness** -> executar em paralelo com timeout curto e nunca no liveness.
- **OTEL mal configurado pode gerar custo ou indisponibilidade** -> exportacao opt-in, filas limitadas e falha aberta.

## Migration Plan

1. Versionar artefatos OpenSpec, alinhar dependencias e ativar gates estaticos sem mudar contratos.
2. Introduzir DTOs/erros/logs seguros e testar compatibilidade OpenAPI.
3. Migrar health, middleware e adapters de resiliencia com rollout por ambiente.
4. Criar tabela de idempotencia e outbox por migracao; implantar antes de exigir headers dos clientes.
5. Ativar exigencia de Idempotency-Key e atualizar o frontend apos contract tests passarem.
6. Habilitar OTLP inicialmente em staging e validar redacao, cardinalidade e custo.

Rollback separa schema de comportamento: tabelas novas sao aditivas; flags podem desabilitar OTLP e a exigencia temporaria de idempotencia sem remover dados. Contratos antigos permanecem durante a janela documentada, e qualquer rollback de aplicacao usa a imagem anterior depois de health/readiness aprovados.

## Open Questions

- O endpoint, autenticacao, sampling e retencao do collector OTLP de producao permanecem responsabilidade do ambiente; exportacao fica desabilitada enquanto nao forem definidos.
- O mecanismo downstream de deduplicacao de AWS IoT e do contrato Web3 precisa ser confirmado antes de declarar exatamente-uma-vez fora da fronteira HTTP.
