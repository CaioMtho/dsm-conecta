import logging
import threading

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MqttSensorClient:
    def __init__(self, config, stop_event: threading.Event | None = None) -> None:
        self.config = config
        self.is_connected = False
        self._connected_event = threading.Event()
        self._stop_event = stop_event or threading.Event()

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        # ... mantenha aqui suas configurações de LWT, username_pw_set e reconnect_delay_set ...

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        is_success = reason_code == 0 or (
            hasattr(reason_code, "is_failure") and not reason_code.is_failure
        )

        if is_success:
            self.is_connected = True
            self._connected_event.set()
            logger.info("Conectado ao broker MQTT com sucesso.")
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

    def disconnect(self) -> None:
        self._stop_event.set()
        self.client.loop_stop()
        if self.is_connected:
            self.client.disconnect()
            self.is_connected = False
        self._connected_event.clear()
