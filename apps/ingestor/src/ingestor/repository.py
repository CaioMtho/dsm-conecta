import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, Protocol
from uuid import UUID

import asyncpg
from schemas import TelemetryEvent

INSERT_TELEMETRY_EVENT_SQL = """
INSERT INTO telemetry_events (event_id, timestamp, session_id, source, category, payload)
VALUES ($1, $2, $3, $4, $5, $6::jsonb)
ON CONFLICT (event_id, timestamp) DO NOTHING
""".strip()


class EventRepository(Protocol):
    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def insert_event(self, event: TelemetryEvent) -> bool: ...


class TelemetryRepository:
    def __init__(
        self,
        dsn: str,
        min_size: int = 1,
        max_size: int = 5,
        command_timeout: float = 10.0,
        close_timeout: float = 5.0,
        pool_factory: Callable[..., Awaitable[Any]] = asyncpg.create_pool,
    ) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._command_timeout = command_timeout
        self._close_timeout = close_timeout
        self._pool_factory = pool_factory
        self._pool: Any = None

    @property
    def is_connected(self) -> bool:
        return self._pool is not None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        self._pool = await self._pool_factory(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=self._command_timeout,
        )

    async def close(self) -> None:
        if self._pool is None:
            return
        pool = self._pool
        self._pool = None
        try:
            await asyncio.wait_for(pool.close(), timeout=self._close_timeout)
        except TimeoutError:
            terminate = getattr(pool, "terminate", None)
            if callable(terminate):
                terminate()

    async def insert_event(self, event: TelemetryEvent) -> bool:
        if self._pool is None:
            raise RuntimeError("Pool de conexões TimescaleDB não foi inicializado.")

        serialized_payload = json.dumps(
            event.payload,
            ensure_ascii=False,
            allow_nan=False,
        )
        async with self._pool.acquire() as conn:
            status = await conn.execute(
                INSERT_TELEMETRY_EVENT_SQL,
                UUID(event.event_id),
                event.timestamp,
                UUID(event.session_id),
                event.source.value,
                event.category.value,
                serialized_payload,
            )
        return status != "INSERT 0 0"
