import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import 'telemetry_buffer_item.dart';
import 'telemetry_buffer_storage.dart';

final telemetryBufferStorageProvider = Provider<TelemetryBufferStorage>((ref) {
  return HiveTelemetryBufferStorage();
});

final telemetryBufferServiceProvider = Provider<TelemetryBufferService>((ref) {
  final storage = ref.watch(telemetryBufferStorageProvider);
  return TelemetryBufferService(storage: storage);
});

class TelemetryBufferService {
  final TelemetryBufferStorage storage;
  final int maxCapacity;
  final Uuid uuid;

  TelemetryBufferService({
    required this.storage,
    this.maxCapacity = 1000,
    this.uuid = const Uuid(),
  });

  Future<void> enqueue({
    required String topic,
    required Map<String, dynamic> payload,
    DateTime? timestamp,
  }) async {
    final currentCount = await storage.count();
    if (currentCount >= maxCapacity) {
      final all = await storage.getAll();
      all.sort((a, b) => a.createdAt.compareTo(b.createdAt));
      final excessCount = (currentCount - maxCapacity) + 1;
      final idsToRemove = all.take(excessCount).map((e) => e.id).toList();
      await storage.deleteBatch(idsToRemove);
    }

    final id = uuid.v4();
    final item = TelemetryBufferItem(
      id: id,
      topic: topic,
      payloadJson: jsonEncode(payload),
      createdAt: timestamp ?? DateTime.now().toUtc(),
    );

    await storage.put(id, item);
  }

  Future<List<TelemetryBufferItem>> peekBatch({int limit = 50}) async {
    final all = await storage.getAll();
    all.sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return all.take(limit).toList();
  }

  Future<void> dequeueBatch(List<String> ids) async {
    if (ids.isEmpty) return;
    await storage.deleteBatch(ids);
  }

  Future<int> count() async {
    return storage.count();
  }

  Future<void> clear() async {
    await storage.clear();
  }
}
