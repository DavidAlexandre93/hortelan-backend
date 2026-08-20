import asyncio
from types import SimpleNamespace

import api.index
from scripts import perf_baseline


class FakeClient:
    async def get(self, url: str) -> SimpleNamespace:
        return SimpleNamespace(status_code=503 if url.endswith('/fail') else 200)


class FakeClientContext:
    async def __aenter__(self) -> FakeClient:
        return FakeClient()

    async def __aexit__(self, *_: object) -> None:
        return None


def test_asgi_entrypoint_exports_application() -> None:
    assert api.index.app.title == 'Hortelan Backend'


def test_percentile_handles_empty_boundaries_and_ordering() -> None:
    assert perf_baseline.percentile([], 0.95) == 0
    assert perf_baseline.percentile([3.0, 1.0, 2.0], 0) == 1.0
    assert perf_baseline.percentile([3.0, 1.0, 2.0], 1) == 3.0


def test_request_worker_and_main_report(monkeypatch, capsys) -> None:
    result = asyncio.run(perf_baseline.run_request(FakeClient(), 'http://test', '/health'))
    assert result.status_code == 200
    assert result.elapsed >= 0

    monkeypatch.setattr(perf_baseline.random, 'choice', lambda endpoints: endpoints[-1])
    results = asyncio.run(
        perf_baseline.worker(FakeClient(), 'http://test', ['/health', '/fail'], 2)
    )
    assert [item.status_code for item in results] == [503, 503]

    monkeypatch.setattr(
        perf_baseline.argparse.ArgumentParser,
        'parse_args',
        lambda _: SimpleNamespace(base_url='http://test', requests=4, concurrency=2),
    )
    monkeypatch.setattr(perf_baseline.httpx, 'AsyncClient', lambda **_: FakeClientContext())
    asyncio.run(perf_baseline.main())

    output = capsys.readouterr().out
    assert 'total_requests=4' in output
    assert 'error_rate=0.00%' in output
    assert 'latency_p99_ms=' in output
