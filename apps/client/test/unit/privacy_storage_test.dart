import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late SharedPreferences prefs;
  late PrivacyStorage storage;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    storage = PrivacyStorage(prefs);
  });

  group('PrivacyStorage', () {
    test('returns initial state when storage is empty', () {
      final state = storage.loadConsent();
      expect(state.status, ConsentStatus.undetermined);
      expect(state.telemetryAccepted, isFalse);
    });

    test('saves and loads accepted consent state', () async {
      final now = DateTime.utc(2026, 9, 12, 12, 0, 0);
      final toSave = ConsentState(
        status: ConsentStatus.accepted,
        telemetryAccepted: true,
        sensorsAccepted: true,
        acceptedAt: now,
      );

      await storage.saveConsent(toSave);
      final loaded = storage.loadConsent();

      expect(loaded.status, ConsentStatus.accepted);
      expect(loaded.telemetryAccepted, isTrue);
      expect(loaded.sensorsAccepted, isTrue);
      expect(loaded.acceptedAt, now);
    });

    test('saves consent with null acceptedAt removes timestamp', () async {
      final now = DateTime.utc(2026, 9, 12, 12, 0, 0);
      await storage.saveConsent(
        ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: true,
          acceptedAt: now,
        ),
      );

      await storage.saveConsent(
        const ConsentState(
          status: ConsentStatus.rejected,
          telemetryAccepted: false,
          sensorsAccepted: false,
          acceptedAt: null,
        ),
      );

      final loaded = storage.loadConsent();
      expect(loaded.status, ConsentStatus.rejected);
      expect(loaded.acceptedAt, isNull);
    });

    test('clearAll wipes stored privacy keys', () async {
      await storage.saveConsent(
        ConsentState(
          status: ConsentStatus.accepted,
          telemetryAccepted: true,
          sensorsAccepted: false,
          acceptedAt: DateTime.now().toUtc(),
        ),
      );

      await storage.clearAll();
      final loaded = storage.loadConsent();

      expect(loaded.status, ConsentStatus.undetermined);
      expect(loaded.telemetryAccepted, isFalse);
    });

    test('privacyStorageProvider provides instance and sharedPreferencesProvider throws by default', () {
      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
      );
      addTearDown(container.dispose);

      final providerStorage = container.read(privacyStorageProvider);
      expect(providerStorage, isA<PrivacyStorage>());

      final unoverriddenContainer = ProviderContainer();
      addTearDown(unoverriddenContainer.dispose);
      expect(
        () => unoverriddenContainer.read(sharedPreferencesProvider),
        throwsUnimplementedError,
      );
    });
  });
}
