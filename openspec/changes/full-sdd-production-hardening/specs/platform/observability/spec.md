## Purpose

Define observabilidade estruturada e vendor-neutral que permita diagnosticar incidentes ponta a ponta sem transformar logs, metricas ou traces em fonte de dados sensiveis.

## ADDED Requirements

### Requirement: Logs JSON allowlist-first
Cada evento de aplicacao SHALL ser emitido como um objeto JSON por linha com timestamp UTC, severidade, servico, ambiente, evento e correlacao; campos contextuais MUST passar por allowlist e redacao antes da serializacao.

#### Scenario: Contexto potencialmente sensivel
- **WHEN** uma excecao contem token, email, segredo, payload ou query string
- **THEN** o log omite ou mascara o valor e preserva somente metadados operacionais aprovados

### Requirement: Diagnostico interno completo de excecao
Falhas internas SHALL registrar classe, modulo, arquivo, funcao, linha, mensagem segura, causa e stack completa no canal protegido, correlacionadas ao mesmo incident/request/trace/span id da resposta.

#### Scenario: Excecao encadeada
- **WHEN** uma integracao levanta uma excecao com causa
- **THEN** o log interno contem a cadeia e localizacao completa, mas a resposta HTTP nao contem esses detalhes

### Requirement: Propagacao OpenTelemetry padrao
A API SHALL aceitar e propagar contexto W3C valido, criar spans para requisicoes e integracoes e exportar via OTLP somente quando configurado; falha do exportador MUST NOT impedir o atendimento.

#### Scenario: Collector ausente
- **WHEN** OTEL esta desabilitado ou o collector esta indisponivel
- **THEN** a API continua operando com logs correlacionados e sem despejar spans nao estruturados em stdout

### Requirement: Metricas limitadas e semanticamente estaveis
Metricas de HTTP, banco e dependencias SHALL usar labels de cardinalidade limitada, caminhos de rota normalizados e nomes escapados.

#### Scenario: Recurso com identificador dinamico
- **WHEN** duas requisicoes acessam dispositivos diferentes pela mesma rota parametrizada
- **THEN** ambas incrementam a mesma serie baseada no template da rota

