import 'dart:convert';
import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_notifier.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/core/telemetry/platform_source_detector.dart';
import 'package:client/core/telemetry/telemetry_dispatcher.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../helpers/fake_mqtt_transport_client.dart';

void main() {
  group('TelemetryDispatcher', () {
    late FakeMqttTransportClient fakeTransport;
    late MqttService mqttService;

    setUp(() {
      fakeTransport = FakeMqttTransportClient();
      mqttService = MqttService(
        config: const MqttConfig(),
        transport: fakeTransport,
      );
    });

    tearDown(() {
      fakeTransport.dispose();
      mqttService.dispose();
    });

    test('discards screen interaction when consent is rejected or not granted', () async {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.rejected,
          telemetryAccepted: false,
          sensorsAccepted: false,
        ),
        sessionId: 'session-123',
      );
      final dispatcher = TelemetryDispatcher(
        gatekeeper: gatekeeper,
        mqttService: mqttService,
        platformSourceDetector: const PlatformSourceDetector(),
      );

      final dispatched = await dispatcher.dispatchScreenInteraction(
        screenName: 'HomeScreen',
        durationSeconds: 15.0,
      );

      expect(dispatched, isFalse);
      expect(fakeTransport.lastPublishedTopic, isNull);
      expect(fakeTransport.lastPublishedPayload, isNull);
    });

    test('discards screen interaction when telemetry consent is disabled', () async {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: false,
          sensorsAccepted: false,
        ),
        sessionId: 'session-123',
      );
      final dispatcher = TelemetryDispatcher(
        gatekeeper: gatekeeper,
        mqttService: mqttService,
        platformSourceDetector: const PlatformSourceDetector(),
      );

      final dispatched = await dispatcher.dispatchScreenInteraction(
        screenName: 'HomeScreen',
        durationSeconds: 15.0,
      );

      expect(dispatched, isFalse);
      expect(fakeTransport.lastPublishedTopic, isNull);
    });

    test('discards screen interaction when session ID is missing or empty', () async {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: false,
        ),
        sessionId: null,
      );
      final dispatcher = TelemetryDispatcher(
        gatekeeper: gatekeeper,
        mqttService: mqttService,
        platformSourceDetector: const PlatformSourceDetector(),
      );

      final dispatched = await dispatcher.dispatchScreenInteraction(
        screenName: 'HomeScreen',
        durationSeconds: 15.0,
      );

      expect(dispatched, isFalse);
      expect(fakeTransport.lastPublishedTopic, isNull);
    });

    test('publishes screen interaction to dsm/prod/app/interacao/tela when consented', () async {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: true,
        ),
        sessionId: 'valid-session-uuid-456',
      );
      final dispatcher = TelemetryDispatcher(
        gatekeeper: gatekeeper,
        mqttService: mqttService,
        platformSourceDetector: const PlatformSourceDetector(),
      );

      final dispatched = await dispatcher.dispatchScreenInteraction(
        screenName: 'SettingsScreen',
        durationSeconds: 8.5,
      );

      expect(dispatched, isTrue);
      expect(fakeTransport.lastPublishedTopic, 'dsm/prod/app/interacao/tela');
      expect(fakeTransport.lastPublishedQos, MqttQos.atLeastOnce);

      final payload = json.decode(fakeTransport.lastPublishedPayload!) as Map<String, dynamic>;
      expect(payload['schema_version'], '1.0');
      expect(payload['session_id'], 'valid-session-uuid-456');
      expect(payload['category'], 'interacao_tela');
      expect(payload['event_id'], isNotEmpty);
      expect(payload['timestamp'], isNotEmpty);
      expect(payload['source'], isNotEmpty);
      expect(payload['payload']['screen_name'], 'SettingsScreen');
      expect(payload['payload']['duration_seconds'], 8.5);
    });
  });

  group('Riverpod Providers', () {
    test('platformSourceDetectorProvider provides PlatformSourceDetector', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final detector = container.read(platformSourceDetectorProvider);
      expect(detector, isA<PlatformSourceDetector>());
    });

    test('telemetryDispatcherProvider wires dependencies correctly', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final fakeTransport = FakeMqttTransportClient();
      final testService = MqttService(
        config: const MqttConfig(),
        transport: fakeTransport,
      );

      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          mqttServiceProvider.overrideWithValue(testService),
        ],
      );
      addTearDown(() {
        container.dispose();
        testService.dispose();
      });

      final dispatcher = container.read(telemetryDispatcherProvider);
      expect(dispatcher, isA<TelemetryDispatcher>());

      // Consent not accepted yet, should not dispatch
      final beforeConsent = await dispatcher.dispatchScreenInteraction(
        screenName: 'TestScreen',
        durationSeconds: 3.0,
      );
      expect(beforeConsent, isFalse);

      // Accept consent and check dispatch through container
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      final updatedDispatcher = container.read(telemetryDispatcherProvider);
      final afterConsent = await updatedDispatcher.dispatchScreenInteraction(
        screenName: 'TestScreen',
        durationSeconds: 3.0,
      );
      expect(afterConsent, isTrue);
      expect(fakeTransport.lastPublishedTopic, 'dsm/prod/app/interacao/tela');
      expect(fakeTransport.lastPublishedQos, MqttQos.atLeastOnce);
    });
  });
}
