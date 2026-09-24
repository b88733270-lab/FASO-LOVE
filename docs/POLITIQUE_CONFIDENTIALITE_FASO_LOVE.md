# Politique de confidentialité — FASO LOVE

> ⚠️ **Document de travail — brouillon juridique.**
> À faire valider par un juriste connaissant la loi burkinabè sur la
> protection des données (loi n° 010-2017/AN créant la CIL, et textes
> connexes) avant mise en production. Version 0.1, 24 septembre 2025.

## 1. Responsable du traitement

L'Éditeur de FASO LOVE (identité et coordonnées à compléter avant
publication) est responsable du traitement des données personnelles
collectées via l'application et l'API FASO LOVE.

## 2. Données collectées

| Donnée | Finalité | Base / note |
| --- | --- | --- |
| Numéro de téléphone (+226) | Authentification OTP, sécurité | Obligatoire |
| Date de naissance | Application stricte de la règle **18+** (vérifiée côté serveur) | Obligatoire ; l'âge est affiché, la date complète JAMAIS |
| Profil (prénom affiché, genre, orientation, bio, ville, centres d'intérêt) | Fonctionnement du matching | Obligatoire |
| Photos | Profil public | Modérées (statut pending/approved/rejected) ; EXIF/GPS automatiquement **supprimés** à l'upload ; redimensionnées à 1600 px max |
| Localisation (latitude/longitude) | Tri par proximité (km) | **Optionnelle (opt-in)** ; jamais divulguée aux autres utilisateurs : seule la distance calculée est affichée |
| Messages (contenu, accusés de lecture) | Messagerie entre matchs | Chiffrés en transit (HTTPS) ; stockés chiffrés au repos en production |
| Signalements, blocages | Sécurité, modération, prévention des arnaques | Conservés à titre probatoire |
| Journaux techniques (IP, requêtes) | Sécurité, anti-abus, débogage | Durée courte (objectif ≤ 12 mois) |

**Données sensibles :** l'orientation de rencontre déclarée n'est jamais
affichée publiquement ni partagée ; elle sert uniquement au filtrage
réciproque des profils.

## 3. Ce que les autres utilisateurs voient

- Prénom affiché, âge, genre, ville, bio, centres d'intérêt, photos.
- Distance approximative en kilomètres (jamais la position exacte).
- **Jamais** : numéro de téléphone, date de naissance, coordonnées
  exactes.

## 4. Partage avec des tiers

- **Fournisseur SMS** : le numéro de téléphone est transmis pour envoyer
  les codes OTP (code de vérification uniquement).
- Pas de vente, pas de ciblage publicitaire, pas de partage commercial.
- Forces de l'ordre / autorités burkinabè : uniquement sur réquisition
  légale ou en cas de danger grave (ex. signalement de mineur).

## 5. Durées de conservation

- Compte actif : données conservées tant que le compte existe.
- **Suppression de compte** (depuis l'application) : effacement
  irréversible du profil, photos (fichiers inclus), matchs, messages,
  likes, blocages et sessions, sans délai supplémentaire.
- **Export (portabilité)** : l'utilisateur peut télécharger
  l'intégralité de ses données (Profil → fonction d'export / API
  `GET /users/me/export`).
- Comptes inactifs : objectif d'anonymisation après 24 mois
  (dès la fin du pilote).

## 6. Vos droits

Conformément à la loi burkinabè et aux bonnes pratiques internationales
(RGPD par alignement) :

- accès, rectification (depuis l'écran Profil) ;
- effacement (suppression de compte) ;
- portabilité (export) ;
- opposition et retrait du consentement pour la géolocalisation.

Réclamations : e-mail de contact (à compléter). Autorité de tutelle :
la **CIL (Commission de l'Informatique et des Libertés, Ouagadougou)**.

## 7. Sécurité

- Mots de passe : aucun (authentification OTP sans mot de passe stocké).
- Jetons de session courts (JWT 30 min) + rafraîchissement rotatif,
  révocables.
- HTTPS obligatoire en production, en-têtes de sécurité, limitation de
  débit anti-spam (OTP, réactions).
- Hébergement : à préciser (objectif pilote : serveur en Afrique de
  l'Ouest ou UE).

## 8. Mineurs

Le service est interdit aux moins de 18 ans. Toute inscription de mineur
détectée (âge déclaré, signalement, modération) conduit à suppression
immédiate.

## 9. Modifications

Toute évolution substantielle de la présente politique sera notifiée
dans l'application avant son entrée en vigueur.

## 10. Contact

- Support / privacité : e-mail à compléter.
- Délégué à la protection des données : à désigner dès le passage en
  production.
