import json
import logging
import time

import paho.mqtt.client as mqtt
from schemas import TelemetryEvent

from src.config import SimulatorConfig

logger = logging.getLogger(__name__)


class MqttSensorClient:
    def __init__(self, config: SimulatorConfig, mqtt_client: mqtt.Client | None = None) -> None:
        self.config = config
        self.is_connected = False

        self.client = mqtt_client or mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.client_id,
            clean_session=True,
        )

        if config.username:
            self.client.username_pw_set(config.username, config.password)

        # Last Will and Testament (RNF02, RNF06)
        self.client.will_set(
            topic=self.config.topic_status,
            payload=json.dumps({"status": "offline"}),
            qos=1,
            retain=True,
        )

        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0 or getattr(reason_code, "is_failure", False) is False:
            self.is_connected = True
            logger.info("Conectado ao broker MQTT em %s:%s", self.config.broker_host, self.config.broker_port)
            self.client.publish(
                topic=self.config.topic_status,
                payload=json.dumps({"status": "online"}),
                qos=1,
                retain=True,
            )
        else:
            self.is_connected = False
            logger.error("Falha na conexão MQTT: %s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None) -> None:
        self.is_connected = False
        logger.warning("Desconectado do broker MQTT (motivo=%s). Aguardando reconexão...", reason_code)

    def connect(self) -> None:
        while True:
            try:
                self.client.connect(self.config.broker_host, self.config.broker_port, keepalive=30)
                self.client.loop_start()
                break
            except OSError as exc:
                logger.error("Broker inacessível (%s). Nova tentativa em 3s...", exc)
                time.sleep(3)

    def publish_event(self, event: TelemetryEvent) -> bool:
        if not self.is_connected:
            logger.warning("Broker offline. Evento %s não enviado.", event.event_id)
            return False

        info = self.client.publish(
            topic=self.config.topic_telemetry,
            payload=event.model_dump_json(),
            qos=1,
        )
        return info.rc == mqtt.MQTT_ERR_SUCCESS

    def disconnect(self) -> None:
        if self.is_connected:
            self.client.publish(
                topic=self.config.topic_status,
                payload=json.dumps({"status": "offline"}),
                qos=1,
                retain=True,
            ).wait_for_publish(timeout=2.0)
        self.client.loop_stop()
        self.client.disconnect()
