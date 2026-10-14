import 'package:hive_flutter/hive_flutter.dart';
import 'telemetry_buffer_item.dart';

abstract class TelemetryBufferStorage {
  Future<void> init();
  Future<void> put(String id, TelemetryBufferItem item);
  Future<void> delete(String id);
  Future<void> deleteBatch(List<String> ids);
  Future<List<TelemetryBufferItem>> getAll();
  Future<int> count();
  Future<void> clear();
}

class HiveTelemetryBufferStorage implements TelemetryBufferStorage {
  static const String boxName = 'telemetry_buffer';
  Box<Map>? _box;

  @override
  Future<void> init() async {
    if (_box != null && _box!.isOpen) return;
    _box = await Hive.openBox<Map>(boxName);
  }

  @override
  Future<void> put(String id, TelemetryBufferItem item) async {
    await _box?.put(id, item.toMap());
  }

  @override
  Future<void> delete(String id) async {
    await _box?.delete(id);
  }

  @override
  Future<void> deleteBatch(List<String> ids) async {
    await _box?.deleteAll(ids);
  }

  @override
  Future<List<TelemetryBufferItem>> getAll() async {
    final values = _box?.values ?? [];
    return values
        .map((e) => TelemetryBufferItem.fromMap(e))
        .toList();
  }

  @override
  Future<int> count() async {
    return _box?.length ?? 0;
  }

  @override
  Future<void> clear() async {
    await _box?.clear();
  }
}
