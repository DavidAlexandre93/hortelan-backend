import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Hortelan Backend'
    app_env: str = 'development'
    app_port: int = 8000
    cors_origins: list[str] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://localhost:5173']
    )

    aws_region: str = 'us-east-1'
    aws_iot_endpoint: str = ''
    aws_iot_topic_prefix: str = 'hortelan/devices'

    kafka_bootstrap_servers: str = 'localhost:9092'
    kafka_topic_telemetry: str = 'hortelan.telemetry'
    kafka_topic_commands: str = 'hortelan.commands'

    redis_url: str = 'redis://localhost:6379/0'

    relational_db_url: str = Field(
        default_factory=lambda: (
            'sqlite+aiosqlite:////tmp/hortelan.db'
            if os.getenv('VERCEL')
            else 'sqlite+aiosqlite:///./hortelan.db'
        )
    )
    mongo_url: str = 'mongodb://localhost:27017'
    mongo_db_name: str = 'hortelan'

    web3_rpc_url: str = 'http://localhost:8545'
    web3_contract_address: str = ''
    web3_contract_abi_json: str = '[]'
    web3_account_private_key: str = ''


@lru_cache
def get_settings() -> Settings:
    return Settings()
