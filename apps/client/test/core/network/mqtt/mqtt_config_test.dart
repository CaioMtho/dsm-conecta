import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('MqttConfig', () {
    tearDown(() {
      debugDefaultTargetPlatformOverride = null;
    });

    test('provides default configuration values', () {
      debugDefaultTargetPlatformOverride = TargetPlatform.linux;
      const config = MqttConfig();
      expect(config.host, 'localhost');
      expect(config.tcpPort, 1883);
      expect(config.wsPort, 9001);
      expect(config.wsPath, '');
      expect(config.username, 'app_user');
      expect(config.password, 'app_pass_dev');
      expect(config.clientPrefix, 'client_app_');
    });

    test('resolves host to 10.0.2.2 on Android platform by default', () {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      const config = MqttConfig();
      expect(config.host, '10.0.2.2');
    });

    test('supports custom overrides', () {
      const config = MqttConfig(
        host: 'broker.example.com',
        tcpPort: 1884,
        wsPort: 9002,
        wsPath: '/mqtt',
        username: 'custom_user',
        password: 'custom_password',
        clientPrefix: 'custom_prefix_',
      );
      expect(config.host, 'broker.example.com');
      expect(config.tcpPort, 1884);
      expect(config.wsPort, 9002);
      expect(config.wsPath, '/mqtt');
      expect(config.username, 'custom_user');
      expect(config.password, 'custom_password');
      expect(config.clientPrefix, 'custom_prefix_');
    });

    test('custom host override takes precedence over Android default', () {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      const config = MqttConfig(host: 'custom.broker');
      expect(config.host, 'custom.broker');
    });

    test('resolves port to tcpPort on non-web platform', () {
      const config = MqttConfig(tcpPort: 1884, wsPort: 9002);
      expect(config.port, 1884);
    });

    test('builds wsServerUri without path when wsPath is empty', () {
      const config = MqttConfig(host: 'localhost', wsPath: '');
      expect(config.wsServerUri, 'ws://localhost');
    });

    test('builds wsServerUri with leading slash preserved', () {
      const config = MqttConfig(host: 'localhost', wsPath: '/mqtt');
      expect(config.wsServerUri, 'ws://localhost/mqtt');
    });

    test('adds leading slash to wsPath in wsServerUri when missing', () {
      const config = MqttConfig(host: 'example.com', wsPath: 'mqtt');
      expect(config.wsServerUri, 'ws://example.com/mqtt');
    });
  });
}
