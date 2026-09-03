#!/bin/sh
set -e

PASSWD_FILE="/mosquitto/data/password_file"

mkdir -p /mosquitto/data
# Limpa ou inicializa o arquivo de senhas
> "$PASSWD_FILE"

add_user() {
    user="$1"
    pass="$2"
    if [ -n "$user" ] && [ -n "$pass" ]; then
        mosquitto_passwd -b "$PASSWD_FILE" "$user" "$pass"
    fi
}

add_user "${MQTT_APP_USER:-app_user}" "${MQTT_APP_PASSWORD:-app_pass_dev}"
add_user "${MQTT_SIMULATOR_USER:-simulator_user}" "${MQTT_SIMULATOR_PASSWORD:-simulator_pass_dev}"
add_user "${MQTT_INGESTOR_USER:-ingestor_user}" "${MQTT_INGESTOR_PASSWORD:-ingestor_pass_dev}"
add_user "${MQTT_ADMIN_USER:-admin_user}" "${MQTT_ADMIN_PASSWORD:-admin_pass_dev}"

chmod 0700 "$PASSWD_FILE"
chown mosquitto:mosquitto "$PASSWD_FILE" 2>/dev/null || true

exec /docker-entrypoint.sh /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
