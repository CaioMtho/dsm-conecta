import json
import logging
import threading

import paho.mqtt.client as mqtt
from schemas import TelemetryEvent

from simulator.config import SimulatorConfig

logger = logging.getLogger(__name__)


class MqttSensorClient:
    def __init__(self, config: SimulatorConfig, stop_event: threading.Event | None = None, mqtt_client:mqtt.Client | None = None,) -> None:
        self.config = config
        self.is_connected = False
        self._connected_event = threading.Event()
        self._stop_event = stop_event or threading.Event()

        self.client = mqtt_client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
        client_id=config.client_id,
        clean_session=True,
        )
        # Configurações de LWT, username_pw_set e reconnect_delay_set ...
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
        is_success = reason_code == 0 or (
            hasattr(reason_code, "is_failure") and not reason_code.is_failure
        )

        if is_success:
            self.is_connected = True
            self._connected_event.set()
            logger.info("Conectado ao broker MQTT em %s:%s", self.config.host, self.config.port)
            self.client.publish(
                topic=self.config.topic_status,
                payload=json.dumps({"status":"online"}),
                qos=1,
                retain=True,
            )
        else:
            self.is_connected = False
            self._connected_event.clear()
            logger.error("Falha na conexão/autenticação MQTT (reason_code=%s).", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self.is_connected = False
        self._connected_event.clear()
        logger.warning("Desconectado do broker MQTT (reason_code=%s).", reason_code)

    def connect(self, timeout: float = 5.0) -> bool:
        self._connected_event.clear()
        self.client.loop_start()

        while not self._stop_event.is_set():
            try:
                self.client.connect(self.config.host, self.config.port, keepalive=60)
                if self._connected_event.wait(timeout=timeout):
                    return True
                logger.warning("Timeout aguardando CONNACK do broker. Tentando novamente...")
            except OSError as exc:
                logger.error("Broker inacessível (%s). Nova tentativa em 3s...", exc)

            # Substitui time.sleep(3) para responder imediatamente ao SIGINT/SIGTERM
            if self._stop_event.wait(timeout=3.0):
                break

        return False
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
        self._stop_event.set()
        if self.is_connected:
            try:
                self.client.publish(
                    topic=self.config.topic_status,
                    payload=json.dumps({"status": "offline"}),
                    qos=1,
                    retain=True,
                ).wait_for_publish(timeout=2.0)
            except (OSError, RuntimeError, ValueError) as exc:
                logger.warning("Não foi possível publicar status offline antes de sair: %s", exc)        
        self.client.loop_stop()
        if self.is_connected:
            self.client.disconnect()
            self.is_connected = False
        self._connected_event.clear()
