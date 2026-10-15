import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../privacy/consent_state.dart';
import '../privacy/privacy_notifier.dart';
import '../session/session_notifier.dart';

final telemetryGatekeeperProvider = Provider<TelemetryGatekeeper>((ref) {
  final consent = ref.watch(privacyNotifierProvider);
  final sessionId = ref.watch(sessionNotifierProvider);
  return TelemetryGatekeeper(consent: consent, sessionId: sessionId);
});

class TelemetryGatekeeper {
  final ConsentState consent;
  final String? sessionId;

  const TelemetryGatekeeper({
    ConsentState? consent,
    String? sessionId,
    bool? hasConsent,
    String? currentSessionId,
  })  : consent = consent ??
            (hasConsent == true
                ? const ConsentState(
                    status: ConsentStatus.accepted,
                    telemetryAccepted: true,
                    sensorsAccepted: true,
                  )
                : const ConsentState(
                    status: ConsentStatus.undetermined,
                    telemetryAccepted: false,
                    sensorsAccepted: false,
                  )),
        sessionId = sessionId ?? currentSessionId;

  bool canEmitTelemetry() {
    return consent.status == ConsentStatus.accepted &&
        consent.telemetryAccepted &&
        sessionId != null &&
        sessionId!.isNotEmpty;
  }

  bool canCollectSensors() {
    return canEmitTelemetry() && consent.sensorsAccepted;
  }

  String? get currentSessionId {
    return canEmitTelemetry() ? sessionId : null;
  }
}
