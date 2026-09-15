# REAL-DATA-FULL-001 — pending acquisition

This directory is intentionally empty of data.

`preflight.json` records the acquisition attempt: Binance is not reachable from
this environment (`data-api.binance.vision` refused by the egress policy,
`api.binance.com` answering HTTP 451 for this region). No dataset is fabricated
to fill the gap.

The pipeline that will populate this directory is implemented, audited and
tested — see `docs/specs/REAL-DATA-FULL-001.md`. It runs the moment either
ingress path opens:

```bash
python -m igwt.fixtures.real_data_full_001 --preflight
python -m igwt.fixtures.real_data_full_001 --from-files <dir>   # vendor CSV exports
python -m igwt.fixtures.real_data_full_001 --fetch              # Binance public API
```

`REAL-DATA-FIXTURE-001` stays locked and untouched: this is a second dataset to
compare against, never a replacement.
