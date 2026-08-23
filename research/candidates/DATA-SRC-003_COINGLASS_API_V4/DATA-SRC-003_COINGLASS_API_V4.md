# DATA-SRC-003 -- CoinGlass API V4

## Statut

`COINGLASS_DATA_STATUS = UNVERIFIED` (voir `coinglass.py`).

Le client (`coinglass.py`, `CoinGlassClient`) est écrit et couvert par des
tests unitaires (mocks). Cela valide le comportement du code, pas
l'intégration réelle avec l'API CoinGlass. Aucun appel réel n'a encore été
effectué : le réseau sortant de la session qui a écrit ce module n'a pas
accès à `coinglass.com` (voir `ENDPOINT_VALIDATION.md`).

Ne pas construire de feature/alpha sur ces données avant `RESEARCH_READY`.

## Périmètre

Couche "Market Microstructure & Derivatives Intelligence" pour IGWT :
positionnement dérivé, flux réels (order flow), liquidité.

### P0 -- implémenté dans `CoinGlassClient`, en attente de validation

| Famille | Méthode client | Endpoint |
|---|---|---|
| Open Interest | `open_interest_history` | `/api/futures/open-interest/history` |
| Open Interest (agrégé) | `open_interest_aggregated_history` | `/api/futures/open-interest/aggregated-history` |
| Funding (brut) | `funding_rate_history` | `/api/futures/funding-rate/history` |
| Funding (pondéré OI) | `funding_rate_oi_weighted_history` | `/api/futures/funding-rate/oi-weight-history` |
| Funding (pondéré volume) | `funding_rate_vol_weighted_history` | `/api/futures/funding-rate/vol-weight-history` |
| Liquidations | `liquidation_history` | `/api/futures/liquidation/history` |
| Liquidations (agrégées) | `liquidation_aggregated_history` | `/api/futures/liquidation/aggregated-history` |
| Spot CVD | `spot_cvd_history` | `/api/spot/cvd/history` |
| Futures CVD | `futures_cvd_history` | `/api/futures/cvd/history` |
| Spot NetFlow | `spot_coin_netflow` | `/api/spot/coin/netflow` |

### P1 -- pas encore implémenté

Order Book / Large Orders, Whales (Hyperliquid), ETF flows, Token Unlocks,
Exchange Balance/Transparency, Basis, Futures/Spot Volume Ratio.

## Pipeline

```text
DATA-SRC-003
      |
      +-- Phase A -- API Reality Check      (ENDPOINT_VALIDATION.md)
      |
      +-- Phase B -- Contract validation     (DATA_DICTIONARY.md)
      |
      +-- Phase C -- CoinGlass -> IGWT        (Hydrator -> CanonicalRecord -> FeatureRecord)
      |
      +-- Phase D -- Alpha candidates         (ALPHA_CANDIDATES.md)
```

Le client (`coinglass.py`) reste une source de données brute. Aucune
donnée CoinGlass n'entre dans un score ou une règle de décision sans être
passée par ce pipeline complet, avec validation statistique out-of-sample.
