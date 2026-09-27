import 'dart:convert';

import 'package:client/core/network/mqtt/mqtt_config.dart';
import 'package:client/core/network/mqtt/mqtt_service.dart';
import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_notifier.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/core/session/session_notifier.dart';
import 'package:client/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/network/mqtt/mqtt_service_test.dart';

class IntegrationPrivacyNotifier extends PrivacyNotifier {
  final ConsentState _consentState;
  IntegrationPrivacyNotifier([
    this._consentState = const ConsentState(
      status: ConsentStatus.accepted,
      telemetryAccepted: true,
      sensorsAccepted: true,
    ),
  ]);

  @override
  ConsentState build() => _consentState;
}

class IntegrationSessionNotifier extends SessionNotifier {
  final String? _sessionId;
  IntegrationSessionNotifier([this._sessionId = 'integration-session-1234']);

  @override
  String? build() => _sessionId;
}

void main() {
  group('Screen Tracking & MQTT Integration', () {
    late FakeMqttTransportClient fakeTransport;

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      fakeTransport = FakeMqttTransportClient();
    });

    tearDown(() {
      fakeTransport.dispose();
    });

    testWidgets(
      'tracks navigation to Settings and emits MQTT telemetry when consent is accepted',
      (tester) async {
        final sharedPreferences = await SharedPreferences.getInstance();

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              sharedPreferencesProvider.overrideWithValue(sharedPreferences),
              mqttServiceProvider.overrideWith(
                (ref) => MqttService(
                  config: const MqttConfig(),
                  transport: fakeTransport,
                ),
              ),
              privacyNotifierProvider.overrideWith(
                IntegrationPrivacyNotifier.new,
              ),
              sessionNotifierProvider.overrideWith(
                IntegrationSessionNotifier.new,
              ),
            ],
            child: const MyApp(),
          ),
        );

        await tester.pumpAndSettle();

        // Navigate to Settings
        await tester.tap(find.byKey(const Key('appbar_settings_button')));
        await tester.pumpAndSettle();

        // Verify SettingsScreen opened
        expect(find.text('Configurações de Privacidade'), findsOneWidget);

        // Pop back to Home
        final NavigatorState navigator = tester.state(find.byType(Navigator));
        navigator.pop();
        await tester.pumpAndSettle();

        // Verify that at least one screen interaction event was published
        expect(fakeTransport.lastPublishedTopic, 'dsm/prod/app/interacao/tela');
        expect(fakeTransport.lastPublishedPayload, isNotNull);

        final payload = json.decode(
          fakeTransport.lastPublishedPayload!,
        ) as Map<String, dynamic>;
        expect(payload['schema_version'], '1.0');
        expect(payload['session_id'], 'integration-session-1234');
        expect(payload['category'], 'interacao_tela');
        expect(payload['payload']['screen_name'], 'SettingsScreen');
        expect(payload['payload']['duration_seconds'], isA<num>());
      },
    );

    testWidgets(
      'does not emit MQTT telemetry when telemetry consent is not accepted',
      (tester) async {
        final sharedPreferences = await SharedPreferences.getInstance();

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              sharedPreferencesProvider.overrideWithValue(sharedPreferences),
              mqttServiceProvider.overrideWith(
                (ref) => MqttService(
                  config: const MqttConfig(),
                  transport: fakeTransport,
                ),
              ),
              privacyNotifierProvider.overrideWith(
                () => IntegrationPrivacyNotifier(
                  const ConsentState(
                    status: ConsentStatus.rejected,
                    telemetryAccepted: false,
                    sensorsAccepted: false,
                  ),
                ),
              ),
              sessionNotifierProvider.overrideWith(
                () => IntegrationSessionNotifier(null),
              ),
            ],
            child: const MyApp(),
          ),
        );

        await tester.pumpAndSettle();

        // Navigate to Settings
        await tester.tap(find.byKey(const Key('appbar_settings_button')));
        await tester.pumpAndSettle();

        expect(find.text('Configurações de Privacidade'), findsOneWidget);

        // Pop back to Home
        final NavigatorState navigator = tester.state(find.byType(Navigator));
        navigator.pop();
        await tester.pumpAndSettle();

        // Verify that NO screen interaction telemetry event was published
        expect(fakeTransport.lastPublishedTopic, isNull);
        expect(fakeTransport.lastPublishedPayload, isNull);
      },
    );
  });
}
