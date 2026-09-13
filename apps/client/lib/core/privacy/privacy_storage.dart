import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'consent_state.dart';

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

final privacyStorageProvider = Provider<PrivacyStorage>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return PrivacyStorage(prefs);
});

class PrivacyStorage {
  static const _keyStatus = 'privacy_consent_status';
  static const _keyTelemetry = 'privacy_telemetry_accepted';
  static const _keySensors = 'privacy_sensors_accepted';
  static const _keyTimestamp = 'privacy_consent_timestamp';

  final SharedPreferences _prefs;

  PrivacyStorage(this._prefs);

  Future<void> saveConsent(ConsentState state) async {
    await _prefs.setString(_keyStatus, state.status.name);
    await _prefs.setBool(_keyTelemetry, state.telemetryAccepted);
    await _prefs.setBool(_keySensors, state.sensorsAccepted);
    if (state.acceptedAt != null) {
      await _prefs.setString(_keyTimestamp, state.acceptedAt!.toIso8601String());
    } else {
      await _prefs.remove(_keyTimestamp);
    }
  }

  ConsentState loadConsent() {
    final statusStr = _prefs.getString(_keyStatus);
    if (statusStr == null) {
      return ConsentState.initial();
    }

    final status = ConsentStatus.values.firstWhere(
      (e) => e.name == statusStr,
      orElse: () => ConsentStatus.undetermined,
    );
    final telemetry = _prefs.getBool(_keyTelemetry) ?? false;
    final sensors = _prefs.getBool(_keySensors) ?? false;
    final timestampStr = _prefs.getString(_keyTimestamp);
    final timestamp = timestampStr != null ? DateTime.tryParse(timestampStr) : null;

    return ConsentState(
      status: status,
      telemetryAccepted: telemetry,
      sensorsAccepted: sensors,
      acceptedAt: timestamp,
    );
  }

  Future<void> clearAll() async {
    await _prefs.remove(_keyStatus);
    await _prefs.remove(_keyTelemetry);
    await _prefs.remove(_keySensors);
    await _prefs.remove(_keyTimestamp);
  }
}
