# Blockers Register
**Date**: 2026-10-06  
**Authority**: Session Guard  

## M4.2 WFV BCE  
**Status**: 🔴 CLOSED / FAIL  
**Finding**: F1=0.0000 (no valid BCE signals on BTC 1D 2020-2025)  
**Root Cause**: BCE designed for accumulation; BTC in expansion. Market regime mismatch.  
**Resolution**: Documented real finding; no code changes required.

---

## CoinDesk C2-C6  
**Status**: 🔴 BLOCKED — Artifact Absent  
**Scope**: C1 (framework) ✅ PASS | C2-C6 (live API, validation) 🔴 NOT IMPLEMENTED  
**Blocker**: CoinDesk collector + tests missing from repo  
**Search Result**: `/src/data/`, `/src/layers/layer1_data/`, `/tests/` → zero CoinDesk code  
**Do NOT**: Create CoinDesk code | Redefine C2-C6 | Modify CoinGecko  
**Next Step**: Recover CoinDesk implementation from external source or defer until available  

---

## Traceability Note
CoinDesk C2-C6 was defined in conversation history but not committed to repo.  
This is a **governance/traceability issue**, not a technical failure.
