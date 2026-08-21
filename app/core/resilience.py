from __future__ import annotations

import time
from dataclasses import dataclass

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from app.core.observability import metrics_registry
from app.core.settings import Settings


@dataclass(slots=True)
class ExternalCallPolicy:
    name: str
    metric_name: str
    timeout_seconds: float
    circuit_breaker: CircuitBreaker

    @classmethod
    def from_settings(cls, name: str, metric_name: str, settings: Settings) -> ExternalCallPolicy:
        return cls(
            name=name,
            metric_name=metric_name,
            timeout_seconds=settings.external_timeout_seconds,
            circuit_breaker=CircuitBreaker(
                name=name,
                config=CircuitBreakerConfig(
                    failure_rate_threshold=settings.circuit_breaker_failure_rate_threshold,
                    sliding_window_size=settings.circuit_breaker_sliding_window_size,
                    minimum_number_of_calls=settings.circuit_breaker_minimum_calls,
                    wait_duration_in_open_state_seconds=settings.circuit_breaker_wait_duration_seconds,
                    permitted_calls_in_half_open_state=settings.circuit_breaker_permitted_half_open_calls,
                ),
            ),
        )

    def start(self) -> float:
        self.circuit_breaker.call_permitted()
        return time.perf_counter()

    def success(self, started: float) -> None:
        self.circuit_breaker.on_success()
        metrics_registry.track_external_call(
            self.metric_name,
            time.perf_counter() - started,
            ok=True,
        )

    def failure(self, started: float) -> None:
        self.circuit_breaker.on_failure()
        metrics_registry.track_external_call(
            self.metric_name,
            time.perf_counter() - started,
            ok=False,
        )
