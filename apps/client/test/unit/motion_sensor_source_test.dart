import 'package:client/core/sensors/sensor_reading.dart';
import 'package:client/core/sensors/sources/motion_sensor_source.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sensors_plus/sensors_plus.dart';

void main() {
  group('MotionSensorSource graceful fallback', () {
    test('reports unavailable on unsupported platforms', () {
      final source = MotionSensorSource(supportedOverride: false);

      expect(source.isAvailable, isFalse);
    });

    test('returns an empty stream when unsupported', () async {
      final source = MotionSensorSource(supportedOverride: false);

      final readings = await source.readings().toList();

      expect(readings, isEmpty);
    });
  });

  group('MotionSensorSource sampling', () {
    test('maps accelerometer events into motion readings', () async {
      final source = MotionSensorSource(
        supportedOverride: true,
        streamFactory: () => Stream<AccelerometerEvent>.fromIterable([
          AccelerometerEvent(1.0, 2.0, 3.0, DateTime.utc(2026)),
        ]),
      );

      final readings = await source.readings().toList();

      expect(readings, hasLength(1));
      expect(readings.single.type, SensorType.motion);
      expect(readings.single.values['x'], 1.0);
      expect(readings.single.values['y'], 2.0);
      expect(readings.single.values['z'], 3.0);
    });
  });

  group('SensorReading serialization', () {
    test('serializes to a wire map with sensor name and values', () {
      final reading = SensorReading(
        type: SensorType.motion,
        capturedAt: DateTime.utc(2026, 5, 10, 8, 30),
        values: const {'x': 0.0, 'y': 1.0, 'z': 2.0},
      );

      final map = reading.toMap();

      expect(map['sensor'], 'movimento');
      expect(map['captured_at'], '2026-05-10T08:30:00.000Z');
      expect(map['values'], const {'x': 0.0, 'y': 1.0, 'z': 2.0});
    });

    test('maps light sensor type to its wire name', () {
      final reading = SensorReading(
        type: SensorType.light,
        capturedAt: DateTime.utc(2026),
        values: const {'lux': 120.0},
      );

      expect(reading.toMap()['sensor'], 'luminosidade');
    });
  });
}
