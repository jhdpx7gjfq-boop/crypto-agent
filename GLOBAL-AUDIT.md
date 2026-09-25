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

## Chemin 2: REAL-DATA-FULL-001 — Binance Spot 730j

**Status:** 🔴 DATA-BLOCKED / ✅ FORMALIZED

### Artefact formel:

✅ **REAL-DATA-FULL-001.md** (docs/specs/)
- Objective: Binance Spot OHLCV 730 jours (BTC, ETH, SOL, AVAX)
- Status: `PENDING ACQUISITION`
- Control fixture: REAL-DATA-FIXTURE-001 (LOCKED)
- Contract: WFV-V2-CONTRACT (FROZEN)
- Registered in lineage.json (10 rules enforced)

### État actuel:

| Élément | État | Détail |
|---------|------|--------|
| Specification | ✅ | REAL-DATA-FULL-001.md formalisée |
| **Data** | 🔴 | Vide (preflight.json: API blocked) |
| **Lineage** | ✅ | Enregistré, 6 relations validées |
| **Validation intégrité** | ⏳ | En attente de données |
| **Pipeline** | ✅ | Implémenté (igwt/fixtures/real_data_full_001.py) |

### Note sur B-004:

- **B-004** était une référence conversationnelle (pas un artefact repository formel)
- Correspond au besoin "Real Data Path A" formalisé par **REAL-DATA-FULL-001**
- Si B-004 doit devenir artefact formel: créer `B-004_SPECIFICATION_FROZEN.md` avec lineage explicite
- **Actuellement**: REAL-DATA-FULL-001 est le chemin formel pour acquisition Binance
- Voir TRACEABILITY-CORRECTION.md pour clarification

### Dépendances:

```
PATH-A (Liquidation Alpha)
    ↓
Binance OHLCV 730j ← GATE COMMUNE
    ↓
REAL-DATA-FULL-001 (Binance Spot validation)
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

