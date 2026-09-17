import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_notifier.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/features/privacy/consent_dialog.dart';
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

  Widget buildTestableWidget() {
    return ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
      child: const MaterialApp(
        home: Scaffold(
          body: ConsentDialog(),
        ),
      ),
    );
  }

  group('ConsentDialog', () {
    testWidgets('renders LGPD information and primary buttons', (tester) async {
      await tester.pumpWidget(buildTestableWidget());

      expect(find.text('Privacidade e Consentimento'), findsOneWidget);
      expect(find.text('Aceitar Todos'), findsOneWidget);
      expect(find.text('Recusar'), findsOneWidget);
      expect(find.text('Personalizar'), findsOneWidget);
    });

    testWidgets('clicking Aceitar Todos accepts all permissions', (tester) async {
      await tester.pumpWidget(buildTestableWidget());

      await tester.tap(find.text('Aceitar Todos'));
      await tester.pumpAndSettle();

      final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
      final state = container.read(privacyNotifierProvider);

      expect(state.status, ConsentStatus.accepted);
      expect(state.telemetryAccepted, isTrue);
      expect(state.sensorsAccepted, isTrue);
    });

    testWidgets('clicking Recusar rejects permissions', (tester) async {
      await tester.pumpWidget(buildTestableWidget());

      await tester.tap(find.text('Recusar'));
      await tester.pumpAndSettle();

      final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
      final state = container.read(privacyNotifierProvider);

      expect(state.status, ConsentStatus.rejected);
      expect(state.telemetryAccepted, isFalse);
    });

    testWidgets('customizing permits individual toggle and saving preferences', (tester) async {
      await tester.pumpWidget(buildTestableWidget());

      await tester.tap(find.text('Personalizar'));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('switch_telemetry')), findsOneWidget);
      expect(find.byKey(const Key('switch_sensors')), findsOneWidget);
      expect(find.text('Salvar Preferências'), findsOneWidget);

      await tester.tap(find.byKey(const Key('switch_telemetry')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('switch_sensors')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Salvar Preferências'));
      await tester.pumpAndSettle();

      final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
      final state = container.read(privacyNotifierProvider);

      expect(state.status, ConsentStatus.accepted);
      expect(state.telemetryAccepted, isFalse);
      expect(state.sensorsAccepted, isTrue);
    });

    testWidgets('showConsentDialogIfNeeded displays dialog when undetermined', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(prefs),
          ],
          child: MaterialApp(
            home: Consumer(
              builder: (context, ref, _) {
                return ElevatedButton(
                  onPressed: () => showConsentDialogIfNeeded(context, ref),
                  child: const Text('Check'),
                );
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      expect(find.byType(ConsentDialog), findsOneWidget);
    });

    testWidgets('showConsentDialogIfNeeded does not show dialog when already decided', (tester) async {
      await prefs.setString('privacy_consent_status', 'accepted');

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(prefs),
          ],
          child: MaterialApp(
            home: Consumer(
              builder: (context, ref, _) {
                return ElevatedButton(
                  onPressed: () => showConsentDialogIfNeeded(context, ref),
                  child: const Text('Check'),
                );
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('Check'));
      await tester.pumpAndSettle();

      expect(find.byType(ConsentDialog), findsNothing);
    });
  });
}
