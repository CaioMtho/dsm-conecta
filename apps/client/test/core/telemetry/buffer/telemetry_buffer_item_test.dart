import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TelemetryBufferItem', () {
    test('serializes to and from map correctly preserving timestamp', () {
      final now = DateTime.utc(2026, 10, 12, 15, 30, 0);
      final item = TelemetryBufferItem(
        id: 'test-item-1',
        topic: 'dsm/prod/app/interacao/tela',
        payloadJson: '{"event_id":"123","category":"interacao_tela"}',
        createdAt: now,
      );

      final map = item.toMap();
      expect(map['id'], 'test-item-1');
      expect(map['topic'], 'dsm/prod/app/interacao/tela');
      expect(map['payloadJson'], '{"event_id":"123","category":"interacao_tela"}');
      expect(map['createdAt'], now.toIso8601String());

      final reconstituted = TelemetryBufferItem.fromMap(map);
      expect(reconstituted.id, item.id);
      expect(reconstituted.topic, item.topic);
      expect(reconstituted.payloadJson, item.payloadJson);
      expect(reconstituted.createdAt, now);
    });
  });
}
