import 'package:client/core/network/mqtt/mqtt_connection_status.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/features/status/mqtt_status_icon.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeMqttService extends Fake implements MqttService {
  int connectCallCount = 0;

  @override
  Future<bool> connect() async {
    connectCallCount++;
    return true;
  }
}

void main() {
  group('MqttStatusIcon', () {
    testWidgets('renders connected state in green with correct tooltip', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.connected),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byIcon(Icons.cloud_done), findsOneWidget);

      final icon = tester.widget<Icon>(find.byIcon(Icons.cloud_done));
      expect(icon.color, Colors.green);
      expect(find.byTooltip('MQTT: Conectado'), findsOneWidget);
    });

    testWidgets('renders connecting state in orange with correct tooltip', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.connecting),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byIcon(Icons.cloud_sync), findsOneWidget);

      final icon = tester.widget<Icon>(find.byIcon(Icons.cloud_sync));
      expect(icon.color, Colors.orange);
      expect(find.byTooltip('MQTT: Conectando...'), findsOneWidget);
    });

    testWidgets('renders disconnected state in grey with correct tooltip', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.disconnected),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byIcon(Icons.cloud_off), findsOneWidget);

      final icon = tester.widget<Icon>(find.byIcon(Icons.cloud_off));
      expect(icon.color, Colors.grey);
      expect(find.byTooltip('MQTT: Desconectado'), findsOneWidget);
    });

    testWidgets('renders fault state in grey with correct tooltip', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.fault),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byIcon(Icons.cloud_off), findsOneWidget);

      final icon = tester.widget<Icon>(find.byIcon(Icons.cloud_off));
      expect(icon.color, Colors.grey);
      expect(find.byTooltip('MQTT: Desconectado'), findsOneWidget);
    });

    testWidgets('triggers connect on tap when disconnected', (tester) async {
      final fakeMqttService = FakeMqttService();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttServiceProvider.overrideWithValue(fakeMqttService),
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.disconnected),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('mqtt_status_icon_button')));
      await tester.pumpAndSettle();

      expect(fakeMqttService.connectCallCount, 1);
    });

    testWidgets('triggers connect on tap when in fault state', (tester) async {
      final fakeMqttService = FakeMqttService();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttServiceProvider.overrideWithValue(fakeMqttService),
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.fault),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('mqtt_status_icon_button')));
      await tester.pumpAndSettle();

      expect(fakeMqttService.connectCallCount, 1);
    });

    testWidgets('does not trigger connect on tap when connected', (
      tester,
    ) async {
      final fakeMqttService = FakeMqttService();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mqttServiceProvider.overrideWithValue(fakeMqttService),
            mqttConnectionStatusProvider.overrideWith(
              (ref) => Stream.value(MqttConnectionStatus.connected),
            ),
          ],
          child: const MaterialApp(
            home: Scaffold(
              appBar: PreferredSize(
                preferredSize: Size.fromHeight(56),
                child: MqttStatusIcon(),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('mqtt_status_icon_button')));
      await tester.pumpAndSettle();

      expect(fakeMqttService.connectCallCount, 0);
    });
  });
}
