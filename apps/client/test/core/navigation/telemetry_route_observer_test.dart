import 'package:client/core/navigation/telemetry_route_observer.dart';
import 'package:client/core/telemetry/telemetry_dispatcher.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeTelemetryDispatcher implements TelemetryDispatcher {
  final List<Map<String, dynamic>> dispatchedEvents = [];

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);

  @override
  Future<bool> dispatchScreenInteraction({
    required String screenName,
    required double durationSeconds,
  }) async {
    dispatchedEvents.add({
      'screen_name': screenName,
      'duration_seconds': durationSeconds,
    });
    return true;
  }
}

class FakeBuildContext extends Fake implements BuildContext {}

class TestPopupRoute extends PopupRoute<void> {
  @override
  Color? get barrierColor => null;

  @override
  bool get barrierDismissible => false;

  @override
  String? get barrierLabel => null;

  @override
  Widget buildPage(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
  ) =>
      const SizedBox();

  @override
  Duration get transitionDuration => Duration.zero;
}

void main() {
  group('TelemetryRouteObserver', () {
    late FakeTelemetryDispatcher fakeDispatcher;
    late TelemetryRouteObserver observer;

    setUp(() {
      fakeDispatcher = FakeTelemetryDispatcher();
      observer = TelemetryRouteObserver(dispatcher: fakeDispatcher);
    });

    test('tracks duration on route push and pop', () async {
      final routeA = MaterialPageRoute<void>(
        settings: const RouteSettings(name: 'HomeScreen'),
        builder: (_) => const SizedBox(),
      );
      final routeB = MaterialPageRoute<void>(
        settings: const RouteSettings(name: 'SettingsScreen'),
        builder: (_) => const SizedBox(),
      );

      observer.didPush(routeA, null);
      expect(fakeDispatcher.dispatchedEvents, isEmpty);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      observer.didPush(routeB, routeA);
      expect(fakeDispatcher.dispatchedEvents.length, 1);
      expect(fakeDispatcher.dispatchedEvents.first['screen_name'], 'HomeScreen');
      expect(fakeDispatcher.dispatchedEvents.first['duration_seconds'], greaterThan(0.04));

      await Future<void>.delayed(const Duration(milliseconds: 30));

      observer.didPop(routeB, routeA);
      expect(fakeDispatcher.dispatchedEvents.length, 2);
      expect(fakeDispatcher.dispatchedEvents[1]['screen_name'], 'SettingsScreen');
      expect(fakeDispatcher.dispatchedEvents[1]['duration_seconds'], greaterThan(0.02));
    });

    test('ignores modal dialogs and popup routes', () {
      final routeA = MaterialPageRoute<void>(
        settings: const RouteSettings(name: 'HomeScreen'),
        builder: (_) => const SizedBox(),
      );
      final dialogRoute = DialogRoute<void>(
        context: FakeBuildContext(),
        barrierLabel: 'Dismiss',
        builder: (_) => const SizedBox(),
      );
      final popupRoute = TestPopupRoute();

      observer.didPush(routeA, null);
      observer.didPush(dialogRoute, routeA);
      expect(fakeDispatcher.dispatchedEvents, isEmpty);

      observer.didPop(dialogRoute, routeA);
      expect(fakeDispatcher.dispatchedEvents, isEmpty);

      observer.didPush(popupRoute, routeA);
      expect(fakeDispatcher.dispatchedEvents, isEmpty);

      observer.didPop(popupRoute, routeA);
      expect(fakeDispatcher.dispatchedEvents, isEmpty);
    });

    test('tracks duration on route replace', () async {
      final routeA = MaterialPageRoute<void>(
        settings: const RouteSettings(name: 'LoginScreen'),
        builder: (_) => const SizedBox(),
      );
      final routeB = MaterialPageRoute<void>(
        settings: const RouteSettings(name: 'DashboardScreen'),
        builder: (_) => const SizedBox(),
      );

      observer.didPush(routeA, null);
      await Future<void>.delayed(const Duration(milliseconds: 40));

      observer.didReplace(newRoute: routeB, oldRoute: routeA);
      expect(fakeDispatcher.dispatchedEvents.length, 1);
      expect(fakeDispatcher.dispatchedEvents.first['screen_name'], 'LoginScreen');
      expect(fakeDispatcher.dispatchedEvents.first['duration_seconds'], greaterThan(0.03));
    });

    test('falls back to route runtimeType when settings name is null or empty', () async {
      final unnamedRoute = MaterialPageRoute<void>(
        builder: (_) => const SizedBox(),
      );
      final emptyNamedRoute = MaterialPageRoute<void>(
        settings: const RouteSettings(name: ''),
        builder: (_) => const SizedBox(),
      );

      observer.didPush(unnamedRoute, null);
      await Future<void>.delayed(const Duration(milliseconds: 10));

      observer.didPush(emptyNamedRoute, unnamedRoute);
      expect(fakeDispatcher.dispatchedEvents.length, 1);
      expect(fakeDispatcher.dispatchedEvents.first['screen_name'], contains('MaterialPageRoute'));

      await Future<void>.delayed(const Duration(milliseconds: 10));
      observer.didPop(emptyNamedRoute, unnamedRoute);
      expect(fakeDispatcher.dispatchedEvents.length, 2);
      expect(fakeDispatcher.dispatchedEvents[1]['screen_name'], contains('MaterialPageRoute'));
    });

    test('tracks duration on route remove', () async {
      final routeA = MaterialPageRoute<void>(
        settings: const RouteSettings(name: 'RemovedScreen'),
        builder: (_) => const SizedBox(),
      );

      observer.didPush(routeA, null);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      observer.didRemove(routeA, null);
      expect(fakeDispatcher.dispatchedEvents.length, 1);
      expect(fakeDispatcher.dispatchedEvents.first['screen_name'], 'RemovedScreen');
      expect(fakeDispatcher.dispatchedEvents.first['duration_seconds'], greaterThan(0.02));
    });

    test('telemetryRouteObserverProvider creates instance using telemetryDispatcherProvider', () {
      final container = ProviderContainer(
        overrides: [
          telemetryDispatcherProvider.overrideWithValue(fakeDispatcher),
        ],
      );
      addTearDown(container.dispose);

      final observerInstance = container.read(telemetryRouteObserverProvider);
      expect(observerInstance, isA<TelemetryRouteObserver>());
    });
  });
}
