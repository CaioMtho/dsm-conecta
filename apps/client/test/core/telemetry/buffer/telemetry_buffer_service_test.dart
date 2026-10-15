import 'dart:convert';
import 'package:client/core/telemetry/buffer/telemetry_buffer_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../helpers/fake_telemetry_buffer_storage.dart';

void main() {
  group('TelemetryBufferService', () {
    late FakeTelemetryBufferStorage storage;
    late TelemetryBufferService service;

    setUp(() {
      storage = FakeTelemetryBufferStorage();
      service = TelemetryBufferService(
        storage: storage,
        maxCapacity: 3,
      );
    });

    test('enqueues items in order and retrieves FIFO batch', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});

      expect(await service.count(), 2);
      final batch = await service.peekBatch(limit: 10);
      expect(batch.length, 2);
      expect(jsonDecode(batch[0].payloadJson)['seq'], 1);
      expect(jsonDecode(batch[1].payloadJson)['seq'], 2);
    });

    test('drops oldest items when maxCapacity is exceeded', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});
      await service.enqueue(topic: 'topic/3', payload: {'seq': 3});
      expect(await service.count(), 3);

      await service.enqueue(topic: 'topic/4', payload: {'seq': 4});
      expect(await service.count(), 3);

      final batch = await service.peekBatch(limit: 10);
      final seqs = batch.map((e) => jsonDecode(e.payloadJson)['seq']).toList();
      expect(seqs, [2, 3, 4]);
    });

    test('dequeueBatch removes selected items', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});

      final batch = await service.peekBatch(limit: 1);
      await service.dequeueBatch([batch.first.id]);

      expect(await service.count(), 1);
      final remaining = await service.peekBatch(limit: 10);
      expect(jsonDecode(remaining.first.payloadJson)['seq'], 2);
    });

    test('dequeueBatch does nothing when ids list is empty', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.dequeueBatch([]);
      expect(await service.count(), 1);
    });

    test('enqueue accepts custom timestamp', () async {
      final customTime = DateTime.utc(2026, 1, 1, 12, 0, 0);
      await service.enqueue(
        topic: 'topic/1',
        payload: {'seq': 1},
        timestamp: customTime,
      );

      final batch = await service.peekBatch();
      expect(batch.first.createdAt, customTime);
    });

    test('clear removes all entries', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});

      await service.clear();
      expect(await service.count(), 0);
    });

    test('providers initialize correctly and resolve service instance', () {
      final container = ProviderContainer(
        overrides: [
          telemetryBufferStorageProvider.overrideWithValue(storage),
        ],
      );
      addTearDown(container.dispose);

      final s = container.read(telemetryBufferServiceProvider);
      expect(s.storage, storage);
      expect(s.maxCapacity, 1000);
    });
  });
}
