import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/mqtt/mqtt_connection_status.dart';
import '../../core/network/mqtt/mqtt_service.dart';

class MqttStatusIcon extends ConsumerWidget {
  const MqttStatusIcon({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusAsync = ref.watch(mqttConnectionStatusProvider);
    final status = statusAsync.value ?? MqttConnectionStatus.disconnected;

    final IconData iconData;
    final Color iconColor;
    final String tooltip;

    switch (status) {
      case MqttConnectionStatus.connected:
        iconData = Icons.cloud_done;
        iconColor = Colors.green;
        tooltip = 'MQTT: Conectado';
        break;
      case MqttConnectionStatus.connecting:
        iconData = Icons.cloud_sync;
        iconColor = Colors.orange;
        tooltip = 'MQTT: Conectando...';
        break;
      case MqttConnectionStatus.disconnected:
      case MqttConnectionStatus.fault:
        iconData = Icons.cloud_off;
        iconColor = Colors.grey;
        tooltip = 'MQTT: Desconectado';
        break;
    }

    return IconButton(
      key: const Key('mqtt_status_icon_button'),
      icon: Icon(iconData, color: iconColor),
      tooltip: tooltip,
      onPressed: () {
        if (status == MqttConnectionStatus.disconnected ||
            status == MqttConnectionStatus.fault) {
          ref.read(mqttServiceProvider).connect();
        }
      },
    );
  }
}
