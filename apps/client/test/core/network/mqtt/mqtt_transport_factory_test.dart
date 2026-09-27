import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_transport_client.dart';
import 'package:client/core/network/mqtt/mqtt_transport_factory.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('MqttTransportFactory', () {
    test('creates an MqttTransportClient instance for current platform', () {
      const config = MqttConfig(host: 'localhost');
      final client = createMqttTransportClient(config, 'test_client_id');
      expect(client, isA<MqttTransportClient>());
      client.dispose();
    });

    test('verifies MqttConnectionStatus enum values', () {
      expect(MqttConnectionStatus.values, contains(MqttConnectionStatus.disconnected));
      expect(MqttConnectionStatus.values, contains(MqttConnectionStatus.connecting));
      expect(MqttConnectionStatus.values, contains(MqttConnectionStatus.connected));
      expect(MqttConnectionStatus.values, contains(MqttConnectionStatus.fault));
    });

    test('deduplicates status updates when status does not change', () async {
      const config = MqttConfig(host: 'localhost');
      final client = createMqttTransportClient(config, 'test_client_id');
      final statuses = <MqttConnectionStatus>[];
      final sub = client.statusStream.listen(statuses.add);

      client.disconnect();
      await Future<void>.delayed(Duration.zero);

      expect(statuses, isEmpty);
      await sub.cancel();
      client.dispose();
    });
  });
}
