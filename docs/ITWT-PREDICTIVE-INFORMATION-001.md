# ITWT-PREDICTIVE-INFORMATION-001
## Specification de Validation de l'Information Prédictive Indépendante

**Version:** 1.0  
**Date:** 2026-09-25  
**Statut:** Active  
**Auteur:** IGWT-PF26 Research Team

---

## 1. OBJECTIF

Valider que chaque composante IGWT apporte une **information prédictive indépendante** mesurable en OOS/WFV, avant intégration dans la pipeline de décision.

Pas de composante n'entre en production sans preuve :
- ✅ Signal positif en IS → extrapolable OOS
- ✅ Contribution marginale non nulle après contrôle des autres variables
- ✅ Zéro look-ahead, zéro data leakage
- ✅ Reproductibilité sur régimes et horizons multiples
- ✅ Stabilité temporelle du paramétrage

---

## 2. PRINCIPES FONDAMENTAUX

| Principe | Règle | Conséquence |
|----------|-------|-------------|
| **Information, pas prédiction** | Mesurer IC/Rank IC, pas P&L | Pas de backtesting classique |
| **OOS/WFV seul** | Jamais IS comme preuve | Data leakage = rejet automatique |
| **Pas d'optimisation OOS** | Paramètres figés avant test | WFV valide, pas IS retrain |
| **Pas de look-ahead** | PIT + timestamps rigoureux | Springer Detector-like validation |
| **Indépendance** | Ablation + permutation + MI | Chaque brique isolée d'abord |

---

## 3. PHASES DE VALIDATION

### Phase A : Signaux Individuels

Chaque composante validée **isolément** avant intégration.

| # | Composante | Status | IC Target | OOS Horizon | Notes |
|---|------------|--------|-----------|-------------|-------|
| 1 | DXY | — | > 0.02 | 1-5j | Macro baseline |
| 2 | FX (JPY/Carry) | — | > 0.02 | 1-5j | Positioning |
| 3 | Copper/Gold | — | > 0.01 | 1-5j | Risk-on/off |
| 4 | BTC/Gold | — | > 0.01 | 1-5j | Correlation shift |
| 5 | ETF Flows | — | > 0.015 | 1-5j | Capital positioning |
| 6 | Wyckoff (Spring) | ✅ Partial | > 0.025 | 1-10j | **A valider OOS** |
| 7 | UABC | — | > 0.02 | 1-10j | **PRIORITY** |
| 8 | CBD (Cost Basis) | — | > 0.015 | 5-30j | Longer horizon |
| 9 | Market Structure | — | > 0.01 | 1-5j | Liquidity zones |

### Phase B : Architecture Complète

Une fois Phase A validée, assembler selon :

```
Macro Regime (DXY, FX, Copper/Gold)
    ↓
Positioning (ETF Flows, BTC/Gold, JPY/Carry)
    ↓
Liquidity Event (Wyckoff Spring Detector)
    ↓
Structure (UABC + CBD + Market Structure)
    ↓
Entry Decision (Combined Signal)
```

À chaque étape : tester ΔIC du nouvel étage par rapport au précédent.

---

## 4. MÉTHODOLOGIE DE TEST

### 4.1 Setup de Base

```python
# Données
data = PIT_only(source_data)  # Point-in-time uniquement
train_start = date_earliest_available
train_end = date_latest - lookforward_max
test_start = date_latest - lookforward_max
test_end = date_latest

# Validation : Walk-Forward avec 6 mois de sliding
windows = WalkForward(
    train_period=6m,
    test_period=1m,
    overlap=0,
    reuse_params=False  # Paramètres figés du test
)

# Pas d'optimization en OOS
assert no_optimization_on(test_set)
```

### 4.2 Niveau 1 : Signal Individuel (IS)

**Objectif:** Vérifier que le signal a un IC positif baseline avant OOS.

```
1. Feature engineering
2. Calcul IC sur 3 ans de données (IS)
3. Check : IC > seuil minimal
4. Si IC < seuil → arrêt, pas de brique
```

**Critère acceptation:** IC > 0.01 en IS

### 4.3 Niveau 2 : Information Incrémentale (IS)

**Objectif:** Vérifier que le signal apporte quelque chose au-delà du baseline.

```
Modèle A (Baseline, ex: DXY seul)
Modèle B (Baseline + Nouvelle brique)

ΔIC = IC(B) - IC(A)

Si ΔIC < 0.005 → rejeter la brique
Si ΔIC ≈ 0 après ablation → rejeter
```

