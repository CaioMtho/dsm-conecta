import 'package:flutter/foundation.dart';

class MqttConfig {
  final String? _explicitHost;
  final int tcpPort;
  final int wsPort;
  final String wsPath;
  final String username;
  final String password;
  final String clientPrefix;

  const MqttConfig({
    String? host,
    this.tcpPort = const int.fromEnvironment('MQTT_TCP_PORT', defaultValue: 1883),
    this.wsPort = const int.fromEnvironment('MQTT_WS_PORT', defaultValue: 9001),
    this.wsPath = const String.fromEnvironment('MQTT_WS_PATH', defaultValue: ''),
    this.username = const String.fromEnvironment('MQTT_USERNAME', defaultValue: 'app_user'),
    this.password = const String.fromEnvironment('MQTT_PASSWORD', defaultValue: 'app_pass_dev'),
    this.clientPrefix = const String.fromEnvironment('MQTT_CLIENT_PREFIX', defaultValue: 'client_app_'),
  }) : _explicitHost = host;

  static const String _envHost = String.fromEnvironment('MQTT_HOST', defaultValue: '');

  static String get defaultHost {
    if (_envHost.isNotEmpty) {
      return _envHost;
    }
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return '10.0.2.2';
    }
    return 'localhost';
  }

  String get host => _explicitHost ?? defaultHost;

  String get wsServerUri {
    final path = wsPath.isNotEmpty
        ? (wsPath.startsWith('/') ? wsPath : '/$wsPath')
        : '';
    return 'ws://$host$path';
  }

  int get port => kIsWeb ? wsPort : tcpPort;
}
