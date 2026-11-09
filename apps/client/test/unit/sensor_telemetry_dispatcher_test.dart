import 'dart:convert';

import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/sensors/sensor_reading.dart';
import 'package:client/core/sensors/sensor_telemetry_dispatcher.dart';
import 'package:client/core/telemetry/platform_source_detector.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mqtt_client/mqtt_client.dart';

import '../helpers/fake_mqtt_transport_client.dart';

TelemetryGatekeeper _gatekeeper({
  ConsentStatus status = ConsentStatus.accepted,
  bool telemetry = true,
  bool sensors = true,
  String? sessionId = 'session-uuid',
}) {
  return TelemetryGatekeeper(
    consent: ConsentState(
      status: status,
      telemetryAccepted: telemetry,
      sensorsAccepted: sensors,
    ),
    sessionId: sessionId,
  );
}

void main() {
  late FakeMqttTransportClient transport;
  late MqttService mqttService;

  setUp(() {
    transport = FakeMqttTransportClient();
    mqttService = MqttService(config: const MqttConfig(), transport: transport);
  });

  tearDown(() {
    mqttService.dispose();
  });

  SensorTelemetryDispatcher buildDispatcher(TelemetryGatekeeper gatekeeper) {
    return SensorTelemetryDispatcher(
      gatekeeperResolver: () => gatekeeper,
      mqttService: mqttService,
      platformSourceDetector: const PlatformSourceDetector(),
    );
  }

  final reading = SensorReading(
    type: SensorType.motion,
    capturedAt: _fixedTime,
    values: const {'x': 0.1, 'y': 9.8, 'z': 0.0},
  );

  group('SensorTelemetryDispatcher publication', () {
    test('publishes to the sensor topic with QoS 1 when consent allows', () {
      final dispatcher = buildDispatcher(_gatekeeper());

      final result = dispatcher.dispatchReading(reading);

      expect(result, isTrue);
      expect(
        transport.lastPublishedTopic,
        SensorTelemetryDispatcher.sensorTopic,
      );
      expect(transport.lastPublishedTopic, 'dsm/prod/app/sensor/dispositivo');
      expect(transport.lastPublishedQos, MqttQos.atLeastOnce);
    });

    test('serializes a well-formed telemetry payload', () {
      final dispatcher = buildDispatcher(_gatekeeper());

      dispatcher.dispatchReading(reading);

      final decoded =
          json.decode(transport.lastPublishedPayload!) as Map<String, dynamic>;

      expect(decoded['schema_version'], '1.0');
      expect(decoded['category'], 'leitura_sensor');
      expect(decoded['session_id'], 'session-uuid');
      expect(decoded['event_id'], isNotEmpty);
      expect(decoded['source'], isNotEmpty);

      final payload = decoded['payload'] as Map<String, dynamic>;
      expect(payload['sensor'], 'movimento');
      expect(payload['captured_at'], isNotEmpty);

      final values = payload['values'] as Map<String, dynamic>;
      expect(values['x'], 0.1);
      expect(values['y'], 9.8);
      expect(values['z'], 0.0);
    });
  });

  group('SensorTelemetryDispatcher consent gating', () {
    test('does not publish when sensor consent is missing', () {
      final dispatcher = buildDispatcher(_gatekeeper(sensors: false));

      final result = dispatcher.dispatchReading(reading);

      expect(result, isFalse);
      expect(transport.lastPublishedTopic, isNull);
    });

    test('does not publish when consent is rejected', () {
      final dispatcher =
          buildDispatcher(_gatekeeper(status: ConsentStatus.rejected));

      final result = dispatcher.dispatchReading(reading);

      expect(result, isFalse);
      expect(transport.lastPublishedTopic, isNull);
    });

    test('does not publish when there is no active session', () {
      final dispatcher = buildDispatcher(_gatekeeper(sessionId: null));

      final result = dispatcher.dispatchReading(reading);

      expect(result, isFalse);
      expect(transport.lastPublishedTopic, isNull);
    });
  });
}

final DateTime _fixedTime = DateTime.utc(2026, 1, 1, 12);
