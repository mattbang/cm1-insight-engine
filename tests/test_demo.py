"""Contracts at the public demo boundary, separate from engine rule tests."""
import csv
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo import generate, read_inputs  # noqa: E402

INPUT = ROOT / "examples/input/synthetic-pvm.json"


@pytest.fixture
def reports(tmp_path):
    result = generate(INPUT, tmp_path)
    return {report["scope"]: report for report in result["reports"]}


def write_modified_input(tmp_path, mutate):
    data = json.loads(INPUT.read_text())
    mutate(data)
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data))
    return path


def test_demo_covers_three_countries_and_a_reconciled_region(reports):
    assert len(reports) == 4
    expected = {"Country A": 850, "Country B": 20, "Country C": 150, "Synthetic region": 1020}
    for scope, total in expected.items():
        evidence = reports[scope]["evidence"]
        assert evidence["diagnosis"]["total"] == pytest.approx(total)
        assert evidence["diagnosis"]["reconciliation_gap"] == pytest.approx(0)
        assert evidence["detail_gap"] == pytest.approx(0)
        assert evidence["unattributed_delta"] == pytest.approx(0)


def test_country_a_drills_to_price_product_but_stops_volume_at_segment(reports):
    evidence = reports["Country A"]["evidence"]
    assert evidence["primary"]["path"][-1] == ("SlideSubSegment", "Product A1")
    assert evidence["primary"]["share"] == pytest.approx(0.7)
    assert evidence["offset"]["path"] == [("Final_Segment", "Segment A")]


def test_country_b_exposes_distributed_cancellation_in_the_generated_story(reports):
    report = reports["Country B"]
    divergence = report["evidence"]["divergence"]
    assert divergence["growth"]["path"] == [("Final_Segment", "Segment C")]
    assert divergence["decline"]["path"] == [("Final_Segment", "Segment D")]
    assert "+20 kEUR" in report["story"]
    assert "+400 kEUR" in report["story"] and "-380 kEUR" in report["story"]


def test_country_c_uses_different_products_for_the_driver_and_offset(reports):
    evidence = reports["Country C"]["evidence"]
    assert evidence["diagnosis"]["pattern"] == "price_volume_tradeoff"
    assert evidence["primary"]["path"][-1] == ("SlideSubSegment", "Growth product")
    assert evidence["offset"]["path"][-1] == ("SlideSubSegment", "Price product")
    assert "-600 kEUR" in reports["Country C"]["story"]
    assert "-50 kEUR" in reports["Country C"]["subtitle"]


def test_region_keeps_country_identity_in_product_attribution(reports):
    path = reports["Synthetic region"]["evidence"]["primary"]["path"]
    assert path == [("ViewName", "Country C"), ("Final_Segment", "Segment E"),
                    ("SlideSubSegment", "Growth product")]


def test_exports_preserve_exact_stories_and_numeric_values(tmp_path):
    result = generate(INPUT, tmp_path)
    evidence = json.loads((tmp_path / "evidence.json").read_text())
    assert evidence["synthetic"] is True
    assert evidence["input_record_count"] == 13
    commentary = (tmp_path / "management-commentary.md").read_text()
    with (tmp_path / "reporting-feed.csv").open(newline="") as stream:
        feed = {row["scope"]: row for row in csv.DictReader(stream)}
    for report in result["reports"]:
        row = feed[report["scope"]]
        assert row["management_story"] == report["story"]
        assert row["subtitle"] == report["subtitle"]
        assert report["story"] in commentary
        assert float(row["cm1_change"]) == pytest.approx(report["evidence"]["diagnosis"]["total"])
        assert float(row["price"]) + float(row["volume"]) + float(row["residual_mix"]) == pytest.approx(float(row["cm1_change"]))


def test_shuffling_records_does_not_change_the_exports(tmp_path):
    reversed_input = write_modified_input(tmp_path, lambda data: data["records"].reverse())
    generate(INPUT, tmp_path / "original")
    generate(reversed_input, tmp_path / "reversed")
    for name in ("management-commentary.md", "evidence.json", "reporting-feed.csv"):
        assert (tmp_path / "original" / name).read_bytes() == (tmp_path / "reversed" / name).read_bytes()


@pytest.mark.parametrize("value", [None, "100", True, float("nan"), float("inf")])
def test_invalid_effects_are_rejected_before_any_report_is_written(tmp_path, value):
    path = write_modified_input(tmp_path, lambda data: data["records"][0].update(Price_Segment=value))
    with pytest.raises(ValueError, match="finite number"):
        generate(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("key", ["ViewName", "Final_Segment", "SlideSubSegment"])
def test_missing_hierarchy_labels_are_rejected(tmp_path, key):
    path = write_modified_input(tmp_path, lambda data: data["records"][0].pop(key))
    with pytest.raises(ValueError, match="nonempty label"):
        read_inputs(path)


def test_input_must_declare_synthetic_data_and_correct_units(tmp_path):
    path = write_modified_input(tmp_path, lambda data: data.update(synthetic=False, units="EUR"))
    with pytest.raises(ValueError, match="synthetic=true and units=kEUR"):
        read_inputs(path)


def test_inconsistent_supplied_pvm_is_rejected(tmp_path):
    path = write_modified_input(tmp_path, lambda data: data["records"][0].update(Base_CM1=9999))
    with pytest.raises(ValueError, match="do not reconcile"):
        read_inputs(path)


def test_missing_explicit_policy_is_not_silently_replaced_by_defaults(tmp_path):
    with pytest.raises(ValueError, match="policy file does not exist"):
        generate(INPUT, tmp_path / "output", tmp_path / "missing.json")
