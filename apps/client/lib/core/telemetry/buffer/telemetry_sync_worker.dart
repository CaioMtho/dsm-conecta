import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../network/mqtt/mqtt_connection_status.dart';
import '../../network/mqtt/mqtt_service.dart';
import 'telemetry_buffer_service.dart';

final telemetrySyncWorkerProvider = Provider<TelemetrySyncWorker>((ref) {
  final bufferService = ref.watch(telemetryBufferServiceProvider);
  final mqttService = ref.watch(mqttServiceProvider);
  final worker = TelemetrySyncWorker(
    bufferService: bufferService,
    mqttService: mqttService,
  );
  worker.startListening();
  ref.onDispose(() => worker.dispose());
  return worker;
});

class TelemetrySyncWorker {
  final TelemetryBufferService bufferService;
  final MqttService mqttService;
  StreamSubscription<MqttConnectionStatus>? _statusSubscription;
  bool _isSyncing = false;

  TelemetrySyncWorker({
    required this.bufferService,
    required this.mqttService,
  });

  void startListening() {
    _statusSubscription ??= mqttService.statusStream.listen((status) {
      if (status == MqttConnectionStatus.connected) {
        syncPending();
      }
    });
  }

  Future<int> syncPending({int batchSize = 50}) async {
    if (_isSyncing) return 0;
    if (mqttService.currentStatus != MqttConnectionStatus.connected) {
      return 0;
    }

    _isSyncing = true;
    var totalSynced = 0;

    try {
      while (mqttService.currentStatus == MqttConnectionStatus.connected) {
        final batch = await bufferService.peekBatch(limit: batchSize);
        if (batch.isEmpty) break;

        final confirmedIds = <String>[];
        for (final item in batch) {
          if (mqttService.currentStatus != MqttConnectionStatus.connected) {
            break;
          }
          final Map<String, dynamic> decodedPayload;
          try {
            decodedPayload = jsonDecode(item.payloadJson) as Map<String, dynamic>;
          } catch (_) {
            confirmedIds.add(item.id);
            continue;
          }
          mqttService.publish(
            topic: item.topic,
            payload: decodedPayload,
          );
          confirmedIds.add(item.id);
          totalSynced++;
        }

        await bufferService.dequeueBatch(confirmedIds);
        if (confirmedIds.length < batch.length) {
          break;
        }
      }
    } finally {
      _isSyncing = false;
    }

    return totalSynced;
  }

  void dispose() {
    _statusSubscription?.cancel();
    _statusSubscription = null;
  }
}
