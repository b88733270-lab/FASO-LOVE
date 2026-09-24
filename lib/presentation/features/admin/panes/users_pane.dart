import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/data/models/admin/admin_models.dart';
import 'package:flutter/material.dart';

import 'stats_pane.dart';

/// Panneau « Utilisateurs » : recherche par téléphone/prénom,
/// activation/désactivation (coupure immédiate de l'accès API).
class UsersPane extends StatefulWidget {
  const UsersPane({super.key});

  @override
  State<UsersPane> createState() => _UsersPaneState();
}

class _UsersPaneState extends State<UsersPane> {
  final ApiClient _api = ApiClient.instance;
  final TextEditingController _recherche = TextEditingController();
  List<AdminUser> _utilisateurs = [];
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  @override
  void dispose() {
    _recherche.dispose();
    super.dispose();
  }

  Future<void> _charger({String? q}) async {
    setState(() => _chargement = true);
    try {
      final chemin = (q == null || q.isEmpty)
          ? '/admin/users?limit=50'
          : '/admin/users?limit=50&q=${Uri.encodeQueryComponent(q)}';
      final liste = await _api.getList(chemin);
      if (!mounted) return;
      setState(() {
        _utilisateurs = liste
            .map((u) => AdminUser.fromJson(u as Map<String, dynamic>))
            .toList();
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

  Future<void> _basculerActif(AdminUser u) async {
    final nouvelEtat = !u.isActive;
    if (!nouvelEtat) {
      final confirme = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('Désactiver ${u.displayName} ?'),
          content: const Text(
            'Le compte perdra immédiatement l\'accès à l\'application '
            '(jetons rejetés par l\'API). Action réversible.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Annuler'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Désactiver'),
            ),
          ],
        ),
      );
      if (confirme != true) return;
    }
    try {
      await _api.patchJson(
        '/admin/users/${u.id}',
        {'is_active': nouvelEtat},
      );
      _charger(q: _recherche.text.trim());
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  String _date(DateTime? d) {
    if (d == null) return '—';
    final l = d.toLocal();
    return '${l.day.toString().padLeft(2, '0')}/${l.month.toString().padLeft(2, '0')}/${l.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AdminTitre(
            titre: 'Utilisateurs',
            sousTitre: '${_utilisateurs.length} comptes affichés',
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              SizedBox(
                width: 320,
                child: TextField(
                  controller: _recherche,
                  decoration: InputDecoration(
                    hintText: 'Rechercher (téléphone, prénom)…',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    isDense: true,
                  ),
                  onSubmitted: (v) => _charger(q: v.trim()),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: () => _charger(q: _recherche.text.trim()),
                icon: const Icon(Icons.search),
                label: const Text('Rechercher'),
              ),
              TextButton.icon(
                onPressed: () {
                  _recherche.clear();
                  _charger();
                },
                icon: const Icon(Icons.clear),
                label: const Text('Réinitialiser'),
              ),
            ],
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
      return AdminErreur(message: _erreur!, auReessai: () => _charger());
    }
    if (_utilisateurs.isEmpty) {
      return const Center(child: Text('Aucun utilisateur trouvé.'));
    }
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: SingleChildScrollView(
        child: SizedBox(
          width: double.infinity,
          child: DataTable(
            columns: const [
              DataColumn(label: Text('Prénom')),
              DataColumn(label: Text('Téléphone')),
              DataColumn(label: Text('Âge')),
              DataColumn(label: Text('Ville')),
              DataColumn(label: Text('Rôle')),
              DataColumn(label: Text('Depuis')),
              DataColumn(label: Text('Statut')),
              DataColumn(label: Text('Action')),
            ],
            rows: [
              for (final u in _utilisateurs)
                DataRow(
                  cells: [
                    DataCell(Text(u.displayName,
                        style:
                            const TextStyle(fontWeight: FontWeight.w600))),
                    DataCell(Text(u.phone)),
                    DataCell(Text(u.age == null ? '—' : '${u.age}')),
                    DataCell(Text(u.city.isEmpty ? '—' : u.city)),
                    DataCell(
                      u.role == 'admin'
                          ? const Chip(
                              label: Text('admin'),
                              backgroundColor: Color(0x1A0FA958),
                              labelStyle: TextStyle(
                                  color: Color(0xFF0FA958),
                                  fontWeight: FontWeight.bold),
                            )
                          : const Text('utilisateur'),
                    ),
                    DataCell(Text(_date(u.createdAt))),
                    DataCell(
                      Chip(
                        label: Text(u.isActive ? 'actif' : 'désactivé'),
                        backgroundColor: u.isActive
                            ? Colors.green.shade50
                            : Colors.red.shade50,
                        labelStyle: TextStyle(
                          color:
                              u.isActive ? Colors.green.shade800 : Colors.red,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    DataCell(
                      u.role == 'admin'
                          ? const Text('—')
                          : TextButton.icon(
                              onPressed: () => _basculerActif(u),
                              icon: Icon(
                                u.isActive
                                    ? Icons.block
                                    : Icons.check_circle_outline,
                                size: 18,
                                color: u.isActive ? Colors.red : Colors.green,
                              ),
                              label: Text(
                                u.isActive ? 'Désactiver' : 'Réactiver',
                                style: TextStyle(
                                  color:
                                      u.isActive ? Colors.red : Colors.green,
                                ),
                              ),
                            ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
