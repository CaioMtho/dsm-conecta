# Buffer Local de Telemetria e Tolerância a Falhas Offline no Flutter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o buffer local persistente em disco (Outbox Pattern) com Hive no Flutter (`apps/client`), garantindo tolerância a falhas offline, retenção ordenada (FIFO), preservação de timestamps UTC originais, limite de capacidade com política *drop-oldest* e purga imediata em caso de revogação de consentimento LGPD.

**Architecture:** O `TelemetryDispatcher` encaminha os eventos estruturados para o `TelemetryBufferService`, que grava itens em disco (`telemetry_buffer_storage` via Hive) respeitando o limite máximo e a política *drop-oldest*. O `TelemetrySyncWorker` observa o `MqttService.statusStream`: quando conectado, esvazia o buffer em ordem FIFO com QoS 1 e confirma a remoção dos itens despachados. Em caso de revogação LGPD (`PrivacyNotifier`), o buffer é completamente purgado.

**Tech Stack:** Flutter / Dart, Riverpod 2.6.1, Hive 2.2.3, hive_flutter 1.1.0, mqtt_client 10.5.0, uuid 4.5.1, flutter_test.

**Spec:** `docs/superpowers/specs/2026-10-12-telemetry-offline-buffer-design.md`

## Global Constraints
- FVM mandatório para Flutter (`fvm flutter test`, `fvm flutter pub get`, `fvm dart`).
- Cobertura de testes superior a 70% com ciclo Red-Green-Refactor estrito.
- Sem comentários redundantes ou que apenas narrem o código.
- Sem quebrar suporte multiplataforma (Android, iOS, Web via IndexedDB e Desktop).

---

### Task 1: Adicionar Dependências do Hive e Estruturar o Modelo `TelemetryBufferItem`

**Files:**
- Modify: `apps/client/pubspec.yaml`
- Create: `apps/client/lib/core/telemetry/buffer/telemetry_buffer_item.dart`
- Test: `apps/client/test/core/telemetry/buffer/telemetry_buffer_item_test.dart`

**Interfaces:**
- Consumes: Dart core `DateTime`, `Map<String, dynamic>`
- Produces: `TelemetryBufferItem` com `id`, `topic`, `payloadJson`, `createdAt`, `toMap()` e `fromMap()`

- [ ] **Step 1: Adicionar dependências no `pubspec.yaml` e executar `fvm flutter pub get`**

Modificar `apps/client/pubspec.yaml` adicionando:
```yaml
  hive: ^2.2.3
  hive_flutter: ^1.1.0
```
Executar: `cd apps/client && fvm flutter pub get`

- [ ] **Step 2: Escrever teste de unidade falhando para `TelemetryBufferItem`**

Criar `apps/client/test/core/telemetry/buffer/telemetry_buffer_item_test.dart`:
```dart
import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TelemetryBufferItem', () {
    test('serializes to and from map correctly preserving timestamp', () {
      final now = DateTime.utc(2026, 10, 12, 15, 30, 0);
      final item = TelemetryBufferItem(
        id: 'test-item-1',
        topic: 'dsm/prod/app/interacao/tela',
        payloadJson: '{"event_id":"123","category":"interacao_tela"}',
        createdAt: now,
      );

      final map = item.toMap();
      expect(map['id'], 'test-item-1');
      expect(map['topic'], 'dsm/prod/app/interacao/tela');
      expect(map['payloadJson'], '{"event_id":"123","category":"interacao_tela"}');
      expect(map['createdAt'], now.toIso8601String());

      final reconstituted = TelemetryBufferItem.fromMap(map);
      expect(reconstituted.id, item.id);
      expect(reconstituted.topic, item.topic);
      expect(reconstituted.payloadJson, item.payloadJson);
      expect(reconstituted.createdAt, now);
    });
  });
}
```

- [ ] **Step 3: Executar o teste para verificar a falha**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_buffer_item_test.dart`
Expected: FAIL (compilation error, classe não encontrada).

- [ ] **Step 4: Implementar `TelemetryBufferItem`**

Criar `apps/client/lib/core/telemetry/buffer/telemetry_buffer_item.dart`:
```dart
class TelemetryBufferItem {
  final String id;
  final String topic;
  final String payloadJson;
  final DateTime createdAt;

  const TelemetryBufferItem({
    required this.id,
    required this.topic,
    required this.payloadJson,
    required this.createdAt,
  });

