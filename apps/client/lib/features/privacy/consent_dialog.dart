import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/privacy/consent_state.dart';
import '../../core/privacy/privacy_notifier.dart';

Future<void> showConsentDialogIfNeeded(BuildContext context, WidgetRef ref) async {
  final consent = ref.read(privacyNotifierProvider);
  if (consent.status == ConsentStatus.undetermined && context.mounted) {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const ConsentDialog(),
    );
  }
}

class ConsentDialog extends ConsumerStatefulWidget {
  const ConsentDialog({super.key});

  @override
  ConsumerState<ConsentDialog> createState() => _ConsentDialogState();
}

class _ConsentDialogState extends ConsumerState<ConsentDialog> {
  bool _isCustomizing = false;
  bool _telemetryAccepted = true;
  bool _sensorsAccepted = false;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.privacy_tip_outlined, color: Colors.deepPurple),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Privacidade e Consentimento',
              style: TextStyle(fontSize: 18),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Em conformidade com a LGPD (Lei nº 13.709/2018), o DSM Conecta solicita sua autorização para coletar métricas de uso anonimizadas durante sua visita. '
              'Toda telemetria é associada unicamente a um identificador aleatório e descartável de sessão, sem qualquer vínculo com seus dados pessoais.',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 12),
            if (!_isCustomizing)
              TextButton.icon(
                key: const Key('btn_personalizar_toggle'),
                onPressed: () {
                  setState(() {
                    _isCustomizing = true;
                  });
                },
                icon: const Icon(Icons.tune),
                label: const Text('Personalizar'),
              )
            else ...[
              const Divider(),
              SwitchListTile(
                key: const Key('switch_telemetry'),
                title: const Text('Telemetria de Navegação'),
                subtitle: const Text('Métricas de telas visualizadas e interações.'),
                value: _telemetryAccepted,
                onChanged: (val) {
                  setState(() {
                    _telemetryAccepted = val;
                  });
                },
              ),
              SwitchListTile(
                key: const Key('switch_sensors'),
                title: const Text('Sensores do Dispositivo'),
                subtitle: const Text('Leituras contextuais de acelerômetro e movimento.'),
                value: _sensorsAccepted,
                onChanged: (val) {
                  setState(() {
                    _sensorsAccepted = val;
                  });
                },
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          key: const Key('btn_recusar'),
          onPressed: () async {
            await ref.read(privacyNotifierProvider.notifier).reject();
            if (context.mounted && Navigator.of(context).canPop()) {
              Navigator.of(context).pop();
            }
          },
          child: const Text('Recusar', style: TextStyle(color: Colors.red)),
        ),
        if (_isCustomizing)
          FilledButton(
            key: const Key('btn_salvar_personalizado'),
            onPressed: () async {
              await ref.read(privacyNotifierProvider.notifier).acceptCustom(
                    telemetry: _telemetryAccepted,
                    sensors: _sensorsAccepted,
                  );
              if (context.mounted && Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              }
            },
            child: const Text('Salvar Preferências'),
          )
        else
          FilledButton(
            key: const Key('btn_aceitar_todos'),
            onPressed: () async {
              await ref.read(privacyNotifierProvider.notifier).acceptAll();
              if (context.mounted && Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              }
            },
            child: const Text('Aceitar Todos'),
          ),
      ],
    );
  }
}
