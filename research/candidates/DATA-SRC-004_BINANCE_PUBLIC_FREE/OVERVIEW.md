# DATA-SRC-004 -- Binance Public API (gratuit, sans clé)

## Pourquoi cette source

CoinGlass n'a pas de plan API gratuit (le moins cher est Hobbyist à
29 $/mois, 30 req/min, usage personnel -- voir `DATA-SRC-003_COINGLASS_API_V4/`).
Faute de clé, cette source explore ce qu'on peut couvrir des P0 sans aucun
abonnement, directement auprès des exchanges.

`binance_public.py` (`BinancePublicClient`) ne nécessite ni clé API ni
compte : ce sont des endpoints de marché publics.

## Statut

`COINGLASS_DATA_STATUS`-style : `UNVERIFIED`. Le client est testé
(mocks) mais pas vérifié en direct -- voir la section connectivité
ci-dessous, le blocage n'est pas le même que pour CoinGlass.

## Périmètre couvert

| Famille P0 | Méthode | Endpoint Binance | Notes |
|---|---|---|---|
| Open Interest | `open_interest` / `open_interest_history` | `/fapi/v1/openInterest`, `/futures/data/openInterestHist` | Futures uniquement ; historique limité à ~30 jours |
| Funding Rate | `funding_rate_history` | `/fapi/v1/fundingRate` | Brut uniquement -- pas de version pondérée OI/volume (c'est une agrégation cross-exchange propre à CoinGlass) |
| Spot CVD | `spot_cvd_history` | `/api/v3/klines` | **Calculé localement**, pas natif -- voir ci-dessous |
| Futures CVD | `futures_cvd_history` | `/fapi/v1/klines` | Idem |

### Comment le CVD est calculé

Binance n'expose pas de CVD directement. Chaque kline contient
`taker_buy_base_volume` (volume acheté par des ordres agressifs / taker) et
le `volume` total. On en déduit :

```text
taker_sell_volume = volume - taker_buy_base_volume
delta             = taker_buy_base_volume - taker_sell_volume
CVD               = cumsum(delta)
```

C'est un proxy raisonnable pour un seul exchange, mais **ce n'est pas la
même chose** que le CVD agrégé multi-exchange de CoinGlass -- à documenter
clairement si les deux sources sont un jour comparées dans un même alpha.

## Ce qui n'a pas d'équivalent gratuit correct

### Liquidations

Binance n'expose pas d'historique REST public de liquidations (l'ancien
endpoint `/fapi/v1/allForceOrders` public a été retiré/restreint). Le seul
flux public disponible est le WebSocket temps réel `!forceOrder@arr` : pour
en tirer un historique, il faudrait faire tourner un collecteur qui
écoute en continu et persiste les évènements soi-même -- une pièce
d'infrastructure différente d'un simple client REST, pas juste une méthode
en plus. Non implémenté ici.

### NetFlow (spot, cross-exchange)

Nécessite de tracer les dépôts/retraits vers des adresses on-chain
labellisées par exchange -- ce n'est pas un endpoint de marché, c'est de la
donnée on-chain agrégée (le métier de CoinGlass, Glassnode, Nansen,
Arkham...). Pas d'équivalent gratuit satisfaisant identifié ; le construire
soi-même demanderait un accès aux explorateurs de blockchain (Etherscan,
etc.) et un jeu d'adresses labellisées par exchange, pour un travail bien
au-delà du périmètre d'un client REST.

**Conclusion : sur les 6 familles P0 de CoinGlass, cette source gratuite en
couvre 3 correctement (OI, Funding, CVD proxy single-exchange) et n'a pas
d'équivalent réaliste pour 2 (Liquidations, NetFlow).**

## Connectivité -- constat depuis ce sandbox

Testé le 2026-08-23 depuis l'environnement qui a écrit ce module :

| Domaine | Résultat |
|---|---|
| `fapi.binance.com` (futures) | Bloqué par la politique d'egress de la session (`CONNECT tunnel failed, response 403`) |
| `api.bybit.com` | Idem, bloqué |
| `www.okx.com` | Idem, bloqué |
| `api.binance.com` (spot) | **Passe le proxy**, mais Binance répond HTTP 451 : *"Service unavailable from a restricted location according to 'b. Eligibility'..."* |

Le 403 sur les trois premiers domaines est une politique d'organisation
sur cette session précise (confirmé via `/root/.ccr/README.md` : *"The
destination host is not allowed by your organization's egress policy for
this session"*) -- probablement différent depuis ta propre machine ou un
autre environnement.

Le 451 sur `api.binance.com` est en revanche une restriction **de
Binance lui-même**, basée sur la localisation apparente de la requête
sortante (conditions d'éligibilité de Binance, indépendantes de cette
session). Si tu comptes utiliser ce client en production, vérifie que
l'IP/juridiction depuis laquelle il tournera est éligible aux CGU Binance
avant d'investir davantage dans cette source.

## Prochaine étape

Lancer `client.open_interest("BTCUSDT")` / `client.funding_rate_history(...)`
/ `client.spot_cvd_history(...)` depuis un environnement qui n'a ni
restriction réseau ni restriction géographique Binance, pour confirmer que
les schémas de réponse correspondent à ce qu'attend `binance_public.py`
avant de brancher ces données sur les mêmes hypothèses CG-ALPHA que
`DATA-SRC-003` (`ALPHA_CANDIDATES.md`).
