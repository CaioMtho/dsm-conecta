import 'sensor_reading.dart';

abstract class SensorSource {
  SensorType get type;

  bool get isAvailable;

  Stream<SensorReading> readings();

  Future<void> dispose();
}
