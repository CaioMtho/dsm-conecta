import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:uuid/uuid.dart';

import 'mqtt_config.dart';
import 'mqtt_connection_status.dart';
import 'mqtt_transport_client.dart';
import 'mqtt_transport_factory.dart';

final mqttConfigProvider = Provider<MqttConfig>((ref) => const MqttConfig());

final mqttServiceProvider = Provider<MqttService>((ref) {
  final config = ref.watch(mqttConfigProvider);
  final clientId = '${config.clientPrefix}${const Uuid().v4()}';
  final transport = createMqttTransportClient(config, clientId);
  final service = MqttService(config: config, transport: transport);
  ref.onDispose(() => service.dispose());
  return service;
});

final mqttConnectionStatusProvider = StreamProvider<MqttConnectionStatus>((ref) async* {
  final service = ref.watch(mqttServiceProvider);
  yield service.status;
  yield* service.statusStream;
});

class MqttService {
  final MqttConfig config;
  final MqttTransportClient transport;
  final StreamController<MqttConnectionStatus> _statusController =
      StreamController<MqttConnectionStatus>.broadcast();
  late final StreamSubscription<MqttConnectionStatus> _subscription;
  MqttConnectionStatus _status = MqttConnectionStatus.disconnected;

  MqttService({
    required this.config,
    required this.transport,
  }) {
    _status = transport.currentStatus;
    _subscription = transport.statusStream.listen((newStatus) {
      _status = newStatus;
      if (!_statusController.isClosed) {
        _statusController.add(newStatus);
      }
    });
  }

  MqttConnectionStatus get status => _status;
  Stream<MqttConnectionStatus> get statusStream => _statusController.stream;

  Future<bool> connect() {
    return transport.connect(username: config.username, password: config.password);
  }

  void disconnect() {
    transport.disconnect();
  }

  void publish({
    required String topic,
    required String payload,
    MqttQos qos = MqttQos.atLeastOnce,
    bool retain = false,
  }) {
    transport.publish(topic: topic, payload: payload, qos: qos, retain: retain);
  }

  void dispose() {
    _subscription.cancel();
    if (!_statusController.isClosed) {
      _statusController.close();
    }
    transport.disconnect();
    transport.dispose();
  }
}
