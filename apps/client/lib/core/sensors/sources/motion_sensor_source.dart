import 'package:flutter/foundation.dart';
import 'package:sensors_plus/sensors_plus.dart';

import '../sensor_reading.dart';
import '../sensor_source.dart';

class MotionSensorSource implements SensorSource {
  final Duration samplingPeriod;
  final Stream<AccelerometerEvent> Function()? streamFactory;
  final bool _supported;

  MotionSensorSource({
    this.samplingPeriod = SensorInterval.normalInterval,
    this.streamFactory,
    bool? supportedOverride,
  }) : _supported = supportedOverride ?? _platformSupportsMotion();

  static bool _platformSupportsMotion() {
    if (kIsWeb) {
      return false;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
      case TargetPlatform.iOS:
        return true;
      case TargetPlatform.linux:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.fuchsia:
        return false;
    }
  }

  @override
  SensorType get type => SensorType.motion;

  @override
  bool get isAvailable => _supported;

  @override
  Stream<SensorReading> readings() {
    if (!_supported) {
      return const Stream<SensorReading>.empty();
    }

    final source = streamFactory?.call() ??
        accelerometerEventStream(samplingPeriod: samplingPeriod);

    return source
        .map(
          (event) => SensorReading(
            type: SensorType.motion,
            capturedAt: DateTime.now().toUtc(),
            values: {
              'x': event.x,
              'y': event.y,
              'z': event.z,
            },
          ),
        )
        .handleError((_) {});
  }

  @override
  Future<void> dispose() async {}
}
