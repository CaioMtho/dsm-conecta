import 'package:mqtt_client/mqtt_client.dart';
import 'package:uuid/uuid.dart';

import '../network/mqtt/mqtt_service.dart';
import '../telemetry/platform_source_detector.dart';
import '../telemetry/telemetry_event_model.dart';
import '../telemetry/telemetry_gatekeeper.dart';
import 'sensor_reading.dart';

class SensorTelemetryDispatcher {
  static const String sensorTopic = 'dsm/prod/app/sensor/dispositivo';
  static const String category = 'leitura_sensor';

  final TelemetryGatekeeper Function() gatekeeperResolver;
  final MqttService mqttService;
  final PlatformSourceDetector platformSourceDetector;
  final Uuid uuid;

  SensorTelemetryDispatcher({
    required this.gatekeeperResolver,
    required this.mqttService,
    required this.platformSourceDetector,
    this.uuid = const Uuid(),
  });

  bool dispatchReading(SensorReading reading) {
    final gatekeeper = gatekeeperResolver();
    if (!gatekeeper.canCollectSensors()) {
      return false;
    }

    final sessionId = gatekeeper.currentSessionId;
    if (sessionId == null || sessionId.isEmpty) {
      return false;
    }

    final event = TelemetryEventModel(
      schemaVersion: '1.0',
      timestamp: DateTime.now().toUtc(),
      eventId: uuid.v4(),
      sessionId: sessionId,
      source: platformSourceDetector.detect(),
      category: category,
      payload: reading.toMap(),
    );

    mqttService.publish(
      topic: sensorTopic,
      payload: event.toJson(),
      qos: MqttQos.atLeastOnce,
    );

    return true;
  }
}
