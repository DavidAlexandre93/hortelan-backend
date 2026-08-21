import os
from enum import StrEnum
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = 'development'
    TEST = 'test'
    STAGING = 'staging'
    PRODUCTION = 'production'


class LogLevel(StrEnum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
    )

    app_name: str = Field(default='Hortelan Backend', min_length=1, max_length=80)
    app_version: str = Field(default='1.0.0', pattern=r'^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$')
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: LogLevel = LogLevel.INFO
    enable_metrics: bool = True

    api_key: SecretStr = SecretStr('')
    enforce_api_key_in_production: bool = True
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10_000)
    external_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    health_check_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    cors_origins: list[str] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://localhost:5173']
    )
    cors_methods: list[str] = Field(
        default_factory=lambda: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    )
    cors_headers: list[str] = Field(
        default_factory=lambda: [
            'Authorization',
            'Content-Type',
            'Idempotency-Key',
            'X-API-Key',
            'X-Request-ID',
        ]
    )

    aws_region: str = Field(default='us-east-1', min_length=1, max_length=32)
    aws_iot_endpoint: str = Field(default='', max_length=255)
    aws_iot_topic_prefix: str = Field(default='hortelan/devices', min_length=1, max_length=128)

    kafka_bootstrap_servers: str = Field(default='localhost:9092', min_length=1, max_length=512)
    kafka_topic_telemetry: str = Field(default='hortelan.telemetry', min_length=1, max_length=249)
    kafka_topic_commands: str = Field(default='hortelan.commands', min_length=1, max_length=249)

    redis_url: str = 'redis://localhost:6379/0'
    relational_db_url: str = Field(
        default_factory=lambda: (
            'sqlite+aiosqlite:////tmp/hortelan.db'
            if os.getenv('VERCEL')
            else 'sqlite+aiosqlite:///./hortelan.db'
        )
    )
    mongo_url: str = 'mongodb://localhost:27017'
    mongo_db_name: str = Field(default='hortelan', min_length=1, max_length=64)

    web3_rpc_url: str = 'http://localhost:8545'
    web3_contract_address: str = ''
    web3_contract_abi_json: str = '[]'
    web3_account_private_key: SecretStr = SecretStr('')

    otel_enabled: bool = True
    otel_service_name: str = Field(default='hortelan-backend', min_length=1, max_length=128)
    otel_service_version: str = Field(default='1.0.0', min_length=1, max_length=64)
    otel_exporter_otlp_endpoint: str = ''
    otel_exporter_timeout: int = Field(default=10, ge=1, le=60)

    circuit_breaker_failure_rate_threshold: float = Field(default=50.0, gt=0, le=100)
    circuit_breaker_sliding_window_size: int = Field(default=10, ge=2, le=10_000)
    circuit_breaker_minimum_calls: int = Field(default=5, ge=1, le=10_000)
    circuit_breaker_wait_duration_seconds: int = Field(default=30, ge=1, le=3_600)
    circuit_breaker_permitted_half_open_calls: int = Field(default=2, ge=1, le=100)

    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        normalized: list[str] = []
        for origin in origins:
            candidate = origin.rstrip('/')
            parsed = urlparse(candidate)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.query:
                raise ValueError(
                    'CORS_ORIGINS deve conter apenas origens HTTP(S), sem path ou query'
                )
            if parsed.path not in {'', '/'}:
                raise ValueError('CORS_ORIGINS nao aceita paths')
            normalized.append(candidate)
        if len(normalized) != len(set(normalized)):
            raise ValueError('CORS_ORIGINS nao aceita duplicatas')
        return normalized

    @field_validator('redis_url')
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        if urlparse(value).scheme not in {'redis', 'rediss'}:
            raise ValueError('REDIS_URL deve usar redis:// ou rediss://')
        return value

    @field_validator('mongo_url')
    @classmethod
    def validate_mongo_url(cls, value: str) -> str:
        if not value.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError('MONGO_URL deve usar mongodb:// ou mongodb+srv://')
        return value

    @field_validator('web3_rpc_url', 'otel_exporter_otlp_endpoint')
    @classmethod
    def validate_optional_http_url(cls, value: str) -> str:
        if value and urlparse(value).scheme not in {'http', 'https'}:
            raise ValueError('a URL deve usar http:// ou https://')
        return value.rstrip('/')

    @model_validator(mode='after')
    def validate_security_invariants(self) -> 'Settings':
        if self.circuit_breaker_minimum_calls > self.circuit_breaker_sliding_window_size:
            raise ValueError('minimum_calls nao pode exceder sliding_window_size')
        if (
            self.app_env is AppEnvironment.PRODUCTION
            and self.enforce_api_key_in_production
            and not self.api_key.get_secret_value()
        ):
            raise ValueError('API_KEY e obrigatoria quando APP_ENV=production')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
