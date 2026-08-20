## Purpose

Formaliza OpenSpec como fonte de verdade para mudancas observaveis e preserva rastreabilidade entre necessidade, contrato, decisao, implementacao e evidencia.

## ADDED Requirements

### Requirement: Mudancas observaveis nascem de especificacao
Qualquer mudanca de API, seguranca, consistencia, confiabilidade, observabilidade, dependencia ou gate SHALL possuir proposal, delta specs, design quando transversal, tasks e validacao estrita antes de ser concluida.

#### Scenario: Implementacao diverge do contrato
- **WHEN** o trabalho revela comportamento diferente do especificado
- **THEN** o delta e atualizado e validado antes de marcar a tarefa correspondente

### Requirement: Rastreabilidade verificavel
Cada requirement SHALL possuir cenarios e SHALL ser mapeado a tarefas e testes ou a uma justificativa de verificacao manual reproduzivel.

#### Scenario: Auditoria de mudanca
- **WHEN** um revisor inspeciona o change
- **THEN** consegue localizar a decisao, implementacao e evidencia de cada comportamento normativo

### Requirement: Integracao de assistente limitada ao Codex
O repositorio SHALL manter somente os artefatos OpenSpec do Codex selecionado e MUST NOT versionar configuracao, comandos ou memoria de Claude Code.

#### Scenario: Varredura de estrutura de assistente
- **WHEN** o gate inspeciona arquivos versionados
- **THEN** nao encontra `.claude` ou `CLAUDE.md` e preserva `.agents/skills/openspec-*` usada pelo Codex

