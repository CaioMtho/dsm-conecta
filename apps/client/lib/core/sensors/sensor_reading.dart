enum SensorType {
  motion,
  light,
}

extension SensorTypeWire on SensorType {
  String get wireName {
    switch (this) {
      case SensorType.motion:
        return 'movimento';
      case SensorType.light:
        return 'luminosidade';
    }
  }
}

class SensorReading {
  final SensorType type;
  final DateTime capturedAt;
  final Map<String, dynamic> values;

  const SensorReading({
    required this.type,
    required this.capturedAt,
    required this.values,
  });

  Map<String, dynamic> toMap() {
    return {
      'sensor': type.wireName,
      'captured_at': capturedAt.toUtc().toIso8601String(),
      'values': values,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SensorReading &&
          runtimeType == other.runtimeType &&
          type == other.type &&
          capturedAt == other.capturedAt &&
          _mapEquals(values, other.values);

  @override
  int get hashCode => type.hashCode ^ capturedAt.hashCode ^ values.length.hashCode;

  static bool _mapEquals(Map<String, dynamic> a, Map<String, dynamic> b) {
    if (a.length != b.length) return false;
    for (final key in a.keys) {
      if (!b.containsKey(key) || a[key] != b[key]) return false;
    }
    return true;
  }
}
