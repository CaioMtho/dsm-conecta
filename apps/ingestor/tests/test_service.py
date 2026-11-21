import asyncio
import io
import json
import logging
from types import SimpleNamespace
from typing import Self
from unittest.mock import AsyncMock

import aiomqtt
from ingestor.config import IngestorConfig
from ingestor.logging_config import JsonLogFormatter
from ingestor.processor import MessageProcessor
from ingestor.service import IngestorService

VALID_EVENT_ID_1 = "550e8400-e29b-41d4-a716-446655440001"
VALID_EVENT_ID_2 = "550e8400-e29b-41d4-a716-446655440002"
VALID_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def _make_json_logger(name: str) -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    return logger, stream


def _make_config(**overrides) -> IngestorConfig:
    defaults = {
        "database_url": "postgresql://dsm_user:dsm_password@localhost:5432/dsm_conecta",
        "mqtt_host": "broker",
        "mqtt_port": 1883,
        "mqtt_username": "ingestor_user",
        "mqtt_password": "ingestor_pass_dev",
        "mqtt_topic": "dsm/prod/#",
        "mqtt_qos": 1,
        "reconnect_initial_delay": 0.01,
        "reconnect_max_delay": 0.05,
    }
    defaults.update(overrides)
    return IngestorConfig(**defaults)


def _valid_message(event_id: str, topic: str = "dsm/prod/app/interacao/tela") -> SimpleNamespace:
    payload = json.dumps(
        {
            "schema_version": "1.0",
            "timestamp": "2026-11-21T18:00:00Z",
            "event_id": event_id,
            "session_id": VALID_SESSION_ID,
            "source": "app_mobile",
            "category": "interacao_tela",
            "payload": {"screen_name": "home"},
        }
    ).encode("utf-8")
    return SimpleNamespace(topic=topic, payload=payload)


class _FakeMqttClient:
    def __init__(
        self,
        *,
        messages: list[SimpleNamespace | Exception],
        enter_error: Exception | None = None,
        hold_open: bool = False,
    ) -> None:
        self._items = list(messages)
        self._enter_error = enter_error
        self._hold_open = hold_open
        self.subscribe = AsyncMock()
        self.exited = False

    async def __aenter__(self) -> Self:
        if self._enter_error is not None:
            raise self._enter_error
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True

    @property
    def messages(self):
        return self._iter_messages()

    async def _iter_messages(self):
        for item in self._items:
            if isinstance(item, Exception):
                raise item
            yield item
        if self._hold_open:
            await asyncio.Future()


async def test_service_connects_subscribes_qos1_and_persists_valid_messages():
    config = _make_config(mqtt_client_id="ingestor-test")
    repo = AsyncMock()
    logger, stream = _make_json_logger("test.service.happy")
    processor = MessageProcessor(repository=repo, logger=logger)
    stop_event = asyncio.Event()

    received_kwargs: list[dict] = []
    processed_done = asyncio.Event()
    original_insert = repo.insert_event

    async def _insert_and_stop(event):
        await original_insert(event)
        processed_done.set()
        stop_event.set()

    repo.insert_event = AsyncMock(side_effect=_insert_and_stop)

    fake_client = _FakeMqttClient(
        messages=[
            SimpleNamespace(topic="dsm/prod/app/interacao/tela", payload=b"{bad-json"),
            _valid_message(VALID_EVENT_ID_1),
        ],
        hold_open=True,
    )

    def _client_factory(**kwargs):
        received_kwargs.append(kwargs)
        return fake_client

    service = IngestorService(
        config=config,
        repository=repo,
        processor=processor,
        client_factory=_client_factory,
        logger=logger,
    )

    assert not service.is_running
    await service.run(stop_event=stop_event)

    assert not service.is_running
    assert processed_done.is_set()
    repo.connect.assert_awaited_once()
    repo.close.assert_awaited_once()
    repo.insert_event.assert_awaited_once()
    assert repo.insert_event.await_args.args[0].event_id == VALID_EVENT_ID_1

    assert received_kwargs == [
        {
            "hostname": "broker",
            "port": 1883,
            "username": "ingestor_user",
            "password": "ingestor_pass_dev",
            "keepalive": 60,
            "identifier": "ingestor-test",
        }
    ]
    fake_client.subscribe.assert_awaited_once_with("dsm/prod/#", qos=1)
    assert fake_client.exited is True

    events = [json.loads(line)["event"] for line in stream.getvalue().strip().splitlines()]
    assert "mqtt_connected_and_subscribed" in events
    assert "message_discarded" in events
    assert "event_persisted" in events


