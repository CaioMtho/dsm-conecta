import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_notifier.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late SharedPreferences prefs;
  late ProviderContainer container;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('TelemetryGatekeeper', () {
    test('blocks telemetry when consent is undetermined', () {
      final gatekeeper = container.read(telemetryGatekeeperProvider);

      expect(gatekeeper.canEmitTelemetry(), isFalse);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNull);
    });

    test('blocks telemetry when consent is rejected', () async {
      await container.read(privacyNotifierProvider.notifier).reject();
      final gatekeeper = container.read(telemetryGatekeeperProvider);

      expect(gatekeeper.canEmitTelemetry(), isFalse);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNull);
    });

    test('allows telemetry and sensors when accepted with full consent', () async {
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      final gatekeeper = container.read(telemetryGatekeeperProvider);

      expect(gatekeeper.canEmitTelemetry(), isTrue);
      expect(gatekeeper.canCollectSensors(), isTrue);
      expect(gatekeeper.currentSessionId, isNotNull);
    });

    test('allows telemetry but blocks sensors when granular consent excludes sensors', () async {
      await container.read(privacyNotifierProvider.notifier).acceptCustom(
            telemetry: true,
            sensors: false,
          );
      final gatekeeper = container.read(telemetryGatekeeperProvider);

      expect(gatekeeper.canEmitTelemetry(), isTrue);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNotNull);
    });

    test('immediately revokes access when consent is revoked', () async {
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      var gatekeeper = container.read(telemetryGatekeeperProvider);
      expect(gatekeeper.canEmitTelemetry(), isTrue);

      await container.read(privacyNotifierProvider.notifier).revoke();
      gatekeeper = container.read(telemetryGatekeeperProvider);

      expect(gatekeeper.canEmitTelemetry(), isFalse);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNull);
    });
  });

  group('TelemetryGatekeeper direct instantiation', () {
    test('blocks telemetry when sessionId is null even if consent accepted', () {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: true,
        ),
        sessionId: null,
      );

      expect(gatekeeper.canEmitTelemetry(), isFalse);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNull);
    });

    test('blocks telemetry when sessionId is empty even if consent accepted', () {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: true,
        ),
        sessionId: '',
      );

      expect(gatekeeper.canEmitTelemetry(), isFalse);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNull);
    });

    test('blocks telemetry when consent is rejected despite active session ID', () {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.rejected,
          telemetryAccepted: true,
          sensorsAccepted: true,
        ),
        sessionId: 'test-session-uuid',
      );

      expect(gatekeeper.canEmitTelemetry(), isFalse);
      expect(gatekeeper.canCollectSensors(), isFalse);
      expect(gatekeeper.currentSessionId, isNull);
    });

    test('allows telemetry and exposes session ID when consent accepted with valid session', () {
      const gatekeeper = TelemetryGatekeeper(
        consent: ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: true,
        ),
        sessionId: 'test-session-uuid',
      );

      expect(gatekeeper.canEmitTelemetry(), isTrue);
      expect(gatekeeper.canCollectSensors(), isTrue);
      expect(gatekeeper.currentSessionId, equals('test-session-uuid'));
    });
  });
}
