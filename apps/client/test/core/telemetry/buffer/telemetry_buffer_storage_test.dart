import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import '../../../helpers/fake_telemetry_buffer_storage.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TelemetryBufferStorage', () {
    late FakeTelemetryBufferStorage storage;

    setUp(() async {
      storage = FakeTelemetryBufferStorage();
      await storage.init();
    });

    test('stores, retrieves and deletes buffer items', () async {
      final item1 = TelemetryBufferItem(
        id: 'id-1',
        topic: 'topic/1',
        payloadJson: '{}',
        createdAt: DateTime.utc(2026, 1, 1),
      );
      final item2 = TelemetryBufferItem(
        id: 'id-2',
        topic: 'topic/2',
        payloadJson: '{}',
        createdAt: DateTime.utc(2026, 1, 2),
      );

      await storage.put(item1.id, item1);
      await storage.put(item2.id, item2);

      expect(await storage.count(), 2);
      final all = await storage.getAll();
      expect(all.length, 2);
      expect(all.first.id, 'id-1');

      await storage.delete('id-1');
      expect(await storage.count(), 1);
      expect((await storage.getAll()).first.id, 'id-2');

      await storage.clear();
      expect(await storage.count(), 0);
    });

    test('deleteBatch removes multiple items at once', () async {
      for (var i = 0; i < 5; i++) {
        await storage.put(
          'id-$i',
          TelemetryBufferItem(
            id: 'id-$i',
            topic: 'topic',
            payloadJson: '{}',
            createdAt: DateTime.utc(2026, 1, 1),
          ),
        );
      }
      expect(await storage.count(), 5);

      await storage.deleteBatch(['id-0', 'id-2', 'id-4']);
      expect(await storage.count(), 2);
      final remainingIds = (await storage.getAll()).map((e) => e.id).toList();
      expect(remainingIds, ['id-1', 'id-3']);
    });
  });
}
