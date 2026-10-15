import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_sync_worker.dart';
import 'package:client/core/telemetry/platform_source_detector.dart';
import 'package:client/core/telemetry/telemetry_dispatcher.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/fake_mqtt_transport_client.dart';
import '../helpers/fake_telemetry_buffer_storage.dart';

void main() {
  group('Offline Buffer Integration', () {
    late FakeTelemetryBufferStorage storage;
    late TelemetryBufferService bufferService;
    late FakeMqttTransportClient transport;
    late MqttService mqttService;
    late TelemetrySyncWorker syncWorker;
    late TelemetryDispatcher dispatcher;

    setUp(() {
      storage = FakeTelemetryBufferStorage();
      bufferService = TelemetryBufferService(storage: storage);
      transport = FakeMqttTransportClient();
      mqttService = MqttService(transportClient: transport);
      syncWorker = TelemetrySyncWorker(
        bufferService: bufferService,
        mqttService: mqttService,
      );
      syncWorker.startListening();

      dispatcher = TelemetryDispatcher(
        gatekeeper: const TelemetryGatekeeper(
          hasConsent: true,
          currentSessionId: 'active-session-id',
        ),
        mqttService: mqttService,
        platformSourceDetector: const PlatformSourceDetector(),
        bufferService: bufferService,
        syncWorker: syncWorker,
      );
    });

    tearDown(() {
      syncWorker.dispose();
      mqttService.dispose();
      transport.dispose();
    });

    test('retains events in buffer when offline and syncs on connection', () async {
      transport.emitStatus(MqttConnectionStatus.disconnected);

      final dispatched = await dispatcher.dispatchScreenInteraction(
        screenName: 'HomeScreen',
        durationSeconds: 15.5,
      );

      expect(dispatched, isTrue);
      expect(await bufferService.count(), 1);
      expect(transport.publishedMessages, isEmpty);

      transport.emitStatus(MqttConnectionStatus.connected);
      await pumpEventQueue();

      expect(await bufferService.count(), 0);
      expect(transport.publishedMessages.length, 1);
      expect(transport.publishedMessages.first['topic'], TelemetryDispatcher.screenInteractionTopic);
    });
  });
}
