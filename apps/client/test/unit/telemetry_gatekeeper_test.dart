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
}
