import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

final sessionNotifierProvider =
    NotifierProvider<SessionNotifier, String?>(SessionNotifier.new);

class SessionNotifier extends Notifier<String?> {
  static const _uuid = Uuid();

  @override
  String? build() => null;

  String? get currentSessionId => state;

  String createSession() {
    final newId = _uuid.v4();
    state = newId;
    return newId;
  }

  String regenerateSession() {
    final newId = _uuid.v4();
    state = newId;
    return newId;
  }

  void clearSession() {
    state = null;
  }
}
