import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_storage.dart';

class FakeTelemetryBufferStorage implements TelemetryBufferStorage {
  final Map<String, TelemetryBufferItem> _storage = {};

  @override
  Future<void> init() async {}

  @override
  Future<void> put(String id, TelemetryBufferItem item) async {
    _storage[id] = item;
  }

  @override
  Future<void> delete(String id) async {
    _storage.remove(id);
  }

  @override
  Future<void> deleteBatch(List<String> ids) async {
    for (final id in ids) {
      _storage.remove(id);
    }
  }

  @override
  Future<List<TelemetryBufferItem>> getAll() async {
    return _storage.values.toList();
  }

  @override
  Future<int> count() async {
    return _storage.length;
  }

  @override
  Future<void> clear() async {
    _storage.clear();
  }
}
