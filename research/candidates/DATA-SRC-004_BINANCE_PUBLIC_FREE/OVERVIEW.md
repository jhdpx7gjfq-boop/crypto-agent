# DATA-SRC-004 -- Binance Public API (gratuit, sans clé)

## Pourquoi cette source

CoinGlass n'a pas de plan API gratuit (le moins cher est Hobbyist à
29 $/mois, 30 req/min, usage personnel -- voir `DATA-SRC-003_COINGLASS_API_V4/`).
Faute de clé, cette source explore ce qu'on peut couvrir des P0 sans aucun
abonnement, directement auprès des exchanges.

`binance_public.py` (`BinancePublicClient`) ne nécessite ni clé API ni
compte : ce sont des endpoints de marché publics.

## Statut

`BINANCE_DATA_STATUS = "SCHEMA_VERIFIED"` (voir `binance_public.py`) pour
les 4 méthodes REST/calculées (`open_interest`, `open_interest_history`,
`funding_rate_history`, `*_cvd_history`) -- confirmé en direct le
2026-08-24 depuis la machine de l'utilisateur avec
`scripts/binance_verify.py` (voir la section Vérification en direct
ci-dessous pour les schémas réels obtenus). Pas encore
`DATA_QUALITY_VERIFIED` : il reste à faire la checklist trous/doublons/
timezone sur une fenêtre d'au moins 30 jours.

Le collecteur de liquidations (`liquidation_collector.py`) n'est **pas**
couvert par ce statut -- il n'a jamais tourné en conditions réelles, à
vérifier séparément (voir plus bas).

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

### Liquidations -- implémenté, mais différent des autres

Binance n'expose pas d'historique REST public de liquidations (l'ancien
endpoint `/fapi/v1/allForceOrders` public a été retiré/restreint). Le seul
flux public disponible est le WebSocket temps réel `!forceOrder@arr`.

`liquidation_collector.py` (`LiquidationCollector`) écoute ce flux en
continu et persiste chaque évènement via `liquidation_store.py`
(`LiquidationStore`, SQLite). C'est volontairement une pièce
d'infrastructure différente des clients REST ci-dessus : un **worker
long-lived** (voir `Procfile` : process `liquidation_collector`), pas une
méthode qu'on appelle à la demande.

Limite importante à documenter partout où cette donnée est utilisée :
**il n'y a pas de backfill**. L'historique commence au moment où le
collecteur a démarré ; toute coupure (redéploiement, crash, coupure
réseau) crée un trou définitif dans la série, contrairement à
`open_interest_history`/`funding_rate_history` qui peuvent rattraper le
passé sur demande.

### NetFlow (spot, cross-exchange)

Nécessite de tracer les dépôts/retraits vers des adresses on-chain
labellisées par exchange -- ce n'est pas un endpoint de marché, c'est de la
donnée on-chain agrégée (le métier de CoinGlass, Glassnode, Nansen,
Arkham...). Pas d'équivalent gratuit satisfaisant identifié ; le construire
soi-même demanderait un accès aux explorateurs de blockchain (Etherscan,
etc.) et un jeu d'adresses labellisées par exchange, pour un travail bien
au-delà du périmètre d'un client REST.

**Conclusion : sur les 6 familles P0 de CoinGlass, cette source gratuite en
couvre 4 (OI, Funding, CVD proxy single-exchange, Liquidations via
collecteur continu) et n'a pas d'équivalent réaliste pour 1 (NetFlow).**

## Connectivité -- constat depuis ce sandbox

Testé le 2026-08-23 depuis l'environnement qui a écrit ce module :

| Domaine | Résultat |
|---|---|
| `fapi.binance.com` (futures) | Bloqué par la politique d'egress de la session (`CONNECT tunnel failed, response 403`) |
| `api.bybit.com` | Idem, bloqué |
| `www.okx.com` | Idem, bloqué |
| `api.binance.com` (spot) | **Passe le proxy**, mais Binance répond HTTP 451 : *"Service unavailable from a restricted location according to 'b. Eligibility'..."* |
| `fstream.binance.com` (WebSocket liquidations) | Bloqué par la politique d'egress, comme `fapi.binance.com` |

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

## Vérification en direct -- 2026-08-24

Exécuté par l'utilisateur (Windows, PowerShell) avec `scripts/binance_verify.py`,
depuis sa propre machine -- réseau non restreint, contrairement à ce
sandbox. Résultat : **5/5 PASS**, HTTP 200 partout.

| Endpoint | Statut | Data quality |
|---|---|---|
| Open Interest (current) | PASS | OK |
| Open Interest (history) | PASS | OK |
| Funding Rate (history) | PASS | OK* |
| Futures CVD (from klines) | PASS | OK |
| Spot CVD (from klines) | PASS | OK |

\* Le script a d'abord affiché un faux "WARN (no timestamp field found)"
pour Funding Rate -- bug du script de vérification (il ne reconnaissait
pas `fundingTime` comme champ de timestamp), pas un problème de données.
Corrigé.

### Schémas réels observés (à comparer à tout changement futur de l'API Binance)

- **Open Interest (current)** : `['openInterest', 'symbol', 'time']`
- **Open Interest (history)** : `['CMCCirculatingSupply', 'sumOpenInterest', 'sumOpenInterestValue', 'symbol', 'timestamp']`
  -- note : pas un simple champ `openInterest`, contrairement à l'endpoint
  "current". Contient aussi `CMCCirculatingSupply` (CoinMarketCap),
  spécifique à cet endpoint historique.
- **Funding Rate (history)** : `['fundingRate', 'fundingTime', 'markPrice', 'rateType', 'symbol']`
- **Futures / Spot CVD (calculé)** : `['open_time', 'close_time', 'taker_buy_volume', 'taker_sell_volume', 'delta', 'cvd']`
  -- conforme à `cvd_from_klines()`, confirme que le calcul local fonctionne
  sur de vraies données.

### Connectivité confirmée depuis une machine normale (hors sandbox)

- `https://fapi.binance.com/...` : accessible, données réelles retournées.
- `https://api.binance.com/...` : accessible, données réelles retournées
  (contrairement au 451 obtenu depuis ce sandbox -- confirme que c'était
  bien une restriction liée à la localisation apparente de *ce*
  environnement, pas à Binance en général).
- `https://open-api-v4.coinglass.com/...` (sans clé) : accessible aussi,
  répond `401 API key missing` comme attendu -- donc `DATA-SRC-003`
  (CoinGlass) n'est bloquée que par l'absence de clé, pas par le réseau,
  depuis cette même machine.

## Prochaine étape

- Lancer `liquidation_collector.py` en continu depuis cette même machine
  (ou un hébergement qui reste allumé) pour vérifier en conditions réelles
  le flux `!forceOrder@arr` et commencer à construire un historique --
  actuellement non testé en direct.
- Faire la checklist qualité (trous, doublons, timezone) sur >=30 jours
  avant de passer à `DATA_QUALITY_VERIFIED`.
- Si une clé CoinGlass est obtenue un jour, comparer les deux sources sur
  les mêmes hypothèses CG-ALPHA (`DATA-SRC-003/ALPHA_CANDIDATES.md`) --
  garder à l'esprit que le CVD Binance est single-exchange, pas agrégé.
