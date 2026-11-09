import 'dart:async';

import 'sensor_reading.dart';
import 'sensor_source.dart';

class SensorCaptureService {
  final List<SensorSource> sources;
  final Duration samplingInterval;

  final StreamController<SensorReading> _output =
      StreamController<SensorReading>.broadcast();
  final Map<SensorType, SensorReading> _latest = {};
  final List<StreamSubscription<SensorReading>> _subscriptions = [];

  Timer? _timer;
  bool _running = false;

  SensorCaptureService({
    required this.sources,
    this.samplingInterval = const Duration(seconds: 5),
  });

  bool get isRunning => _running;

  List<SensorSource> get availableSources =>
      sources.where((s) => s.isAvailable).toList(growable: false);

  Stream<SensorReading> get readings => _output.stream;

  void start() {
    if (_running) return;

    final available = availableSources;
    if (available.isEmpty) {
      return;
    }

    _running = true;

    for (final source in available) {
      final subscription = source.readings().listen(
        (reading) {
          _latest[reading.type] = reading;
        },
        onError: (_) {},
        cancelOnError: false,
      );
      _subscriptions.add(subscription);
    }

    _timer = Timer.periodic(samplingInterval, (_) => _emitSnapshot());
  }

  void _emitSnapshot() {
    if (!_running) return;
    for (final reading in _latest.values) {
      if (!_output.isClosed) {
        _output.add(reading);
      }
    }
  }

  Future<void> stop() async {
    if (!_running) return;
    _running = false;

    _timer?.cancel();
    _timer = null;

    for (final subscription in _subscriptions) {
      await subscription.cancel();
    }
    _subscriptions.clear();
    _latest.clear();
  }

  Future<void> dispose() async {
    await stop();
    for (final source in sources) {
      await source.dispose();
    }
    if (!_output.isClosed) {
      await _output.close();
    }
  }
}
