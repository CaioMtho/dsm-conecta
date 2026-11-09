import 'dart:async';

import 'package:flutter/widgets.dart';

import 'sensor_capture_service.dart';
import 'sensor_reading.dart';
import 'sensor_telemetry_dispatcher.dart';

class SensorCollectionCoordinator with WidgetsBindingObserver {
  final SensorCaptureService captureService;
  final SensorTelemetryDispatcher dispatcher;

  StreamSubscription<SensorReading>? _readingSubscription;
  bool _consentGranted = false;
  bool _foreground = true;
  bool _attached = false;

  SensorCollectionCoordinator({
    required this.captureService,
    required this.dispatcher,
  });

  bool get isCollecting => captureService.isRunning;

  void attach() {
    if (_attached) return;
    _attached = true;
    WidgetsBinding.instance.addObserver(this);
  }

  void setConsent({required bool granted}) {
    _consentGranted = granted;
    _reconcile();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _reconcile();
  }

  void _reconcile() {
    final shouldCollect = _consentGranted && _foreground;
    if (shouldCollect && !captureService.isRunning) {
      _startCollection();
    } else if (!shouldCollect && captureService.isRunning) {
      _stopCollection();
    }
  }

  void _startCollection() {
    _readingSubscription ??= captureService.readings.listen(
      (reading) => dispatcher.dispatchReading(reading),
      onError: (_) {},
      cancelOnError: false,
    );
    captureService.start();
  }

  void _stopCollection() {
    unawaited(captureService.stop());
  }

  Future<void> dispose() async {
    if (_attached) {
      WidgetsBinding.instance.removeObserver(this);
      _attached = false;
    }
    await _readingSubscription?.cancel();
    _readingSubscription = null;
    await captureService.dispose();
  }
}
