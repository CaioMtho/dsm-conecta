import 'dart:async';
import 'package:mqtt_client/mqtt_browser_client.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'mqtt_config.dart';
import 'mqtt_connection_status.dart';
import 'mqtt_transport_client.dart';

class MqttTransportWeb implements MqttTransportClient {
  final MqttBrowserClient _client;
  final StreamController<MqttConnectionStatus> _statusController =
      StreamController<MqttConnectionStatus>.broadcast();
  MqttConnectionStatus _currentStatus = MqttConnectionStatus.disconnected;

  MqttTransportWeb(MqttConfig config, String clientId)
      : _client = MqttBrowserClient.withPort('ws://${config.host}', clientId, config.wsPort) {
    _client.keepAlivePeriod = 30;
    _client.autoReconnect = true;
    _client.websocketProtocols = MqttClientConstants.protocolsSingleDefault;
    _client.onConnected = _onConnected;
    _client.onDisconnected = _onDisconnected;
    _client.onAutoReconnected = _onConnected;
    _client.onAutoReconnect = () => _updateStatus(MqttConnectionStatus.connecting);
  }

  void _updateStatus(MqttConnectionStatus status) {
    _currentStatus = status;
    _statusController.add(status);
  }

  void _onConnected() => _updateStatus(MqttConnectionStatus.connected);
  void _onDisconnected() => _updateStatus(MqttConnectionStatus.disconnected);

  @override
  Stream<MqttConnectionStatus> get statusStream => _statusController.stream;

  @override
  MqttConnectionStatus get currentStatus => _currentStatus;

  @override
  Future<bool> connect({required String username, required String password}) async {
    _updateStatus(MqttConnectionStatus.connecting);
    try {
      final result = await _client.connect(username, password);
      if (result?.state == MqttConnectionState.connected) {
        _updateStatus(MqttConnectionStatus.connected);
        return true;
      } else {
        _updateStatus(MqttConnectionStatus.fault);
        return false;
      }
    } catch (_) {
      _updateStatus(MqttConnectionStatus.fault);
      return false;
    }
  }

  @override
  void disconnect() {
    _client.disconnect();
    _updateStatus(MqttConnectionStatus.disconnected);
  }

  @override
  void publish({
    required String topic,
    required String payload,
    MqttQos qos = MqttQos.atLeastOnce,
    bool retain = false,
  }) {
    final builder = MqttClientPayloadBuilder();
    builder.addString(payload);
    _client.publishMessage(topic, qos, builder.payload!, retain: retain);
  }
}

MqttTransportClient createMqttTransportClient(MqttConfig config, String clientId) {
  return MqttTransportWeb(config, clientId);
}
