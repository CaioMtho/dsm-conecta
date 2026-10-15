import 'mqtt_config.dart';
import 'mqtt_transport_client.dart';

MqttTransportClient createMqttTransportClient(MqttConfig config, String clientId) {
  throw UnsupportedError('Cannot create MQTT transport on this platform.');
}
