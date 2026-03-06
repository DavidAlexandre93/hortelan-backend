"""Ferramenta simples para baseline de latência/erros/throughput do backend.

Uso:
    python scripts/perf_baseline.py --base-url http://localhost:8000 --requests 300 --concurrency 25
"""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class Result:
    elapsed: float
    status_code: int


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * q)))
    return ordered[idx]


async def run_request(client: httpx.AsyncClient, base_url: str, endpoint: str) -> Result:
    started = time.perf_counter()
    response = await client.get(f"{base_url}{endpoint}")
    elapsed = time.perf_counter() - started
    return Result(elapsed=elapsed, status_code=response.status_code)


async def worker(
    client: httpx.AsyncClient,
    base_url: str,
    endpoints: list[str],
    iterations: int,
) -> list[Result]:
    results: list[Result] = []
    for _ in range(iterations):
        endpoint = random.choice(endpoints)
        results.append(await run_request(client, base_url, endpoint))
    return results


async def main() -> None:
    parser = argparse.ArgumentParser(description='Executa cenário de carga simples para baseline.')
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--requests', type=int, default=300)
    parser.add_argument('--concurrency', type=int, default=25)
    args = parser.parse_args()

    endpoints = ['/health', '/api/v1/telemetry?limit=20', '/metrics']
    per_worker = max(1, args.requests // args.concurrency)

    async with httpx.AsyncClient(timeout=10.0) as client:
        started = time.perf_counter()
        tasks = [worker(client, args.base_url, endpoints, per_worker) for _ in range(args.concurrency)]
        nested = await asyncio.gather(*tasks)
        total_elapsed = time.perf_counter() - started

    results = [item for group in nested for item in group]
    latencies_ms = [r.elapsed * 1000 for r in results]
    errors = [r for r in results if r.status_code >= 500]

    print('--- Baseline de carga ---')
    print(f'total_requests={len(results)}')
    print(f'throughput_rps={len(results)/total_elapsed:.2f}')
    print(f'error_rate={(len(errors)/len(results))*100:.2f}%')
    print(f'latency_avg_ms={statistics.fmean(latencies_ms):.2f}')
    print(f'latency_p95_ms={percentile(latencies_ms, 0.95):.2f}')
    print(f'latency_p99_ms={percentile(latencies_ms, 0.99):.2f}')


if __name__ == '__main__':
    asyncio.run(main())
