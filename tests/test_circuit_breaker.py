from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError, CircuitState


def test_circuit_breaker_opens_after_failure_rate_threshold() -> None:
    breaker = CircuitBreaker(
        name='test',
        config=CircuitBreakerConfig(
            failure_rate_threshold=50,
            sliding_window_size=4,
            minimum_number_of_calls=4,
            wait_duration_in_open_state_seconds=60,
            permitted_calls_in_half_open_state=1,
        ),
    )

    breaker.on_failure()
    breaker.on_success()
    breaker.on_failure()
    breaker.on_failure()

    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_rejects_calls_when_open() -> None:
    breaker = CircuitBreaker(
        name='test',
        config=CircuitBreakerConfig(
            failure_rate_threshold=50,
            sliding_window_size=2,
            minimum_number_of_calls=2,
            wait_duration_in_open_state_seconds=60,
            permitted_calls_in_half_open_state=1,
        ),
    )

    breaker.on_failure()
    breaker.on_failure()

    assert breaker.state == CircuitState.OPEN

    try:
        breaker.call_permitted()
        raise AssertionError('Expected CircuitBreakerOpenError')
    except CircuitBreakerOpenError:
        assert True
