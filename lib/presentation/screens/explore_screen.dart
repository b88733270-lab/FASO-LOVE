import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/constants/assets_path.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:faso_love/core/utils/helpers/profile_image.dart';
import 'package:faso_love/data/models/users/user_model.dart';
import 'package:flutter/material.dart';

/// Onglet « Explorer » : grille de profils autour de l'utilisateur —
/// données réelles (`GET /discover`), repli hors-ligne sur la maquette
/// locale (aucune photo de personne réelle).
class ExploreScreen extends StatelessWidget {
  const ExploreScreen({super.key});

  /// Charge la file via l'API ; repli maquette si le serveur est injoignable.
  Future<List<User>> _charger() async {
    try {
      final liste = await ApiClient.instance.getList('/discover?limit=40');
      final cartes = liste
          .map((c) => User.fromDiscoverJson(c as Map<String, dynamic>))
          .toList();
      if (cartes.isNotEmpty) return cartes;
    } catch (_) {
      // API indisponible → démo hors-ligne.
    }
    return _generateMockUsers();
  }

  /// Like depuis la fiche : si l'autre a déjà liké → MATCH.
  Future<void> _aimer(BuildContext context, User user) async {
    try {
      final reponse = await ApiClient.instance.postJson(
        '/discover/react',
        {'target_user_id': user.id, 'action': 'like'},
      );
      if (!context.mounted) return;
      if (reponse['matched'] == true) {
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('🎉 C\'est un match !'),
            content: Text(
              '${user.name} vous aime aussi !\nRetrouvez votre conversation dans l\'onglet Matchs.',
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Super !'),
              ),
            ],
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${user.name} recevra votre like ❤️')),
        );
      }
    } on ApiException catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<User>>(
      future: _charger(),
      builder: (context, snapshot) {
        final exploreUsers = snapshot.data ?? const <User>[];
        final chargement =
            snapshot.connectionState != ConnectionState.done;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Explorer autour de moi'),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            tooltip: 'Filtres',
            onPressed: () => _showFilters(context),
          ),
        ],
      ),
      body: chargement
          ? const Center(child: CircularProgressIndicator())
          : exploreUsers.isEmpty
          ? _buildEmptyState()
          : CustomScrollView(
              physics: const BouncingScrollPhysics(),
              slivers: [
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  sliver: SliverGrid(
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 16,
                      mainAxisSpacing: 16,
                      childAspectRatio: 0.7,
                    ),
                    delegate: SliverChildBuilderDelegate(
                      (context, index) =>
                          _buildExploreCard(context, exploreUsers[index]),
                      childCount: exploreUsers.length,
                    ),
                  ),
                ),
              ],
            ),
        );
      },
    );
  }

  /// Profils de démonstration (avatars génériques locaux, distances en km).
  /// TODO(phase-3) : supprimer au profit des données API.
  List<User> _generateMockUsers() {
    return [
      User(
        id: '1',
        name: 'Kadiatou',
        age: 26,
        photoUrl: AssetsPath.avatar1,
        bio: 'Couturière | Faso Dan Fani',
        distance: 2.5,
        interests: const ['Mode', 'Cuisine', 'Voyage'],
      ),
      User(
        id: '2',
        name: 'Idrissa',
        age: 29,
        photoUrl: AssetsPath.avatar2,
        bio: 'Informaticien | Mélomane',
        distance: 3.1,
        interests: const ['Tech', 'Football', 'Photo'],
      ),
      User(
        id: '3',
        name: 'Mariam',
        age: 24,
        photoUrl: AssetsPath.avatar3,
        bio: 'Étudiante en médecine | Danse',
        distance: 1.2,
        interests: const ['Lecture', 'Danse', 'Musique'],
      ),
      User(
        id: '4',
        name: 'Abdoulaye',
        age: 31,
        photoUrl: AssetsPath.avatar4,
        bio: 'Chef cuisinier | Voyageur',
        distance: 4.7,
        interests: const ['Cuisine', 'Voyage', 'Cinéma'],
      ),
      User(
        id: '5',
        name: 'Awa',
        age: 27,
        photoUrl: AssetsPath.avatar5,
        bio: 'Coach sportive | Bien-être',
        distance: 0.8,
        interests: const ['Sport', 'Nature', 'Santé'],
      ),
      User(
        id: '6',
        name: 'Moussa',
        age: 30,
        photoUrl: AssetsPath.avatar6,
        bio: 'Entrepreneur | Cinéphile',
        distance: 5.3,
        interests: const ['Cinéma', 'Théâtre', 'Langues'],
      ),
    ];
  }

  Widget _buildExploreCard(BuildContext context, User user) {
    return GestureDetector(
      onTap: () => _showProfileDetail(context, user),
      child: Card(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        elevation: 2,
        clipBehavior: Clip.antiAlias,
        child: Stack(
          children: [
            Hero(
              tag: 'explore-${user.id}',
              child: Image(
                image: profileImageProvider(user.photoUrl),
                fit: BoxFit.cover,
                height: double.infinity,
                width: double.infinity,
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return Container(
                    color: Colors.grey[200],
                    child: Center(
                      child: CircularProgressIndicator(
                        value: loadingProgress.expectedTotalBytes != null
                            ? loadingProgress.cumulativeBytesLoaded /
                                loadingProgress.expectedTotalBytes!
                            : null,
                      ),
                    ),
                  );
                },
                errorBuilder: (context, error, stackTrace) => Container(
                  color: Colors.grey[200],
                  child: const Center(
                    child: Icon(Icons.error, color: Colors.grey),
                  ),
                ),
              ),
            ),
            Positioned(
              top: 8,
              right: 8,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.location_on,
                        size: 14, color: Colors.white),
                    const SizedBox(width: 4),
                    Text(
                      '${user.distance.toStringAsFixed(1)} km',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      Colors.black.withOpacity(0.9),
                      Colors.transparent,
                    ],
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${user.name}, ${user.age}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      user.bio,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.9),
                        fontSize: 14,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 8),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: user.interests
                            .map((interest) => Container(
                                  margin: const EdgeInsets.only(right: 6),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.primary.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: AppColors.primary.withOpacity(0.5),
                                      width: 1,
                                    ),
                                  ),
                                  child: Text(
                                    interest,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 10,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ))
                            .toList(),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.explore_off,
            size: 60,
            color: Colors.grey[300],
          ),
          const SizedBox(height: 16),
          Text(
            'Aucun profil trouvé',
            style: TextStyle(
              fontSize: 20,
              color: Colors.grey[600],
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40),
            child: Text(
              'Ajustez vos filtres ou revenez plus tard pour découvrir de nouveaux profils près de chez vous',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey[500],
              ),
            ),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: () {
              // TODO(phase-3) : recharger la file depuis l'API.
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
            child: const Text(
              'Actualiser',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  /// Panneau de filtres — maquette visuelle uniquement.
  /// TODO(phase-3) : filtres réels (âge, distance, centres d'intérêt).
  void _showFilters(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Container(
          padding: const EdgeInsets.all(16),
          height: MediaQuery.of(context).size.height * 0.8,
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Filtres',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const Divider(),
              Expanded(
                child: ListView(
                  children: [
                    _buildFilterSection(
                      title: 'Distance',
                      child: Column(
                        children: [
                          Slider(
                            value: 10,
                            min: 1,
                            max: 100,
                            divisions: 99,
                            label: '10 km',
                            onChanged: (value) {},
                          ),
                          const SizedBox(height: 8),
                          const Text('Dans un rayon de 10 km'),
                        ],
                      ),
                    ),
                    _buildFilterSection(
                      title: 'Tranche d’âge',
                      child: RangeSlider(
                        values: const RangeValues(18, 35),
                        min: 18,
                        max: 60,
                        divisions: 42,
                        labels: const RangeLabels('18', '35'),
                        onChanged: (values) {},
                      ),
                    ),
                    _buildFilterSection(
                      title: 'Centres d’intérêt',
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          'Cuisine',
                          'Musique',
                          'Football',
                          'Voyage',
                          'Danse',
                          'Tech',
                          'Sport',
                          'Lecture'
                        ]
                            .map((interest) => FilterChip(
                                  label: Text(interest),
                                  selected: false,
                                  onSelected: (selected) {},
                                ))
                            .toList(),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text(
                    'Appliquer les filtres',
                    style: TextStyle(fontSize: 16),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildFilterSection({required String title, required Widget child}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }

  /// Fiche détaillée d'un profil (bottom sheet).
  void _showProfileDetail(BuildContext context, User user) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.85,
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      Hero(
                        tag: 'explore-${user.id}',
                        child: ClipRRect(
                          borderRadius: const BorderRadius.vertical(
                              top: Radius.circular(20)),
                          child: Image(
                            image: profileImageProvider(user.photoUrl),
                            width: double.infinity,
                            height: 400,
                            fit: BoxFit.cover,
                          ),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  '${user.name}, ${user.age}',
                                  style: const TextStyle(
                                    fontSize: 28,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(Icons.favorite_border),
                                  tooltip: 'Aimer',
                                  onPressed: () => _aimer(context, user),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                const Icon(Icons.location_on,
                                    size: 16, color: Colors.grey),
                                const SizedBox(width: 4),
                                Text(
                                  'À ${user.distance.toStringAsFixed(1)} km',
                                  style: const TextStyle(color: Colors.grey),
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'À propos',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              user.bio,
                              style: const TextStyle(fontSize: 16),
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'Centres d’intérêt',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: user.interests
                                  .map((interest) => Chip(
                                        label: Text(interest),
                                        backgroundColor:
                                            AppColors.primary.withOpacity(0.1),
                                        labelStyle: const TextStyle(
                                            color: AppColors.primary),
                                      ))
                                  .toList(),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(context),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          side: const BorderSide(color: AppColors.primary),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: const Text(
                          'Fermer',
                          style: TextStyle(color: AppColors.primary),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          Navigator.pop(context); // ferme la fiche
                          _aimer(context, user);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: const Text(
                          'Aimer ❤️',
                          style: TextStyle(color: Colors.white),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
