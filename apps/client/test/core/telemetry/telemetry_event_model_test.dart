import 'dart:convert';
import 'package:client/core/telemetry/telemetry_event_model.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TelemetryEventModel', () {
    test('serializes to JSON adhering to backend TelemetryEvent schema', () {
      final now = DateTime.utc(2026, 9, 21, 18, 0, 0);
      final event = TelemetryEventModel(
        schemaVersion: '1.0',
        timestamp: now,
        eventId: 'test-event-uuid-1234',
        sessionId: 'test-session-uuid-5678',
        source: 'app_mobile',
        category: 'interacao_tela',
        payload: {
          'screen_name': 'HomeScreen',
          'duration_seconds': 12.5,
        },
      );

      final map = event.toMap();
      expect(map['schema_version'], '1.0');
      expect(map['timestamp'], '2026-09-21T18:00:00.000Z');
      expect(map['event_id'], 'test-event-uuid-1234');
      expect(map['session_id'], 'test-session-uuid-5678');
      expect(map['source'], 'app_mobile');
      expect(map['category'], 'interacao_tela');
      expect(map['payload'], {
        'screen_name': 'HomeScreen',
        'duration_seconds': 12.5,
      });

      final jsonStr = event.toJson();
      final decoded = json.decode(jsonStr) as Map<String, dynamic>;
      expect(decoded['category'], 'interacao_tela');
      expect(decoded['payload']['screen_name'], 'HomeScreen');
    });
  });
}
