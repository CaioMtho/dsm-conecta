import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_notifier.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/core/session/session_notifier.dart';
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

  group('PrivacyNotifier', () {
    test('loads initial undetermined state on startup', () {
      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.undetermined);
      expect(container.read(sessionNotifierProvider), isNull);
    });

    test('restores saved accepted consent and creates session on startup', () async {
      final storage = container.read(privacyStorageProvider);
      await storage.saveConsent(
        ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: true,
          acceptedAt: DateTime.now().toUtc(),
        ),
      );

      final newContainer = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
      );
      addTearDown(newContainer.dispose);

      final state = newContainer.read(privacyNotifierProvider);
      await Future<void>.value();
      expect(state.status, ConsentStatus.accepted);
      expect(state.telemetryAccepted, isTrue);
      expect(newContainer.read(sessionNotifierProvider), isNotNull);
    });

    test('acceptAll updates status and starts session', () async {
      final notifier = container.read(privacyNotifierProvider.notifier);
      await notifier.acceptAll();

      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.accepted);
      expect(state.telemetryAccepted, isTrue);
      expect(state.sensorsAccepted, isTrue);
      expect(state.acceptedAt, isNotNull);

      expect(container.read(sessionNotifierProvider), isNotNull);
    });

    test('acceptCustom without telemetry does not start session', () async {
      final notifier = container.read(privacyNotifierProvider.notifier);
      await notifier.acceptCustom(telemetry: false, sensors: true);

      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.accepted);
      expect(state.telemetryAccepted, isFalse);
      expect(state.sensorsAccepted, isTrue);

      expect(container.read(sessionNotifierProvider), isNull);
    });

    test('acceptCustom with telemetry starts session', () async {
      final notifier = container.read(privacyNotifierProvider.notifier);
      await notifier.acceptCustom(telemetry: true, sensors: false);

      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.accepted);
      expect(state.telemetryAccepted, isTrue);
      expect(state.sensorsAccepted, isFalse);

      expect(container.read(sessionNotifierProvider), isNotNull);
    });

    test('reject sets rejected status and clears session', () async {
      final notifier = container.read(privacyNotifierProvider.notifier);
      await notifier.acceptAll();
      expect(container.read(sessionNotifierProvider), isNotNull);

      await notifier.reject();

      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.rejected);
      expect(state.telemetryAccepted, isFalse);
      expect(state.sensorsAccepted, isFalse);
      expect(container.read(sessionNotifierProvider), isNull);
    });

    test('revoke reverts consent and clears session', () async {
      final notifier = container.read(privacyNotifierProvider.notifier);
      await notifier.acceptAll();

      await notifier.revoke();

      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.rejected);
      expect(container.read(sessionNotifierProvider), isNull);
    });

    test('clearAllData wipes storage and sets state to initial', () async {
      final notifier = container.read(privacyNotifierProvider.notifier);
      await notifier.acceptAll();

      await notifier.clearAllData();

      final state = container.read(privacyNotifierProvider);
      expect(state.status, ConsentStatus.undetermined);
      expect(container.read(sessionNotifierProvider), isNull);
    });
  });
}
