import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import aiomqtt
import asyncpg

from ingestor.config import IngestorConfig
from ingestor.logging_config import log_structured
from ingestor.processor import MessageProcessor
from ingestor.repository import EventRepository

DB_CONNECT_EXCEPTIONS = (
    asyncpg.PostgresError,
    asyncpg.InterfaceError,
    asyncpg.InternalClientError,
    OSError,
    TimeoutError,
)


async def _wait_for_reconnect(stop_event: asyncio.Event, delay: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except TimeoutError:
        pass


def _is_failed_reason_code(reason_code: Any) -> bool:
    if getattr(reason_code, "is_failure", False):
        return True
    return isinstance(reason_code, int) and reason_code >= 128


def _extract_failed_suback_codes(result: Any) -> list[Any]:
    if result is None:
        return []
    codes = result if isinstance(result, (list, tuple)) else (result,)
    return [code for code in codes if _is_failed_reason_code(code)]


class IngestorService:
    def __init__(
        self,
        config: IngestorConfig,
        repository: EventRepository,
        processor: MessageProcessor | None = None,
        client_factory: Callable[..., Any] = aiomqtt.Client,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._repository = repository
        self._logger = logger or logging.getLogger("ingestor")
        self._processor = processor or MessageProcessor(
            repository=repository,
            logger=self._logger,
            max_payload_bytes=config.max_payload_bytes,
            max_log_payload_chars=config.max_log_payload_chars,
        )
        self._client_factory = client_factory
        self._stop_event = asyncio.Event()
        self._active_stop_event: asyncio.Event | None = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def stop(self) -> None:
        self._stop_event.set()
        if self._active_stop_event is not None:
            self._active_stop_event.set()

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        target_stop = stop_event or self._stop_event
        self._active_stop_event = target_stop
        self._is_running = True
        log_structured(
            self._logger,
            logging.INFO,
            "ingestor_starting",
            mqtt_host=self._config.mqtt_host,
            mqtt_port=self._config.mqtt_port,
            mqtt_topic=self._config.mqtt_topic,
            mqtt_qos=self._config.mqtt_qos,
        )

        try:
            connected = await self._connect_repository(target_stop)
            if connected:
                await self._run_mqtt_loop(target_stop)
        finally:
            await self._repository.close()
            self._active_stop_event = None
            self._is_running = False
            log_structured(self._logger, logging.INFO, "ingestor_stopped")

    async def _connect_repository(self, stop_event: asyncio.Event) -> bool:
        delay = self._config.reconnect_initial_delay

        while True:
            try:
                await self._repository.connect()
                return True
            except DB_CONNECT_EXCEPTIONS as exc:
                if stop_event.is_set():
                    return False
                log_structured(
                    self._logger,
                    logging.ERROR,
                    "db_connection_failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    retry_in_seconds=delay,
                )
                await _wait_for_reconnect(stop_event, delay)
                if stop_event.is_set():
                    return False
                delay = min(delay * 2, self._config.reconnect_max_delay)

    def _build_client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "hostname": self._config.mqtt_host,
            "port": self._config.mqtt_port,
            "username": self._config.mqtt_username,
            "password": self._config.mqtt_password,
            "keepalive": self._config.mqtt_keepalive,
            "identifier": self._config.mqtt_client_id,
            "max_queued_incoming_messages": self._config.mqtt_max_queued_messages,
        }
        if self._config.mqtt_clean_session is not None:
            kwargs["clean_session"] = self._config.mqtt_clean_session
        return kwargs

    async def _run_mqtt_loop(self, stop_event: asyncio.Event) -> None:
        delay = self._config.reconnect_initial_delay

        while not stop_event.is_set():
            try:
                async with self._client_factory(**self._build_client_kwargs()) as client:
                    suback = await client.subscribe(
                        self._config.mqtt_topic,
                        qos=self._config.mqtt_qos,
                    )
                    failed_codes = _extract_failed_suback_codes(suback)
                    if failed_codes:
                        log_structured(
                            self._logger,
                            logging.ERROR,
                            "mqtt_subscribe_rejected",
                            topic=self._config.mqtt_topic,
                            qos=self._config.mqtt_qos,
                            reason_codes=[str(code) for code in failed_codes],
                        )
                        raise aiomqtt.MqttError(
                            f"Assinatura rejeitada pelo broker para {self._config.mqtt_topic}: "
                            f"{failed_codes[0]}"
                        )

                    delay = self._config.reconnect_initial_delay
                    log_structured(
                        self._logger,
                        logging.INFO,
                        "mqtt_connected_and_subscribed",
                        mqtt_host=self._config.mqtt_host,
                        mqtt_port=self._config.mqtt_port,
                        topic=self._config.mqtt_topic,
                        qos=self._config.mqtt_qos,
                    )
                    await self._consume_messages(client, stop_event)
            except aiomqtt.MqttError as exc:
                if stop_event.is_set():
                    break
                log_structured(
                    self._logger,
                    logging.WARNING,
                    "mqtt_connection_lost",
                    error=str(exc),
                    retry_in_seconds=delay,
                )
                await _wait_for_reconnect(stop_event, delay)
                delay = min(delay * 2, self._config.reconnect_max_delay)

    async def _consume_messages(
        self,
        client: Any,
        stop_event: asyncio.Event,
    ) -> None:
        # Disputa stop_event apenas na leitura do próximo item para não cancelar INSERT em voo.
        messages_iter = aiter(client.messages)
        stop_task = asyncio.create_task(stop_event.wait())
        try:
            while not stop_event.is_set():
                next_task = asyncio.create_task(anext(messages_iter))
                done, _ = await asyncio.wait(
                    {next_task, stop_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if next_task in done:
                    try:
                        message = next_task.result()
                    except StopAsyncIteration:
                        break
                    await self._processor.process_message(
                        topic=str(message.topic),
                        payload=message.payload,
                    )
                else:
                    next_task.cancel()
                    with suppress(asyncio.CancelledError, StopAsyncIteration):
                        await next_task
                    break
        finally:
            if not stop_task.done():
                stop_task.cancel()
                with suppress(asyncio.CancelledError):
                    await stop_task
