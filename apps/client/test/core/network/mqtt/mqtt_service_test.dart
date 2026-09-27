import 'dart:async';
import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/network/mqtt/mqtt_transport_client.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mqtt_client/mqtt_client.dart';

class FakeMqttTransportClient implements MqttTransportClient {
  final StreamController<MqttConnectionStatus> _controller =
      StreamController<MqttConnectionStatus>.broadcast();
  MqttConnectionStatus _status = MqttConnectionStatus.disconnected;

  bool shouldSucceed = true;
  bool disconnectCalled = false;
  bool disposeCalled = false;
  String? lastPublishedTopic;
  String? lastPublishedPayload;
  MqttQos? lastPublishedQos;
  bool? lastPublishedRetain;
  String? lastConnectUsername;
  String? lastConnectPassword;

  @override
  MqttConnectionStatus get currentStatus => _status;

  @override
  Stream<MqttConnectionStatus> get statusStream => _controller.stream;

  @override
  Future<bool> connect({required String username, required String password}) async {
    lastConnectUsername = username;
    lastConnectPassword = password;
    _status = shouldSucceed ? MqttConnectionStatus.connected : MqttConnectionStatus.fault;
    if (!_controller.isClosed) {
      _controller.add(_status);
    }
    return shouldSucceed;
  }

  @override
  void disconnect() {
    disconnectCalled = true;
    _status = MqttConnectionStatus.disconnected;
    if (!_controller.isClosed) {
      _controller.add(_status);
    }
  }

  @override
  void publish({
    required String topic,
    required String payload,
    MqttQos qos = MqttQos.atLeastOnce,
    bool retain = false,
  }) {
    lastPublishedTopic = topic;
    lastPublishedPayload = payload;
    lastPublishedQos = qos;
    lastPublishedRetain = retain;
  }

  @override
  void dispose() {
    disposeCalled = true;
    disconnect();
    if (!_controller.isClosed) {
      _controller.close();
    }
  }
}

void main() {
  group('MqttService', () {
    late FakeMqttTransportClient fakeTransport;
    late MqttService service;

    setUp(() {
      fakeTransport = FakeMqttTransportClient();
      service = MqttService(
        config: const MqttConfig(username: 'test_user', password: 'test_password'),
        transport: fakeTransport,
      );
    });

    tearDown(() {
      service.dispose();
    });

    test('initializes with disconnected status', () {
      expect(service.status, MqttConnectionStatus.disconnected);
    });

    test('connects successfully and updates status', () async {
      final success = await service.connect();
      expect(success, isTrue);
      expect(service.status, MqttConnectionStatus.connected);
      expect(fakeTransport.lastConnectUsername, 'test_user');
      expect(fakeTransport.lastConnectPassword, 'test_password');
    });

    test('handles connection failure and updates status to fault', () async {
      fakeTransport.shouldSucceed = false;
      final success = await service.connect();
      expect(success, isFalse);
      expect(service.status, MqttConnectionStatus.fault);
    });

    test('publishes payload with QoS 1', () async {
      await service.connect();
      service.publish(
        topic: 'dsm/prod/app/interacao/tela',
        payload: '{"test": true}',
      );
      expect(fakeTransport.lastPublishedTopic, 'dsm/prod/app/interacao/tela');
      expect(fakeTransport.lastPublishedPayload, '{"test": true}');
      expect(fakeTransport.lastPublishedQos, MqttQos.atLeastOnce);
      expect(fakeTransport.lastPublishedRetain, isFalse);
    });

    test('disconnect updates transport and status', () {
      service.disconnect();
      expect(fakeTransport.disconnectCalled, isTrue);
      expect(service.status, MqttConnectionStatus.disconnected);
    });

    test('dispose cancels subscription and closes resources', () {
      service.dispose();
      expect(fakeTransport.disconnectCalled, isTrue);
      expect(fakeTransport.disposeCalled, isTrue);
    });

    test('statusStream emits status updates when transport updates', () async {
      final statuses = <MqttConnectionStatus>[];
      final subscription = service.statusStream.listen(statuses.add);
      addTearDown(subscription.cancel);

      await service.connect();
      service.disconnect();

      await pumpEventQueue();
      expect(statuses, [MqttConnectionStatus.connected, MqttConnectionStatus.disconnected]);
    });
  });

  group('Riverpod Providers', () {
    test('mqttConfigProvider provides default MqttConfig', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final config = container.read(mqttConfigProvider);
      expect(config.host, 'localhost');
      expect(config.clientPrefix, 'client_app_');
    });

    test('mqttServiceProvider instantiates MqttService with config and clientId', () {
      final container = ProviderContainer();
      final service = container.read(mqttServiceProvider);

      expect(service, isA<MqttService>());
      expect(service.config.clientPrefix, 'client_app_');

      container.dispose();
      expect(service.status, MqttConnectionStatus.disconnected);
    });

    test('mqttConnectionStatusProvider exposes status stream of mqttServiceProvider', () async {
      final fakeTransport = FakeMqttTransportClient();
      final testService = MqttService(
        config: const MqttConfig(),
        transport: fakeTransport,
      );

      final container = ProviderContainer(
        overrides: [
          mqttServiceProvider.overrideWithValue(testService),
        ],
      );
      addTearDown(() {
        container.dispose();
        testService.dispose();
      });

      expect(
        container.read(mqttConnectionStatusProvider),
        const AsyncLoading<MqttConnectionStatus>(),
      );

      await testService.connect();
      final status = await container.read(mqttConnectionStatusProvider.future);
      expect(status, MqttConnectionStatus.connected);
    });
  });
}
