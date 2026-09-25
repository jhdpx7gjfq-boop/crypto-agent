# PATH-A — Liquidation Independent Alpha

| | |
|---|---|
| **ID** | `PATH-A-LIQUIDATION-ALPHA` |
| **Couche IGWT** | Layer 1 (acquisition) → Layer 2 (features) → Layer 8 (WFV) |
| **Statut** | `IN PROGRESS` |
| **Contrat** | `WFV-V2-CONTRACT` — **FROZEN** |

---

## 1. Objectif

Tester une hypothèse d'alpha indépendant basée sur la micro-structure de marché
(liquidation flows, funding rates, open interest) sur des données réelles Binance.

Pipeline complet:
```
Raw Data (Binance)
  ↓  audit d'intégrité
  ↓  normalisation OHLCV + OI + funding
  ↓  features point-in-time (sans lookahead)
  ↓  construction observations WFV
  ↓  walk-forward validation
  ↓  IC/OOS/robustesse
  ↓  verdict indépendant
```

---

## 2. Données

### Sources

| Source | Symboles | Timeframe | Champs | État |
|---|---|---|---|---|
| Binance Spot | BTC, ETH, SOL, AVAX | 1d | OHLCV | À acquérir |
| Binance Perp | BTC, ETH, SOL, AVAX | 1d | OI, funding rate | À acquérir |

### Fenêtre historique

Minimum: 365 jours pour validation robuste.
Idéal: 730 jours (2 ans, aligner avec REAL-DATA-FULL-001).

### Validation d'intégrité (par symbole)

| Champ | Description |
|---|---|
| `source` | "binance-spot" / "binance-perp" |
| `symbol` | symbole standardisé |
| `start_date` / `end_date` | couverture réelle |
| `row_count` | barres acceptées |
| `missing_dates` | jours calendaires absents |
| `duplicate_rows` | doublons écartés |
| `cohesion_check` | low ≤ min(open, close), high ≥ max(open, close) |
| `sha256_raw` | hachage données brutes |
| `sha256_normalized` | hachage après normalisation |

---

## 3. Signal et hypothèse

(À définir explicitement avant implémentation features)

Candidats:
- **Liquidation cascade**: détection des seuils de liquidation par niveau OI/funding
- **Funding squeeze**: décorrélation funding rate vs. momentum
- **OI regime shift**: changements de structure open interest
- Autre (à spécifier)

**Contrainte**: signal calculé uniquement sur `… ≤ date` (PIT stricte).

---

## 4. Features point-in-time

Utiliser les primitives existantes de `igwt.features.pit`:
- `trailing_return` (ROI lookback)
- `realized_volatility` (volatilité historique)
- `cross_sectional_zscore` (normalisation)

Ajouter:
- OI trend (pente / normalisée par market cap)
- Funding rate trend
- Liquidation pressure (proxy)

**Tous les calculs doivent satisfaire**: `data_used ≤ date_point_in_time`.

---

## 5. Contrat WFV v2

Observations exactement conformes:

| Clé | Calculé sur |
|---|---|
| `date` | date point-in-time |
| `asset` | symbole (BTC/ETH/SOL/AVAX) |
| `signal` | hypothèse d'alpha, features ≤ date |
| `fwdRet` | rendement forward horizon_days |
| `regimeVol` | volatilité glissante du régime |

WFVConfig:
- `horizon_days`: À définir (ex. 5, 10 jours)
- `embargo_days`: ≥ horizon_days
- `fold_windows`: Walk-forward folds, ex. 180/30 (180 train, 30 test, 30 embargo)
- `train_start`: Date minimale (dépend des données)

---

## 6. Métriques de validité

| Métrique | Interprétation |
|---|---|
| `train_ic` | Corrélation signal-return sur entraînement |
| `oos_ic` | IC hors échantillon — **critère principal** |
| `oos_ic_t_stat` | Significativité (ordre de grandeur) |
| `oos_hit_rate` | Part de dates IC positif |
| `direction_flips` | Instabilité du signe fold-à-fold |
| `regime_conditioned` | IC en régime haut/bas volatilité |
| `long_short_spread` | PnL différentiel long minus short |

**PASS**: oos_ic statistiquement positif + direction flips stables + regime conditioning robuste.
**FAIL**: oos_ic ≈ 0 ou négatif, ou direction flips fréquents.

---

## 7. Ablation et robustesse

Test de sensibilité:
- Retrait de chaque feature → rerun WFV → delta IC
- Fenêtre lookback variable → impact sur IC
- Fold size variable → overfitting check
- Cross-validation par régime (volatilité haut/bas)

---

## 8. Gouvernance

**Scope limitation**:
- Path A valide une hypothèse d'alpha
- Aucune intégration à BCE / X20 / RPM / NARM-P+
- Résultats enregistrés comme RESEARCH-CANDIDATE
- B-004 est indépendant (second dataset pour comparison)

**Évolution des artefacts**:
- Chaque variation (signal, features, horizon, dataset) → nouvel ID
- Lineage enregistré via `docs/registry/lineage.json`
- Aucun overwrite d'artefact locked

---

## 9. Livrables

- [ ] `data/binance/raw/` — données brutes par symbole
- [ ] `igwt/data/binance_audit.py` — audit d'intégrité
- [ ] `igwt/features/liquidation_alpha.py` — signal et features
- [ ] `fixtures/real/PATH-A-LIQUIDATION-ALPHA/` — observations + WFV report
- [ ] `docs/registry/PATH-A-LIQUIDATION-ALPHA.json` — artefact lock
- [ ] Verdict: PASS/FAIL/INCONCLUSIVE
