"""Lineage graph validation (IGWT governance).

A lineage that nobody checks drifts into folklore: an artefact acquires a
parent because the names look alike, or because one was recorded shortly after
the other. This module refuses that. Every declared relation must resolve to
something readable in this repository, and every rule below fails the build
rather than issuing a warning.

    python -m igwt.registry.lineage        # validate and print findings

The ten rules, as implemented:

1.  every artefact has a canonical, unique id
2.  every artefact is present in the registry (its record file exists)
3.  every artefact declares a known status
4.  every relation targets a declared artefact
5.  the lineage graph is acyclic
6.  a sibling is never also declared as an ancestor
7.  every relation respects the allowed target kinds
8.  a deleted or renamed record, specification or path fails validation
9.  relation kinds are explicit and unambiguous — one kind per (source, target)
10. no relation without evidence resolvable inside this repository
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LINEAGE_PATH = Path("docs/registry/lineage.json")

#: Registry ids are uppercase and hyphenated. A code artefact is registered the
#: same way, so that rule 1 has a single form to check.
CANONICAL_ID = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")

#: Relations that carry ancestry. ``sibling`` deliberately does not.
ANCESTRY_RELATIONS = frozenset({"parent", "derived", "result_of", "contract_dependency"})


@dataclass(frozen=True)
class Finding:
    rule: int
    artefact: str
    message: str

    def __str__(self) -> str:
        return f"[rule {self.rule:>2}] {self.artefact}: {self.message}"


def load(path: Path = LINEAGE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(graph: dict, *, root: Path = Path(".")) -> list[Finding]:
    """Run every rule and return all findings, not just the first."""
    findings: list[Finding] = []
    artefacts = graph["artefacts"]

    for rule in (
        _rule_1_canonical_ids,
        _rule_2_present_in_registry,
        _rule_3_known_status,
        _rule_4_targets_exist,
        _rule_5_acyclic,
        _rule_6_sibling_is_not_an_ancestor,
        _rule_7_allowed_targets,
        _rule_8_referenced_files_exist,
        _rule_9_unambiguous_relation_kinds,
        _rule_10_evidence_resolves,
    ):
        findings.extend(rule(graph, artefacts, root))

    findings.extend(_excluded_ancestors_absent(graph, root))
    return findings


def _rule_1_canonical_ids(graph, artefacts, root) -> list[Finding]:
    return [
        Finding(1, artefact_id, "id is not canonical (expected UPPER-CASE-HYPHENATED)")
        for artefact_id in artefacts
        if not CANONICAL_ID.match(artefact_id)
    ]


def _rule_2_present_in_registry(graph, artefacts, root) -> list[Finding]:
    findings = []
    for artefact_id, artefact in artefacts.items():
        record = artefact.get("record")
        if not record:
            findings.append(Finding(2, artefact_id, "declares no registry record"))
        elif not (root / record).exists():
            findings.append(Finding(2, artefact_id, f"registry record {record} does not exist"))
    return findings


def _rule_3_known_status(graph, artefacts, root) -> list[Finding]:
    known = set(graph["statuses"])
    return [
        Finding(3, artefact_id, f"unknown status {artefact.get('status')!r}")
        for artefact_id, artefact in artefacts.items()
        if artefact.get("status") not in known
    ]


def _rule_4_targets_exist(graph, artefacts, root) -> list[Finding]:
    findings = []
    for artefact_id, artefact in artefacts.items():
        for relation in artefact.get("relations", []):
            target = relation.get("target")
            if target not in artefacts:
                findings.append(
                    Finding(4, artefact_id, f"declares {relation.get('type')} on undeclared {target!r}")
                )
    return findings


def _rule_5_acyclic(graph, artefacts, root) -> list[Finding]:
    edges = {
        artefact_id: [
            relation["target"]
            for relation in artefact.get("relations", [])
            if relation.get("type") in ANCESTRY_RELATIONS and relation.get("target") in artefacts
        ]
        for artefact_id, artefact in artefacts.items()
    }

    findings: list[Finding] = []
    visiting: set[str] = set()
    done: set[str] = set()

    def walk(node: str, trail: list[str]) -> None:
        if node in done:
            return
        if node in visiting:
            cycle = " -> ".join(trail + [node])
            findings.append(Finding(5, node, f"ancestry cycle: {cycle}"))
            return
        visiting.add(node)
        for target in edges.get(node, []):
            walk(target, trail + [node])
        visiting.discard(node)
        done.add(node)

    for artefact_id in artefacts:
        walk(artefact_id, [])
    return findings


def _rule_6_sibling_is_not_an_ancestor(graph, artefacts, root) -> list[Finding]:
    findings = []
    for artefact_id, artefact in artefacts.items():
        relations = artefact.get("relations", [])
        siblings = {item["target"] for item in relations if item.get("type") == "sibling"}
        ancestors = {
            item["target"] for item in relations if item.get("type") in ANCESTRY_RELATIONS
        }

        for target in siblings & ancestors:
            findings.append(
                Finding(6, artefact_id, f"declares {target!r} as both a sibling and an ancestor")
            )

        # The mirror case: the sibling must not claim this artefact as an ancestor.
        for sibling in siblings:
            mirror = artefacts.get(sibling, {}).get("relations", [])
            if any(
                item.get("target") == artefact_id and item.get("type") in ANCESTRY_RELATIONS
                for item in mirror
            ):
                findings.append(
                    Finding(
                        6,
                        artefact_id,
                        f"declared sibling {sibling!r} claims this artefact as an ancestor",
                    )
                )
    return findings


def _rule_7_allowed_targets(graph, artefacts, root) -> list[Finding]:
    allowed = graph["allowed_targets"]
    known_types = set(graph["relation_types"])
    findings = []

    for artefact_id, artefact in artefacts.items():
        for relation in artefact.get("relations", []):
            relation_type = relation.get("type")
            if relation_type not in known_types:
                findings.append(Finding(7, artefact_id, f"unknown relation type {relation_type!r}"))
                continue
            target = artefacts.get(relation.get("target"))
            if target is None:
                continue  # already reported by rule 4
            if target["kind"] not in allowed[relation_type]:
                findings.append(
                    Finding(
                        7,
                        artefact_id,
                        f"{relation_type} may not target a {target['kind']} "
                        f"({relation['target']}); allowed: {allowed[relation_type]}",
                    )
                )
    return findings


def _rule_8_referenced_files_exist(graph, artefacts, root) -> list[Finding]:
    findings = []
    for artefact_id, artefact in artefacts.items():
        for key in ("specification", "path"):
            reference = artefact.get(key)
            if reference and not (root / reference).exists():
                findings.append(
                    Finding(8, artefact_id, f"{key} {reference} does not exist (deleted or renamed)")
                )
    return findings


def _rule_9_unambiguous_relation_kinds(graph, artefacts, root) -> list[Finding]:
    findings = []
    for artefact_id, artefact in artefacts.items():
        seen: dict[str, str] = {}
        for relation in artefact.get("relations", []):
            target = relation.get("target")
            relation_type = relation.get("type")
            if target in seen:
                findings.append(
                    Finding(
                        9,
                        artefact_id,
                        f"declares {target!r} twice, as {seen[target]!r} and {relation_type!r}",
                    )
                )
            else:
                seen[target] = relation_type
    return findings


def _rule_10_evidence_resolves(graph, artefacts, root) -> list[Finding]:
    """Rule 10 made enforceable: no evidence, no relation.

    This is what stops ancestry being inferred from a name or from two records
    happening to be written the same week.
    """
    findings = []
    for artefact_id, artefact in artefacts.items():
        for relation in artefact.get("relations", []):
            evidence = relation.get("evidence")
            target = relation.get("target")
            if not evidence:
                findings.append(
                    Finding(10, artefact_id, f"relation on {target!r} carries no evidence")
                )
                continue

            if "shared_ancestor" in evidence:
                findings.extend(
                    _check_shared_ancestor(artefact_id, target, evidence, artefacts)
                )
                continue

            reference = evidence.get("file")
            if not reference:
                findings.append(
                    Finding(10, artefact_id, f"evidence for {target!r} names no file")
                )
                continue

            path = root / reference
            if not path.exists():
                findings.append(
                    Finding(10, artefact_id, f"evidence file {reference} does not exist")
                )
                continue

            needle = evidence.get("contains")
            if needle and needle not in path.read_text(encoding="utf-8"):
                findings.append(
                    Finding(
                        10,
                        artefact_id,
                        f"evidence file {reference} no longer contains {needle!r}",
                    )
                )
    return findings


def _check_shared_ancestor(artefact_id, target, evidence, artefacts) -> list[Finding]:
    """A sibling claim is evidenced by both sides descending from one ancestor."""
    ancestor = evidence["shared_ancestor"]
    findings = []
    for side in (artefact_id, target):
        relations = artefacts.get(side, {}).get("relations", [])
        if not any(
            item.get("target") == ancestor and item.get("type") in ANCESTRY_RELATIONS
            for item in relations
        ):
            findings.append(
                Finding(
                    10,
                    artefact_id,
                    f"sibling evidence names {ancestor!r} as a shared ancestor, "
                    f"but {side!r} does not descend from it",
                )
            )
    return findings


def _excluded_ancestors_absent(graph, root) -> list[Finding]:
    """An excluded external reference must stay absent from this repository.

    If one ever appears, this fails — forcing a governance decision instead of
    letting the reference quietly become a parent.
    """
    excluded = graph.get("excluded_ancestors")
    if not excluded:
        return []

    exceptions = {root / item for item in excluded.get("search_exceptions", [])}
    findings = []

    for token in excluded["tokens"]:
        pattern = re.compile(rf"\b{re.escape(token)}\b")
        for scope in excluded["search_scope"]:
            for path in _text_files(root / scope):
                if path in exceptions or path.resolve() == (root / LINEAGE_PATH).resolve():
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if pattern.search(content):
                    findings.append(
                        Finding(
                            10,
                            token,
                            f"excluded external reference appears in {path}; "
                            "it must not become a lineage parent without a verifiable link",
                        )
                    )
    return findings


def _text_files(target: Path):
    if target.is_file():
        yield target
    elif target.is_dir():
        for path in sorted(target.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                yield path


def main(argv: list[str] | None = None) -> int:
    graph = load()
    findings = validate(graph)
    if not findings:
        print(f"lineage: {len(graph['artefacts'])} artefacts, 10 rules, no findings")
        return 0
    for finding in findings:
        print(finding, file=sys.stderr)
    print(f"lineage: {len(findings)} finding(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
