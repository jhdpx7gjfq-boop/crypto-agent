"""Lineage governance: the canonical graph, and proof that each rule bites.

A rule that has never failed is a rule nobody has tested. Every rule below is
exercised twice — once on the real graph, which must pass, and once on a
deliberately broken copy, which must produce that rule's finding.
"""

import copy
import json
import shutil
from pathlib import Path

import pytest

from igwt.registry import lineage

REPO = Path(".")


@pytest.fixture(scope="module")
def graph():
    return lineage.load()


def rules_fired(findings):
    return {finding.rule for finding in findings}


def broken(graph, artefact, **changes):
    """A copy of the real graph with one artefact altered."""
    mutated = copy.deepcopy(graph)
    mutated["artefacts"][artefact].update(changes)
    return mutated


class TestCanonicalGraph:
    def test_the_committed_lineage_passes_every_rule(self, graph):
        findings = lineage.validate(graph, root=REPO)
        assert findings == [], "\n".join(str(item) for item in findings)

    def test_the_declared_artefacts_are_the_expected_five(self, graph):
        assert set(graph["artefacts"]) == {
            "WFV-V2-CONTRACT",
            "REAL-DATA-FIXTURE-001",
            "CODE-FEATURE-CONTRACT",
            "REAL-DATA-FULL-001",
            "MOMENTUM-30D-WFV-001",
        }

    def test_the_contract_is_the_root(self, graph):
        assert graph["artefacts"]["WFV-V2-CONTRACT"]["relations"] == []

    def test_the_feature_code_descends_from_the_fixture_and_nothing_else(self, graph):
        relations = graph["artefacts"]["CODE-FEATURE-CONTRACT"]["relations"]
        derived = [item for item in relations if item["type"] == "derived"]
        assert [item["target"] for item in derived] == ["REAL-DATA-FIXTURE-001"]

    def test_the_momentum_result_is_a_result_not_an_ancestor_of_the_full_dataset(self, graph):
        momentum = graph["artefacts"]["MOMENTUM-30D-WFV-001"]["relations"]
        by_target = {item["target"]: item["type"] for item in momentum}
        assert by_target["REAL-DATA-FIXTURE-001"] == "result_of"
        assert by_target["REAL-DATA-FULL-001"] == "sibling"

        full = graph["artefacts"]["REAL-DATA-FULL-001"]["relations"]
        assert "MOMENTUM-30D-WFV-001" not in {item["target"] for item in full}

    def test_the_full_dataset_descends_from_the_locked_control(self, graph):
        relations = graph["artefacts"]["REAL-DATA-FULL-001"]["relations"]
        by_target = {item["target"]: item["type"] for item in relations}
        assert by_target["REAL-DATA-FIXTURE-001"] == "parent"
        assert by_target["WFV-V2-CONTRACT"] == "contract_dependency"