**Critère acceptation:** ΔIC > 0.005 en IS

### 4.4 Niveau 3 : Indépendance & Overlap (IS)

**Test 1: Corrélation**
```python
corr = correlation(signal_X, signal_Y)
assert abs(corr) < 0.5, "Trop corrélé, information overlap"
```

**Test 2: Mutual Information**
```python
mi = mutual_information(signal_X, signal_Y)
assert mi < threshold, "Dépendance détectée"
```

**Test 3: Ablation & Permutation**
```python
# Retirer signal_X du modèle complet
performance_without_X = train_and_eval(model - X)

# Permuter aléatoirement signal_X
performance_shuffled_X = train_and_eval(model + shuffle(X))

# Signal_X apporte-t-il vraiment ?
assert performance_full > performance_without_X
assert performance_full > performance_shuffled_X
```

**Test 4: Conditional IC**
```python
# IC de X contrôlé pour Y (X explique Y après élimination de Y)
ic_X_given_Y = ic(X | Y)
assert ic_X_given_Y > 0.003, "Zéro info après contrôle"
```

**Critère acceptation:** Indépendance confirmée par 3/4 tests

### 4.5 Niveau 4 : Reproductibilité OOS/WFV

**Walk-Forward Validation sur 3+ régimes**

```
Pour chaque fenêtre de WFV :
  1. Entrainer paramètres sur train_period
  2. Tester sur test_period sans retoucher
  3. Mesurer IC, Rank IC, hit rate
  4. Enregistrer (date, régime, IC, hit_rate, Sharpe)

Agrégation :
  IC_mean = moyenne des IC OOS
  IC_std = écart-type des IC OOS
  hit_rate_mean = moyenne des hit rates
  stability = 1 - (IC_std / IC_mean)
```

**Critère acceptation:**
- `IC_OOS_mean > IC_IS_mean * 0.8` (pas de dégradation massive)
- `IC_std < 0.008` (stabilité)
- `hit_rate > 52%` (au-dessus du 50% aléatoire)
- Persistance sur 3+ régimes différents

### 4.6 Niveau 5 : Mesures Finales

| Métrique | Calcul | Seuil Min | Raison |
|----------|--------|-----------|--------|
| **IC** | corrélation(signal, target) | > 0.015 OOS | Signal brut |
| **Rank IC** | spearman(signal_rank, target) | > 0.012 OOS | Robustesse |
| **Hit Rate** | % décisions correctes | > 52% | Au-dessus aléatoire |
| **Expectancy** | (W×win% - L×loss%) / N | > 0.001 | Asymétrie |
| **Sharpe OOS** | mean(returns) / std(returns) | > 0.5 | Risque ajusté |
| **Max DD** | drawdown maximal | < 15% | Contrôle du risque |
| **Calibration** | P(forecast=1 \| signal=x) | Brier < 0.20 | Probabilité réelle |
| **Stability** | 1 - (IC_std / IC_mean) | > 0.75 | Pas de micro-variation |
| **Contribution Marginale** | ΔPerformance avec/sans | > 0% | Info indépendante |

---

## 5. CRITÈRES D'ACCEPTATION GLOBAUX

Une composante est **acceptée** pour intégration si :

### Critère A : Signal Détecté
```
✅ IC_OOS > threshold spécifique
✅ Hit rate OOS > 52%
✅ Expectancy positive
```

### Critère B : Indépendance Confirmée
```
✅ Corrélation < 0.5 avec autres signaux
✅ MI faible (pas de dépendance)
✅ Ablation confirme l'apport (ΔPerf > 0)
✅ Permutation détruit le signal (ΔPerf_shuffle < ΔPerf_signal)
```

### Critère C : Reproductibilité OOS/WFV
```
✅ IC_OOS stable sur 3+ fenêtres WFV
✅ Pas de dégradation OOS vs IS (< 20%)
✅ Persistance sur 3+ régimes (bull, bear, sideways)
✅ Persistance sur 2+ horizons (1-5j, 5-30j)
```

### Critère D : Pas de Look-Ahead
```
✅ PIT validation (point-in-time uniquement)
✅ Timestamps strictement < signal
✅ Pas de optimization OOS
✅ Pas de data leakage (test indépendant de train)
```

### Critère E : Paramètres Figés
```
✅ Pas de tuning des paramètres en OOS
✅ Paramètres définis AVANT le test
✅ Même paramètres tout au long du WFV
✅ Pas de refitting par fenêtre (sauf train_period)
```

