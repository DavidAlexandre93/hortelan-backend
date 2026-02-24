# Hortelan Backend (Hexagonal Architecture + FastAPI)

Backend em **Python + FastAPI** estruturado em **Arquitetura Hexagonal (Ports and Adapters)** para integração com:

- AWS IoT Core
- Kafka
- Web3 / Blockchain (EVM)
- Redis
- Banco relacional (SQLAlchemy)
- Banco não relacional (MongoDB)

Também preparado para consumo por frontends SPA (ex.: `hortelan-frontend`) via CORS e APIs REST.

## Arquitetura

```text
app/
  domain/
    entities/        # Entidades de negócio puras
    ports/           # Interfaces (contratos)
  application/
    use_cases/       # Regras de aplicação (orquestração)
  infrastructure/
    adapters/        # Implementações externas (AWS, Kafka, Redis, Web3)
    persistence/     # Repositórios SQL e Mongo
  api/               # Controllers / rotas FastAPI
  core/              # Settings e container de dependências
```

## Endpoints

- `GET /health`
- `POST /api/v1/telemetry`
- `POST /api/v1/commands`
- `POST /api/v1/ledger`
- `GET /api/v1/telemetry?limit=20&device_id=<opcional>`
- `GET /api/v1/telemetry/latest/{device_id}`
- `GET /api/v1/commands/latest/{device_id}`
- `GET /api/v1/devices/{device_id}/snapshot`
- `GET /api/v1/strategic/coverage`

## Integração com frontend

1. Configure CORS em `cors_origins` (arquivo `.env`).
2. O frontend pode enviar telemetria e comandos pelos endpoints REST.
3. Para produção, adicione autenticação (JWT/Cognito) e observabilidade.

## Variáveis de ambiente principais

```env
APP_ENV=development
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

## Gerenciamento de dependências com Poetry

Este projeto utiliza o **Poetry** para gerenciar dependências e ambiente virtual.

```bash
poetry install
```

## Execução

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

## Deploy na Vercel

Este projeto já está preparado para rodar como função Python (ASGI) na Vercel:

- `api/index.py` exporta a instância `app` do FastAPI.
- `vercel.json` direciona todas as rotas para essa função.

### Passos

1. Instale a CLI da Vercel e autentique:

   ```bash
   npm i -g vercel
   vercel login
   ```

2. Faça o deploy:

   ```bash
   vercel
   ```

3. Configure as variáveis de ambiente no painel da Vercel (Project Settings → Environment Variables).

### Observações importantes para produção

- Defina serviços gerenciados para Redis, Kafka, MongoDB e banco relacional.
- Em ambiente Vercel, se `RELATIONAL_DB_URL` não for informado, o backend usa `sqlite` em `/tmp/hortelan.db` (ephemero, apenas fallback).

## Análise de cobertura estratégica

Foi adicionada uma análise objetiva de aderência do backend ao núcleo estratégico do produto em `docs/strategic-feature-gap-analysis.md`.

## Testes

```bash
poetry run pytest -q
```

## CI/CD

O projeto agora possui pipeline de **CI/CD no GitHub Actions** com foco no que é essencial:

- CI roda somente quando há mudanças de backend (`app/`, `api/`, `tests/` e arquivos de dependência).
- Validações executadas: instalação de dependências, checagem de sintaxe e testes com `pytest`.
- CD para Vercel acontece apenas em `push` na `main` e somente se os segredos estiverem configurados:
  - `VERCEL_TOKEN`
  - `VERCEL_ORG_ID`
  - `VERCEL_PROJECT_ID`

Também foi adicionado **Dependabot** para atualizar semanalmente dependências Python e GitHub Actions.
