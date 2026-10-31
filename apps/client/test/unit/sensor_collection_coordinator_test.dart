import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/sensors/sensor_capture_service.dart';
import 'package:client/core/sensors/sensor_collection_coordinator.dart';
import 'package:client/core/sensors/sensor_reading.dart';
import 'package:client/core/sensors/sensor_telemetry_dispatcher.dart';
import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/telemetry/platform_source_detector.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/fake_mqtt_transport_client.dart';
import '../helpers/fake_sensor_source.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeMqttTransportClient transport;
  late MqttService mqttService;
  late FakeSensorSource motion;
  late SensorCaptureService captureService;
  late SensorTelemetryDispatcher dispatcher;
  late SensorCollectionCoordinator coordinator;

  var consentGranted = true;

  SensorTelemetryDispatcher buildDispatcher() {
    return SensorTelemetryDispatcher(
      gatekeeperResolver: () => TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: consentGranted,
        ),
        sessionId: 'session-uuid',
      ),
      mqttService: mqttService,
      platformSourceDetector: const PlatformSourceDetector(),
    );
  }

  setUp(() {
    consentGranted = true;
    transport = FakeMqttTransportClient();
    mqttService = MqttService(config: const MqttConfig(), transport: transport);
    motion = FakeSensorSource(type: SensorType.motion);
    captureService = SensorCaptureService(
      sources: [motion],
      samplingInterval: const Duration(milliseconds: 20),
    );
    dispatcher = buildDispatcher();
    coordinator = SensorCollectionCoordinator(
      captureService: captureService,
      dispatcher: dispatcher,
    );
    coordinator.attach();
  });

  tearDown(() async {
    await coordinator.dispose();
    mqttService.dispose();
  });

  test('does not collect before consent is granted', () {
    expect(coordinator.isCollecting, isFalse);
  });

  test('starts collecting only after consent is confirmed', () {
    coordinator.setConsent(granted: true);
    expect(coordinator.isCollecting, isTrue);
  });

  test('publishes readings to MQTT while collecting', () async {
    coordinator.setConsent(granted: true);
    motion.emit({'x': 1.0, 'y': 2.0, 'z': 3.0});

    await Future<void>.delayed(const Duration(milliseconds: 40));

    expect(transport.lastPublishedTopic, 'dsm/prod/app/sensor/dispositivo');
  });

  test('stops immediately when app goes to background', () async {
    coordinator.setConsent(granted: true);
    expect(coordinator.isCollecting, isTrue);

    coordinator.didChangeAppLifecycleState(AppLifecycleState.paused);

    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(coordinator.isCollecting, isFalse);
  });

  test('resumes collection when app returns to foreground with consent',
      () async {
    coordinator.setConsent(granted: true);
    coordinator.didChangeAppLifecycleState(AppLifecycleState.paused);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(coordinator.isCollecting, isFalse);

    coordinator.didChangeAppLifecycleState(AppLifecycleState.resumed);
    expect(coordinator.isCollecting, isTrue);
  });

  test('stops immediately when consent is revoked', () async {
    coordinator.setConsent(granted: true);
    expect(coordinator.isCollecting, isTrue);

    coordinator.setConsent(granted: false);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(coordinator.isCollecting, isFalse);
  });

  test('does not resume collection in foreground without consent', () {
    coordinator.setConsent(granted: false);
    coordinator.didChangeAppLifecycleState(AppLifecycleState.resumed);
    expect(coordinator.isCollecting, isFalse);
  });
}
