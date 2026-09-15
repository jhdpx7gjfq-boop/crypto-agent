# WFV v2 — Contrat et spécification du validateur

| | |
|---|---|
| **Module** | `igwt.validation.wfv` |
| **Couche IGWT** | Layer 8 — Walk Forward Validator |
| **Version** | `igwt 0.1.0` |

---

## 1. Contrat d'entrée

Une **observation** est un mapping portant exactement cinq clés :

| Clé | Type | Rôle |
|---|---|---|
| `date` | `datetime.date` | horodatage point-in-time |
| `asset` | `str` | symbole |
| `signal` | `float` | entrée du modèle, calculée sur `… ≤ date` |
| `fwdRet` | `float` | label, réalisé sur `(date, date + horizon]` |
| `regimeVol` | `float` | volatilité glissante en `date`, conditionneur |

`validate_contract()` refuse : colonne manquante, `date` non typée, valeur non
finie ou `NaN`, `regimeVol` négative, doublon `(date, asset)`, entrée vide.

Le refus est volontairement bruyant. Une observation malformée qui traverse le
validateur ressort sous forme de moyenne — c'est-à-dire invisible.

---

## 2. Purge et embargo

`fwdRet` en `t` n'est connu qu'en `t + horizon`. S'entraîner sur `t` puis
tester en `t + 1` revient donc à tester sur un résultat que le label
d'entraînement contenait déjà.

Chaque fold laisse un intervalle d'au moins `horizon` jours entre la dernière
date d'entraînement et la première date de test :

```
train_start ──────── train_end │ embargo ≥ horizon │ test_start ──── test_end
```

Deux garde-fous indépendants :

1. `WFVConfig.resolved_embargo()` refuse `embargo_days < horizon_days`.
2. `assert_no_leakage()` revérifie **ligne à ligne** que
   `row.date + horizon < test_start`, sur les lignes réellement utilisées — pas
   seulement sur les bornes du fold.

---

## 3. Ce qui est ajusté

**Un seul paramètre : le signe du signal**, déterminé sur la fenêtre
d'entraînement.

Pas de recherche de grille, pas de seuil optimisé, pas de réutilisation de la
fenêtre de test. Un validateur qui optimise à l'intérieur du fold mesure son
propre optimiseur, pas le signal.

Le seuil de régime (`regimeVol`) est lui aussi appris sur l'entraînement
(médiane de la volatilité de marché) puis appliqué tel quel hors échantillon.

---

## 4. Métriques

| Métrique | Calcul |
|---|---|
| IC quotidien | Spearman(`signal`, `fwdRet`) **au sein d'une date**, puis moyenné |
| `train_ic` | moyenne des IC quotidiens sur l'entraînement |
| `fitted_direction` | `sign(train_ic)` — le paramètre ajusté |
| `oos_ic` | moyenne des IC quotidiens hors échantillon, signés |
| `oos_ic_t_stat` | t-stat de cette moyenne contre zéro |
| `oos_hit_rate` | part de dates à IC signé positif |
| `oos_long_short_spread` | rendement moyen de la jambe haute moins la jambe basse |
| `direction_flips` | changements de signe entre folds consécutifs |
| `regime_conditioned` | IC hors échantillon, séparé basse / haute volatilité |

L'IC est transversal par date avant d'être moyenné : un mouvement de marché
commun à tous les actifs ne peut pas être compté comme de la compétence.

**Limite déclarée** : les rendements forward de dates voisines se chevauchent,
les IC quotidiens ne sont donc pas indépendants. Le t-stat se lit comme un
ordre de grandeur, pas comme une p-value.

`direction_flips` mérite une lecture particulière : un signe qui ne tient pas
en place d'un fold à l'autre est le signal qui dit lui-même qu'il n'est pas
stable, quelle que soit l'IC moyenne.

---

## 5. Sensibilité et spécificité du validateur

Un validateur doit être testé dans les deux sens (`tests/test_wfv.py`) :

| Entrée construite | Attendu | Vérifié |
|---|---|---|
| `signal = fwdRet` | IC hors échantillon ≈ **+1** | oui |
| `signal = -fwdRet` | direction apprise **-1**, IC ≈ **+1** | oui |
| `signal` = bruit indépendant | \|IC\| < 0.15, \|t\| < 2 | oui |

Ces trois tests utilisent des données synthétiques — c'est leur place : on y
interroge le validateur, dont la réponse doit être connue d'avance. Le fixture,
lui, n'en contient aucune.

---

## 6. Usage

```python
from igwt.validation import wfv

config = wfv.WFVConfig(horizon_days=7, train_days=180, test_days=30)
report = wfv.run(observations, config)
```

`embargo_days` vaut `horizon_days` par défaut, `step_days` vaut `test_days`
(fenêtres de test non chevauchantes), `mode` vaut `"rolling"` (`"expanding"`
disponible).

---

## 7. Hors périmètre

Ce module valide la **stabilité hors échantillon d'un signal**. Il n'est pas un
moteur de backtest : pas de coûts de transaction, pas de slippage, pas de
dimensionnement de position, pas de courbe d'équité. Les seuils du registre
(`Trades ≥ 200`, `Profit Factor > 1.3`, `Max Drawdown < 25%`) relèvent du
**RPM X20 Optimizer Engine** et ne sont ni calculés ni satisfaits ici.
