class TelemetryBufferItem {
  final String id;
  final String topic;
  final String payloadJson;
  final DateTime createdAt;

  const TelemetryBufferItem({
    required this.id,
    required this.topic,
    required this.payloadJson,
    required this.createdAt,
  });

  Map<String, dynamic> toMap() => {
    'id': id,
    'topic': topic,
    'payloadJson': payloadJson,
    'createdAt': createdAt.toIso8601String(),
  };

  factory TelemetryBufferItem.fromMap(Map<dynamic, dynamic> map) {
    return TelemetryBufferItem(
      id: map['id'] as String,
      topic: map['topic'] as String,
      payloadJson: map['payloadJson'] as String,
      createdAt: DateTime.parse(map['createdAt'] as String),
    );
  }
}
