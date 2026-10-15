import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('MqttConfig', () {
    test('provides default configuration values', () {
      const config = MqttConfig();
      expect(config.host, 'localhost');
      expect(config.tcpPort, 1883);
      expect(config.wsPort, 9001);
      expect(config.username, 'app_user');
      expect(config.password, 'app_password');
      expect(config.clientPrefix, 'client_app_');
    });

    test('supports custom overrides', () {
      const config = MqttConfig(
        host: 'broker.example.com',
        tcpPort: 1884,
        wsPort: 9002,
        username: 'custom_user',
        password: 'custom_password',
        clientPrefix: 'custom_prefix_',
      );
      expect(config.host, 'broker.example.com');
      expect(config.tcpPort, 1884);
      expect(config.wsPort, 9002);
      expect(config.username, 'custom_user');
      expect(config.password, 'custom_password');
      expect(config.clientPrefix, 'custom_prefix_');
    });

    test('resolves port to tcpPort on non-web platform', () {
      const config = MqttConfig(tcpPort: 1884, wsPort: 9002);
      expect(config.port, 1884);
    });
  });
}
