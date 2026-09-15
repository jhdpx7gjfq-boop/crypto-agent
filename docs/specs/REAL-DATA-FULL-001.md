# REAL-DATA-FULL-001 — Spécification

| | |
|---|---|
| **ID** | `REAL-DATA-FULL-001` |
| **Couche IGWT** | Layer 1 (acquisition + audit d'intégrité) → Layer 8 (WFV) |
| **Statut** | `PENDING ACQUISITION` — pipeline implémenté et testé, données non disponibles |
| **Contrôle indépendant** | `REAL-DATA-FIXTURE-001` (**LOCKED**, jamais écrasé) |
| **Contrat** | `WFV-V2-CONTRACT` — **FROZEN** |

---

## 1. Objectif

Constituer le second dataset : OHLC **complet**, historique **long**, source
**Binance**. Il ne remplace pas `REAL-DATA-FIXTURE-001` ; il s'y compare.

```
                    DATA SOURCES
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
       CoinGecko                Binance
       composite                OHLC réel
             │                       │
             ▼                       ▼
 REAL-DATA-FIXTURE-001       REAL-DATA-FULL-001
       LOCKED                    PENDING
             │                       │
             └───────────┬───────────┘
                         ▼
                      WFV v2  (contrat gelé)
                         │
                         ▼
                 comparaison des résultats
```

**Règle d'architecture** : une source différente, une profondeur différente ou
un champ de prix différent produisent un **nouvel artefact**. Aucune
modification rétroactive d'un fixture verrouillé.

---

## 2. Pipeline

```
RAW
 ↓  audit d'intégrité      igwt.data.integrity.audit
 ↓  normalisation          igwt.data.ohlcv.normalise
 ↓  validation PIT         masques de contiguïté, features ≤ t
 ↓  construction features  igwt.features.contract.build_observations
 ↓  WFV                    igwt.validation.wfv.run
```

La ligne décisive est l'avant-dernière : **`build_observations` est la même
fonction que celle du fixture CoinGecko**. Il n'existe pas deux implémentations
des features. C'est ce qui rend la comparaison des deux datasets interprétable —
si les résultats divergent, la divergence est dans les données, pas dans deux
copies du code.

L'audit précède délibérément tout calcul de feature : un trou, un doublon ou une
barre incohérente découverts après un backtest ont déjà contaminé le résultat.

---

## 3. Manifeste d'intégrité (par symbole)

Champs requis, tous produits par `igwt.data.integrity.audit` :

| Champ | Contenu |
|---|---|
| `source` | fournisseur déclaré |
| `endpoint` | URL ou répertoire d'origine |
| `symbol` | symbole du registre |
| `market_type` | `spot` / `perp` |
| `timeframe` | `1d` |
| `start_date` / `end_date` | couverture réelle après normalisation |
| `retrieval_timestamp` | horodatage d'acquisition (UTC) |
| `row_count` | lignes acceptées |
| `missing_dates` / `missing_dates_count` | jours calendaires absents, **énumérés** |
| `duplicate_rows` | doublons écartés |
| `sha256_raw` | hachage de la réponse ou du fichier source |
| `sha256_normalized` | hachage de la série normalisée |
| `timezone` | UTC |
| `price_field` | **colonne source réellement lue** |
| `volume_field` | colonne de volume **base**, ou `null` |

`price_field` et `volume_field` sont des faits relevés, pas des hypothèses :
le résolveur enregistre la colonne qu'il a effectivement lue.

### Verdict

| Verdict | Signification |
|---|---|
| `PASS` | aucun défaut |
| `WARN` | défauts comptés et publiés — trous, doublons, barres incohérentes, volume absent |
| `FAIL` | aucune ligne exploitable — **la construction est bloquée** |

L'ordre des lignes source n'est **pas** un défaut : les exports fournisseurs
sont conventionnellement descendants, la normalisation les trie, et le fait
reste consigné dans `out_of_order_input`.

---

## 4. Contrôles de normalisation

Au-delà des contrôles déjà appliqués au fixture CoinGecko, l'OHLC autorise un
contrôle qu'une série de clôtures ne permet pas :

**Cohérence de barre** — une barre est rejetée si
`low > min(open, close)`, `high < max(open, close)`, `low > high`, si un prix
est nul, négatif ou `NaN`, ou si le volume est négatif. Une barre qui viole son
propre ordonnancement n'est pas une barre.

Volume : le résolveur préfère la colonne de volume **base** (`Volume BTC`) et
**refuse d'accepter silencieusement** une colonne de volume quote
(`Volume USDT`) à sa place — les confondre rééchelonne la série sans le dire.

---

## 5. Voies d'acquisition

```bash
python -m igwt.fixtures.real_data_full_001 --preflight
python -m igwt.fixtures.real_data_full_001 --from-files data/binance/
python -m igwt.fixtures.real_data_full_001 --fetch --start 2017-01-01
```

| Voie | État dans cet environnement |
|---|---|
| API publique Binance (`--fetch`) | **BLOQUÉE** — `data-api.binance.vision` refusé par la politique réseau ; `api.binance.com` en HTTP 451 |
| Exports CSV du registre (`--from-files`) | **disponible** — en attente des fichiers |

`--preflight` diagnostique sans lever d'exception ; la trace est conservée dans
`fixtures/real/REAL-DATA-FULL-001/preflight.json`.

Le lecteur CSV tolère la ligne de préambule des exports, résout les colonnes
sans tenir compte de la casse, accepte les horodatages Unix (s / ms / µs) comme
les dates ISO, et trie les lignes descendantes.

> Les fichiers `.xlsx` du registre doivent être exportés en CSV avant ingestion.
> Aucune dépendance de lecture Excel n'est ajoutée pour un format non vérifié.

---

## 6. Ce qui reste bloqué tant que les données manquent

- Le dataset lui-même : aucune barre n'est fabriquée pour combler l'absence.
- La robustesse historique 2017–2026.
- **BCE / Wyckoff**, qui exige l'OHLC complet — débloqué *par* ce dataset, pas
  par le fixture CoinGecko.

## 7. Ce qui est déjà vérifié

Le pipeline est testé de bout en bout sur des exports fabriqués, confinés au
répertoire temporaire des tests (`tests/test_real_data_full_001.py`) : aucune
barre synthétique n'est committée comme fixture. Les tests établissent que les
observations produites satisfont le contrat WFV gelé, que le runner WFV les
accepte sans modification, et que les paramètres de features sont identiques à
ceux du fixture de contrôle.
