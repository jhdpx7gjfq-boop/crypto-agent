"""
Layer 1: Data Intelligence

Responsible for data collection, validation, and immutable snapshot management.

Controls:
- C1.1: Historical Availability
- C1.2: Timestamp Precision & Stability
- C1.3: Forecast + Actual Availability
- C1.4: Revision Traceability (via C1.4-IGWT capture-layer audit)
- C1.5: Point-in-Time Reconstruction (via C1.5-IGWT snapshot freezing, NOT C1.5-PIT)
- C1.6: BTC/ETH Intraday Alignment ≥15m
- C1.7: Event Inventory Coverage

CRITICAL INVARIANT:
- PIT_STATUS = "UNVERIFIED" (mandatory default on all artifacts)
- Prevents accidental conflation of C1.5-IGWT (reproducibility) with C1.5-PIT (provider availability)
"""

from .snapshot_manifest import SnapshotManifest, SourceMetadata, Checksum

__all__ = [
    "SnapshotManifest",
    "SourceMetadata",
    "Checksum",
]
