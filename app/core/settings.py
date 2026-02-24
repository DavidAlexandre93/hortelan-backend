import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Hortelan Backend'
    app_env: str = 'development'
    app_port: int = 8000
    log_level: str = 'INFO'
    enable_metrics: bool = True
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

    otel_enabled: bool = True
    otel_service_name: str = 'hortelan-backend'
    otel_service_version: str = '1.0.0'
    otel_exporter_otlp_endpoint: str = ''
    otel_exporter_timeout: int = 10

    circuit_breaker_failure_rate_threshold: float = 50.0
    circuit_breaker_sliding_window_size: int = 10
    circuit_breaker_minimum_calls: int = 5
    circuit_breaker_wait_duration_seconds: int = 30
    circuit_breaker_permitted_half_open_calls: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
