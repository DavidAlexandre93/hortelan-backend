# Hortelan Backend

Backend do **Hortelan** desenvolvido com **FastAPI + Python 3.11** em **Arquitetura Hexagonal (Ports and Adapters)**, focado em integração com IoT e evolução incremental para módulos estratégicos de produto.

---

## Sumário

- [Visão geral](#visão-geral)
- [Stack e integrações](#stack-e-integrações)
- [Arquitetura](#arquitetura)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Pré-requisitos](#pré-requisitos)
- [Configuração rápida](#configuração-rápida)
- [Execução local](#execução-local)
- [Documentação da API](#documentação-da-api)
- [Endpoints disponíveis](#endpoints-disponíveis)
- [Exemplos de uso com cURL](#exemplos-de-uso-com-curl)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Testes e qualidade](#testes-e-qualidade)
- [Deploy na Vercel](#deploy-na-vercel)
- [CI/CD](#cicd)
- [Cobertura estratégica do produto](#cobertura-estratégica-do-produto)
- [Roadmap técnico sugerido](#roadmap-técnico-sugerido)
- [Licença](#licença)

---

## Visão geral

Este serviço expõe APIs para:

- ingestão de telemetria de dispositivos;
- despacho de comandos de irrigação;
- registro de eventos em ledger (Web3);
- leitura de snapshots operacionais por dispositivo;
- análise de cobertura de requisitos e prontidão de módulos do produto.

A base atual está mais madura em **telemetria/comandos IoT**, com suporte de repositórios relacional + documental e cache distribuído.

## Stack e integrações

- **API:** FastAPI
- **Validação/configuração:** Pydantic + pydantic-settings
- **Mensageria:** Kafka (`aiokafka`)
- **Comandos IoT:** AWS IoT Core (`boto3`)
- **Cache:** Redis (`redis`)
- **Ledger / Blockchain:** Web3 (`web3`)
- **Persistência relacional:** SQLAlchemy async + SQLite (default local)
- **Persistência documental:** MongoDB (`motor`)
- **Testes:** pytest + pytest-asyncio

## Arquitetura

O projeto segue **Hexagonal Architecture** para reduzir acoplamento com frameworks/provedores.

- **Domain**: entidades e contratos (ports)
- **Application**: casos de uso e orquestração
- **Infrastructure**: adapters externos e persistência
- **API**: camada HTTP (rotas/schemas)
- **Core**: configuração e composição de dependências

## Estrutura de pastas

```text
app/
  api/
    routes.py            # Endpoints FastAPI
    schemas.py           # Contratos de entrada/saída
  application/
    use_cases/           # Casos de uso
  core/
    settings.py          # Configurações por ambiente
    dependencies.py      # Container de dependências
  domain/
    entities/            # Modelos de domínio
    ports/               # Interfaces de portas
  infrastructure/
    adapters/            # Kafka, Redis, AWS IoT, Web3
    persistence/         # Repositórios SQL e Mongo
  main.py                # App FastAPI + middlewares + lifespan

api/index.py             # Entrada ASGI para Vercel
tests/                   # Testes automatizados
docs/                    # Documentação técnica complementar
```

## Pré-requisitos

- Python **3.11+**
- Poetry
- (Opcional para cenário completo) Redis, Kafka, MongoDB e endpoint RPC EVM

## Configuração rápida

1. **Instale as dependências**:

   ```bash
   poetry install
   ```

2. **Crie seu `.env`** (a partir dos exemplos da seção de variáveis).

3. **Suba os serviços externos** necessários para o seu cenário (ou use defaults locais quando possível).

## Execução local

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Documentação da API

Com o servidor em execução:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints disponíveis

Base path principal: `/api/v1`

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica status da aplicação e ambiente |
| POST | `/api/v1/telemetry` | Ingestão de telemetria |
| GET | `/api/v1/telemetry` | Lista telemetria com filtros |
| GET | `/api/v1/telemetry/latest/{device_id}` | Última telemetria por dispositivo |
| POST | `/api/v1/commands` | Envia comando de irrigação |
| GET | `/api/v1/commands/latest/{device_id}` | Último comando enviado |
| POST | `/api/v1/ledger` | Registra payload em ledger |
| GET | `/api/v1/devices/{device_id}/snapshot` | Snapshot (telemetria + comando) |
| GET | `/api/v1/requirements` | Catálogo de cobertura por requisito |
| GET | `/api/v1/strategic/coverage` | Relatório de cobertura estratégica |
| GET | `/api/v1/product/readiness` | Prontidão de módulos do produto |
| GET | `/api/v1/product/modules/{module_slug}` | Detalhe de um módulo específico |

## Exemplos de uso com cURL

### 1) Ingerir telemetria

```bash
curl -X POST "http://localhost:8000/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor-01",
    "moisture": 58.4,
    "temperature": 25.1,
    "ph": 6.4,
    "metadata": {"zone": "canteiro-a"}
  }'
```

### 2) Enviar comando de irrigação

```bash
curl -X POST "http://localhost:8000/api/v1/commands" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor-01",
    "action": "irrigate",
    "duration_seconds": 120
  }'
```

### 3) Registrar no ledger

```bash
curl -X POST "http://localhost:8000/api/v1/ledger" \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "evt-2026-001",
    "payload": {"type": "irrigation_completed", "device_id": "sensor-01"}
  }'
```

### 4) Obter snapshot por dispositivo

```bash
curl "http://localhost:8000/api/v1/devices/sensor-01/snapshot"
```

## Variáveis de ambiente

Exemplo base:

```env
APP_NAME=Hortelan Backend
APP_ENV=development
APP_PORT=8000
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

AWS_REGION=us-east-1
AWS_IOT_ENDPOINT=
AWS_IOT_TOPIC_PREFIX=hortelan/devices

KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_TELEMETRY=hortelan.telemetry
KAFKA_TOPIC_COMMANDS=hortelan.commands

REDIS_URL=redis://localhost:6379/0

RELATIONAL_DB_URL=sqlite+aiosqlite:///./hortelan.db
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=hortelan

WEB3_RPC_URL=http://localhost:8545
WEB3_CONTRACT_ADDRESS=
WEB3_CONTRACT_ABI_JSON=[]
WEB3_ACCOUNT_PRIVATE_KEY=
```

> Observação: em ambiente Vercel, se `RELATIONAL_DB_URL` não for informado, o fallback é `sqlite` em `/tmp/hortelan.db`.

## Testes e qualidade

Rodar suíte de testes:

```bash
poetry run pytest -q
```

Checagem simples de sintaxe (equivalente ao pipeline):

```bash
python -m compileall app api tests
```

## Deploy na Vercel

O projeto já está preparado para deploy ASGI:

- `api/index.py` exporta a app FastAPI;
- `vercel.json` roteia requisições para a função Python.

Passos:

1. Instalar e autenticar na CLI:

   ```bash
   npm i -g vercel
   vercel login
   ```

2. Deploy:

   ```bash
   vercel
   ```

3. Configurar variáveis de ambiente no painel da Vercel.

## CI/CD

Pipeline GitHub Actions com foco em mudanças de backend:

- detecta mudanças em `app/`, `api/`, `tests/` e arquivos-chave;
- instala dependências;
- valida sintaxe com `compileall`;
- executa testes (`pytest -q`);
- deploy para Vercel no `push` em `main` quando segredos estão configurados.

Segredos esperados para deploy:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

## Cobertura estratégica do produto

Há uma análise formal em:

- `docs/strategic-feature-gap-analysis.md`

Também existem endpoints dedicados para inspeção de cobertura/prontidão:

- `/api/v1/strategic/coverage`
- `/api/v1/product/readiness`
- `/api/v1/product/modules/{module_slug}`

## Roadmap técnico sugerido

1. Expandir domínio de **horta/planta/tarefas**.
2. Implementar **motor de regras + alertas**.
3. Evoluir para **recomendações inteligentes** em camadas.
4. Adicionar módulos de **comunidade, templates e marketplace**.
5. Fortalecer **backoffice, suporte e trilhas LGPD**.

## Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](./LICENSE).
