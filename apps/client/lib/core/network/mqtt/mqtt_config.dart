import 'package:flutter/foundation.dart';

class MqttConfig {
  final String host;
  final int tcpPort;
  final int wsPort;
  final String username;
  final String password;
  final String clientPrefix;

  const MqttConfig({
    this.host = const String.fromEnvironment('MQTT_HOST', defaultValue: 'localhost'),
    this.tcpPort = const int.fromEnvironment('MQTT_TCP_PORT', defaultValue: 1883),
    this.wsPort = const int.fromEnvironment('MQTT_WS_PORT', defaultValue: 9001),
    this.username = const String.fromEnvironment('MQTT_USERNAME', defaultValue: 'app_user'),
    this.password = const String.fromEnvironment('MQTT_PASSWORD', defaultValue: 'app_password'),
    this.clientPrefix = const String.fromEnvironment('MQTT_CLIENT_PREFIX', defaultValue: 'client_app_'),
  });

  int get port => kIsWeb ? wsPort : tcpPort;
}