  Map<String, dynamic> toMap() => {
    'id': id,
    'topic': topic,
    'payloadJson': payloadJson,
    'createdAt': createdAt.toIso8601String(),
  };

  factory TelemetryBufferItem.fromMap(Map<dynamic, dynamic> map) {
    return TelemetryBufferItem(
      id: map['id'] as String,
      topic: map['topic'] as String,
      payloadJson: map['payloadJson'] as String,
      createdAt: DateTime.parse(map['createdAt'] as String),
    );
  }
}
```

- [ ] **Step 5: Executar o teste para verificar se passa**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_buffer_item_test.dart`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/client/pubspec.yaml apps/client/pubspec.lock apps/client/lib/core/telemetry/buffer/telemetry_buffer_item.dart apps/client/test/core/telemetry/buffer/telemetry_buffer_item_test.dart
git commit -m "feat(client): define modelo de item para buffer de telemetria"
```

---

### Task 2: Implementar Abstração e Armazenamento do Buffer Local (`TelemetryBufferStorage`)

**Files:**
- Create: `apps/client/lib/core/telemetry/buffer/telemetry_buffer_storage.dart`
- Create: `apps/client/test/helpers/fake_telemetry_buffer_storage.dart`
- Test: `apps/client/test/core/telemetry/buffer/telemetry_buffer_storage_test.dart`

**Interfaces:**
- Consumes: `TelemetryBufferItem`
- Produces: `TelemetryBufferStorage` (interface abstrata), `HiveTelemetryBufferStorage` e `FakeTelemetryBufferStorage`

- [ ] **Step 1: Escrever teste falhando para `FakeTelemetryBufferStorage` e operações de armazenamento**

Criar `apps/client/test/core/telemetry/buffer/telemetry_buffer_storage_test.dart`:
```dart
import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import '../../helpers/fake_telemetry_buffer_storage.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TelemetryBufferStorage', () {
    late FakeTelemetryBufferStorage storage;

    setUp(() async {
      storage = FakeTelemetryBufferStorage();
      await storage.init();
    });

    test('stores, retrieves and deletes buffer items', () async {
      final item1 = TelemetryBufferItem(
        id: 'id-1',
        topic: 'topic/1',
        payloadJson: '{}',
        createdAt: DateTime.utc(2026, 1, 1),
      );
      final item2 = TelemetryBufferItem(
        id: 'id-2',
        topic: 'topic/2',
        payloadJson: '{}',
        createdAt: DateTime.utc(2026, 1, 2),
      );

      await storage.put(item1.id, item1);
      await storage.put(item2.id, item2);

      expect(await storage.count(), 2);
      final all = await storage.getAll();
      expect(all.length, 2);
      expect(all.first.id, 'id-1');

      await storage.delete('id-1');
      expect(await storage.count(), 1);
      expect((await storage.getAll()).first.id, 'id-2');

      await storage.clear();
      expect(await storage.count(), 0);
    });

    test('deleteBatch removes multiple items at once', () async {
      for (var i = 0; i < 5; i++) {
        await storage.put(
          'id-$i',
          TelemetryBufferItem(
            id: 'id-$i',
            topic: 'topic',
            payloadJson: '{}',
            createdAt: DateTime.utc(2026, 1, 1),
          ),
        );
      }
      expect(await storage.count(), 5);

      await storage.deleteBatch(['id-0', 'id-2', 'id-4']);
      expect(await storage.count(), 2);
      final remainingIds = (await storage.getAll()).map((e) => e.id).toList();
      expect(remainingIds, ['id-1', 'id-3']);
    });
  });
}
```

- [ ] **Step 2: Executar o teste para verificar a falha**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_buffer_storage_test.dart`
Expected: FAIL (arquivo não existe).

- [ ] **Step 3: Implementar `TelemetryBufferStorage` e `FakeTelemetryBufferStorage`**

