import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/data/models/admin/admin_models.dart';
import 'package:flutter/material.dart';

import 'stats_pane.dart';

/// Panneau « Signalements » : file de modération avec résolution.
/// Les arnaques et profils de mineur présumés remontent en priorité.
class ReportsPane extends StatefulWidget {
  const ReportsPane({super.key});

  @override
  State<ReportsPane> createState() => _ReportsPaneState();
}

class _ReportsPaneState extends State<ReportsPane> {
  final ApiClient _api = ApiClient.instance;
  List<AdminReport> _rapports = [];
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() => _chargement = true);
    try {
      final liste = await _api.getList('/admin/reports');
      if (!mounted) return;
      setState(() {
        _rapports = liste
            .map((r) => AdminReport.fromJson(r as Map<String, dynamic>))
            .toList()
          ..sort((a, b) {
            // Priorité : arnaques & mineurs d'abord, puis plus récents.
            final prio = (b.estPrioritaire ? 1 : 0) - (a.estPrioritaire ? 1 : 0);
            if (prio != 0) return prio;
            return (b.createdAt ?? DateTime(0))
                .compareTo(a.createdAt ?? DateTime(0));
          });
        _chargement = false;
        _erreur = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _chargement = false;
        _erreur = e.message;
      });
    }
  }

  Future<void> _resoudre(AdminReport r, String resolution) async {
    try {
      await _api.postJson(
        '/admin/reports/${r.id}/resolve',
        {'resolution': resolution},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(resolution == 'resolved'
              ? 'Signalement classé — merci ✅'
              : 'Signalement rejeté.'),
        ),
      );
      _charger();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  String _date(DateTime? d) {
    if (d == null) return '';
    final l = d.toLocal();
    return '${l.day.toString().padLeft(2, '0')}/${l.month.toString().padLeft(2, '0')} '
        '${l.hour.toString().padLeft(2, '0')} h ${l.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AdminTitre(
            titre: 'Signalements',
            sousTitre:
                '${_rapports.length} en attente — 🚨 arnaques et mineurs en tête de file',
          ),
          const SizedBox(height: 16),
          Expanded(child: _corps()),
        ],
      ),
    );
  }

  Widget _corps() {
    if (_chargement) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_erreur != null) {
      return AdminErreur(message: _erreur!, auReessai: _charger);
    }
    if (_rapports.isEmpty) {
      return const Center(
        child: Text('✅ Aucun signalement en attente. Tout est à jour !'),
      );
    }
    return RefreshIndicator(
      onRefresh: _charger,
      child: ListView.separated(
        itemCount: _rapports.length,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          final r = _rapports[index];
          return Card(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: r.estPrioritaire
                  ? BorderSide(color: Colors.red.shade200, width: 1.5)
                  : BorderSide.none,
            ),
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    backgroundColor: r.estPrioritaire
                        ? Colors.red.shade50
                        : Colors.grey.shade100,
                    child: Icon(
                      r.estPrioritaire ? Icons.priority_high : Icons.flag_outlined,
                      color: r.estPrioritaire ? Colors.red : Colors.blueGrey,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 10,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              r.motifLibelle,
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: r.estPrioritaire
                                    ? Colors.red.shade700
                                    : null,
                              ),
                            ),
                            Text(
                              '·  Profil signalé : ${r.reportedName}',
                              style: const TextStyle(color: Colors.black87),
                            ),
                            Text(
                              '·  ${_date(r.createdAt)}',
                              style: const TextStyle(color: Colors.black45),
                            ),
                          ],
                        ),
                        if (r.details.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(r.details,
                              style: const TextStyle(color: Colors.black54)),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    children: [
                      FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: Colors.green.shade600,
                        ),
                        onPressed: () => _resoudre(r, 'resolved'),
                        icon: const Icon(Icons.check, size: 18),
                        label: const Text('Classer'),
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: () => _resoudre(r, 'rejected'),
                        icon: const Icon(Icons.close, size: 18),
                        label: const Text('Rejeter'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
