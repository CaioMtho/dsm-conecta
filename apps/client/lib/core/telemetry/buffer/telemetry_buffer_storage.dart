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
  Box<Map>? box;
  final Map<String, TelemetryBufferItem> _fallback = {};

  HiveTelemetryBufferStorage({this.box});

  Box<Map>? get _effectiveBox {
    if (box != null && box!.isOpen) return box;
    try {
      if (Hive.isBoxOpen(boxName)) {
        box = Hive.box<Map>(boxName);
        return box;
      }
    } catch (_) {}
    return null;
  }

  @override
  Future<void> init() async {
    if (_effectiveBox != null) return;
    try {
      box = await Hive.openBox<Map>(boxName);
    } catch (_) {}
  }

  @override
  Future<void> put(String id, TelemetryBufferItem item) async {
    final box = _effectiveBox;
    if (box != null) {
      await box.put(id, item.toMap());
    } else {
      _fallback[id] = item;
    }
  }

  @override
  Future<void> delete(String id) async {
    final box = _effectiveBox;
    if (box != null) {
      await box.delete(id);
    } else {
      _fallback.remove(id);
    }
  }

  @override
  Future<void> deleteBatch(List<String> ids) async {
    final box = _effectiveBox;
    if (box != null) {
      await box.deleteAll(ids);
    } else {
      for (final id in ids) {
        _fallback.remove(id);
      }
    }
  }

  @override
  Future<List<TelemetryBufferItem>> getAll() async {
    final box = _effectiveBox;
    if (box != null) {
      final values = box.values;
      return values.map((e) => TelemetryBufferItem.fromMap(e)).toList();
    }
    return _fallback.values.toList();
  }

  @override
  Future<int> count() async {
    final box = _effectiveBox;
    if (box != null) {
      return box.length;
    }
    return _fallback.length;
  }

  @override
  Future<void> clear() async {
    final box = _effectiveBox;
    if (box != null) {
      await box.clear();
    }
    _fallback.clear();
  }
}
