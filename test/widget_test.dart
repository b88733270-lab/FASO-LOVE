// Tests de widgets FASO LOVE — démarrage de l'application.
//
// Le test « compteur » généré par `flutter create` (et qui était en échec
// car il testait un compteur inexistant) a été remplacé par ce test de fumée.

import 'package:faso_love/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets(
    'Demarrage : titre FASO LOVE, 4 onglets et navigation vers Matchs',
    (WidgetTester tester) async {
      await tester.pumpWidget(const FasoLoveApp());

      // Laisse s'écouler le chargement simulé des profils (1 s dans
      // MatchService) puis reconstruit l'arbre de widgets.
      await tester.pump(const Duration(milliseconds: 1200));
      await tester.pump();

      // L'onglet Découvrir affiche le titre de l'app.
      expect(find.text('FASO LOVE'), findsOneWidget);

      // Les 4 onglets de navigation sont présents.
      expect(find.text('Découvrir'), findsOneWidget);
      expect(find.text('Matchs'), findsOneWidget);
      expect(find.text('Explorer'), findsOneWidget);
      expect(find.text('Profil'), findsOneWidget);

      // Navigation vers l'onglet Matchs (état vide pour l'instant).
      await tester.tap(find.text('Matchs'));
      await tester.pump();
      expect(find.text('Aucun match pour le moment'), findsOneWidget);
    },
  );
}
