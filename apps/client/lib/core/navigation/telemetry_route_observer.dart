import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../telemetry/telemetry_dispatcher.dart';

final telemetryRouteObserverProvider = Provider<TelemetryRouteObserver>((ref) {
  final dispatcher = ref.watch(telemetryDispatcherProvider);
  return TelemetryRouteObserver(dispatcher: dispatcher);
});

class TelemetryRouteObserver extends NavigatorObserver {
  final TelemetryDispatcher dispatcher;
  final Map<Route<dynamic>, DateTime> _entryTimestamps = {};

  TelemetryRouteObserver({required this.dispatcher});

  bool _isTrackable(Route<dynamic>? route) {
    if (route == null) return false;
    if (route is PopupRoute) return false;
    return true;
  }

  String _extractRouteName(Route<dynamic> route) {
    final settingsName = route.settings.name;
    if (settingsName != null && settingsName.isNotEmpty) {
      return settingsName;
    }
    return route.runtimeType.toString();
  }

  void _finishRouteTracking(Route<dynamic> route) {
    final entryTime = _entryTimestamps.remove(route);
    if (entryTime == null) return;

    final duration = DateTime.now().difference(entryTime);
    final durationSeconds = duration.inMilliseconds / 1000.0;
    final screenName = _extractRouteName(route);

    dispatcher.dispatchScreenInteraction(
      screenName: screenName,
      durationSeconds: durationSeconds < 0 ? 0.0 : durationSeconds,
    );
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPush(route, previousRoute);
    if (!_isTrackable(route)) return;

    if (_isTrackable(previousRoute) && previousRoute != null) {
      _finishRouteTracking(previousRoute);
    }
    _entryTimestamps[route] = DateTime.now();
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPop(route, previousRoute);
    if (!_isTrackable(route)) return;

    _finishRouteTracking(route);
    if (_isTrackable(previousRoute) && previousRoute != null) {
      _entryTimestamps[previousRoute] = DateTime.now();
    }
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    super.didReplace(newRoute: newRoute, oldRoute: oldRoute);
    if (oldRoute != null && _isTrackable(oldRoute)) {
      _finishRouteTracking(oldRoute);
    }
    if (newRoute != null && _isTrackable(newRoute)) {
      _entryTimestamps[newRoute] = DateTime.now();
    }
  }

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didRemove(route, previousRoute);
    if (_isTrackable(route)) {
      _finishRouteTracking(route);
    }
  }
}
