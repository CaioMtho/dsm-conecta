import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_sync_worker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../helpers/fake_mqtt_transport_client.dart';
import '../../../helpers/fake_telemetry_buffer_storage.dart';

void main() {
  group('TelemetrySyncWorker', () {
    late FakeTelemetryBufferStorage storage;
    late TelemetryBufferService bufferService;
    late FakeMqttTransportClient transport;
    late MqttService mqttService;
    late TelemetrySyncWorker syncWorker;

    setUp(() {
      storage = FakeTelemetryBufferStorage();
      bufferService = TelemetryBufferService(storage: storage);
      transport = FakeMqttTransportClient();
      mqttService = MqttService(transportClient: transport);
      syncWorker = TelemetrySyncWorker(
        bufferService: bufferService,
        mqttService: mqttService,
      );
    });

    tearDown(() {
      syncWorker.dispose();
      mqttService.dispose();
      transport.dispose();
    });

    test('flushes buffer FIFO when connection is online', () async {
      await bufferService.enqueue(topic: 'topic/1', payload: {'item': 1});
      await bufferService.enqueue(topic: 'topic/2', payload: {'item': 2});

      transport.emitStatus(MqttConnectionStatus.connected);

      final syncedCount = await syncWorker.syncPending();
      expect(syncedCount, 2);
      expect(await bufferService.count(), 0);
      expect(transport.publishedMessages.length, 2);
      expect(transport.publishedMessages[0]['topic'], 'topic/1');
      expect(transport.publishedMessages[1]['topic'], 'topic/2');
    });

    test('does not flush if disconnected', () async {
      await bufferService.enqueue(topic: 'topic/1', payload: {'item': 1});
      transport.emitStatus(MqttConnectionStatus.disconnected);

      final syncedCount = await syncWorker.syncPending();
      expect(syncedCount, 0);
      expect(await bufferService.count(), 1);
      expect(transport.publishedMessages, isEmpty);
    });

    test('listens to status stream and automatically syncs on connected', () async {
      await bufferService.enqueue(topic: 'topic/1', payload: {'item': 1});
      syncWorker.startListening();

      transport.emitStatus(MqttConnectionStatus.connected);
      await pumpEventQueue();

      expect(await bufferService.count(), 0);
      expect(transport.publishedMessages.length, 1);
    });

    test('syncs multiple batches until buffer is empty', () async {
      for (var i = 1; i <= 5; i++) {
        await bufferService.enqueue(topic: 'topic/$i', payload: {'index': i});
      }

      transport.emitStatus(MqttConnectionStatus.connected);

      final synced = await syncWorker.syncPending(batchSize: 2);
      expect(synced, 5);
      expect(await bufferService.count(), 0);
      expect(transport.publishedMessages.length, 5);
    });

    test('stops syncing if connection drops during message iteration', () async {
      await bufferService.enqueue(topic: 'topic/1', payload: {'item': 1});
      await bufferService.enqueue(topic: 'topic/2', payload: {'item': 2});

      transport.emitStatus(MqttConnectionStatus.connected);

      transport.onPublish = (topic, _) {
        if (topic == 'topic/1') {
          transport.emitStatus(MqttConnectionStatus.disconnected);
        }
      };

      final synced = await syncWorker.syncPending();
      expect(synced, 1);
      expect(await bufferService.count(), 1);
      expect(transport.publishedMessages.length, 1);
    });

    test('does not trigger concurrent sync if already running', () async {
      await bufferService.enqueue(topic: 'topic/1', payload: {'item': 1});
      transport.emitStatus(MqttConnectionStatus.connected);

      final future1 = syncWorker.syncPending();
      final future2 = syncWorker.syncPending();

      final results = await Future.wait([future1, future2]);
      expect(results.reduce((a, b) => a + b), 1);
    });

    test('telemetrySyncWorkerProvider instantiates and disposes properly', () {
      final container = ProviderContainer(
        overrides: [
          telemetryBufferStorageProvider.overrideWithValue(storage),
          mqttServiceProvider.overrideWithValue(mqttService),
        ],
      );

      final worker = container.read(telemetrySyncWorkerProvider);
      expect(worker, isA<TelemetrySyncWorker>());

      container.dispose();
    });
  });
}
