import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/mqtt/mqtt_service.dart';
import '../telemetry/telemetry_dispatcher.dart';
import '../telemetry/telemetry_gatekeeper.dart';
import 'sensor_capture_service.dart';
import 'sensor_collection_coordinator.dart';
import 'sensor_source.dart';
import 'sensor_telemetry_dispatcher.dart';
import 'sources/motion_sensor_source.dart';

final sensorSourcesProvider = Provider<List<SensorSource>>((ref) {
  return [
    MotionSensorSource(),
  ];
});

final sensorCaptureServiceProvider = Provider<SensorCaptureService>((ref) {
  final sources = ref.watch(sensorSourcesProvider);
  final service = SensorCaptureService(sources: sources);
  ref.onDispose(() => service.dispose());
  return service;
});

final sensorTelemetryDispatcherProvider =
    Provider<SensorTelemetryDispatcher>((ref) {
  final mqttService = ref.watch(mqttServiceProvider);
  final detector = ref.watch(platformSourceDetectorProvider);
  return SensorTelemetryDispatcher(
    gatekeeperResolver: () => ref.read(telemetryGatekeeperProvider),
    mqttService: mqttService,
    platformSourceDetector: detector,
  );
});

final sensorCollectionCoordinatorProvider =
    Provider<SensorCollectionCoordinator>((ref) {
  final captureService = ref.watch(sensorCaptureServiceProvider);
  final dispatcher = ref.watch(sensorTelemetryDispatcherProvider);
  final coordinator = SensorCollectionCoordinator(
    captureService: captureService,
    dispatcher: dispatcher,
  );
  ref.onDispose(() => coordinator.dispose());
  return coordinator;
});
