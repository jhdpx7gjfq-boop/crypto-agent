# crypto-agent — IGWT-PF26

Infrastructure de recherche quantitative. Aucune exécution de trade, aucun accès
API trading, aucun CEX authentifié : les modules ci-dessous lisent des données
publiques et produisent des artefacts de recherche. La décision reste humaine.

## Couche recherche — `igwt/`

```
igwt/
├── data/         collecte (CoinGecko) + store brut immuable haché
├── features/     validation de snapshot, panel, features point-in-time
├── fixtures/     REAL-DATA-FIXTURE-001
└── validation/   WFV v2 — walk-forward purgé et sous embargo
```

| Artefact | Statut | Document |
|---|---|---|
| Contrat WFV v2 | **FROZEN** | [`docs/specs/WFV-V2-CONTRACT.md`](docs/specs/WFV-V2-CONTRACT.md) |
| REAL-DATA-FIXTURE-001 | **LOCKED** | [`docs/specs/REAL-DATA-FIXTURE-001.md`](docs/specs/REAL-DATA-FIXTURE-001.md) |
| REAL-DATA-FULL-001 | **PENDING ACQUISITION** | [`docs/specs/REAL-DATA-FULL-001.md`](docs/specs/REAL-DATA-FULL-001.md) |
| MOMENTUM-30D-WFV-001 | **NO EVIDENCE OF EDGE** | [`docs/registry/`](docs/registry/REGISTRY.md) |

Les verrous de gouvernance sont vérifiés par la CI (`tests/test_registry_locks.py`) :
un artefact verrouillé qui dérive fait échouer le build. Voir
[`docs/registry/REGISTRY.md`](docs/registry/REGISTRY.md).

```bash
python -m igwt.fixtures.real_data_fixture_001          # reconstruire depuis raw/
python -m igwt.fixtures.real_data_fixture_001 --fetch  # recollecter puis reconstruire
python -m igwt.validation.run_fixture_wfv              # rejouer WFV v2 + gate
python -m igwt.fixtures.real_data_full_001 --preflight # état d'acquisition Binance
```

Artefacts sous `fixtures/real/REAL-DATA-FIXTURE-001/` : snapshots bruts hachés,
`observations.csv`, `manifest.json` (provenance et rejets), `wfv_report.json`.

**Provenance** : le registre IGWT documente des datasets Binance quotidiens qui
n'étaient pas atteignables depuis cet environnement (fichiers absents,
`api.binance.com` en HTTP 451, autres venues refusées par la politique réseau).
Le fixture est donc construit sur CoinGecko — source n°1 de la Layer 1 — avec
l'écart documenté dans le manifeste. Aucune valeur n'est simulée.

## Couche alerte — `main.py`

Interroge le prix BTC/USD chez CoinGecko et envoie une alerte Telegram au
franchissement des seuils configurés.

Variables d'environnement (ne jamais committer de secret) :

- `BOT_TOKEN` — token du bot Telegram
- `CHAT_ID` — identifiant de conversation à notifier
- `HIGH_THRESHOLD` — seuil haut en USD (défaut `70000`)
- `LOW_THRESHOLD` — seuil bas en USD (défaut `55000`)
- `POLL_SECONDS` — intervalle d'interrogation (défaut `60`)

```bash
pip install -r requirements.txt
BOT_TOKEN=... CHAT_ID=... python main.py
```

Tourne comme process `worker` (voir `Procfile`), pas `web` — sur Heroku :
`heroku ps:scale worker=1`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

La suite est hors-ligne : les appels réseau sont mockés et les tests du fixture
relisent les artefacts committés.
