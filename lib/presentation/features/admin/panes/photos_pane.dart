import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/data/models/admin/admin_models.dart';
import 'package:flutter/material.dart';

import 'stats_pane.dart';

/// Panneau « Modération photos » : file des uploads en attente
/// (GET /admin/photos?status=pending) avec approbation/rejet.
///
/// Règle produit : une photo non approuvée n'est jamais affichée dans la
/// découverte — rejeter une photo sans photo approuvée restante retire le
/// profil de la file de rencontre (règles côté serveur).
class PhotosPane extends StatefulWidget {
  const PhotosPane({super.key});

  @override
  State<PhotosPane> createState() => _PhotosPaneState();
}

class _PhotosPaneState extends State<PhotosPane> {
  final ApiClient _api = ApiClient.instance;
  List<AdminPhoto> _photos = [];
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
      final liste = await _api.getList('/admin/photos?status_filter=pending');
      if (!mounted) return;
      setState(() {
        _photos = liste
            .map((p) => AdminPhoto.fromJson(p as Map<String, dynamic>))
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

  Future<void> _moderer(AdminPhoto p, String action) async {
    try {
      await _api.postJson(
        '/admin/photos/${p.id}/moderate',
        {'action': action},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(action == 'approve'
              ? 'Photo approuvée ✅'
              : 'Photo rejetée ❌'),
        ),
      );
      _charger();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AdminTitre(
            titre: 'Modération des photos',
            sousTitre:
                '${_photos.length} photo(s) en attente — validez rapidement pour ne pas bloquer les profils',
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
    if (_photos.isEmpty) {
      return const Center(
        child: Text('✅ Aucune photo en attente de validation.'),
      );
    }
    return RefreshIndicator(
      onRefresh: _charger,
      child: GridView.builder(
        gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 280,
          mainAxisExtent: 340,
          crossAxisSpacing: 20,
          mainAxisSpacing: 20,
        ),
        itemCount: _photos.length,
        itemBuilder: (context, index) {
          final p = _photos[index];
          return Card(
            elevation: 0,
            clipBehavior: Clip.antiAlias,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: Image.network(
                    p.urlAbsolue,
                    fit: BoxFit.cover,
                    loadingBuilder: (context, child, progress) {
                      if (progress == null) return child;
                      return const Center(child: CircularProgressIndicator());
                    },
                    errorBuilder: (_, __, ___) => Container(
                      color: Colors.grey.shade200,
                      child: const Center(
                        child: Icon(Icons.broken_image, size: 42),
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.green.shade600,
                          ),
                          onPressed: () => _moderer(p, 'approve'),
                          icon: const Icon(Icons.check, size: 18),
                          label: const Text('Approuver'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.red,
                          ),
                          onPressed: () => _moderer(p, 'reject'),
                          icon: const Icon(Icons.close, size: 18),
                          label: const Text('Rejeter'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
