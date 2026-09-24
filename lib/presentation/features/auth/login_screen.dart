import 'package:faso_love/data/providers/auth_session.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

/// Écran de connexion FASO LOVE : numéro +226 → code SMS → (premier compte)
/// date de naissance avec règle 18+ vérifiée côté SERVEUR.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _numeroCtrl = TextEditingController(text: '+226');
  final _codeCtrl = TextEditingController();
  final _naissanceCtrl = TextEditingController();

  @override
  void dispose() {
    _numeroCtrl.dispose();
    _codeCtrl.dispose();
    _naissanceCtrl.dispose();
    super.dispose();
  }

  Future<void> _choisirNaissance(AuthSession session) async {
    final aujourdHui = DateTime.now();
    final choix = await showDatePicker(
      context: context,
      initialDate: DateTime(aujourdHui.year - 25),
      firstDate: DateTime(1920),
      lastDate: aujourdHui,
      locale: const Locale('fr'),
      helpText: 'Votre date de naissance',
      confirmText: 'Valider',
    );
    if (choix == null) return;
    final iso =
        '${choix.year}-${choix.month.toString().padLeft(2, '0')}-${choix.day.toString().padLeft(2, '0')}';
    _naissanceCtrl.text = iso;
    await session.confirmerNaissance(iso);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<AuthSession>();

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.favorite, size: 72, color: Color(0xFF0FA958)),
                  const SizedBox(height: 12),
                  const Text(
                    'FASO LOVE',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 30, fontWeight: FontWeight.bold),
                  ),
                  const Text(
                    'L\'' 'amour au pays des Hommes intègres 🇧🇫',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.black54),
                  ),
                  const SizedBox(height: 32),
                  if (session.etape == 'saisie_numero') ..._etapeNumero(session),
                  if (session.etape == 'saisie_code') ..._etapeCode(session),
                  if (session.etape == 'saisie_naissance') ..._etapeNaissance(session),
                  if (session.erreur != null) ...[
                    const SizedBox(height: 16),
                    Text(
                      session.erreur!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ],
                  const SizedBox(height: 24),
                  const Text(
                    'Réservé aux personnes MAJEURES (18 ans et plus).\n'
                    'En vous connectant, vous acceptez nos conditions.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 12, color: Colors.black45),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _etapeNumero(AuthSession session) => [
        TextField(
          controller: _numeroCtrl,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(
            labelText: 'Votre numéro de téléphone',
            hintText: '+226 70 12 34 56',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.phone),
          ),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: session.occupe
              ? null
              : () => session.demanderCode(_numeroCtrl.text),
          icon: session.occupe
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.sms),
          label: const Text('Recevoir mon code par SMS'),
        ),
      ];

  List<Widget> _etapeCode(AuthSession session) {
    final codeDev = session.codeDev;
    return [
      Text(
        'Code envoyé au ${session.telephone}',
        textAlign: TextAlign.center,
      ),
      if (codeDev != null) ...[
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.amber.shade100,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            'MODE DÉMO — votre code : $codeDev',
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ],
      const SizedBox(height: 16),
      TextField(
        controller: _codeCtrl,
        keyboardType: TextInputType.number,
        maxLength: 6,
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 24, letterSpacing: 8),
        decoration: const InputDecoration(
          labelText: 'Code à 6 chiffres',
          border: OutlineInputBorder(),
          counterText: '',
        ),
        onChanged: (v) {
          if (v.length == 6) session.verifierCode(v);
        },
      ),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: session.occupe
            ? null
            : () => session.verifierCode(_codeCtrl.text),
        child: const Text('Vérifier'),
      ),
      TextButton(
        onPressed: session.retourNumero,
        child: const Text('Modifier mon numéro'),
      ),
    ];
  }

  List<Widget> _etapeNaissance(AuthSession session) => [
        const Text(
          'Première connexion : votre date de naissance\n'
          '(règle stricte : 18 ans minimum).',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _naissanceCtrl,
          readOnly: true,
          decoration: InputDecoration(
            labelText: 'Date de naissance',
            hintText: 'AAAA-MM-JJ',
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.cake),
            suffixIcon: IconButton(
              icon: const Icon(Icons.calendar_month),
              onPressed: () => _choisirNaissance(session),
            ),
          ),
        ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed:
              session.occupe ? null : () => _choisirNaissance(session),
          child: const Text('Continuer'),
        ),
      ];
}
