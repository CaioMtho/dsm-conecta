import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../session/session_notifier.dart';
import 'consent_state.dart';
import 'privacy_storage.dart';

final privacyNotifierProvider =
    NotifierProvider<PrivacyNotifier, ConsentState>(PrivacyNotifier.new);

class PrivacyNotifier extends Notifier<ConsentState> {
  late final PrivacyStorage _storage;

  @override
  ConsentState build() {
    _storage = ref.watch(privacyStorageProvider);
    final savedState = _storage.loadConsent();
    if (savedState.status == ConsentStatus.accepted && savedState.telemetryAccepted) {
      Future.microtask(() {
        ref.read(sessionNotifierProvider.notifier).createSession();
      });
    }
    return savedState;
  }

  Future<void> acceptAll() async {
    final newState = ConsentState(
      status: ConsentStatus.accepted,
      telemetryAccepted: true,
      sensorsAccepted: true,
      acceptedAt: DateTime.now().toUtc(),
    );
    await _storage.saveConsent(newState);
    state = newState;
    ref.read(sessionNotifierProvider.notifier).createSession();
  }

  Future<void> acceptCustom({
    required bool telemetry,
    required bool sensors,
  }) async {
    final newState = ConsentState(
      status: ConsentStatus.accepted,
      telemetryAccepted: telemetry,
      sensorsAccepted: sensors,
      acceptedAt: DateTime.now().toUtc(),
    );
    await _storage.saveConsent(newState);
    state = newState;
    if (telemetry) {
      ref.read(sessionNotifierProvider.notifier).createSession();
    } else {
      ref.read(sessionNotifierProvider.notifier).clearSession();
    }
  }

  Future<void> reject() async {
    final newState = ConsentState(
      status: ConsentStatus.rejected,
      telemetryAccepted: false,
      sensorsAccepted: false,
      acceptedAt: DateTime.now().toUtc(),
    );
    await _storage.saveConsent(newState);
    state = newState;
    ref.read(sessionNotifierProvider.notifier).clearSession();
  }

  Future<void> revoke() async {
    await reject();
  }

  Future<void> clearAllData() async {
    await _storage.clearAll();
    ref.read(sessionNotifierProvider.notifier).clearSession();
    state = ConsentState.initial();
  }
}
