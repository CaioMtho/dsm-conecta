enum ConsentStatus {
  undetermined,
  accepted,
  rejected,
}

class ConsentState {
  final ConsentStatus status;
  final bool telemetryAccepted;
  final bool sensorsAccepted;
  final DateTime? acceptedAt;

  const ConsentState({
    required this.status,
    required this.telemetryAccepted,
    required this.sensorsAccepted,
    this.acceptedAt,
  });

  factory ConsentState.initial() {
    return const ConsentState(
      status: ConsentStatus.undetermined,
      telemetryAccepted: false,
      sensorsAccepted: false,
      acceptedAt: null,
    );
  }

  ConsentState copyWith({
    ConsentStatus? status,
    bool? telemetryAccepted,
    bool? sensorsAccepted,
    DateTime? acceptedAt,
  }) {
    return ConsentState(
      status: status ?? this.status,
      telemetryAccepted: telemetryAccepted ?? this.telemetryAccepted,
      sensorsAccepted: sensorsAccepted ?? this.sensorsAccepted,
      acceptedAt: acceptedAt ?? this.acceptedAt,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status.name,
      'telemetryAccepted': telemetryAccepted,
      'sensorsAccepted': sensorsAccepted,
      'acceptedAt': acceptedAt?.toIso8601String(),
    };
  }

  factory ConsentState.fromJson(Map<String, dynamic> json) {
    return ConsentState(
      status: ConsentStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => ConsentStatus.undetermined,
      ),
      telemetryAccepted: json['telemetryAccepted'] as bool? ?? false,
      sensorsAccepted: json['sensorsAccepted'] as bool? ?? false,
      acceptedAt: json['acceptedAt'] != null
          ? DateTime.tryParse(json['acceptedAt'] as String)
          : null,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ConsentState &&
          runtimeType == other.runtimeType &&
          status == other.status &&
          telemetryAccepted == other.telemetryAccepted &&
          sensorsAccepted == other.sensorsAccepted &&
          acceptedAt == other.acceptedAt;

  @override
  int get hashCode =>
      status.hashCode ^
      telemetryAccepted.hashCode ^
      sensorsAccepted.hashCode ^
      acceptedAt.hashCode;
}
