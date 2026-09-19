import 'package:client/core/privacy/consent_state.dart';
import 'package:client/core/privacy/privacy_notifier.dart';
import 'package:client/core/privacy/privacy_storage.dart';
import 'package:client/core/session/session_notifier.dart';
import 'package:client/features/settings/settings_screen.dart';
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

  Widget buildSettingsScreen() {
    return ProviderScope(
      overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
      child: const MaterialApp(home: SettingsScreen()),
    );
  }

  group('SettingsScreen', () {
    testWidgets('displays anonymous session ID when accepted', (tester) async {
      await tester.pumpWidget(buildSettingsScreen());
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      await tester.pumpAndSettle();

      final sessionId = container.read(sessionNotifierProvider);
      expect(find.text(sessionId!), findsOneWidget);
    });

    testWidgets('regenerates session ID on button press', (tester) async {
      await tester.pumpWidget(buildSettingsScreen());
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      await tester.pumpAndSettle();

      final oldSessionId = container.read(sessionNotifierProvider);

      await tester.tap(find.byKey(const Key('btn_regenerate_session')));
      await tester.pumpAndSettle();

      final newSessionId = container.read(sessionNotifierProvider);
      expect(newSessionId, isNot(equals(oldSessionId)));
    });

    testWidgets('revoking consent updates UI and clears session', (
      tester,
    ) async {
      await tester.pumpWidget(buildSettingsScreen());
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      await tester.pumpAndSettle();

      final revokeFinder = find.byKey(const Key('btn_revoke_consent'));
      await tester.ensureVisible(revokeFinder);
      await tester.pumpAndSettle();
      await tester.tap(revokeFinder);
      await tester.pumpAndSettle();

      expect(
        container.read(privacyNotifierProvider).status,
        ConsentStatus.rejected,
      );
      expect(container.read(sessionNotifierProvider), isNull);
      expect(
        find.text('Nenhuma sessão ativa (consentimento inativo)'),
        findsOneWidget,
      );
    });

    testWidgets('deleting local data and session wipes storage (RF12)', (
      tester,
    ) async {
      await tester.pumpWidget(buildSettingsScreen());
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      await tester.pumpAndSettle();

      final deleteFinder = find.byKey(const Key('btn_delete_all_data'));
      await tester.ensureVisible(deleteFinder);
      await tester.pumpAndSettle();
      await tester.tap(deleteFinder);
      await tester.pumpAndSettle();

      expect(
        container.read(privacyNotifierProvider).status,
        ConsentStatus.undetermined,
      );
      expect(container.read(sessionNotifierProvider), isNull);
    });

    testWidgets('copies session ID to clipboard and shows snackbar', (
      tester,
    ) async {
      await tester.pumpWidget(buildSettingsScreen());
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('btn_copy_session')));
      await tester.pumpAndSettle();

      expect(find.text('ID de sessão copiado!'), findsOneWidget);
    });

    testWidgets(
      'toggling telemetry updates state and clears session when disabled',
      (tester) async {
        await tester.pumpWidget(buildSettingsScreen());
        final container = ProviderScope.containerOf(
          tester.element(find.byType(MaterialApp)),
        );
        await container.read(privacyNotifierProvider.notifier).acceptAll();
        await tester.pumpAndSettle();

        expect(container.read(sessionNotifierProvider), isNotNull);

        await tester.tap(
          find.widgetWithText(SwitchListTile, 'Telemetria de Uso'),
        );
        await tester.pumpAndSettle();

        expect(
          container.read(privacyNotifierProvider).telemetryAccepted,
          isFalse,
        );
        expect(container.read(sessionNotifierProvider), isNull);
      },
    );

    testWidgets('toggling sensors updates state', (tester) async {
      await tester.pumpWidget(buildSettingsScreen());
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      await container.read(privacyNotifierProvider.notifier).acceptAll();
      await tester.pumpAndSettle();

      await tester.tap(
        find.widgetWithText(SwitchListTile, 'Sensores do Dispositivo'),
      );
      await tester.pumpAndSettle();

      expect(container.read(privacyNotifierProvider).sensorsAccepted, isFalse);
    });
  });
}
