import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/privacy/consent_state.dart';
import '../../core/privacy/privacy_notifier.dart';
import '../../core/session/session_notifier.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final consent = ref.watch(privacyNotifierProvider);
    final sessionId = ref.watch(sessionNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Configurações de Privacidade')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.fingerprint, color: Colors.deepPurple),
                      SizedBox(width: 8),
                      Text(
                        'Sessão Anônima',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SelectableText(
                    sessionId ?? 'Nenhuma sessão ativa (consentimento inativo)',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 13,
                      color: sessionId != null ? Colors.black87 : Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    children: [
                      if (sessionId != null)
                        OutlinedButton.icon(
                          key: const Key('btn_copy_session'),
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: sessionId));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('ID de sessão copiado!'),
                              ),
                            );
                          },
                          icon: const Icon(Icons.copy, size: 16),
                          label: const Text('Copiar'),
                        ),
                      if (consent.status == ConsentStatus.accepted &&
                          consent.telemetryAccepted)
                        OutlinedButton.icon(
                          key: const Key('btn_regenerate_session'),
                          onPressed: () {
                            ref
                                .read(sessionNotifierProvider.notifier)
                                .regenerateSession();
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Nova sessão gerada.'),
                              ),
                            );
                          },
                          icon: const Icon(Icons.refresh, size: 16),
                          label: const Text('Gerar Nova Sessão'),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Column(
              children: [
                ListTile(
                  title: const Text(
                    'Status de Consentimento',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    consent.status == ConsentStatus.accepted
                        ? 'Ativo (aceite registrado)'
                        : consent.status == ConsentStatus.rejected
                        ? 'Recusado/Revogado'
                        : 'Pendente de resposta',
                  ),
                  trailing: Icon(
                    consent.status == ConsentStatus.accepted
                        ? Icons.check_circle
                        : Icons.cancel,
                    color: consent.status == ConsentStatus.accepted
                        ? Colors.green
                        : Colors.red,
                  ),
                ),
                SwitchListTile(
                  title: const Text('Telemetria de Uso'),
                  subtitle: const Text('Envio de métricas de navegação.'),
                  value: consent.telemetryAccepted,
                  onChanged: (val) {
                    ref
                        .read(privacyNotifierProvider.notifier)
                        .acceptCustom(
                          telemetry: val,
                          sensors: consent.sensorsAccepted,
                        );
                  },
                ),
                SwitchListTile(
                  title: const Text('Sensores do Dispositivo'),
                  subtitle: const Text('Coleta de acelerômetro e movimento.'),
                  value: consent.sensorsAccepted,
                  onChanged: (val) {
                    ref
                        .read(privacyNotifierProvider.notifier)
                        .acceptCustom(
                          telemetry: consent.telemetryAccepted,
                          sensors: val,
                        );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          ListTile(
            key: const Key('btn_revoke_consent'),
            leading: const Icon(Icons.block, color: Colors.orange),
            title: const Text('Revogar Consentimento'),
            subtitle: const Text(
              'Interrompe qualquer coleta e descarta a sessão atual.',
            ),
            onTap: () async {
              await ref.read(privacyNotifierProvider.notifier).revoke();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Consentimento revogado com sucesso.'),
                  ),
                );
              }
            },
          ),
          const Divider(),
          ListTile(
            key: const Key('btn_delete_all_data'),
            leading: const Icon(Icons.delete_forever, color: Colors.red),
            title: const Text('Excluir Dados Locais e Sessão (RF12)'),
            subtitle: const Text(
              'Remove todas as preferências e limpa a sessão ativa.',
            ),
            onTap: () async {
              await ref.read(privacyNotifierProvider.notifier).clearAllData();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Dados locais e sessão excluídos.'),
                  ),
                );
              }
            },
          ),
        ],
      ),
    );
  }
}
