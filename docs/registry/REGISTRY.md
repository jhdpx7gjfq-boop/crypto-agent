# Registre IGWT — artefacts de recherche

Statuts de gouvernance. Les verrous ci-dessous sont **vérifiés par la CI**
(`tests/test_registry_locks.py`) : un artefact qui dérive fait échouer le build.

| Artefact | Statut | Enregistrement |
|---|---|---|
| `WFV-V2-CONTRACT` | **FROZEN** | [`WFV-V2-CONTRACT.lock.json`](WFV-V2-CONTRACT.lock.json) |
| `REAL-DATA-FIXTURE-001` | **LOCKED** | [`REAL-DATA-FIXTURE-001.lock.json`](REAL-DATA-FIXTURE-001.lock.json) |
| `MOMENTUM-30D-WFV-001` | **INCONCLUSIVE / NO EVIDENCE OF EDGE** — production **FORBIDDEN** | [`MOMENTUM-30D-WFV-001.json`](MOMENTUM-30D-WFV-001.json) |
| `REAL-DATA-FULL-001` | **PENDING ACQUISITION** | [`../specs/REAL-DATA-FULL-001.md`](../specs/REAL-DATA-FULL-001.md) |

## Règles d'amendement

1. Un artefact `LOCKED` n'est jamais modifié rétroactivement. Une source, une
   profondeur ou un champ de prix différents produisent un **nouvel identifiant**.
2. Le contrat WFV v2 est gelé : toute modification des colonnes, de leur
   sémantique, de la règle d'embargo ou de la précision de sérialisation est un
   **WFV v3** et invalide tous les verrous qui citent celui-ci.
3. Un résultat de recherche est enregistré avec sa portée. `MOMENTUM-30D-WFV-001`
   est négatif **sur cette population, cette période et cette définition du
   signal** — il n'établit pas que le momentum est invalidé.
4. Ces PASS sont des PASS de **recherche**. Rien ici n'est intégré en production
   IGWT, et aucun moteur BCE / X20 / RPM / NARM-P+ n'est touché.

## État du gel production

```
Infrastructure WFV v2        VALIDATED
Isolation synthétique        VALIDATED
Fixture réel (contrôle)      VALIDATED / LOCKED
PIT / anti-lookahead         VALIDATED
Exécution WFV                VALIDATED

Edge momentum-30d            NO EVIDENCE
Données historiques Binance  BLOCKED — voir REAL-DATA-FULL-001
OHLC complet                 BLOCKED
Dataset compatible BCE       BLOCKED UNTIL OHLC

Production IGWT              FROZEN
BCE / X20 / RPM / NARM-P+    UNTOUCHED
```
