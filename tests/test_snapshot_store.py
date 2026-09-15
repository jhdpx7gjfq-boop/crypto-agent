"""The raw store is append-only: silent provider drift must not be absorbed."""

import pytest

from igwt.data import snapshot


def test_writing_then_rereading_round_trips(tmp_path):
    record = snapshot.write_snapshot(tmp_path, "X", {"prices": [[1, 2.0]]})
    assert record["status"] == "written"
    assert snapshot.read_snapshot(tmp_path, "X") == {"prices": [[1, 2.0]]}


def test_rewriting_identical_content_is_a_noop(tmp_path):
    payload = {"prices": [[1, 2.0]]}
    first = snapshot.write_snapshot(tmp_path, "X", payload)
    second = snapshot.write_snapshot(tmp_path, "X", payload)
    assert second["status"] == "unchanged"
    assert second["sha256"] == first["sha256"]


def test_rewriting_different_content_is_refused(tmp_path):
    snapshot.write_snapshot(tmp_path, "X", {"prices": [[1, 2.0]]})
    with pytest.raises(snapshot.SnapshotConflict, match="refusing to replace"):
        snapshot.write_snapshot(tmp_path, "X", {"prices": [[1, 3.0]]})


def test_overwrite_is_possible_but_must_be_explicit(tmp_path):
    snapshot.write_snapshot(tmp_path, "X", {"prices": [[1, 2.0]]})
    record = snapshot.write_snapshot(tmp_path, "X", {"prices": [[1, 3.0]]}, overwrite=True)
    assert record["status"] == "written"


def test_the_hash_is_independent_of_key_order(tmp_path):
    first = snapshot.canonical_bytes({"a": 1, "b": 2})
    second = snapshot.canonical_bytes({"b": 2, "a": 1})
    assert snapshot.sha256_hex(first) == snapshot.sha256_hex(second)
