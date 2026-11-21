import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import aiomqtt

from ingestor.config import IngestorConfig
from ingestor.logging_config import log_structured
from ingestor.processor import MessageProcessor
from ingestor.repository import EventRepository


async def _wait_for_reconnect(stop_event: asyncio.Event, delay: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except TimeoutError:
        pass


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
        )
        self._client_factory = client_factory
        self._stop_event = asyncio.Event()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        target_stop = stop_event or self._stop_event
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
            await self._repository.connect()
            await self._run_mqtt_loop(target_stop)
        finally:
            await self._repository.close()
            self._is_running = False
            log_structured(self._logger, logging.INFO, "ingestor_stopped")

    async def _run_mqtt_loop(self, stop_event: asyncio.Event) -> None:
        delay = self._config.reconnect_initial_delay

        while not stop_event.is_set():
            try:
                async with self._client_factory(
                    hostname=self._config.mqtt_host,
                    port=self._config.mqtt_port,
                    username=self._config.mqtt_username,
                    password=self._config.mqtt_password,
                    keepalive=self._config.mqtt_keepalive,
                    identifier=self._config.mqtt_client_id,
                ) as client:
                    await client.subscribe(
                        self._config.mqtt_topic,
                        qos=self._config.mqtt_qos,
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
        async def _consume() -> None:
            async for message in client.messages:
                if stop_event.is_set():
                    break
                await self._processor.process_message(
                    topic=str(message.topic),
                    payload=message.payload,
                )

        # Corrida com stop_event evita travar aguardando nova mensagem durante shutdown gracioso.
        consume_task = asyncio.create_task(_consume())
        stop_task = asyncio.create_task(stop_event.wait())
        done, pending = await asyncio.wait(
            {consume_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        if consume_task in done and not consume_task.cancelled():
            consume_task.result()
