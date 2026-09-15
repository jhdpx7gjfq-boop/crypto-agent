"""Immutable raw store (IGWT Layer 1 — Snapshot Validator / Raw Store).

A snapshot is the *unmodified* provider response, written once and hashed. Any
downstream artefact can be rebuilt from it, and any silent drift in a provider
response is caught by the hash rather than absorbed into a dataset.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class SnapshotConflict(RuntimeError):
    """Raised when a snapshot already exists with different content."""


def canonical_bytes(payload: object) -> bytes:
    """Serialise a payload deterministically, so its hash is reproducible."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_snapshot(root: Path, name: str, payload: object, *, overwrite: bool = False) -> dict:
    """Write ``payload`` to ``root/name.json`` and return its provenance record.

    Re-writing identical content is a no-op. Re-writing *different* content
    raises ``SnapshotConflict`` unless ``overwrite`` is set: raw history is
    append-only by default.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.json"
    data = canonical_bytes(payload)
    digest = sha256_hex(data)

    if path.exists():
        existing = path.read_bytes()
        if existing == data:
            return _record(path, digest, len(data), status="unchanged")
        if not overwrite:
            raise SnapshotConflict(
                f"{path} already exists with sha256={sha256_hex(existing)}, "
                f"refusing to replace it with sha256={digest}"
            )

    path.write_bytes(data)
    return _record(path, digest, len(data), status="written")


def read_snapshot(root: Path, name: str) -> object:
    return json.loads((Path(root) / f"{name}.json").read_bytes())


def _record(path: Path, digest: str, size: int, *, status: str) -> dict:
    return {"file": path.name, "sha256": digest, "bytes": size, "status": status}
