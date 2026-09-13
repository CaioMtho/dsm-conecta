import 'package:client/core/privacy/consent_state.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ConsentState', () {
    test('initial state has undetermined status and false permissions', () {
      final state = ConsentState.initial();
      expect(state.status, ConsentStatus.undetermined);
      expect(state.telemetryAccepted, isFalse);
      expect(state.sensorsAccepted, isFalse);
      expect(state.acceptedAt, isNull);
    });

    test('serializes to and from json correctly', () {
      final now = DateTime.utc(2026, 9, 12, 10, 0, 0);
      final state = ConsentState(
        status: ConsentStatus.accepted,
        telemetryAccepted: true,
        sensorsAccepted: false,
        acceptedAt: now,
      );

      final json = state.toJson();
      final fromJson = ConsentState.fromJson(json);

      expect(fromJson.status, ConsentStatus.accepted);
      expect(fromJson.telemetryAccepted, isTrue);
      expect(fromJson.sensorsAccepted, isFalse);
      expect(fromJson.acceptedAt, now);
    });

    test('copyWith modifies only specified fields', () {
      final state = ConsentState.initial();
      final updated = state.copyWith(
        status: ConsentStatus.rejected,
        telemetryAccepted: false,
      );

      expect(updated.status, ConsentStatus.rejected);
      expect(updated.telemetryAccepted, isFalse);
    });
  });
}
