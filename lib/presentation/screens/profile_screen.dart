import 'package:faso_love/core/config/api_config.dart';
import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/data/providers/auth_session.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

/// Onglet « Profil » : VOTRE profil réel (GET /profiles/me), édition,
/// déconnexion et suppression de compte (droit à l'effacement).
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiClient _api = ApiClient.instance;
  Map<String, dynamic>? _profil;
  bool _chargement = true;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    try {
      final profil = await _api.getJson('/profiles/me');
      if (!mounted) return;
      setState(() {
        _profil = profil;
        _chargement = false;
        _erreur = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _chargement = false;
        _erreur = e.statusCode == 404
            ? 'Profil incomplet : renseignez vos informations.'
            : e.message;
      });
    }
  }

  static const Map<String, String> _genres = {
    'female': 'Femme',
    'male': 'Homme',
  };
  static const Map<String, String> _recherches = {
    'female': 'des femmes',
    'male': 'des hommes',
    'everyone': 'tout le monde',
  };

  Future<void> _editer() async {
    final nomCtrl =
        TextEditingController(text: '${_profil?['display_name'] ?? ''}');
    final bioCtrl = TextEditingController(text: '${_profil?['bio'] ?? ''}');
    final villeCtrl = TextEditingController(text: '${_profil?['city'] ?? ''}');
    final interetsCtrl = TextEditingController(
      text: ((_profil?['interests'] as List?) ?? const []).join(', '),
    );
    String recherche = '${_profil?['looking_for'] ?? 'everyone'}';
    String genre = '${_profil?['gender'] ?? 'female'}';
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialog) => AlertDialog(
          title: const Text('Modifier mon profil'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nomCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Prénom affiché',
                    hintText: 'Kadiatou',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: genre,
                  decoration: const InputDecoration(
                    labelText: 'Je suis',
                    border: OutlineInputBorder(),
                  ),
                  items: _genres.entries
                      .map((e) =>
                          DropdownMenuItem(value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) => setDialog(() => genre = v!),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: recherche,
                  decoration: const InputDecoration(
                    labelText: 'Je recherche',
                    border: OutlineInputBorder(),
                  ),
                  items: _recherches.entries
                      .map((e) =>
                          DropdownMenuItem(value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) => setDialog(() => recherche = v!),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: bioCtrl,
                  maxLines: 3,
                  decoration: const InputDecoration(
                    labelText: 'À propos de moi',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: villeCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Ville',
                    hintText: 'Ouagadougou',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: interetsCtrl,
                  decoration: const InputDecoration(
                    labelText:
                        'Centres d\'intérêt (séparés par des virgules)',
                    hintText: 'Cuisine, Voyage, Musique',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Annuler'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Enregistrer'),
            ),
          ],
        ),
      ),
    );
    if (ok != true) return;
    if (nomCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Le prénom affiché est obligatoire.')),
      );
      return;
    }
    try {
      final corps = <String, dynamic>{
        'display_name': nomCtrl.text.trim(),
        'gender': genre,
        'looking_for': recherche,
        'bio': bioCtrl.text.trim(),
        'city': villeCtrl.text.trim(),
        'interests': interetsCtrl.text
            .split(',')
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList(),
      };
      // Ne jamais effacer la géolocalisation existante à l'édition.
      if (_profil?['latitude'] != null) {
        corps['latitude'] = _profil!['latitude'];
        corps['longitude'] = _profil!['longitude'];
      }
      await _api.putJson('/profiles/me', corps);
      await _charger();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profil mis à jour ✅')),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _supprimerCompte() async {
    final confirme = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Supprimer mon compte ?'),
        content: const Text(
          'Cette action est DÉFINITIVE : vos photos, matchs et messages '
          'seront effacés de nos serveurs.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Supprimer définitivement'),
          ),
        ],
      ),
    );
    if (confirme != true || !mounted) return;
    try {
      await _api.deleteJson('/users/me');
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
      return;
    }
    if (!mounted) return;
    await context.read<AuthSession>().seDeconnecter();
  }

  @override
  Widget build(BuildContext context) {
    final profil = _profil;
    final session = context.read<AuthSession>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profil'),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Se déconnecter',
            onPressed: () => session.seDeconnecter(),
          ),
        ],
      ),
      body: _chargement
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _charger,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_erreur != null) ...[
                    Text(_erreur!, textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                  ],
                  if (profil == null)
                    FilledButton.icon(
                      onPressed: editerVide,
                      icon: const Icon(Icons.edit),
                      label: const Text('Créer mon profil'),
                    )
                  else ...[
                    _enTete(profil),
                    const SizedBox(height: 16),
                    _section('À propos de moi', '${profil['bio']}'),
                    _chipsInterets((profil['interests'] as List? ?? const [])
                        .cast<String>()),
                    _photos(profil),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.location_city,
                          color: AppColors.primary),
                      title: const Text('Ville'),
                      subtitle: Text('${profil['city']} · ${_recherches[profil['looking_for']] ?? profil['looking_for']}'),
                    ),
                  ],
                  const Divider(height: 32),
                  _bouton(
                    icon: Icons.edit,
                    texte: profil == null
                        ? 'Créer mon profil'
                        : 'Modifier mon profil',
                    auChoix: _editer,
                  ),
                  _bouton(
                    icon: Icons.star_outline,
                    texte: 'FASO LOVE Premium',
                    auChoix: () => ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Bientôt disponible — paiement Mobile Money (Orange Money, Moov Money).',
                        ),
                      ),
                    ),
                  ),
                  _bouton(
                    icon: Icons.logout,
                    texte: 'Se déconnecter',
                    auChoix: () => context.read<AuthSession>().seDeconnecter(),
                  ),
                  _bouton(
                    icon: Icons.delete_forever,
                    texte: 'Supprimer mon compte',
                    danger: true,
                    auChoix: _supprimerCompte,
                  ),
                ],
              ),
            ),
    );
  }

  /// Création initiale si l'utilisateur n'a pas encore de profil.
  void editerVide() {
    setState(() {
      _profil = {
        'bio': '',
        'city': 'Ouagadougou',
        'interests': const [],
        'looking_for': 'everyone',
      };
    });
    _editer().then((_) {
      if (mounted && _profil != null && _profil!.isEmpty) {
        setState(() => _profil = null);
      }
      _charger();
    });
  }

  Widget _enTete(Map<String, dynamic> profil) {
    final photos = (profil['photos'] as List?) ?? const [];
    final photo =
        photos.isNotEmpty ? ApiConfig.absolute('${photos.first['url']}') : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CircleAvatar(
          radius: 48,
          backgroundImage:
              photo == null ? null : NetworkImage(photo),
          child: photo == null ? const Icon(Icons.person, size: 48) : null,
        ),
        const SizedBox(height: 12),
        Text(
          '${profil['display_name']}, ${profil['age']}',
          style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
        ),
        Text(
          '${_genres[profil['gender']] ?? profil['gender']} · ${profil['city']}',
          style: const TextStyle(color: Colors.black54),
        ),
        if (photos.any((p) => p['status'] == 'pending'))
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text(
              '🕐 Une ou plusieurs photos sont en cours de validation.',
              style: TextStyle(fontSize: 12, color: Colors.orange),
            ),
          ),
      ],
    );
  }

  Widget _section(String titre, String contenu) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(titre,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Text(contenu, style: const TextStyle(fontSize: 16)),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _chipsInterets(List<String> interets) {
    if (interets.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Centres d\'intérêt',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: interets
              .map((t) => Chip(
                    label: Text(t),
                    backgroundColor: AppColors.primary.withOpacity(0.1),
                    labelStyle: const TextStyle(color: AppColors.primary),
                  ))
              .toList(),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _photos(Map<String, dynamic> profil) {
    final photos = (profil['photos'] as List?) ?? const [];
    if (photos.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Mes photos',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        SizedBox(
          height: 110,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: photos.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (context, i) {
              final p = photos[i] as Map<String, dynamic>;
              return ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Image.network(
                  ApiConfig.absolute('${p['url']}'),
                  width: 90,
                  height: 110,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    width: 90,
                    height: 110,
                    color: Colors.grey[300],
                    child: const Icon(Icons.broken_image),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _bouton({
    required IconData icon,
    required String texte,
    required VoidCallback auChoix,
    bool danger = false,
  }) {
    return ListTile(
      leading: Icon(icon, color: danger ? Colors.red : AppColors.primary),
      title: Text(
        texte,
        style: TextStyle(color: danger ? Colors.red : null),
      ),
      trailing: const Icon(Icons.chevron_right),
      onTap: auChoix,
    );
  }
}