Criar `apps/client/lib/core/telemetry/buffer/telemetry_buffer_storage.dart`:
```dart
import 'package:hive_flutter/hive_flutter.dart';
import 'telemetry_buffer_item.dart';

abstract class TelemetryBufferStorage {
  Future<void> init();
  Future<void> put(String id, TelemetryBufferItem item);
  Future<void> delete(String id);
  Future<void> deleteBatch(List<String> ids);
  Future<List<TelemetryBufferItem>> getAll();
  Future<int> count();
  Future<void> clear();
}

class HiveTelemetryBufferStorage implements TelemetryBufferStorage {
  static const String boxName = 'telemetry_buffer';
  Box<Map>? _box;

  @override
  Future<void> init() async {
    if (_box != null && _box!.isOpen) return;
    _box = await Hive.openBox<Map>(boxName);
  }

  @override
  Future<void> put(String id, TelemetryBufferItem item) async {
    await _box?.put(id, item.toMap());
  }

  @override
  Future<void> delete(String id) async {
    await _box?.delete(id);
  }

  @override
  Future<void> deleteBatch(List<String> ids) async {
    await _box?.deleteAll(ids);
  }

  @override
  Future<List<TelemetryBufferItem>> getAll() async {
    final values = _box?.values ?? [];
    return values
        .map((e) => TelemetryBufferItem.fromMap(e as Map<dynamic, dynamic>))
        .toList();
  }

  @override
  Future<int> count() async {
    return _box?.length ?? 0;
  }

  @override
  Future<void> clear() async {
    await _box?.clear();
  }
}
```

Criar `apps/client/test/helpers/fake_telemetry_buffer_storage.dart`:
```dart
import 'package:client/core/telemetry/buffer/telemetry_buffer_item.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_storage.dart';

class FakeTelemetryBufferStorage implements TelemetryBufferStorage {
  final Map<String, TelemetryBufferItem> _storage = {};

  @override
  Future<void> init() async {}

  @override
  Future<void> put(String id, TelemetryBufferItem item) async {
    _storage[id] = item;
  }

  @override
  Future<void> delete(String id) async {
    _storage.remove(id);
  }

  @override
  Future<void> deleteBatch(List<String> ids) async {
    for (final id in ids) {
      _storage.remove(id);
    }
  }

  @override
  Future<List<TelemetryBufferItem>> getAll() async {
    return _storage.values.toList();
  }

  @override
  Future<int> count() async {
    return _storage.length;
  }

  @override
  Future<void> clear() async {
    _storage.clear();
  }
}
```

- [ ] **Step 4: Executar o teste para verificar se passa**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_buffer_storage_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/client/lib/core/telemetry/buffer/telemetry_buffer_storage.dart apps/client/test/helpers/fake_telemetry_buffer_storage.dart apps/client/test/core/telemetry/buffer/telemetry_buffer_storage_test.dart
git commit -m "feat(client): implementa armazenamento abstrato e hive para buffer"
```

---

### Task 3: Implementar `TelemetryBufferService` com Capacidade Máxima e Política Drop-Oldest

**Files:**
- Create: `apps/client/lib/core/telemetry/buffer/telemetry_buffer_service.dart`
- Test: `apps/client/test/core/telemetry/buffer/telemetry_buffer_service_test.dart`

**Interfaces:**
- Consumes: `TelemetryBufferStorage`, `TelemetryBufferItem`, `Uuid`
- Produces: `TelemetryBufferService` com `enqueue()`, `peekBatch()`, `dequeueBatch()`, `clear()`, `count()`, e `telemetryBufferServiceProvider` Riverpod.

- [ ] **Step 1: Escrever teste falhando para `TelemetryBufferService`**

Criar `apps/client/test/core/telemetry/buffer/telemetry_buffer_service_test.dart`:
```dart
import 'dart:convert';
import 'package:client/core/telemetry/buffer/telemetry_buffer_service.dart';
import '../../helpers/fake_telemetry_buffer_storage.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TelemetryBufferService', () {
    late FakeTelemetryBufferStorage storage;
    late TelemetryBufferService service;

    setUp(() {
      storage = FakeTelemetryBufferStorage();
      service = TelemetryBufferService(
        storage: storage,
        maxCapacity: 3,
      );
    });

    test('enqueues items in order and retrieves FIFO batch', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});

      expect(await service.count(), 2);
      final batch = await service.peekBatch(limit: 10);
      expect(batch.length, 2);
      expect(jsonDecode(batch[0].payloadJson)['seq'], 1);
      expect(jsonDecode(batch[1].payloadJson)['seq'], 2);
    });

    test('drops oldest items when maxCapacity is exceeded', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});
      await service.enqueue(topic: 'topic/3', payload: {'seq': 3});
      expect(await service.count(), 3);

      await service.enqueue(topic: 'topic/4', payload: {'seq': 4});
      expect(await service.count(), 3);

      final batch = await service.peekBatch(limit: 10);
      final seqs = batch.map((e) => jsonDecode(e.payloadJson)['seq']).toList();
      expect(seqs, [2, 3, 4]); // Item 1 foi descartado
    });

    test('dequeueBatch removes selected items', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});

      final batch = await service.peekBatch(limit: 1);
      await service.dequeueBatch([batch.first.id]);

      expect(await service.count(), 1);
      final remaining = await service.peekBatch(limit: 10);
      expect(jsonDecode(remaining.first.payloadJson)['seq'], 2);
    });

    test('clear removes all entries', () async {
      await service.enqueue(topic: 'topic/1', payload: {'seq': 1});
      await service.enqueue(topic: 'topic/2', payload: {'seq': 2});

      await service.clear();
      expect(await service.count(), 0);
    });
  });
}
```

- [ ] **Step 2: Executar o teste para verificar a falha**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_buffer_service_test.dart`
Expected: FAIL (serviço não existe).

