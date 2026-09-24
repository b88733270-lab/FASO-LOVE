import 'package:faso_love/core/constants/app_colors.dart';
import 'package:faso_love/core/network/api_client.dart';
import 'package:flutter/material.dart';

/// Écran « FASO LOVE Premium » — monétisation Mobile Money (Phase 7).
///
/// Parcours : catalogue FCFA → choix offre/portefeuille → demande USSD
/// (sandbox : instructions) → confirmation → Premium activé.
/// Les messages affichés viennent du serveur (français).
class PremiumScreen extends StatefulWidget {
  const PremiumScreen({super.key});

  @override
  State<PremiumScreen> createState() => _PremiumScreenState();
}

class _PremiumScreenState extends State<PremiumScreen> {
  final ApiClient _api = ApiClient.instance;

  List<Map<String, dynamic>> _offres = [];
  Map<String, dynamic>? _monStatut;
  bool _chargement = true;
  String? _erreur;
  String? _codeSelection;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    try {
      final plans = await _api.getJson('/subscriptions/plans');
      final statut = await _api.getJson('/subscriptions/me');
      if (!mounted) return;
      setState(() {
        _offres = (plans['plans'] as List).cast<Map<String, dynamic>>();
        _monStatut = statut;
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

  // ------------------------------------------------------------- achat

  Future<void> _acheter(Map<String, dynamic> offre) async {
    _codeSelection = '${offre['code']}';
    setState(() {});
    try {
      final reponse = await _api.postJson('/subscriptions/checkout', {
        'plan_code': offre['code'],
        'provider': 'mock',
      });
      if (!mounted) return;
      await _dialogPaiement(
        offre,
        reponse['transaction_id'] as String,
        reponse['instructions'] as String,
      );
      await _charger();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) {
        _codeSelection = null;
        setState(() {});
      }
    }
  }

  Future<void> _dialogPaiement(
    Map<String, dynamic> offre,
    String txnId,
    String instructions,
  ) async {
    bool enCours = false;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialog) => AlertDialog(
          title: const Text('Paiement Mobile Money'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Image.asset(
                'assets/placeholders/logo_small.png',
                height: 56,
                errorBuilder: (_, __, ___) => const Icon(Icons.payments, size: 56),
              ),
              const SizedBox(height: 12),
              Text(
                instructions,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: enCours ? null : () => Navigator.of(context).pop(),
              child: const Text('Annuler'),
            ),
            FilledButton(
              onPressed: enCours
                  ? null
                  : () async {
                      setDialog(() => enCours = true);
                      await _confirmerPaiement(context, txnId);
                    },
              child: Text(
                enCours ? 'Vérification…' : 'J\'ai payé (démo)',
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmerPaiement(BuildContext context, String txnId) async {
    try {
      await _api.postJson('/payments/$txnId/simulate', {});
      // Vérification côté serveur du statut final.
      final statut = await _api.getJson('/payments/$txnId');
      if (!context.mounted) return;
      Navigator.of(context).pop(); // ferme le dialogue paiement
      if (statut['status'] == 'succeeded') {
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('🎉 Bienvenue en Premium !'),
            content: const Text(
              'Votre abonnement est actif : likes et super likes illimités. '
              'Merci de soutenir la rencontre au Burkina Faso.',
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
          const SnackBar(
            content: Text('Paiement non confirmé. Réessayez ou contactez le support.'),
          ),
        );
      }
    } on ApiException catch (e) {
      if (!context.mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  // ------------------------------------------------------------------- vue

  String _dateFin(String? iso) {
    final d = DateTime.tryParse(iso ?? '')?.toLocal();
    if (d == null) return '';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('FASO LOVE Premium')),
      body: _corps(),
    );
  }

  Widget _corps() {
    if (_chargement) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_erreur != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_erreur!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: _charger, child: const Text('Réessayer')),
          ],
        ),
      );
    }
    final premium = _monStatut?['is_premium'] == true;
    final quotas = (_monStatut?['quotas'] as Map<String, dynamic>?) ?? const {};
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        if (premium)
          _bandeauPremium()
        else
          _bandeauQuota(quotas),
        const SizedBox(height: 20),
        const Text(
          'Ne laissez plus passer la bonne personne ✨',
          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 6),
        const Text(
          'Paiement Mobile Money (Orange Money · Moov Money) — désactivation à tout moment.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 20),
        for (final offre in _offres) _carteOffre(offre),
        const SizedBox(height: 12),
        Text(
          'Mode DÉMONSTRATION : aucun prélèvement réel. En production, la '
          'demande de paiement arrive directement sur votre téléphone (USSD).',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11, color: Colors.grey[500]),
        ),
      ],
    );
  }

  Widget _bandeauPremium() {
    final fin = _dateFin(_monStatut?['ends_at'] as String?);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.green.shade200),
      ),
      child: Row(
        children: [
          const Icon(Icons.verified, color: Colors.green, size: 34),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Premium actif jusqu\'au $fin.\nMerci de votre confiance !',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bandeauQuota(Map<String, dynamic> quotas) {
    final restants = (quotas['likes_limit'] as int?) != null
        ? (quotas['likes_limit'] as int) - ((quotas['likes_used'] as int?) ?? 0)
        : null;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.orange.shade50,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.orange.shade200),
      ),
      child: Row(
        children: [
          Icon(Icons.timelapse, color: Colors.orange.shade700),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              restants == null
                  ? 'Compte gratuit : quotas quotidiens actifs.'
                  : 'Compte gratuit : il vous reste $restants like(s) aujourd\'hui.',
            ),
          ),
        ],
      ),
    );
  }

  Widget _carteOffre(Map<String, dynamic> offre) {
    final populaire = offre['code'] == 'premium_month';
    final enCours = _codeSelection == offre['code'];
    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: populaire
            ? const BorderSide(color: AppColors.primary, width: 2)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    '${offre['titre']}',
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
                if (populaire)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      'POPULAIRE',
                      style: TextStyle(color: Colors.white, fontSize: 11),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${offre['prix_fcfa']} FCFA · ${offre['duree_jours']} jours',
              style: TextStyle(
                fontSize: 16,
                color: AppColors.primary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            for (final avantage in (offre['avantages'] as List)) ...[
              Row(
                children: [
                  const Icon(Icons.check_circle,
                      size: 16, color: Colors.green),
                  const SizedBox(width: 8),
                  Text('$avantage', style: const TextStyle(fontSize: 14)),
                ],
              ),
              const SizedBox(height: 4),
            ],
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor:
                      populaire ? AppColors.primary : Colors.blueGrey,
                ),
                onPressed: enCours ? null : () => _acheter(offre),
                child: Text(
                  enCours ? 'Traitement…' : 'Choisir cette offre',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
