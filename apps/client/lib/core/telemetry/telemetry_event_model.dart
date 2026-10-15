import 'dart:convert';

class TelemetryEventModel {
  final String schemaVersion;
  final DateTime timestamp;
  final String eventId;
  final String sessionId;
  final String source;
  final String category;
  final Map<String, dynamic> payload;

  const TelemetryEventModel({
    this.schemaVersion = '1.0',
    required this.timestamp,
    required this.eventId,
    required this.sessionId,
    required this.source,
    required this.category,
    this.payload = const {},
  });

  Map<String, dynamic> toMap() {
    return {
      'schema_version': schemaVersion,
      'timestamp': timestamp.toUtc().toIso8601String(),
      'event_id': eventId,
      'session_id': sessionId,
      'source': source,
      'category': category,
      'payload': payload,
    };
  }

  String toJson() => json.encode(toMap());
}
