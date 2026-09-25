# AUDIT GLOBAL — État des trois chemins

## Chemin 1: PATH-A — Liquidation Independent Alpha

**Status:** ✅ COMPLETE / 🔴 DATA-BLOCKED

| Élément | État | Détail |
|---------|------|--------|
| Spec | ✅ | PATH-A-LIQUIDATION-ALPHA.md (formalisée) |
| Pipeline | ✅ | binance_fetcher, audit, signals, runner |
| Tests | ✅ | 9 tests + 199 existants = 208 PASS |
| Lineage | ✅ | 6 artefacts, 10 règles |
| **Bloqueur** | 🔴 | Binance API HTTP 451 + fichiers CSV manquants |
| **Dépend de** | — | Données Binance OHLCV 365-730j (BTC/ETH/SOL/AVAX) |
| **Prochaine étape** | — | Attendre acquisition data → run_path_a_full() |

---

## Chemin 2: B-004 — Real Data Path A

**Status:** ❓ UNDETERMINED

### Prérequis requis:
1. Dataset OHLCV Binance 730 jours
2. B-004_SPECIFICATION_FROZEN.md
3. Validation intégrité
4. Gel "Set A"

### État actuel:

| Prérequis | État | Détail |
|-----------|------|--------|
| REAL-DATA-FULL-001 spec | ✅ | Existe (REAL-DATA-FULL-001.md) |
| **REAL-DATA-FULL-001 data** | 🔴 | Vide (preflight.json: API blocked) |
| **B-004_SPECIFICATION_FROZEN.md** | ❌ | N'existe pas |
| **Dataset figé** | ❌ | Aucune donnée présente |
| **Validation intégrité** | ⏳ | En attente de données |

### Analyse:

- B-004 n'est **pas une spécification** — c'est un **alias** pour "Real Data Path A"
- Le chemin réel est **REAL-DATA-FULL-001** (Binance Spot 730j)
- **B-004_SPECIFICATION_FROZEN.md** doit être créé AVANT d'exécuter B-004
- Actuellement: **MÊME BLOCAGE QUE PATH-A** (données Binance)

### Dépendances:

```
PATH-A (Liquidation Alpha)
    ↓
Binance OHLCV 730j ← GATE COMMUNE
    ↓
REAL-DATA-FULL-001 (B-004)
    ↓
WFV validation (comparaison vs REAL-DATA-FIXTURE-001)
```

---

## Chemin 3: BCE/X20/RPM/NARM-P+

**Status:** 🚫 BLOCKED INDEFINITELY

| Layer | Statut | Raison |
|-------|--------|--------|
| BCE | 🚫 | Composant gouverné existant — UNTOUCHED |
| X20 | 🚫 | Dépend de BCE — pas d'implémentation autorisée |
| RPM | 🚫 | Dépend de X20 — pas d'implémentation autorisée |
| NARM-P+ | 🚫 | Dépend de RPM — pas d'implémentation autorisée |

**Constraint explicite:** "Aucune modification BCE / X20 / RPM / NARM-P+" (REAL-DATA-FIXTURE-001.md)

**Déblocage:** Explicate authorization uniquement (n'est pas soumis au travail autonomous).

---

## MATRICE DE BLOCAGE GLOBAL

```
┌─────────────────────┬──────────────┬───────────────────────┐
│ Chemin              │ Statut       │ Bloqueur              │
├─────────────────────┼──────────────┼───────────────────────┤
│ PATH-A              │ DATA-BLOCKED │ Binance OHLCV 365-730j│
│ B-004 (REAL-FUL-1)  │ DATA-BLOCKED │ Binance OHLCV 730j    │
│ BCE/X20/RPM/NARM-P+ │ FORBIDDEN    │ Governance constraint │
└─────────────────────┴──────────────┴───────────────────────┘

GATE COMMUNE: Binance OHLCV real data
```

---

## DÉPENDANCES RÉSOLUES

### Si Binance data arrive:

**Séquence autorisée:**
1. PATH-A: run_path_a_full() → audit → observations → WFV → IC → verdict
2. B-004: REAL-DATA-FULL-001 → construct observations → WFV → comparison vs REAL-DATA-FIXTURE-001
3. Lineage: mettre à jour PATH-A et REAL-DATA-FULL-001 avec résultats

### Si Binance data ne sera jamais accessible:

- PATH-A → INCONCLUSIVE (research candidate not validated)
- B-004 → CLOSED (dependency chain broken)
- Alternative: utiliser CoinGecko-only pour validations partielles (moins robuste)

---

## RECOMMANDATION

**Priorité 1: Résoudre DATA GATE**
- Contact: Acquérir Binance OHLCV 730j (BTC/ETH/SOL/AVAX)
- Format: CSV ou JSON (voir DATA-INGESTION-PROTOCOL.md)
- Timeline: Une fois données présentes, PATH-A → B-004 → verdict

**Priorité 2: B-004 formalization**
- Créer B-004_SPECIFICATION_FROZEN.md
- Aligner avec REAL-DATA-FULL-001.md
- Définir gate de validation (intégrité, PIT, WFV)

**Priorité 3: BCE/X20/RPM/NARN-P+**
- ⏸️ Gelés jusqu'à explicit authorization
- Aucune action requise
- Respecter "UNTOUCHED" constraint

---

## État du repository

```
Branch: claude/relaxed-wozniak-01ipk5
Commits: 4 (control type + revert BCE + PATH-A pipeline + ingestion protocol)
Tests: 208 PASS (37 lineage + 9 PATH-A + 162 existing)
Governance: 10 lineage rules + 6 artefacts
Production: FROZEN
```

