# Phase D -- Alpha candidates

**Statut : candidats non validés.** Rien ici ne doit entrer dans une règle
de décision ou un score avant d'avoir traversé le pipeline de validation
ci-dessous. Ne pas implémenter tant que `DATA-SRC-003` n'est pas au moins
`SCHEMA_VERIFIED` (voir `ENDPOINT_VALIDATION.md`).

## Pipeline de validation obligatoire, par candidat

```text
feature
  -> distribution
  -> IC (information coefficient)
  -> forward returns
  -> hit rate
  -> conditional returns (par régime)
  -> stabilité par régime
  -> walk-forward
  -> décision : validé / rejeté
```

Ne jamais coder de règle du type `if funding < 0: buy_signal = True` ou
`if cvd > 0: score += 10` -- ce n'est pas une validation, c'est une
supposition non testée.

## CG-ALPHA-001 -- OI / Price Divergence

- **Hypothèse** : une variation de prix non confirmée par le
  positionnement dérivé (OI) signale un régime différent (short
  covering, shorts entrants, deleveraging...).
- **Données** : `open_interest_history` + prix (OHLC, hors CoinGlass).
- **Feature candidate** : `OI_PRICE_DIVERGENCE = sign(price_return) != sign(oi_change)`,
  puis version continue en z-score des deux composantes.

## CG-ALPHA-002 -- Funding x OI Crowding

- **Hypothèse** : funding et OI extrêmes simultanément indiquent un
  crowding de position (risque de squeeze), plus informatif que le
  funding seul.
- **Données** : `funding_rate_oi_weighted_history` + `open_interest_history`.
- **Feature candidate** : interaction z-score(funding) x z-score(OI change).

## CG-ALPHA-003 -- Spot CVD / Price Divergence

- **Hypothèse** : structure de prix stable + CVD spot en baisse (ou
  l'inverse) peut indiquer une absorption de liquidité agressive.
- **Données** : `spot_cvd_history` + prix.
- **Feature candidate** : `CVD_PRICE_DIVERGENCE` (price_return vs CVD_return, tous deux en z-score).

## CG-ALPHA-004 -- Spot vs Futures CVD

- **Hypothèse** : un mouvement porté par le spot n'a pas la même qualité
  qu'un mouvement porté par les futures (leverage).
- **Données** : `spot_cvd_history` + `futures_cvd_history`.
- **Feature candidate** : `REAL_FLOW_RATIO = spot_cvd / (spot_cvd + futures_cvd)`.

## CG-ALPHA-005 -- Liquidation Sweep / Reclaim

- **Hypothèse** : un breakdown de support suivi de liquidations massives
  puis d'une reprise immédiate du niveau (reclaim) diffère d'un simple
  breakdown -- pertinent pour la détection de Spring Wyckoff.
- **Données** : `liquidation_history` (ou agrégé) + prix + `spot_cvd_history`.
- **Feature candidate** : combinaison `liquidation_zscore` + `distance_from_support` +
  `reclaim_speed` + `cvd_reversal`.

## CG-ALPHA-006 -- NetFlow / Market Cap

- **Hypothèse** : le netflow spot normalisé par market cap est plus
  comparable cross-asset que le netflow brut en USD.
- **Données** : `spot_coin_netflow` + market cap (hors CoinGlass).
- **Feature candidate** : `NETFLOW_MCAP_ZSCORE = zscore(netflow / market_cap)`.

## Hors scope pour ce premier lot

Whale positioning, ETF flows, token unlocks, order book / large orders,
basis, futures/spot volume ratio -- restent en P1, à traiter après
validation des 6 candidats ci-dessus et une fois les endpoints P1
implémentés dans `CoinGlassClient`.