- [ ] **Step 3: Implementar `TelemetryBufferService`**

Criar `apps/client/lib/core/telemetry/buffer/telemetry_buffer_service.dart`:
```dart
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import 'telemetry_buffer_item.dart';
import 'telemetry_buffer_storage.dart';

final telemetryBufferStorageProvider = Provider<TelemetryBufferStorage>((ref) {
  return HiveTelemetryBufferStorage();
});

final telemetryBufferServiceProvider = Provider<TelemetryBufferService>((ref) {
  final storage = ref.watch(telemetryBufferStorageProvider);
  return TelemetryBufferService(storage: storage);
});

class TelemetryBufferService {
  final TelemetryBufferStorage storage;
  final int maxCapacity;
  final Uuid uuid;

  TelemetryBufferService({
    required this.storage,
    this.maxCapacity = 1000,
    this.uuid = const Uuid(),
  });

  Future<void> enqueue({
    required String topic,
    required Map<String, dynamic> payload,
    DateTime? timestamp,
  }) async {
    final currentCount = await storage.count();
    if (currentCount >= maxCapacity) {
      final all = await storage.getAll();
      all.sort((a, b) => a.createdAt.compareTo(b.createdAt));
      final excessCount = (currentCount - maxCapacity) + 1;
      final idsToRemove = all.take(excessCount).map((e) => e.id).toList();
      await storage.deleteBatch(idsToRemove);
    }

    final id = uuid.v4();
    final item = TelemetryBufferItem(
      id: id,
      topic: topic,
      payloadJson: jsonEncode(payload),
      createdAt: timestamp ?? DateTime.now().toUtc(),
    );

    await storage.put(id, item);
  }

  Future<List<TelemetryBufferItem>> peekBatch({int limit = 50}) async {
    final all = await storage.getAll();
    all.sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return all.take(limit).toList();
  }

  Future<void> dequeueBatch(List<String> ids) async {
    if (ids.isEmpty) return;
    await storage.deleteBatch(ids);
  }

  Future<int> count() async {
    return storage.count();
  }

  Future<void> clear() async {
    await storage.clear();
  }
}
```

- [ ] **Step 4: Executar o teste para verificar se passa**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_buffer_service_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/client/lib/core/telemetry/buffer/telemetry_buffer_service.dart apps/client/test/core/telemetry/buffer/telemetry_buffer_service_test.dart
git commit -m "feat(client): implementa servico de buffer local com politica drop-oldest"
```

---

### Task 4: Implementar `TelemetrySyncWorker` para Sincronização Automática FIFO

**Files:**
- Create: `apps/client/lib/core/telemetry/buffer/telemetry_sync_worker.dart`
- Test: `apps/client/test/core/telemetry/buffer/telemetry_sync_worker_test.dart`

**Interfaces:**
- Consumes: `TelemetryBufferService`, `MqttService`, `MqttConnectionStatus`
- Produces: `TelemetrySyncWorker` com `syncPending()`, `startListening()` e `telemetrySyncWorkerProvider` Riverpod.

- [ ] **Step 1: Escrever teste falhando para `TelemetrySyncWorker`**

Criar `apps/client/test/core/telemetry/buffer/telemetry_sync_worker_test.dart`:
```dart
import 'dart:async';
import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_sync_worker.dart';
import '../../helpers/fake_mqtt_transport_client.dart';
import '../../helpers/fake_telemetry_buffer_storage.dart';
import 'package:flutter_test/flutter_test.dart';

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
  });
}
```

- [ ] **Step 2: Executar o teste para verificar a falha**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_sync_worker_test.dart`
Expected: FAIL (worker não existe).

