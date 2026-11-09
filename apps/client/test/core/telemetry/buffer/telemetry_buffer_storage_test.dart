import 'dart:io';

import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';

import '../../../helpers/fake_telemetry_buffer_storage.dart';

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

  group('HiveTelemetryBufferStorage', () {
    late Directory tempDir;
    late Box<Map> box;
    late HiveTelemetryBufferStorage hiveStorage;

    setUp(() async {
      tempDir = await Directory.systemTemp.createTemp('hive_buffer_test_');
      Hive.init(tempDir.path);
      box = await Hive.openBox<Map>(HiveTelemetryBufferStorage.boxName);
      hiveStorage = HiveTelemetryBufferStorage(box: box);
    });

    tearDown(() async {
      await box.close();
      await Hive.deleteBoxFromDisk(HiveTelemetryBufferStorage.boxName);
      if (tempDir.existsSync()) {
        await tempDir.delete(recursive: true);
      }
    });

    test('stores and reads directly from open Hive box', () async {
      final item = TelemetryBufferItem(
        id: 'test-1',
        topic: 'topic/hive',
        payloadJson: '{"test":true}',
        createdAt: DateTime.utc(2026, 1, 1),
      );

      await hiveStorage.put(item.id, item);

      expect(await hiveStorage.count(), 1);
      expect(box.length, 1);
      expect(box.get('test-1'), isNotNull);

      final retrieved = await hiveStorage.getAll();
      expect(retrieved.length, 1);
      expect(retrieved.first.id, 'test-1');
      expect(retrieved.first.topic, 'topic/hive');

      await hiveStorage.delete('test-1');
      expect(await hiveStorage.count(), 0);
      expect(box.isEmpty, isTrue);
    });

    test('dynamically uses open box without explicit constructor injection', () async {
      final uninitializedStorage = HiveTelemetryBufferStorage();
      final item = TelemetryBufferItem(
        id: 'dyn-1',
        topic: 'topic/dyn',
        payloadJson: '{"dyn":true}',
        createdAt: DateTime.utc(2026, 1, 1),
      );

      await uninitializedStorage.put(item.id, item);

      expect(await uninitializedStorage.count(), 1);
      expect(box.get('dyn-1'), isNotNull);

      await uninitializedStorage.clear();
      expect(box.isEmpty, isTrue);
    });

    test('getAll ignores corrupted entries without throwing', () async {
      final validItem = TelemetryBufferItem(
        id: 'valid-1',
        topic: 'topic/valid',
        payloadJson: '{"valid":true}',
        createdAt: DateTime.utc(2026, 1, 1),
      );
      await hiveStorage.put(validItem.id, validItem);

      await box.put('corrupted-1', {'invalid_map': 123});

      final all = await hiveStorage.getAll();
      expect(all.length, 1);
      expect(all.first.id, 'valid-1');
    });
  });
}
