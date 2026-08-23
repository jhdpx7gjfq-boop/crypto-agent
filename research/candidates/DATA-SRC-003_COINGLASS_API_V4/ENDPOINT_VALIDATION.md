# Phase A -- API Reality Check

## Comment exécuter

```
COINGLASS_API_KEY=... python scripts/coinglass_verify.py
```

Ce script fait de vrais appels réseau vers `open-api-v4.coinglass.com`. Il
ne peut **pas** être lancé depuis l'environnement distant qui a écrit ce
module : la tentative ci-dessous, faite pour confirmer l'hypothèse avant
d'écrire ce document, montre que le proxy d'egress bloque le domaine au
niveau du tunnel CONNECT (donc même une clé invalide n'obtiendrait pas de
réponse HTTP) :

```
$ curl https://open-api-v4.coinglass.com/api/futures/open-interest/history ...
curl: (56) CONNECT tunnel failed, response 403
```

Ce script doit donc être lancé depuis une machine/CI ayant un accès réseau
sortant vers `coinglass.com`, avec une vraie clé `COINGLASS_API_KEY`.

## Résultat attendu (à remplir après exécution réelle)

| Endpoint | Statut | HTTP | Auth | Schema | Data quality |
|---|---|---|---|---|---|
| Open Interest | UNVERIFIED | -- | -- | -- | -- |
| Open Interest (agrégé) | UNVERIFIED | -- | -- | -- | -- |
| Funding (brut) | UNVERIFIED | -- | -- | -- | -- |
| Funding (pondéré OI) | UNVERIFIED | -- | -- | -- | -- |
| Funding (pondéré volume) | UNVERIFIED | -- | -- | -- | -- |
| Liquidations | UNVERIFIED | -- | -- | -- | -- |
| Liquidations (agrégées) | UNVERIFIED | -- | -- | -- | -- |
| Spot CVD | UNVERIFIED | -- | -- | -- | -- |
| Futures CVD | UNVERIFIED | -- | -- | -- | -- |
| Spot NetFlow | UNVERIFIED | -- | -- | -- | -- |

Statuts possibles : `UNVERIFIED` / `PASS` / `FAIL` / `WARN`.

## Critères de passage à `API_VERIFIED`

- Les 6 familles P0 (10 endpoints ci-dessus) renvoient HTTP 200 avec
  `code == "0"` et au moins un enregistrement pour `BTC`/`BTCUSDT` sur
  Binance.
- Aucune divergence de chemin d'URL, de méthode HTTP ou de header
  d'authentification par rapport à `coinglass.py`.
- Toute divergence constatée (endpoint renommé, paramètre requis
  manquant, etc.) est corrigée dans `coinglass.py` et ses tests avant de
  cocher la ligne correspondante.

Une fois toutes les lignes à `PASS`, mettre à jour
`COINGLASS_DATA_STATUS = "API_VERIFIED"` dans `coinglass.py` et
documenter la date + la clé/abonnement utilisé (sans la valeur du
secret) dans ce fichier.

## Critères de passage à `SCHEMA_VERIFIED` / `DATA_QUALITY_VERIFIED`

Voir `DATA_DICTIONARY.md` pour le détail par endpoint (unité, devise,
résolution temporelle, timezone, comportement sur donnée manquante) et la
checklist de qualité (trous, doublons, valeurs aberrantes) sur une
fenêtre réelle d'au moins 30 jours avant de passer à
`DATA_QUALITY_VERIFIED`, puis `RESEARCH_READY`.
