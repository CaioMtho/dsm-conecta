import 'dart:async';

import 'package:client/core/sensors/sensor_reading.dart';
import 'package:client/core/sensors/sensor_source.dart';

class FakeSensorSource implements SensorSource {
  @override
  final SensorType type;

  @override
  bool isAvailable;

  bool disposed = false;

  final StreamController<SensorReading> _controller =
      StreamController<SensorReading>.broadcast();

  FakeSensorSource({
    required this.type,
    this.isAvailable = true,
  });

  void emit(Map<String, dynamic> values, {DateTime? capturedAt}) {
    _controller.add(
      SensorReading(
        type: type,
        capturedAt: capturedAt ?? DateTime.utc(2026, 1, 1),
        values: values,
      ),
    );
  }

  void emitError(Object error) {
    _controller.addError(error);
  }

  @override
  Stream<SensorReading> readings() => _controller.stream;

  @override
  Future<void> dispose() async {
    disposed = true;
    if (!_controller.isClosed) {
      await _controller.close();
    }
  }
}
