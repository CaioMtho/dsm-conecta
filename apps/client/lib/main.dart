import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/navigation/telemetry_route_observer.dart';
import 'core/network/mqtt/mqtt_service.dart';
import 'core/privacy/consent_state.dart';
import 'core/privacy/privacy_notifier.dart';
import 'core/privacy/privacy_storage.dart';
import 'features/privacy/consent_dialog.dart';
import 'features/settings/settings_screen.dart';
import 'features/status/mqtt_status_icon.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sharedPreferences = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(sharedPreferences),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routeObserver = ref.watch(telemetryRouteObserverProvider);

    return MaterialApp(
      title: 'DSM Conecta',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      navigatorObservers: [routeObserver],
      home: const PrivacyGate(child: MyHomePage(title: 'DSM Conecta')),
    );
  }
}

class PrivacyGate extends ConsumerStatefulWidget {
  final Widget child;

  const PrivacyGate({super.key, required this.child});

  @override
  ConsumerState<PrivacyGate> createState() => _PrivacyGateState();
}

class _PrivacyGateState extends ConsumerState<PrivacyGate> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkConsent();
      ref.read(mqttServiceProvider).connect();
    });
  }

  void _checkConsent() {
    final consent = ref.read(privacyNotifierProvider);
    if (consent.status == ConsentStatus.undetermined && mounted) {
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const ConsentDialog(),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int _counter = 0;

  void _incrementCounter() {
    setState(() {
      _counter++;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
        actions: [
          const MqttStatusIcon(),
          IconButton(
            key: const Key('appbar_settings_button'),
            icon: const Icon(Icons.settings),
            tooltip: 'Configurações de Privacidade',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  settings: const RouteSettings(name: 'SettingsScreen'),
                  builder: (_) => const SettingsScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('DSM Conecta - Cliente Flutter'),
            const SizedBox(height: 16),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _incrementCounter,
        tooltip: 'Increment',
        child: const Icon(Icons.add),
      ),
    );
  }
}
