import os
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
BROKER_WS_PORT = int(os.getenv("MQTT_WS_PORT", "9001"))

APP_USER = os.getenv("MQTT_APP_USER", "app_user")
APP_PASS = os.getenv("MQTT_APP_PASSWORD", "app_pass_dev")

SIMULATOR_USER = os.getenv("MQTT_SIMULATOR_USER", "simulator_user")
SIMULATOR_PASS = os.getenv("MQTT_SIMULATOR_PASSWORD", "simulator_pass_dev")

INGESTOR_USER = os.getenv("MQTT_INGESTOR_USER", "ingestor_user")
INGESTOR_PASS = os.getenv("MQTT_INGESTOR_PASSWORD", "ingestor_pass_dev")

ADMIN_USER = os.getenv("MQTT_ADMIN_USER", "admin_user")
ADMIN_PASS = os.getenv("MQTT_ADMIN_PASSWORD", "admin_pass_dev")


def connect_client(username=None, password=None, transport="tcp", port=None):
    if port is None:
        port = BROKER_WS_PORT if transport == "websockets" else BROKER_PORT

    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        transport=transport,
    )
    if username is not None:
        client.username_pw_set(username, password)

    connect_result = []

    def on_connect(c, userdata, flags, rc, properties=None):
        connect_result.append(rc)

    client.on_connect = on_connect

    try:
        client.connect(BROKER_HOST, port, keepalive=10)
        client.loop_start()
        for _ in range(30):
            if connect_result:
                break
            time.sleep(0.1)
    finally:
        client.loop_stop()

    if not connect_result:
        return client, -1  # Timeout / no connection
    return client, connect_result[0]


def test_anonymous_connection_rejected():
    """Critério 1: O broker deve rejeitar conexões anônimas."""
    client, rc = connect_client(username=None, password=None)
    try:
        # rc != 0 (em MQTT v5/v3.1.1 rc é código de erro como 4, 5 ou ReasonCodes 134/135)
        # Se for aceito (rc == 0 ou rc.is_failure == False), deve falhar!
        is_success = (rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure))
        assert not is_success, f"Conexão anônima não deve ser permitida, mas retornou rc={rc}"
    finally:
        client.disconnect()


def test_invalid_credentials_rejected():
    """Critério 1: Credenciais inválidas devem ser rejeitadas."""
    client, rc = connect_client(username="invalid_user", password="wrong_password")
    try:
        is_success = (rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure))
        assert not is_success, f"Credenciais inválidas foram aceitas: rc={rc}"
    finally:
        client.disconnect()


def test_valid_users_can_authenticate():
    """Critério 1 e 3: Usuários válidos configurados via env conseguem se autenticar."""
    for user, pwd in [
        (APP_USER, APP_PASS),
        (SIMULATOR_USER, SIMULATOR_PASS),
        (INGESTOR_USER, INGESTOR_PASS),
        (ADMIN_USER, ADMIN_PASS),
    ]:
        client, rc = connect_client(username=user, password=pwd)
        try:
            is_success = (rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure))
            assert is_success, f"Falha ao autenticar usuário '{user}': rc={rc}"
        finally:
            client.disconnect()


def test_acl_restrictions():
    """Critério 2: ACLs restringem publicações e inscrições por perfil."""
    # Ingestor assina dsm/prod/#
    ingestor = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    ingestor.username_pw_set(INGESTOR_USER, INGESTOR_PASS)
    received_messages = []

    def on_message(c, userdata, msg):
        received_messages.append((msg.topic, msg.payload.decode()))

    ingestor.on_message = on_message
    ingestor.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
    ingestor.subscribe("dsm/prod/#")
    ingestor.loop_start()

    time.sleep(0.5)

    try:
        # 1. app_user publica em dsm/prod/app/interacao/tela (deve ser recebido)
        app_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        app_client.username_pw_set(APP_USER, APP_PASS)
        app_client.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
        app_client.loop_start()
        app_client.publish("dsm/prod/app/interacao/tela", "payload_app", qos=1)
        time.sleep(0.5)
        app_client.disconnect()
        app_client.loop_stop()

        # 2. simulator_user publica em dsm/prod/totem/sensor/contagem (deve ser recebido)
        sim_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        sim_client.username_pw_set(SIMULATOR_USER, SIMULATOR_PASS)
        sim_client.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
        sim_client.loop_start()
        sim_client.publish("dsm/prod/totem/sensor/contagem", "payload_sim", qos=1)
        time.sleep(0.5)
        sim_client.disconnect()
        sim_client.loop_stop()

        # Verifica se o ingestor recebeu ambas as mensagens
        topics = [t for t, p in received_messages]
        assert "dsm/prod/app/interacao/tela" in topics, "Ingestor não recebeu mensagem do app"
        assert "dsm/prod/totem/sensor/contagem" in topics, "Ingestor não recebeu mensagem do simulador"

        # 3. app_user tenta publicar em dsm/prod/totem/bloqueado (ACL não deve permitir entrega)
        app_bad = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        app_bad.username_pw_set(APP_USER, APP_PASS)
        app_bad.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
        app_bad.loop_start()
        app_bad.publish("dsm/prod/totem/bloqueado", "payload_violacao", qos=1)
        time.sleep(0.5)
        app_bad.disconnect()
        app_bad.loop_stop()

        violating_topics = [t for t, p in received_messages if t == "dsm/prod/totem/bloqueado"]
        assert len(violating_topics) == 0, "Mensagem não autorizada pela ACL foi entregue!"

    finally:
        ingestor.disconnect()
        ingestor.loop_stop()


def test_websocket_connections():
    """Critério 5: Suporte a WebSockets para permitir conexões do Flutter Web."""
    # 1. Conexão direta na porta WebSocket 9001
    client_ws, rc_ws = connect_client(
        username=APP_USER,
        password=APP_PASS,
        transport="websockets",
        port=BROKER_WS_PORT,
    )
    try:
        is_success = (rc_ws == 0 or (hasattr(rc_ws, "is_failure") and not rc_ws.is_failure))
        assert is_success, f"Falha na conexão MQTT via WebSockets na porta {BROKER_WS_PORT}: rc={rc_ws}"
    finally:
        client_ws.disconnect()

    # 2. Conexão via Nginx proxy na porta 80 endpoint /mqtt
    client_nginx = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        transport="websockets",
    )
    client_nginx.ws_set_options(path="/mqtt")
    client_nginx.username_pw_set(APP_USER, APP_PASS)

    connect_result = []

    def on_connect(c, userdata, flags, rc, properties=None):
        connect_result.append(rc)

    client_nginx.on_connect = on_connect
    try:
        client_nginx.connect(BROKER_HOST, 80, keepalive=10)
        client_nginx.loop_start()
        for _ in range(30):
            if connect_result:
                break
            time.sleep(0.1)
        client_nginx.loop_stop()
        rc_nginx = connect_result[0] if connect_result else -1
        is_success = (rc_nginx == 0 or (hasattr(rc_nginx, "is_failure") and not rc_nginx.is_failure))
        assert is_success, f"Falha na conexão MQTT via Nginx /mqtt na porta 80: rc={rc_nginx}"
    finally:
        client_nginx.disconnect()

