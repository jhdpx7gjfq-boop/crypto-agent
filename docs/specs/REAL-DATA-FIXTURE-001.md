# REAL-DATA-FIXTURE-001 — Spécification

| | |
|---|---|
| **ID** | `REAL-DATA-FIXTURE-001` |
| **Couche IGWT** | Layer 1 (Data Intelligence) → Layer 8 (Walk-Forward Validator) |
| **Statut** | `PASS` — validation d'infrastructure |
| **Version** | `igwt 0.1.0` |
| **Portée** | Validation du pipeline de recherche. **Aucune** modification BCE / X20 / RPM / NARM-P+. Aucune intégration production. |

---

## 1. Objectif

Fournir un jeu d'observations **réelles** conforme au contrat WFV, afin de
vérifier que la chaîne

```
collecte → snapshot immuable → validation → feature engineering → WFV
```

fonctionne de bout en bout sans lookahead, sur des données de marché
effectivement enregistrées.

Ce fixture ne valide **pas** un signal. Il valide l'outillage qui jugera les
signaux.

---

## 2. Provenance des données — écart assumé avec le registre

Le registre IGWT documente les datasets suivants :

```
BTCUSDT_Daily_2017-2026.xlsx
Binance_ETHUSDT_d.csv   Binance_SOLUSDT_d.csv   Binance_BNBUSDT_d.csv
Binance_XRPUSDT_d.csv   Binance_ADAUSDT_d.csv   Binance_DOGEUSDT_d.csv
```

**Ces fichiers n'ont pas pu être atteints depuis cet environnement.** Audit
effectué avant toute construction :

| Source tentée | Résultat |
|---|---|
| Fichiers du registre (Drive / Library) | absents — aucun fichier `*USDT*` ni `Binance_*` dans le Drive connecté |
| `api.binance.com` | **HTTP 451** (restriction géographique de l'hôte d'exécution) |
| `data-api.binance.vision` | **CONNECT 403** — refusé par la politique réseau |
| Coinbase, Kraken, OKX, Bybit, Gate.io, Bitstamp, CryptoCompare | **CONNECT 403** — refusés par la politique réseau |
| `api.coingecko.com` | **accessible** |

Décision : construire le fixture sur **CoinGecko**, qui est la source n°1 de la
Layer 1 du registre, et **documenter l'écart** plutôt que de fabriquer un
substitut synthétique ou de faire passer le gate artificiellement.

### Conséquences à connaître

1. Les prix sont le **composite multi-venues CoinGecko**, pas le spot Binance.
   Les valeurs ne sont pas interchangeables avec `Binance_*USDT_d.csv`.
