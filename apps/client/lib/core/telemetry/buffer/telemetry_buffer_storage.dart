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
  final Map<String, TelemetryBufferItem> _fallback = {};

  @override
  Future<void> init() async {
    if (_box != null && _box!.isOpen) return;
    try {
      if (Hive.isBoxOpen(boxName)) {
        _box = Hive.box<Map>(boxName);
      } else {
        _box = await Hive.openBox<Map>(boxName);
      }
    } catch (_) {}
  }

  @override
  Future<void> put(String id, TelemetryBufferItem item) async {
    if (_box != null && _box!.isOpen) {
      await _box!.put(id, item.toMap());
    } else {
      _fallback[id] = item;
    }
  }

  @override
  Future<void> delete(String id) async {
    if (_box != null && _box!.isOpen) {
      await _box!.delete(id);
    } else {
      _fallback.remove(id);
    }
  }

  @override
  Future<void> deleteBatch(List<String> ids) async {
    if (_box != null && _box!.isOpen) {
      await _box!.deleteAll(ids);
    } else {
      for (final id in ids) {
        _fallback.remove(id);
      }
    }
  }

  @override
  Future<List<TelemetryBufferItem>> getAll() async {
    if (_box != null && _box!.isOpen) {
      final values = _box!.values;
      return values.map((e) => TelemetryBufferItem.fromMap(e)).toList();
    }
    return _fallback.values.toList();
  }

  @override
  Future<int> count() async {
    if (_box != null && _box!.isOpen) {
      return _box!.length;
    }
    return _fallback.length;
  }

  @override
  Future<void> clear() async {
    if (_box != null && _box!.isOpen) {
      await _box!.clear();
    }
    _fallback.clear();
  }
}