- [ ] **Step 3: Implementar `TelemetrySyncWorker`**

Criar `apps/client/lib/core/telemetry/buffer/telemetry_sync_worker.dart`:
```dart
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
          final decodedPayload = jsonDecode(item.payloadJson) as Map<String, dynamic>;
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
```

- [ ] **Step 4: Executar o teste para verificar se passa**

Run: `cd apps/client && fvm flutter test test/core/telemetry/buffer/telemetry_sync_worker_test.dart`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/client/lib/core/telemetry/buffer/telemetry_sync_worker.dart apps/client/test/core/telemetry/buffer/telemetry_sync_worker_test.dart
git commit -m "feat(client): implementa worker de sincronizacao automatica fifo"
```

---

### Task 5: Integrar `TelemetryBufferService` e `TelemetrySyncWorker` ao `TelemetryDispatcher` e Governança LGPD

**Files:**
- Modify: `apps/client/lib/core/telemetry/telemetry_dispatcher.dart`
- Modify: `apps/client/lib/core/privacy/privacy_notifier.dart`
- Modify: `apps/client/lib/core/session/session_notifier.dart`
- Modify: `apps/client/lib/main.dart`
- Test: `apps/client/test/core/telemetry/telemetry_dispatcher_test.dart`
- Create: `apps/client/test/integration/offline_buffer_integration_test.dart`

**Interfaces:**
- Consumes: `TelemetryDispatcher`, `TelemetryBufferService`, `TelemetrySyncWorker`, `PrivacyNotifier`, `SessionNotifier`
- Produces: Enfileiramento offline com sync imediato se conectado, e purga total no descarte de dados LGPD.

- [ ] **Step 1: Atualizar testes existentes e criar teste de integração do fluxo offline**

Criar `apps/client/test/integration/offline_buffer_integration_test.dart`:
```dart
import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_buffer_service.dart';
import 'package:client/core/telemetry/buffer/telemetry_sync_worker.dart';
import 'package:client/core/telemetry/platform_source_detector.dart';
import 'package:client/core/telemetry/telemetry_dispatcher.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import '../helpers/fake_mqtt_transport_client.dart';
import '../helpers/fake_telemetry_buffer_storage.dart';
import 'package:flutter_test/flutter_test.dart';

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
```

- [ ] **Step 2: Executar teste para verificar falhas na assinatura**

Run: `cd apps/client && fvm flutter test test/integration/offline_buffer_integration_test.dart`
Expected: FAIL (argumentos adicionais no `TelemetryDispatcher`).

- [ ] **Step 3: Atualizar `TelemetryDispatcher` com o buffer service e sync worker**

Modificar `apps/client/lib/core/telemetry/telemetry_dispatcher.dart`:
Adicionar injeção opcional/provedor de `bufferService` e `syncWorker`, garantindo gravação no buffer e disparo de `syncPending()`.

- [ ] **Step 4: Integrar purga do buffer em `PrivacyNotifier` e `SessionNotifier`**

Modificar `apps/client/lib/core/privacy/privacy_notifier.dart` e `apps/client/lib/core/session/session_notifier.dart`:
Ao revogar consentimento ou limpar dados de sessão, invocar `bufferService.clear()`.

- [ ] **Step 5: Inicializar o Hive no `main.dart` com inicialização defensiva**

Atualizar `apps/client/lib/main.dart` para chamar `await Hive.initFlutter()` antes de `runApp()`.

- [ ] **Step 6: Executar toda a suíte de testes do cliente**

Run: `cd apps/client && fvm flutter test`
Expected: PASS com 100% dos testes verdes.

- [ ] **Step 7: Executar análise estática**

Run: `cd apps/client && fvm flutter analyze`
Expected: 0 issues.

- [ ] **Step 8: Commit**

```bash
git add apps/client/lib/ apps/client/test/
git commit -m "feat(client): integra buffer persistente ao dispatcher e governanca lgpd"
```
