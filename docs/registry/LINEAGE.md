# Filiation des artefacts IGWT

Graphe canonique : [`lineage.json`](lineage.json).
Validateur : `igwt/registry/lineage.py` — `python -m igwt.registry.lineage`.
Application CI : `tests/test_lineage.py`.

---

## 1. Structure canonique

```text
┌──────────────────────────┐
│     WFV-V2-CONTRACT      │
│         FROZEN           │
└────────────┬─────────────┘
             │ contract_dependency
             ▼
┌──────────────────────────┐
│  REAL-DATA-FIXTURE-001   │
│         LOCKED           │
└──────┬─────────────┬─────┘
       │ derived     │ parent
       ▼             ▼
 contract.py   REAL-DATA-FULL-001
 (CODE-        PENDING_ACQUISITION
  FEATURE-           │
  CONTRACT)          ├── acquisition
       │             ├── RAW
       ├─ fixture    ├── integrity audit
       │  CoinGecko  ├── normalization
       └─ pipeline   ├── PIT
          Binance    ├── features
                     └── WFV
```

Et, en parallèle — **résultat, pas prédécesseur** :

```text
REAL-DATA-FIXTURE-001
        │ result_of
        ▼
MOMENTUM-30D-WFV-001
  NO EVIDENCE OF EDGE
  PRODUCTION FORBIDDEN
        │
        └── sibling ──► REAL-DATA-FULL-001
            (ancêtre commun : REAL-DATA-FIXTURE-001)
```

La relation interdite, explicitement :

```text
MOMENTUM-30D-WFV-001 ──✗──► REAL-DATA-FULL-001   (jamais un parent)
```

Le résultat momentum ne conditionne pas l'acquisition Binance. Les deux
descendent du même fixture et ne dépendent pas l'un de l'autre. La règle 6
échoue en CI si cette arête devient une filiation.

---

## 2. Ascendances exclues

```text
DATA-005      ──✗── REAL-DATA-FIXTURE-001
DATA-005      ──✗── CODE-FEATURE-CONTRACT
DATA-005      ──✗── REAL-DATA-FULL-001
FeatureRegistry, GLME, DPE, LSI, SCE   ──✗── (idem)
```

Ces identifiants apparaissent dans des notes de travail IGWT externes mais
**sont absents de ce dépôt**. Tant qu'aucun lien vérifiable n'existe ici,
aucune référence externe ne devient un parent.

Le validateur ne se contente pas de les omettre : il **vérifie qu'ils restent
absents** du code, des tests, des fixtures et des spécifications. Si l'un
d'eux réapparaît, la CI échoue — ce qui force une décision de gouvernance au
lieu de laisser la référence redevenir silencieusement un parent.

`igwt/features/contract.py` a une seule ascendance vérifiable : l'extraction du
code de features qui se trouvait à l'intérieur du builder de
`REAL-DATA-FIXTURE-001`, sortie inchangée au hachage près.

---

## 3. Types de relations

Cinq types, distincts et non interchangeables. C'est cette distinction qui
empêche l'erreur « résultat pris pour prédécesseur ».

| Type | Signification |
|---|---|
| `contract_dependency` | cet artefact doit satisfaire le contrat cible |
| `parent` | cet artefact descend de la cible : même code de features et mêmes paramètres, ou la cible est le contrôle auquel il se compare |
| `derived` | cet artefact a été extrait de la cible |
| `result_of` | cet artefact est un résultat de recherche calculé sur le dataset cible |
| `sibling` | les deux partagent un ancêtre et aucun ne dépend de l'autre |

`sibling` ne porte **aucune** ascendance : il est exclu du calcul de cycles et
interdit de coexister avec une arête d'ascendance vers la même cible.

---

## 4. Les dix règles, appliquées en CI

| # | Règle | Échec si |
|---|---|---|
| 1 | identifiant canonique et unique | id non conforme à `UPPER-CASE-HYPHENATED` |
| 2 | présent dans le registre | l'enregistrement déclaré n'existe pas |
| 3 | statut connu | statut hors de la table des statuts |
| 4 | parents existants | une relation vise un artefact non déclaré |
| 5 | absence de cycle | le graphe d'ascendance boucle |
| 6 | un frère n'est jamais un ancêtre | `sibling` et ascendance vers la même cible, dans un sens ou dans l'autre |
| 7 | relations autorisées | type de cible non autorisé pour ce type de relation |
| 8 | suppression / renommage | une spécification ou un chemin déclaré n'existe plus |
| 9 | types explicites | deux relations de types différents vers la même cible |
| 10 | aucune filiation inférée | une relation sans preuve, ou dont la preuve ne résout plus |

### La règle 10, rendue exécutoire

C'est la règle qui compte le plus, parce que c'est celle qu'on enfreint sans
s'en apercevoir. Elle est traduite en contrainte vérifiable :

> **Aucune relation sans preuve résolvant dans ce dépôt.**

Chaque arête porte un champ `evidence` :

- soit un fichier **et** une chaîne qu'il doit contenir — la CI ouvre le
  fichier et vérifie la chaîne ;
- soit, pour un `sibling`, un `shared_ancestor` — la CI vérifie que **les deux
  côtés** déclarent effectivement une ascendance vers cet ancêtre.

Une filiation ne peut donc pas naître d'une ressemblance de nom ni d'une
proximité de date : il faut qu'une ligne de ce dépôt la porte, et elle échoue
dès que cette ligne disparaît.

---

## 5. Règle d'amendement n°1

> **Une nouvelle source de données ne modifie jamais rétroactivement un
> artefact de recherche existant. Lorsque la portée méthodologique change, elle
> crée une nouvelle référence.**

Conséquence concrète, quand Binance deviendra disponible :

```text
REAL-DATA-FULL-001
        │ result_of
        ▼
MOMENTUM-30D-WFV-002
        └── nouvelle portée, nouveau résultat, nouvelle validation
```

`MOMENTUM-30D-WFV-001` n'est **ni révisé ni débloqué**. Il reste figé sur sa
portée — composite CoinGecko, 2025-10-16 → 2026-09-08 — et les deux résultats
coexistent, comparables parce qu'ils partagent le contrat gelé et la même
implémentation de features.
