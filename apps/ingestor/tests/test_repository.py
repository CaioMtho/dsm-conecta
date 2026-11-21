import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from ingestor.repository import INSERT_TELEMETRY_EVENT_SQL, TelemetryRepository
from schemas import EventCategory, EventSource, TelemetryEvent

VALID_EVENT_ID = "550e8400-e29b-41d4-a716-446655440000"
VALID_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


class _FakePool:
    def __init__(self) -> None:
        self.connection = AsyncMock()
        self.close = AsyncMock()

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def _sample_event() -> TelemetryEvent:
    return TelemetryEvent(
        schema_version="1.0",
        timestamp=datetime(2026, 11, 21, 18, 0, 0, tzinfo=UTC),
        event_id=VALID_EVENT_ID,
        session_id=VALID_SESSION_ID,
        source=EventSource.APP_MOBILE,
        category=EventCategory.INTERACAO_TELA,
        payload={"screen_name": "cursos", "duration_seconds": 4.2},
    )


async def test_repository_connects_pool_and_inserts_event():
    fake_pool = _FakePool()
    pool_factory = AsyncMock(return_value=fake_pool)

    repo = TelemetryRepository(
        dsn="postgresql://dsm_user:dsm_password@db:5432/dsm_conecta",
        min_size=2,
        max_size=8,
        command_timeout=12.0,
        pool_factory=pool_factory,
    )

    await repo.connect()
    pool_factory.assert_awaited_once_with(
        dsn="postgresql://dsm_user:dsm_password@db:5432/dsm_conecta",
        min_size=2,
        max_size=8,
        command_timeout=12.0,
    )

    event = _sample_event()
    await repo.insert_event(event)

    fake_pool.connection.execute.assert_awaited_once()
    sql, *params = fake_pool.connection.execute.await_args.args
    assert sql == INSERT_TELEMETRY_EVENT_SQL
    assert "INSERT INTO telemetry_events" in sql
    assert "ON CONFLICT (event_id, timestamp) DO NOTHING" in sql
    assert params == [
        UUID(VALID_EVENT_ID),
        datetime(2026, 11, 21, 18, 0, 0, tzinfo=UTC),
        UUID(VALID_SESSION_ID),
        "app_mobile",
        "interacao_tela",
        json.dumps({"screen_name": "cursos", "duration_seconds": 4.2}, ensure_ascii=False),
    ]

    await repo.close()
    fake_pool.close.assert_awaited_once()


async def test_repository_insert_before_connect_raises():
    repo = TelemetryRepository(dsn="postgresql://u:p@localhost:5432/db")

    with pytest.raises(RuntimeError, match="Pool"):
        await repo.insert_event(_sample_event())


async def test_repository_connect_and_close_are_idempotent():
    fake_pool = _FakePool()
    pool_factory = AsyncMock(return_value=fake_pool)
    repo = TelemetryRepository(
        dsn="postgresql://u:p@localhost:5432/db",
        pool_factory=pool_factory,
    )

    await repo.connect()
    await repo.connect()
    pool_factory.assert_awaited_once()

    await repo.close()
    await repo.close()
    fake_pool.close.assert_awaited_once()
