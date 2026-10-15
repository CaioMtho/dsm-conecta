import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../network/mqtt/mqtt_service.dart';
import 'platform_source_detector.dart';
import 'telemetry_event_model.dart';
import 'telemetry_gatekeeper.dart';

final platformSourceDetectorProvider = Provider<PlatformSourceDetector>((ref) {
  return const PlatformSourceDetector();
});

final telemetryDispatcherProvider = Provider<TelemetryDispatcher>((ref) {
  final gatekeeper = ref.watch(telemetryGatekeeperProvider);
  final mqttService = ref.watch(mqttServiceProvider);
  final detector = ref.watch(platformSourceDetectorProvider);
  return TelemetryDispatcher(
    gatekeeper: gatekeeper,
    mqttService: mqttService,
    platformSourceDetector: detector,
  );
});

class TelemetryDispatcher {
  static const String screenInteractionTopic = 'dsm/prod/app/interacao/tela';

  final TelemetryGatekeeper gatekeeper;
  final MqttService mqttService;
  final PlatformSourceDetector platformSourceDetector;
  final Uuid uuid;

  TelemetryDispatcher({
    required this.gatekeeper,
    required this.mqttService,
    required this.platformSourceDetector,
    this.uuid = const Uuid(),
  });

  Future<bool> dispatchScreenInteraction({
    required String screenName,
    required double durationSeconds,
  }) async {
    if (!gatekeeper.canEmitTelemetry()) {
      return false;
    }

    final sessionId = gatekeeper.currentSessionId;
    if (sessionId == null || sessionId.isEmpty) {
      return false;
    }

    final event = TelemetryEventModel(
      schemaVersion: '1.0',
      timestamp: DateTime.now().toUtc(),
      eventId: uuid.v4(),
      sessionId: sessionId,
      source: platformSourceDetector.detect(),
      category: 'interacao_tela',
      payload: {
        'screen_name': screenName,
        'duration_seconds': durationSeconds,
      },
    );

    mqttService.publish(
      topic: screenInteractionTopic,
      payload: event.toJson(),
    );

    return true;
  }
}
