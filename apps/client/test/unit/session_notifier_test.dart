import 'package:client/core/session/session_notifier.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SessionNotifier', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer();
    });

    tearDown(() {
      container.dispose();
    });

    test('initial session is null', () {
      final session = container.read(sessionNotifierProvider);
      expect(session, isNull);
    });

    test('currentSessionId returns active session ID or null', () {
      final notifier = container.read(sessionNotifierProvider.notifier);
      expect(notifier.currentSessionId, isNull);

      final sessionId = notifier.createSession();
      expect(notifier.currentSessionId, equals(sessionId));

      notifier.clearSession();
      expect(notifier.currentSessionId, isNull);
    });

    test('createSession generates valid UUID v4', () {
      final notifier = container.read(sessionNotifierProvider.notifier);
      final sessionId = notifier.createSession();

      expect(sessionId, isNotEmpty);
      expect(container.read(sessionNotifierProvider), equals(sessionId));

      final uuidRegex = RegExp(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        caseSensitive: false,
      );
      expect(uuidRegex.hasMatch(sessionId), isTrue);
    });

    test('regenerateSession produces a new different UUID', () {
      final notifier = container.read(sessionNotifierProvider.notifier);
      final firstSession = notifier.createSession();
      final secondSession = notifier.regenerateSession();

      expect(firstSession, isNot(equals(secondSession)));
      expect(container.read(sessionNotifierProvider), equals(secondSession));
    });

    test('clearSession nullifies the session', () {
      final notifier = container.read(sessionNotifierProvider.notifier);
      notifier.createSession();
      expect(container.read(sessionNotifierProvider), isNotNull);

      notifier.clearSession();
      expect(container.read(sessionNotifierProvider), isNull);
    });
  });
}
