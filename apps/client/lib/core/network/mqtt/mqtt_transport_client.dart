import 'package:mqtt_client/mqtt_client.dart';
import 'mqtt_connection_status.dart';

abstract class MqttTransportClient {
  Stream<MqttConnectionStatus> get statusStream;
  MqttConnectionStatus get currentStatus;

  Future<bool> connect({required String username, required String password});
  void disconnect();
  void publish({
    required String topic,
    required String payload,
    MqttQos qos = MqttQos.atLeastOnce,
    bool retain = false,
  });
  void dispose();
}