---

## 6. CHECKLIST DE VALIDATION

### Avant de commencer

- [ ] Composante bien définie (doc spec complète)
- [ ] Données PIT sourcing confirmé
- [ ] Fenêtres temporelles définies
- [ ] Régimes identifiés (bull, bear, sideways)
- [ ] Horizons de prédiction fixés

### Niveau 1 : Signal Individuel (IS)

- [ ] Feature engineering documenté
- [ ] IC calculé sur 3 ans IS
- [ ] IC > seuil minimal
- [ ] Pas d'anomalies de données
- [ ] Visualisation du signal vs target

### Niveau 2 : Information Incrémentale (IS)

- [ ] Baseline défini
- [ ] Modèle A (baseline) testé
- [ ] Modèle B (baseline + brique) testé
- [ ] ΔIC > 0.005 confirmé
- [ ] Pas de dégradation du baseline

### Niveau 3 : Indépendance (IS)

- [ ] Corrélation vs autres signaux < 0.5
- [ ] Mutual Information calculée
- [ ] Test d'ablation réalisé
- [ ] Test de permutation réalisé
- [ ] 3/4 tests d'indépendance passent

### Niveau 4 : OOS/WFV

- [ ] Paramètres figés (pas d'optimization)
- [ ] WFV configurée (6m train, 1m test)
- [ ] Régimes identifiés dans chaque fenêtre
- [ ] IC OOS calculé par fenêtre
- [ ] Hit rate OOS calculé par fenêtre
- [ ] Stabilité confirmée (IC_std < 0.008)
- [ ] Pas de dégradation vs IS (< 20%)

### Niveau 5 : Mesures Finales

- [ ] IC_OOS_mean enregistré
- [ ] Rank IC_OOS calculé
- [ ] Hit rate OOS > 52%
- [ ] Expectancy positive
- [ ] Sharpe OOS calculé
- [ ] Max DD < 15%
- [ ] Calibration probabiliste
- [ ] Contribution marginale > 0%

### Pas de Look-Ahead

- [ ] Dates strictes : signal_time < target_time
- [ ] PIT check : pas de future data
- [ ] Pas d'optimization sur test_set
- [ ] Code review pour leakage
- [ ] Test indépendant reproduit les résultats

### Documentation & Gel

- [ ] Rapport complet généré
- [ ] Visualisations (IC par régime, WFV curve, etc.)
- [ ] Paramètres figés dans config/
- [ ] Critères d'acceptation tous cochés
- [ ] Gate sign-off : OK pour intégration

---

## 7. GATES D'INTÉGRATION

### Gate 1 : Phase A Complète
Avant d'assembler l'architecture (Phase B) :
```
∀ composante ∈ Phase A :
  assert (Niveau 1 ✅ ET Niveau 2 ✅ ET Niveau 3 ✅ ET Niveau 4 ✅)
  assert (Critères A, B, C, D, E tous verts)
```

### Gate 2 : Phase B - Première Intégration
Avant d'ajouter la composante à la pipeline :
```
ΔIC_architecture = IC(pipeline + composante) - IC(pipeline)
assert ΔIC_architecture > 0.003, "Pas d'apport marginal"
assert no_information_leakage()
assert walk_forward_validates(ΔIC_architecture)
```

### Gate 3 : Production
Avant déploiement :
```
assert monitored_metric_aligns_with_backtest()
assert live_correlation_with_prediction > 0.8
assert no_regime_shift_undetected()
assert kill_switch_configured()
```

---

## 8. COMPOSANTES : STATUT ACTUEL

| Composante | Niveau Max Atteint | Status | Next Step |
|------------|-------------------|--------|-----------|
| Spring Detector (Wyckoff) | 4 (OOS/WFV) | 🟡 À valider OOS | WFV sur 3 régimes |
| DXY | — | ⬜ À commencer | Niveau 1 |
| FX (JPY/Carry) | — | ⬜ À commencer | Niveau 1 |
| Copper/Gold | — | ⬜ À commencer | Niveau 1 |
| BTC/Gold | — | ⬜ À commencer | Niveau 1 |
| ETF Flows | — | ⬜ À commencer | Niveau 1 |
| **UABC** | 1 (ITWT backtest) | 🔴 **PRIORITY** | Validation indépendante |
| CBD (Cost Basis) | — | ⬜ À commencer | Niveau 1 |
| Market Structure | — | ⬜ À commencer | Niveau 1 |

---

## 9. TEMPLATE DE RAPPORT

Chaque composante génère un rapport suivant ce template :

```markdown
# Validation Report : [Composante]

## Executive Summary
- Signal identifié : OUI/NON
- Information indépendante : OUI/NON
- Prêt pour intégration : OUI/NON

## Niveau 1 : Signal Individuel
- IC IS : [valeur]
- Hit rate IS : [%]
- Status : ✅/❌

## Niveau 2 : Information Incrémentale
- ΔIC vs baseline : [valeur]
- Baseline : [description]
- Status : ✅/❌

## Niveau 3 : Indépendance
- Corrélation max : [valeur]
- MI : [valeur]
- Ablation ΔPerf : [valeur]
- Permutation ΔPerf : [valeur]
- Status : ✅/❌ (3/4 tests)

## Niveau 4 : OOS/WFV
- IC_OOS_mean : [valeur]
- IC_OOS_std : [valeur]
- Hit rate OOS : [%]
- Régimes testés : [liste]
- Horizons testés : [liste]
- Status : ✅/❌

## Niveau 5 : Mesures Finales
| Métrique | IS | OOS | Seuil | Status |
|----------|----|----|-------|--------|
| IC | [x] | [x] | > 0.015 | ✅/❌ |
| Rank IC | [x] | [x] | > 0.012 | ✅/❌ |
| Hit rate | [x]% | [x]% | > 52% | ✅/❌ |
| Expectancy | [x] | [x] | > 0 | ✅/❌ |
| Sharpe OOS | [x] | [x] | > 0.5 | ✅/❌ |
| MaxDD | [x]% | [x]% | < 15% | ✅/❌ |
| Stability | [x] | [x] | > 0.75 | ✅/❌ |
| Contribution Marginale | [x] | [x] | > 0% | ✅/❌ |

## Pas de Look-Ahead
- PIT validation : ✅/❌
- Pas d'optimization OOS : ✅/❌
- Code review leakage : ✅/❌

## Conclusion
Gate status : ✅ ACCEPTÉ / ⚠️ CONDITIONNEL / ❌ REJETÉ

Si conditionnel ou rejeté :
- Issues identifiés : [liste]
- Actions correctives : [liste]
- Re-test requis : [date cible]
```

---

## 10. CALENDRIER DE VALIDATION

| Phase | Composantes | Durée Est. | Start | End |
|-------|-------------|-----------|-------|-----|
| **A.1** | Spring Detector OOS | 2-3j | Now | Now+3j |
| **A.2** | DXY, FX, Copper/Gold | 1-2w | Now+3j | Now+17j |
| **A.3** | ETF Flows, BTC/Gold | 1-2w | Now+17j | Now+31j |
| **A.4** | **UABC (Priority)** | 2-3w | Now+3j | Now+24j |
| **A.5** | CBD, Market Structure | 2w | Now+24j | Now+38j |
| **B.1** | Intégration Macro Regime | 1w | Now+38j | Now+45j |
| **B.2** | Intégration Positioning | 1w | Now+45j | Now+52j |
| **B.3** | Intégration Liquidity Event | 1w | Now+52j | Now+59j |
| **B.4** | Intégration Structure | 2w | Now+59j | Now+73j |
| **B.5** | Intégration Entry Decision | 1w | Now+73j | Now+80j |

---

## 11. NOTES D'IMPLÉMENTATION

### Code Structure
```
src/validation/
├── level_1_signal.py          # IC individuel
├── level_2_incremental.py     # ΔIC vs baseline
├── level_3_independence.py    # Corrélation, MI, ablation, permutation
├── level_4_oos_wfv.py         # Walk-forward validation
├── level_5_metrics.py         # IC, Rank IC, Hit rate, Expectancy, etc.
├── pit_validator.py           # Vérification PIT, pas de look-ahead
└── reporting.py               # Génération rapports

tests/
├── test_validation_level_1.py
├── test_validation_level_2.py
├── test_validation_level_3.py
├── test_validation_level_4.py
├── test_validation_level_5.py
└── test_pit_compliance.py
```

### Monitoring Live
Une fois validé et intégré :
```
monitoring/
├── ic_daily.py                # IC calculé quotidiennement
├── regime_detector.py         # Détection auto du régime actuel
├── kill_switch.py             # Désactiver si IC drift
└── performance_reconciliation.py  # Compare live vs backtest
```

---

**Document gelé pour IGWT-PF26.** Aucune composante n'entre en production sans passage complet de cette validation.
