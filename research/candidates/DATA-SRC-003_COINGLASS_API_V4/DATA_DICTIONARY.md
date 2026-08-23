# Phase B -- Contract validation

À remplir une fois Phase A (`ENDPOINT_VALIDATION.md`) passée à `PASS` pour
un endpoint donné -- ne pas deviner ces valeurs à partir de la
documentation seule, les confirmer sur une réponse réelle.

Pour chaque endpoint, documenter :

- **Champs** : liste exacte des clés retournées (comparer à
  `scripts/coinglass_verify.py`, section "Schema").
- **Unité** : USD, coin natif, ratio, %, etc.
- **Devise de cotation** : USD, USDT, ou dépend du symbole/exchange.
- **Timestamp** : nom du champ, résolution (s vs ms), timezone (UTC
  attendu -- à confirmer), alignement de bougie (open time vs close time).
- **Résolution / agrégation** : ce que représente un point (ex: OHLC sur
  l'intervalle demandé, ou snapshot instantané agrégé multi-exchange).
- **Comportement sur donnée manquante** : trou dans la série, valeur
  nulle, ou exchange absent silencieusement.

## Open Interest -- `open_interest_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Open Interest (agrégé) -- `open_interest_aggregated_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Funding (brut) -- `funding_rate_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Funding (pondéré OI) -- `funding_rate_oi_weighted_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Funding (pondéré volume) -- `funding_rate_vol_weighted_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Liquidations -- `liquidation_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Liquidations (agrégées) -- `liquidation_aggregated_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Spot CVD -- `spot_cvd_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Futures CVD -- `futures_cvd_history`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Spot NetFlow -- `spot_coin_netflow`

| Champ | Type | Unité | Notes |
|---|---|---|---|
| _à remplir_ | | | |

## Checklist qualité (par endpoint, sur >=30 jours réels)

- [ ] Pas de trou dans la série au-delà de la résolution attendue
- [ ] Pas de doublons de timestamp
- [ ] Timezone confirmée UTC (ou conversion documentée)
- [ ] Valeurs dans une plage plausible (pas de zéro/NaN silencieux)
- [ ] Comportement identique entre `exchange` explicite et agrégé (cohérence)
