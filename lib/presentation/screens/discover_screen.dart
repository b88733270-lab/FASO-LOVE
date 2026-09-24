import 'package:faso_love/data/models/users/user_model.dart';
import 'package:faso_love/data/providers/discover_provider.dart';
import 'package:faso_love/presentation/features/discover/action_button.dart';
import 'package:faso_love/presentation/features/discover/profile_card.dart';
import 'package:faso_love/presentation/features/premium/premium_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

/// Onglet « Découvrir » : file de profils réels à swiper
/// (like / passer / coup de cœur), branchée sur l'API FASO LOVE.
class DiscoverScreen extends StatelessWidget {
  const DiscoverScreen({super.key});

  /// Fenêtre « C'est un match ! » 🎉
  void _annoncerMatch(BuildContext context, User pair) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('🎉 C\'est un match !'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(
              radius: 40,
              backgroundImage:
                  pair.photoUrl.isEmpty ? null : NetworkImage(pair.photoUrl),
              child: pair.photoUrl.isEmpty
                  ? const Icon(Icons.person, size: 40)
                  : null,
            ),
            const SizedBox(height: 12),
            Text(
              '${pair.name} vous aime aussi !',
              textAlign: TextAlign.center,
            ),
            const Text(
              'Retrouvez votre conversation dans l\'onglet Matchs.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: Colors.black54),
            ),
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Continuer'),
          ),
        ],
      ),
    );
  }

  /// Invitation Premium quand le quota freemium est atteint (403 serveur).
  void _proposerPremium(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('⭐ Quota du jour atteint'),
        content: const Text(
          'Vous avez utilisé tous vos likes gratuits de la journée.\n'
          'Avec FASO LOVE Premium, aimez sans limites !',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Plus tard'),
          ),
          FilledButton.icon(
            onPressed: () {
              Navigator.of(context).pop();
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const PremiumScreen()),
              );
            },
            icon: const Icon(Icons.star),
            label: const Text('Découvrir Premium'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => DiscoverProvider()
        ..onMatch = (pair) => _annoncerMatch(context, pair)
        ..onQuotaAtteint = () => _proposerPremium(context),
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('FASO LOVE'),
          actions: [
            Consumer<DiscoverProvider>(
              builder: (context, provider, _) => IconButton(
                icon: const Icon(Icons.refresh),
                tooltip: 'Rafraîchir',
                onPressed: provider.recharger,
              ),
            ),
          ],
        ),
        body: Consumer<DiscoverProvider>(
          builder: (context, provider, _) {
            if (provider.isLoading) {
              return const Center(child: CircularProgressIndicator());
            }

            if (provider.users.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.explore,
                          size: 60, color: Colors.grey[300]),
                      const SizedBox(height: 12),
                      Text(
                        provider.erreur ??
                            'Plus de profils à découvrir pour le moment',
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      TextButton.icon(
                        onPressed: provider.recharger,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Recharger'),
                      ),
                      if (provider.erreur != null &&
                          provider.erreur!.contains('photo'))
                        const Padding(
                          padding: EdgeInsets.only(top: 12),
                          child: Text(
                            'Astuce : ajoutez une photo dans l\'onglet Profil pour apparaître dans les recherches.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 12, color: Colors.black45),
                          ),
                        ),
                    ],
                  ),
                ),
              );
            }

            return Column(
              children: [
                if (provider.horsLigne)
                  Container(
                    width: double.infinity,
                    color: Colors.orange.shade100,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    child: const Text(
                      'Mode démo hors-ligne : profils d\'exemple locaux.',
                      style: TextStyle(fontSize: 12),
                      textAlign: TextAlign.center,
                    ),
                  ),
                Expanded(
                  child: GestureDetector(
                    onHorizontalDragEnd: (details) {
                      if (details.primaryVelocity! > 0) {
                        provider.swipeRight();
                      } else if (details.primaryVelocity! < 0) {
                        provider.swipeLeft();
                      }
                    },
                    child: PageView.builder(
                      controller: provider.pageController,
                      itemCount: provider.users.length,
                      onPageChanged: provider.onPageChanged,
                      itemBuilder: (context, index) {
                        return ProfileCard(user: provider.users[index]);
                      },
                    ),
                  ),
                ),
                ActionButtons(
                  onSwipeLeft: provider.swipeLeft,
                  onSwipeRight: provider.swipeRight,
                  onSuperLike: provider.superLike,
                ),
                const SizedBox(height: 20),
              ],
            );
          },
        ),
      ),
    );
  }
}
