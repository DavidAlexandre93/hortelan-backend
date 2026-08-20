# ADR 001: preservar fronteiras hexagonais

- Status: aceito
- Data: 2026-08-20

## Contexto

O backend ja separava domain, application, infrastructure e API, mas rotas e testes acessavam
implementacoes concretas do container. Uma reescrita para outra nomenclatura arquitetural criaria
custo sem alterar as dependencias reais.

## Decisao

Preservar a arquitetura hexagonal e reforcar a direcao das dependencias. Domain declara ports;
application orquestra; infrastructure implementa adapters; API converte DTOs. Repository e
Adapter sao usados onde existe variacao real. Policies pequenas substituem hierarquias de heranca.

## Consequencias

- casos de uso podem ser testados com fakes de ports;
- frameworks permanecem fora do dominio;
- novos patterns exigem um problema concreto e um teste que demonstre o beneficio;
- nao sera criada uma camada ou interface para cada classe por padrao.
