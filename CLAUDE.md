# IGWT-PF26 — Contexte projet (Claude Code)

Infrastructure personnelle de recherche quantitative crypto.
Objectif : système d'aide à la décision moyen/long terme. **Pas un bot de trading.**
La décision finale est humaine. Aucune exécution automatique d'ordre, jamais.

---

## 1. ÉTAT RÉEL DU REPO (à jour : 2026-09-13)

Ne pas supposer que les layers ci-dessous (§4) existent. Ce qui existe :

| Élément | État |
|---|---|
| `main.py` | Bot d'alerte BTC : poll CoinGecko → Telegram sur franchissement de seuil |
| `tests/test_main.py` | Tests unitaires du bot |
| `.github/workflows/tests.yml` | CI pytest sur push + PR |
| Layers 1-8 | **Non implémentés** |

Phase courante : **Phase 1 — structure repo + data layer**.
Avant d'implémenter : vérifier l'existant avec `ls`/`grep`, ne pas recréer.

---

## 2. DÉCISIONS FIGÉES (ne pas rediscuter)

- **Langage** : Python 3.11 (`.python-version`). Pas de 3.12+ sans migration CI explicite.
- **Tests** : pytest, `pythonpath = .` (`pytest.ini`).
- **Deps runtime** : `requirements.txt`, versions bornées (`requests>=2.31,<3`). Deps dev : `requirements-dev.txt`.
- **OHLCV** : Binance public API (source primaire, gratuite, historique profond).
- **Prix spot / market cap / catégories** : CoinGecko.
- **On-chain** : Glassnode / CryptoQuant. **TVL** : DefiLlama.
- **Stockage** : Parquet (raw + features) + DuckDB (requêtes). Pas de Postgres en local.
- **Backend cible** : FastAPI. **Frontend cible** : Next.js, mobile-first (iPhone).
- **Wallet** : Tangem. Exécution manuelle uniquement.
- **Secrets** : variables d'environnement uniquement. Jamais dans le code, jamais commités.

---

## 3. NE JAMAIS FAIRE

1. **Jamais** de clé API trading, de SDK CEX authentifié, ni de code passant un ordre.
2. **Jamais** de secret / token / chat_id en dur dans un fichier versionné.
3. **Jamais** de signal LONG émis avec `BCE < 5/6`.
4. **Jamais** de backtest sans protection anti-lookahead (features calculées à `t` n'utilisent que des données `<= t`).
5. **Jamais** de résultat de stratégie présenté sans : nb trades, profit factor, max drawdown, walk-forward.
6. **Jamais** de module isolé : vérifier son point d'intégration dans le pipeline (§5) avant d'écrire.
7. **Jamais** de valeur magique en dur (seuils, poids, fenêtres) → fichier de config externe.
8. **Jamais** de fichier de données (`.parquet`, `.csv`) commité dans git.
9. **Jamais** `git push --force` sur `main`. **Jamais** de PR sans demande explicite.
10. **Jamais** de test skippé/désactivé pour faire passer la CI.

---

## 4. ARCHITECTURE CIBLE (1 ligne par layer)

- **L1 Data Intelligence** — collecteurs → validation → feature engineering → research dataset.
- **L2 Market Regime** — régime BTC, liquidité, risk-on/off, macro (DXY, US10Y, CPI, M2, ETF flows, funding, OI).
- **L3 BCE (Bottom Confirmation Engine)** — score 0-6 : structure Wyckoff, volume, selling exhaustion, accumulation smart money, market structure, momentum. **Seuil de validation : >= 5/6.**
- **L4 X20 Engine** — asymétrie : fondamentaux (équipe, investisseurs, tokenomics, unlocks, revenus, adoption) + narratif + quantitatif.
- **L5 NARM-P+** — score /100 (narrative, adoption, rotation capital, fondamentaux, timing). **Découverte uniquement, poids faible dans la décision.**
- **L6 RCM/RPM** — rotation de capitaux. Poids : capital_flow 25 / relative_strength 25 / narrative_accel 20 / fundamental_confirm 20 / derivatives 10. Walk-forward obligatoire.
- **L7 RRP Revival Radar** — collector → snapshot validator → raw store immuable → enrichment → performance tracker → validation statistique.
- **L8 Optimizer** — regime detector, dynamic exit, MFE/MAE, param optimization, walk-forward, overfit detection.

**Seuils d'acceptation d'une stratégie** : trades >= 200, profit factor > 1.3, max drawdown < 25 %, walk-forward PASS.

**FOMO Circuit Breaker** : price discovery / euphorie / extension excessive → réduction du score. Obligatoire sur tout moteur de scoring.

---

## 5. PIPELINE DE DÉCISION (ordre non négociable)

`DATA → FEATURE ENGINEERING → SCORING → VALIDATION → RISK FILTER → ALERT → décision humaine`

Tout nouveau module doit se rattacher explicitement à une de ces étapes.

---

## 6. CONVENTIONS DE CODE

**Structure cible** (migration progressive depuis `main.py`) :

```
src/igwt/
  collectors/     # 1 fichier = 1 source (binance_ohlcv.py, coingecko_markets.py)
  storage/        # parquet + duckdb
  features/       # feature engineering, pur, sans I/O
  engines/        # bce.py, x20.py, narm.py, rcm.py, rrp.py
  risk/
  alerts/
config/           # YAML : seuils, poids, fenêtres
docs/             # *_SPEC.md, 1 par module
tests/            # miroir de src/
data/             # gitignoré, jamais lu par Claude
```

- **Nommage** : `snake_case` fonctions/modules, `UPPER_SNAKE` constantes, `PascalCase` classes.
- **Fonctions pures d'abord** : logique de calcul séparée des I/O (cf. `classify_zone` vs `get_btc` dans `main.py`) → testable sans réseau.
- **I/O réseau** : `timeout=` obligatoire, `raise_for_status()`, exceptions attrapées explicitement (`requests.RequestException, KeyError, ValueError`) — jamais `except Exception`.
- **Logs** : module `logging`, jamais `print`. Un échec de source ne doit pas tuer le process.
- **Config** : lue depuis l'environnement ou `config/*.yaml`, avec valeur par défaut explicite.
- **Typage** : type hints sur toute fonction publique.

---

## 7. DEFINITION OF DONE

Un module n'est livré que s'il a les 5 :
1. `docs/<module>_SPEC.md` (objectif, entrées, sorties, formules, critères de validation)
2. implémentation
3. tests (cas nominal + cas d'erreur réseau/données)
4. validation (backtest ou test statistique si module de scoring)
5. commit avec message descriptif

Sans preuve chiffrée, un module n'est pas "terminé". Ne pas l'annoncer comme tel.

---

## 8. COMMANDES

```bash
pip install -r requirements-dev.txt   # env dev complet
pytest                                # tous les tests
pytest tests/test_main.py -k bce      # ciblé
python main.py                        # bot alerte (BOT_TOKEN, CHAT_ID requis)
```

Lancer `pytest` avant tout commit.

---

## 9. FORMAT DE RÉPONSE

- Pas de préambule, pas de résumé après le code.
- Pas de réexplication du code écrit : le diff est la réponse.
- Commentaires inline : uniquement si le *pourquoi* n'est pas évident. Jamais de commentaire qui paraphrase la ligne.
- Référencer par `chemin:ligne`, ne pas recoller le code existant dans la réponse.
- Signaler explicitement ce qui n'a **pas** été fait ou vérifié.
- Exactitude > rapidité. Validation > intuition. Données > opinions. Robustesse > complexité.
