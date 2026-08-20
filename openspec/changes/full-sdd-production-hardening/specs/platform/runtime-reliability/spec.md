## Purpose

Define protecoes e sinais operacionais consistentes para manter a API segura, previsivel e recuperavel diante de abuso, configuracao invalida e falha de dependencias.

## ADDED Requirements

### Requirement: Configuracao validada por ambiente
A aplicacao SHALL validar enums, limites, URLs e invariantes de seguranca no startup e MUST falhar cedo quando a configuracao de producao for insegura.

#### Scenario: Producao sem credencial obrigatoria
- **WHEN** o ambiente e production e a autenticacao obrigatoria nao possui segredo configurado
- **THEN** o startup falha com diagnostico seguro e acionavel

### Requirement: Protecao uniforme de requisicoes
Rotas sensiveis SHALL usar comparacao de credencial resistente a timing, rate limit com resposta tipada, CORS explicito e headers de seguranca consistentes inclusive nos caminhos de erro.

#### Scenario: Limite excedido
- **WHEN** a identidade excede o limite configurado
- **THEN** a API retorna 429 no envelope padrao com Retry-After e identificadores de correlacao

### Requirement: Integracoes externas resilientes
Cada chamada externa SHALL possuir timeout finito, circuit breaker observavel e classificacao explicita entre falha transitoria, degradacao aceitavel e falha fatal.

#### Scenario: Circuito aberto
- **WHEN** uma dependencia excede a taxa de falhas configurada
- **THEN** novas chamadas falham rapidamente ou usam fallback explicitamente seguro sem reportar sucesso falso

### Requirement: Liveness e readiness semanticamente distintas
Liveness SHALL indicar apenas que o processo responde; readiness SHALL testar dependencias obrigatorias com timeout e retornar 503 quando a instancia nao pode receber trafego.

#### Scenario: Banco indisponivel
- **WHEN** o probe SQL falha ou excede o timeout
- **THEN** liveness permanece 200 e readiness retorna 503 sem expor a excecao