2. Profondeur limitée à **365 jours** (le tier public refuse toute fenêtre
   antérieure, code d'erreur `10012`).
3. `market_chart` ne renvoie que la **clôture**, la capitalisation et le volume
   quotidien : ni open, ni high, ni low. Les modules Wyckoff/BCE qui exigent un
   OHLC complet ne peuvent pas être servis par ce fixture.
4. **Aucune valeur n'est simulée.** Chaque observation remonte à un snapshot
   fournisseur haché sous `raw/`.

---

## 3. Univers et paramètres

| Symbole registre | id CoinGecko |
|---|---|
| BTCUSDT | `bitcoin` |
| ETHUSDT | `ethereum` |
| SOLUSDT | `solana` |
| BNBUSDT | `binancecoin` |
| XRPUSDT | `ripple` |
| ADAUSDT | `cardano` |
| DOGEUSDT | `dogecoin` |

| Paramètre | Valeur |
|---|---|
| `MOMENTUM_LOOKBACK_DAYS` | 30 |
| `FORWARD_HORIZON_DAYS` | 7 |
| `VOLATILITY_WINDOW_DAYS` | 30 |
| `MIN_CROSS_SECTION` | 3 |

Ces paramètres sont **figés avant exécution** et n'ont pas été ajustés au vu du
résultat. Un fixture dont les paramètres sont choisis après avoir vu le score
mesure l'opérateur, pas le pipeline.

---

## 4. Contrat de sortie

`observations.csv` — exactement cinq colonnes :

| Colonne | Type | Définition | Fenêtre lue |
|---|---|---|---|
| `date` | ISO-8601 | horodatage point-in-time (UTC) | — |
| `asset` | str | symbole du registre | — |
| `signal` | float | z-score **transversal**, à date fixée, du rendement simple sur 30 jours glissants | `t-30 … t` |
| `fwdRet` | float | rendement simple sur les 7 jours suivants (**label**) | `t … t+7` |
| `regimeVol` | float | écart-type annualisé des log-rendements quotidiens sur 30 jours | `t-30 … t` |

`signal` et `regimeVol` ne lisent **jamais** au-delà de `t`. `fwdRet` est le
label : il lit le futur par construction et ne doit jamais être réinjecté en
entrée.

Le z-score est transversal (entre actifs à une même date) et non temporel :
un mouvement de marché commun ne peut donc pas se déguiser en signal.

---

## 5. Traitement des irrégularités

Toute ligne écartée est **comptée et publiée** dans `manifest.json`
(`snapshot_validation`). Une donnée rejetée en silence n'est pas auditable.

| Irrégularité | Traitement |
|---|---|
| Dernier point intraday (horodatage non aligné sur 00:00:00 UTC) | **écarté** — c'est une journée en cours, encore mouvante |
| Date dupliquée | **écartée** — la première occurrence fait foi |
| Prix nul, négatif, `NaN` ou absent | **écarté** |
| Points désordonnés | re-triés, et le fait est **signalé** (`out_of_order_input`) |
| Trou calendaire | **signalé, jamais comblé** — aucune interpolation |
| Fenêtre de feature enjambant un trou | **invalidée** (`contiguous_backward_mask` / `contiguous_forward_mask`) |

Point important : une feature « 30 périodes » calculée sur des *lignes*
s'étire silencieusement sur plus de 30 jours dès qu'il existe un trou. Les
masques de contiguïté invalident ces valeurs au lieu de les laisser mentir sur
leur propre horizon.

Sur le tirage courant, la seule irrégularité réellement présente est le point
intraday terminal (1 par actif, 7 au total). Les autres cas sont couverts par
des tests unitaires sur données construites — **pas** par injection d'anomalies
artificielles dans le fixture, qui cesserait alors d'être un fixture réel.

---

## 6. Artefacts

```
fixtures/real/REAL-DATA-FIXTURE-001/
├── raw/<SYMBOLE>.json   réponses fournisseur brutes, non modifiées, hachées
├── observations.csv     le fixture (contrat WFV)
├── manifest.json        provenance, hachages, rapports de validation, paramètres
└── wfv_report.json      sortie WFV v2 + gate
```

## 7. Reproduction

```bash
python -m igwt.fixtures.real_data_fixture_001          # reconstruit depuis raw/
python -m igwt.validation.run_fixture_wfv              # rejoue WFV + gate
pytest                                                 # suite complète
```

`--fetch` recollecte depuis CoinGecko. Le store brut est **append-only** :
réécrire un snapshot avec un contenu différent lève `SnapshotConflict`, ce qui
rend visible toute dérive fournisseur au lieu de l'absorber.

## 8. Preuve d'absence de lookahead

Trois niveaux, tous exécutés par `pytest` :

1. **Unitaire** — modifier les prix postérieurs à `t` ne change aucune feature
   en `t` (`tests/test_pit_features.py`).
2. **Bout en bout** — le fixture est entièrement reconstruit à partir de
   snapshots **tronqués de 90 jours**, comme si l'on était trois mois plus tôt.
   Toutes les observations communes aux deux constructions doivent être
   identiques au 1e-9 près (`TestBlindToTheFuture`). Si une seule étape du
   pipeline regardait devant elle, les deux constructions divergeraient.
3. **Validation** — l'embargo WFV couvre l'horizon du label, et
   `assert_no_leakage` revérifie ligne à ligne, pas seulement aux bornes.

## 9. Ce que ce fixture ne prouve pas

- Que le signal momentum 30j est prédictif.
- Qu'un module BCE / X20 / RPM / NARM-P+ est validé.
- Qu'il remplace les datasets Binance du registre.
- Qu'un OHLC complet est disponible pour les analyses Wyckoff.

## 10. Prochain mouvement

Rendre accessibles les datasets Binance du registre (dépôt, stockage objet, ou
autorisation réseau vers `data-api.binance.vision`), puis relancer
`--fetch` sur un collecteur Binance : le contrat, les features et le validateur
restent inchangés, seule la couche collecte est à substituer.
