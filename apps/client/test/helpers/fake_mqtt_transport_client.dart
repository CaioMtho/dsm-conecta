import 'dart:async';
import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_transport_client.dart';
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
  final List<Map<String, dynamic>> publishedMessages = [];
  void Function(String topic, String payload)? onPublish;

  void emitStatus(MqttConnectionStatus status) {
    _status = status;
    if (!_controller.isClosed) {
      _controller.add(status);
    }
  }

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
    publishedMessages.add({
      'topic': topic,
      'payload': payload,
      'qos': qos,
      'retain': retain,
    });
    onPublish?.call(topic, payload);
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