class TestEachRuleBites:
    def test_rule_1_rejects_a_non_canonical_id(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["lowercase_id"] = mutated["artefacts"].pop("WFV-V2-CONTRACT")
        assert 1 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_2_rejects_a_missing_registry_record(self, graph):
        mutated = broken(graph, "REAL-DATA-FIXTURE-001", record="docs/registry/absent.json")
        findings = lineage.validate(mutated, root=REPO)
        assert 2 in rules_fired(findings)

    def test_rule_2_rejects_an_artefact_with_no_record_at_all(self, graph):
        mutated = copy.deepcopy(graph)
        del mutated["artefacts"]["MOMENTUM-30D-WFV-001"]["record"]
        assert 2 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_3_rejects_an_unknown_status(self, graph):
        mutated = broken(graph, "REAL-DATA-FULL-001", status="PROBABLY_FINE")
        assert 3 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_4_rejects_a_relation_to_an_undeclared_artefact(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"].append(
            {"type": "parent", "target": "DATA-005", "evidence": {"file": "README.md"}}
        )
        assert 4 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_5_rejects_a_cycle(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["REAL-DATA-FIXTURE-001"]["relations"].append(
            {
                "type": "parent",
                "target": "REAL-DATA-FULL-001",
                "evidence": {"file": "README.md", "contains": "IGWT"},
            }
        )
        assert 5 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_6_rejects_a_sibling_that_is_also_an_ancestor(self, graph):
        """The exact error this lineage exists to prevent."""
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["MOMENTUM-30D-WFV-001"]["relations"].append(
            {
                "type": "parent",
                "target": "REAL-DATA-FULL-001",
                "evidence": {"file": "README.md", "contains": "IGWT"},
            }
        )
        findings = lineage.validate(mutated, root=REPO)
        assert 6 in rules_fired(findings)

    def test_rule_6_rejects_the_mirror_case(self, graph):
        """MOMENTUM declares FULL a sibling; FULL must not claim MOMENTUM as an ancestor."""
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"].append(
            {
                "type": "result_of",
                "target": "MOMENTUM-30D-WFV-001",
                "evidence": {"file": "README.md", "contains": "IGWT"},
            }
        )
        findings = lineage.validate(mutated, root=REPO)
        assert 6 in rules_fired(findings)
        assert any("claims this artefact as an ancestor" in str(item) for item in findings)

    def test_rule_7_rejects_a_contract_dependency_on_a_dataset(self, graph):
        mutated = copy.deepcopy(graph)
        relations = mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"]
        # Keep only the contract dependency, then point it at a dataset, so this
        # asserts rule 7 alone rather than tripping the duplicate-target rule.
        mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"] = [relations[0]]
        relations[0]["target"] = "REAL-DATA-FIXTURE-001"
        findings = lineage.validate(mutated, root=REPO)
        assert 7 in rules_fired(findings)
        assert 9 not in rules_fired(findings)

    def test_rule_7_rejects_a_result_of_pointing_at_a_contract(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["MOMENTUM-30D-WFV-001"]["relations"][0]["target"] = "WFV-V2-CONTRACT"
        assert 7 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_7_rejects_an_unknown_relation_type(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["MOMENTUM-30D-WFV-001"]["relations"][0]["type"] = "inspired_by"
        assert 7 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_8_rejects_a_renamed_code_path(self, graph, tmp_path):
        """A rename is indistinguishable from a deletion, and both must fail."""
        shutil.copytree(REPO / "igwt", tmp_path / "igwt")
        shutil.copytree(REPO / "docs", tmp_path / "docs")
        (tmp_path / "igwt/features/contract.py").rename(tmp_path / "igwt/features/renamed.py")

        findings = lineage.validate(graph, root=tmp_path)
        assert 8 in rules_fired(findings)
        assert any("deleted or renamed" in str(item) for item in findings)

    def test_rule_9_rejects_two_relation_kinds_to_the_same_target(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"].append(
            {
                "type": "derived",
                "target": "REAL-DATA-FIXTURE-001",
                "evidence": {"file": "README.md", "contains": "IGWT"},
            }
        )
        assert 9 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_10_rejects_a_relation_without_evidence(self, graph):
        mutated = copy.deepcopy(graph)
        del mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"][1]["evidence"]
        findings = lineage.validate(mutated, root=REPO)
        assert 10 in rules_fired(findings)
        assert any("carries no evidence" in str(item) for item in findings)

    def test_rule_10_rejects_evidence_that_no_longer_resolves(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"][1]["evidence"]["contains"] = (
            "CONTROL_FIXTURE = \"SOMETHING-ELSE\""
        )
        findings = lineage.validate(mutated, root=REPO)
        assert 10 in rules_fired(findings)
        assert any("no longer contains" in str(item) for item in findings)

    def test_rule_10_rejects_evidence_naming_a_missing_file(self, graph):
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["REAL-DATA-FULL-001"]["relations"][1]["evidence"]["file"] = "gone.py"
        assert 10 in rules_fired(lineage.validate(mutated, root=REPO))

    def test_rule_10_rejects_a_sibling_claim_with_no_shared_ancestor(self, graph):
        """A sibling claim is only as good as the ancestry both sides declare."""
        mutated = copy.deepcopy(graph)
        mutated["artefacts"]["MOMENTUM-30D-WFV-001"]["relations"][1]["evidence"] = {
            "shared_ancestor": "WFV-V2-CONTRACT"
        }
        findings = lineage.validate(mutated, root=REPO)
        assert 10 in rules_fired(findings)
        assert any("does not descend from it" in str(item) for item in findings)


class TestExcludedAncestors:
    def test_the_excluded_references_are_absent_from_the_repository(self, graph):
        findings = lineage._excluded_ancestors_absent(graph, REPO)
        assert findings == [], "\n".join(str(item) for item in findings)

    def test_data_005_is_named_as_excluded_with_a_reason(self, graph):
        excluded = graph["excluded_ancestors"]
        assert "DATA-005" in excluded["tokens"]
        assert "absent from this repository" in excluded["reason"]

    def test_the_check_fires_when_an_excluded_reference_reappears(self, graph, tmp_path):
        (tmp_path / "igwt").mkdir()
        (tmp_path / "igwt" / "sneaky.py").write_text(
            '"""Derived from DATA-005 FeatureRegistry."""\n', encoding="utf-8"
        )
        mutated = copy.deepcopy(graph)
        mutated["excluded_ancestors"]["search_scope"] = ["igwt"]

        findings = lineage._excluded_ancestors_absent(mutated, tmp_path)
        assert findings, "an excluded reference reappeared and was not caught"
        assert any("must not become a lineage parent" in str(item) for item in findings)


class TestAmendmentRules:
    def test_amendment_rule_one_is_recorded_verbatim(self, graph):
        rule = graph["amendment_rules"]["new_source_never_amends"]
        assert "never retroactively modifies" in rule
        assert "creates a new reference" in rule

    def test_the_no_inferred_ancestry_rule_is_recorded(self, graph):
        rule = graph["amendment_rules"]["no_inferred_ancestry"]
        assert "never inferred" in rule
        assert "evidence" in rule

    def test_the_document_states_the_successor_result_id(self):
        document = Path("docs/registry/LINEAGE.md").read_text(encoding="utf-8")
        assert "MOMENTUM-30D-WFV-002" in document
        assert "ni révisé ni débloqué" in document


class TestValidatorEntryPoint:
    def test_the_cli_succeeds_on_the_committed_graph(self, capsys):
        assert lineage.main([]) == 0
        assert "no findings" in capsys.readouterr().out

    def test_findings_render_with_their_rule_number(self):
        finding = lineage.Finding(6, "X", "because")
        assert str(finding) == "[rule  6] X: because"

    def test_the_graph_is_valid_json_with_a_schema_version(self, graph):
        assert graph["schema_version"] == 1
        json.dumps(graph)
