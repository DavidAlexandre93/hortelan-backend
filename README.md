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

## Execução

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Testes

```bash
pytest -q
```
