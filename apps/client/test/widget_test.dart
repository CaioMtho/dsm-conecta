import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/core/telemetry/telemetry_gatekeeper.dart';
import 'package:client/features/privacy/consent_dialog.dart';
import 'package:client/features/settings/settings_screen.dart';
import 'package:client/features/status/mqtt_status_icon.dart';
import 'package:client/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late SharedPreferences prefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
  });

  testWidgets('shows ConsentDialog on startup when consent is undetermined', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
        child: const MyApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(ConsentDialog), findsOneWidget);
    expect(find.text('Privacidade e Consentimento'), findsOneWidget);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(MyApp)),
    );
    final gatekeeper = container.read(telemetryGatekeeperProvider);
    expect(gatekeeper.canEmitTelemetry(), isFalse);
  });

  testWidgets('renders MqttStatusIcon in AppBar', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
        child: const MyApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(MqttStatusIcon), findsOneWidget);
  });

  testWidgets('navigates to SettingsScreen when settings icon is tapped', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
        child: const MyApp(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Aceitar Todos'));
    await tester.pumpAndSettle();

    expect(find.byType(ConsentDialog), findsNothing);

    await tester.tap(find.byKey(const Key('appbar_settings_button')));
    await tester.pumpAndSettle();

    expect(find.byType(SettingsScreen), findsOneWidget);
  });
}
