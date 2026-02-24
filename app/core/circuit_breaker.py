from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


class CircuitBreakerOpenError(RuntimeError):
    pass


@dataclass(slots=True)
class CircuitBreakerConfig:
    failure_rate_threshold: float = 50.0
    sliding_window_size: int = 10
    minimum_number_of_calls: int = 5
    wait_duration_in_open_state_seconds: int = 30
    permitted_calls_in_half_open_state: int = 2


class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig) -> None:
        self.name = name
        self.config = config
        self._state: CircuitState = CircuitState.CLOSED
        self._opened_at: datetime | None = None
        self._half_open_calls = 0
        self._results: deque[bool] = deque(maxlen=config.sliding_window_size)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._opened_at:
            elapsed = datetime.now(timezone.utc) - self._opened_at
            if elapsed >= timedelta(seconds=self.config.wait_duration_in_open_state_seconds):
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def allow_request(self) -> bool:
        state = self.state
        if state == CircuitState.OPEN:
            return False

        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.permitted_calls_in_half_open_state:
                return False
            self._half_open_calls += 1

        return True

    def on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls = max(0, self._half_open_calls - 1)
            if self._half_open_calls == 0:
                self._close()
            return

        self._record_result(True)

    def on_failure(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._open()
            return

        self._record_result(False)
        if self._should_open():
            self._open()

    def _record_result(self, success: bool) -> None:
        self._results.append(success)

    def _should_open(self) -> bool:
        total_calls = len(self._results)
        if total_calls < self.config.minimum_number_of_calls:
            return False

        failures = total_calls - sum(self._results)
        failure_rate = (failures / total_calls) * 100
        return failure_rate >= self.config.failure_rate_threshold

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = datetime.now(timezone.utc)

    def _close(self) -> None:
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._half_open_calls = 0
        self._results.clear()

    def call_permitted(self) -> None:
        if not self.allow_request():
            raise CircuitBreakerOpenError(f'Circuit breaker {self.name} is open')
