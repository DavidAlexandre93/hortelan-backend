# Plano de performance e confiabilidade

Este documento consolida o baseline e as práticas recomendadas aplicadas no projeto.

## 1) Baseline e metas

Métricas-alvo iniciais sugeridas para produção:

- Latência: `p95 < 250ms`, `p99 < 500ms` para endpoints de consulta.
- Erros: `5xx < 1%` por rota.
- Throughput: acompanhar RPS por jornada crítica e limite de saturação.
- Recursos: CPU e RAM por instância (fora do escopo local, medir em ambiente observável).
- Build: tempo médio de pipeline e variância por commit.

### Como medir baseline local

1. Subir API local.
2. Rodar `python scripts/perf_baseline.py --base-url http://localhost:8000 --requests 300 --concurrency 25`.
3. Coletar `latency_avg/p95/p99`, `error_rate`, `throughput_rps`.
4. Consultar `/metrics` para ver latência por rota, métricas de DB e integrações externas.

## 2) Instrumentação implementada

- Métricas HTTP por rota:
  - total de requests por status;
  - inflight requests;
  - latência `avg/p95/p99`;
  - taxa de erro 5xx;
  - throughput médio do processo.
- Métricas de banco:
  - latência `avg/p95` por operação (`telemetry.save`, `telemetry.list_recent`);
  - contador de erros por operação.
- Métricas de integrações externas:
  - latência `avg/p95` por integração (`redis`, `kafka`, `aws_iot`, `web3`);
  - contador de erros por integração.

## 3) Melhorias aplicadas em DB

- Índices adicionais para padrões de consulta:
  - `device_id + captured_at`
  - `captured_at`
- Redução de payload do ORM em listagem:
  - removido padrão equivalente a `SELECT *` na listagem recente;
  - seleção apenas das colunas usadas no response.
- Instrumentação de tempo de query para evidenciar gargalos reais.

## 4) Próximos passos recomendados

- Introduzir paginação por cursor para históricos extensos.
- Adicionar slow query log no banco alvo de produção.
- Rodar `EXPLAIN/ANALYZE` nos endpoints mais acessados.
- Criar alertas para p95/p99, 5xx e saturação de conexões.
- Expandir script de carga com fluxos write-heavy e autenticação.