async def test_service_reconnects_and_resubscribes_after_broker_oscillation():
    config = _make_config(reconnect_initial_delay=0.01, reconnect_max_delay=0.04)
    repo = AsyncMock()
    logger, stream = _make_json_logger("test.service.reconnect")
    processor = MessageProcessor(repository=repo, logger=logger)
    stop_event = asyncio.Event()

    persisted_ids: list[str] = []

    async def _track_insert(event):
        persisted_ids.append(event.event_id)
        if len(persisted_ids) == 2:
            stop_event.set()

    repo.insert_event = AsyncMock(side_effect=_track_insert)

    client_1 = _FakeMqttClient(
        messages=[
            _valid_message(VALID_EVENT_ID_1),
            aiomqtt.MqttError("broker disconnected"),
        ]
    )
    client_2 = _FakeMqttClient(
        messages=[],
        enter_error=aiomqtt.MqttError("connection refused"),
    )
    client_3 = _FakeMqttClient(
        messages=[_valid_message(VALID_EVENT_ID_2)],
        hold_open=True,
    )
    clients = iter([client_1, client_2, client_3])

    service = IngestorService(
        config=config,
        repository=repo,
        processor=processor,
        client_factory=lambda **_: next(clients),
        logger=logger,
    )

    await service.run(stop_event=stop_event)

    assert persisted_ids == [VALID_EVENT_ID_1, VALID_EVENT_ID_2]
    client_1.subscribe.assert_awaited_once_with("dsm/prod/#", qos=1)
    client_2.subscribe.assert_not_awaited()
    client_3.subscribe.assert_awaited_once_with("dsm/prod/#", qos=1)
    repo.close.assert_awaited_once()

    logs = [json.loads(line) for line in stream.getvalue().strip().splitlines()]
    loss_logs = [entry for entry in logs if entry["event"] == "mqtt_connection_lost"]
    assert len(loss_logs) == 2
    assert loss_logs[0]["retry_in_seconds"] == 0.01
    assert loss_logs[1]["retry_in_seconds"] == 0.02


async def test_service_stops_gracefully_while_waiting_for_messages():
    config = _make_config()
    repo = AsyncMock()
    logger, _ = _make_json_logger("test.service.stop_idle")
    processor = MessageProcessor(repository=repo, logger=logger)
    fake_client = _FakeMqttClient(messages=[], hold_open=True)

    service = IngestorService(
        config=config,
        repository=repo,
        processor=processor,
        client_factory=lambda **_: fake_client,
        logger=logger,
    )

    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.02)
    assert service.is_running is True

    service.stop()
    await asyncio.wait_for(task, timeout=1.0)

    assert service.is_running is False
    assert fake_client.exited is True
    repo.close.assert_awaited_once()


async def test_service_stops_gracefully_during_reconnect_backoff():
    config = _make_config(reconnect_initial_delay=5.0, reconnect_max_delay=10.0)
    repo = AsyncMock()
    logger, _ = _make_json_logger("test.service.stop_backoff")
    processor = MessageProcessor(repository=repo, logger=logger)
    failed_once = asyncio.Event()

    def _failing_client_factory(**_):
        failed_once.set()
        return _FakeMqttClient(
            messages=[],
            enter_error=aiomqtt.MqttError("broker unreachable"),
        )

    service = IngestorService(
        config=config,
        repository=repo,
        processor=processor,
        client_factory=_failing_client_factory,
        logger=logger,
    )

    task = asyncio.create_task(service.run())
    await asyncio.wait_for(failed_once.wait(), timeout=1.0)
    await asyncio.sleep(0.02)

    service.stop()
    await asyncio.wait_for(task, timeout=1.0)

    assert service.is_running is False
    repo.close.assert_awaited_once()
