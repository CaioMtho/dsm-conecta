import 'package:client/core/sensors/sensor_capture_service.dart';
import 'package:client/core/sensors/sensor_reading.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/fake_sensor_source.dart';

void main() {
  group('SensorCaptureService activation', () {
    test('does not start when no source is available', () {
      final unavailable = FakeSensorSource(
        type: SensorType.motion,
        isAvailable: false,
      );
      final service = SensorCaptureService(sources: [unavailable]);

      service.start();

      expect(service.isRunning, isFalse);
      expect(service.availableSources, isEmpty);
    });

    test('starts only when at least one source is available', () {
      final motion = FakeSensorSource(type: SensorType.motion);
      final light = FakeSensorSource(
        type: SensorType.light,
        isAvailable: false,
      );
      final service = SensorCaptureService(
        sources: [motion, light],
        samplingInterval: const Duration(milliseconds: 20),
      );

      service.start();

      expect(service.isRunning, isTrue);
      expect(service.availableSources, hasLength(1));
      expect(service.availableSources.single.type, SensorType.motion);
    });

    test('start is idempotent', () {
      final motion = FakeSensorSource(type: SensorType.motion);
      final service = SensorCaptureService(
        sources: [motion],
        samplingInterval: const Duration(milliseconds: 20),
      );

      service.start();
      service.start();

      expect(service.isRunning, isTrue);
    });
  });

  group('SensorCaptureService sampling', () {
    test('emits the latest reading of each source at each interval',
        () async {
      final motion = FakeSensorSource(type: SensorType.motion);
      final service = SensorCaptureService(
        sources: [motion],
        samplingInterval: const Duration(milliseconds: 30),
      );

      final emitted = <SensorReading>[];
      final subscription = service.readings.listen(emitted.add);

      service.start();
      motion.emit({'x': 1.0, 'y': 0.0, 'z': 0.0});
      motion.emit({'x': 2.0, 'y': 0.0, 'z': 0.0});

      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(emitted, isNotEmpty);
      expect(emitted.last.values['x'], 2.0);

      await subscription.cancel();
      await service.dispose();
    });

    test('stops emitting after stop is called', () async {
      final motion = FakeSensorSource(type: SensorType.motion);
      final service = SensorCaptureService(
        sources: [motion],
        samplingInterval: const Duration(milliseconds: 20),
      );

      final emitted = <SensorReading>[];
      final subscription = service.readings.listen(emitted.add);

      service.start();
      motion.emit({'x': 1.0, 'y': 0.0, 'z': 0.0});
      await Future<void>.delayed(const Duration(milliseconds: 40));
      await service.stop();
      final countAfterStop = emitted.length;

      await Future<void>.delayed(const Duration(milliseconds: 60));

      expect(service.isRunning, isFalse);
      expect(emitted.length, countAfterStop);

      await subscription.cancel();
      await service.dispose();
    });

    test('tolerates source errors without stopping collection', () async {
      final motion = FakeSensorSource(type: SensorType.motion);
      final service = SensorCaptureService(
        sources: [motion],
        samplingInterval: const Duration(milliseconds: 20),
      );

      final emitted = <SensorReading>[];
      final subscription = service.readings.listen(emitted.add);

      service.start();
      motion.emitError(StateError('sensor glitch'));
      motion.emit({'x': 5.0, 'y': 0.0, 'z': 0.0});
      await Future<void>.delayed(const Duration(milliseconds: 40));

      expect(service.isRunning, isTrue);
      expect(emitted.last.values['x'], 5.0);

      await subscription.cancel();
      await service.dispose();
    });
  });

  group('SensorCaptureService disposal', () {
    test('dispose stops collection and disposes every source', () async {
      final motion = FakeSensorSource(type: SensorType.motion);
      final service = SensorCaptureService(
        sources: [motion],
        samplingInterval: const Duration(milliseconds: 20),
      );

      service.start();
      await service.dispose();

      expect(service.isRunning, isFalse);
      expect(motion.disposed, isTrue);
    });
  });
}
