# Politique de confidentialité — FASO LOVE

**Version 1.0 — 25 septembre 2026 (lancement pilote).**

> 🔐 Cette politique explique simplement quelles données nous collectons,
> pourquoi, combien de temps nous les gardons et quels sont vos recours.
> Elle fait parti intégrante des CGU. Cadre juridique : loi burkinabè
> n°010-2004/AN (protection des données personnelles) et règles relatives
> à la vie privée. Autorité de référence : Commission de l'Informatique et
> des Libertés (CIL) — https://cil.bf.

## 1. Responsable de traitement

L'Éditeur de FASO LOVE (coordonnées dans les Mentions légales, accessibles
dans l'application : Profil → À propos & légal). Contact délégué
confidentialité (DPO) : email figurant dans les Mentions légales.

## 2. Données collectées

| Catégorie | Exemples | Source | Fondement |
|---|---|---|---|
| **Identifiant compte** | numéro +226 vérifié OTP, date de naissance (preuve 18+), version de l'app | vous (OTP) | exécution du contrat + obligation de sécurité (majorité) |
| **Profil** | surnom, genre, recherché(e), ville, bio, intérêts, latitude/longitude (facultatif) | vous | consentement + exécution du service |
| **Photos** | images de profil compressées appareil/serveur | vous | consentement explicite (upload) |
| **Activités** | likes, super likes, matchs, messages, signalements, blocages | votre usage | exécution du contrat |
| **Monétisation** | transaction (montant, plan, moyen de paiement, statut), abonnement actif / historique | notre système + agrégateur (statuts) | exécution du contrat |
| **Notifications** | ton de l'appareil (token push), préférences, contenu minimal de la notification | appareil + app | exécution du service |
| **Technique** | logs IP, horodatages d'accès, événements de sécurité | serveur | intérêt légitime (sécurité) |

**Pas de** : géolocalisation de fond continue, analyse des messages (les
messages restent privés entre vous ; traités uniquement pour livraison,
chiffrement en transit et sauvegarde), vente ou location de données.

## 3. Pourquoi les traitons-nous

- Fournir le service (recherche de matchs, messagerie) ;
- Appliquer la règle stricte 18+ (obligation de sécurité) ;
- Gérer les abonnements payants et leurs preuves (comptabilité) ;
- Assurer la sécurité : anti-spam OTP, anti-brute-force, modération ;
- Respecter des obligations légales (facturation, signalements graves).

## 4. Destinataires / sous-traitants

| Sous-traitant | Rôle | Localisation des données |
|---|---|---|
| Opérateur SMS | envoi des codes OTP | opérateur local (routier), don = numéro court |
| Agrégateur de paiement (ex. PayDunya) | encaissement Mobile Money | réseau Burkina Faso / international selon mandat |
| Hébergeur cloud (serveur + sfg) | stockage application | UE ou data center conforme (cf. Mentions légales) |

Nous concluons des obligations de confidentialité avec chacun.

## 5. Durées de conservation

- Code OTP : **10 minutes** maximum, supprimé après usage ou expiration.
- Compte actif : jusqu'à suppression.
- Après suppression de compte : effacement total immédiat (profil, photos,
  messages, matchs, appareils notif.), sauf :
  - preuve des transactions d'encaissement : 10 ans (comptabilité légale) ;
  - signalements graves (sabotage, contenu illicite) : 12 mois ;
  - sauvegardes chiffrées : rotation 30 jours (elles s'effacent toutes
    seules par cycle).
- Logs techniques serveur : 90 jours en rotation.

## 6. Vos droits

Vous pouvez, **dans l'application elle-même** (plus rapide, instantané) :

- exporter toutes vos données (« Exporter mes données », format JSON) ;
- corriger/modifier votre profil, supprimer des photos ;
- réinitialiser vos préférences de notification ou désenregistrer un
  appareil ;
- **supprimer intégralement votre compte**.

Preuves d'encaissement et signalements graves sont les seuls éléments non
effaçables immédiatement (obligations légales), ils le sont après les
durées légales ci-dessus.

Réclamation : via les Mentions légales / DPO. Si désaccord persistant :
saisine de la **CIL (https://cil.bf)** possible (gratuit).

## 7. Sécurité

- OTP 6 chiffres à usage unique 5 minutes, limites de tentatives ;
- sessions JWT courtes + rotation (révocation instantanée au logout /
  suppression de compte) ;
- transport chiffré TLS obligatoire (HSTS en production) ; aucune donnée
  sensible acceptée hors HTTPS ;
- photos : strips EXIF, compression ≤ 1600 px (vitesse et anonymat) ;
- sauvegardes compressées, sha256-vérifiées, rotation 14-30 jours, restauration certifiée ;
- accès administrateur restreint à l'équipe modération (logs).

## 8. Mineurs

FASO LOVE est **interdit (< 18 ans révolus)**. Découvert = compte fermement
fermé + suppression immédiate + signalement si grave. Si vous avez connu
d'un mineur sur la plateforme : signalez-le immédiatement (signalement in-app
→ sécurité).

## 9. Transferts hors Burkina Faso

L'architecture vise des données au Burkina Faso ou UE ; tout transfert est
encadré par le contrat du sous-traitant (§4) et les garanties appropriées.
Aucun transfert à des fins publicitaires.

## 10. Modifications

Évolution substantielle : notification in-app ≥ 15 jours avant effet.
Version courante dans l'application (Profil → À propos & légal).

---

*Version 1.0 — 25 septembre 2026. Remplace le brouillon 0.1 (24 sept. 2025).
Document en français ; références juridiques : loi 010-2004/AN, CIL BF.*
