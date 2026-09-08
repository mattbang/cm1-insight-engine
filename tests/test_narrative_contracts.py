"""Independent synthetic contracts for the narrative decision layer.

These cases exercise business invariants: preserve opposing movements, identify
the correct metric at the correct hierarchy, and avoid claims from tiny nets.
All values and entity names are synthetic; monetary inputs are kEUR.
"""

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cm1_narratives import (  # noqa: E402
    Policy,
    build_evidence,
    diagnose,
    render_story,
    render_subtitle,
    select_hierarchy,
)


def row(price=0, volume=0, mix=0, label="Country A"):
    total = price + volume + mix
    return pd.Series(
        {
            "ViewName": label,
            "Total_Segment": total,
            "Price_Segment": price,
            "Volume_Segment": volume,
            "Mix_Segment": mix,
            "Base_CM1": 10000 + total,
            "Comp_CM1": 10000,
        }
    )


def detail(segment, product, price=0, volume=0, mix=0, country="Country A", plug=False):
    total = price + volume + mix
    return {
        "ViewName": country,
        "Final_Segment": segment,
        "SlideSubSegment": product,
        "Rollup_Level": 2,
        "Total_Segment": total,
        "Price_Segment": price,
        "Volume_Segment": volume,
        "Mix_Segment": mix,
        "Base_CM1": 1000 + total,
        "Comp_CM1": 1000,
        "_is_plug": plug,
    }


def choose(records, metric="Total_Segment", sign=1, **kwargs):
    return select_hierarchy(
        pd.DataFrame(records), metric, sign,
        ["Final_Segment", "SlideSubSegment"], **kwargs
    )


def fmt(value):
    return f"{value:+g}kEUR" if value else "0kEUR"


def test_zero_result_is_flat_not_a_decline():
    diagnosis = diagnose(row())
    assert diagnosis["pattern"] == "flat"
    subtitle = render_subtitle(diagnosis, fmt)
    assert "below" not in subtitle.lower()
    assert "drop" not in subtitle.lower()
    assert len(subtitle) <= 120


def test_flat_net_with_large_opposing_effects_is_not_immaterial():
    diagnosis = diagnose(row(price=500, volume=-500))
    assert diagnosis["pattern"] == "offsetting"
    assert diagnosis["top"]["value"] * diagnosis["offset"]["value"] < 0
    text = render_subtitle(diagnosis, fmt)
    assert "+500" in text and "-500" in text


@pytest.mark.parametrize(
    "price,volume,mix,pattern",
    [
        (500, 0, -300, "toxic"),
        (-300, 500, 0, "price_volume_tradeoff"),
        (-600, 500, 0, "price_volume_tradeoff"),
        (-100, -50, -20, "broad_decline"),
        (100, 20, 0, "simple"),
    ],
)
def test_representative_driver_relationships(price, volume, mix, pattern):
    assert diagnose(row(price, volume, mix))["pattern"] == pattern


def test_small_price_volume_pair_does_not_override_the_dominant_mix_story():
    diagnosis = diagnose(row(price=-0.6, volume=0.5, mix=1000))
    assert diagnosis["top"]["name"] == "Mix"
    assert diagnosis["pattern"] == "simple"


def test_choose_country_segment_then_product_using_whole_scope_share():
    selection = choose(
        [detail("Segment A", "Product A1", price=700),
         detail("Segment A", "Product A2", price=100),
         detail("Segment B", "Product B1", price=200)]
    )
    assert selection["path"] == [
        ("Final_Segment", "Segment A"), ("SlideSubSegment", "Product A1")
    ]
    assert selection["value"] == pytest.approx(700)
    assert selection["share"] == pytest.approx(0.7)


def test_stop_at_segment_when_products_are_distributed():
    selection = choose(
        [detail("Segment A", "Product A1", price=400),
         detail("Segment A", "Product A2", price=400),
         detail("Segment B", "Product B1", price=200)]
    )
    assert selection["path"] == [("Final_Segment", "Segment A")]
    assert selection["value"] == pytest.approx(800)
    assert selection["share"] == pytest.approx(0.8)


def test_no_product_story_when_no_segment_concentrates_the_movement():
    selection = choose(
        [detail("Segment A", "Common label", price=400),
         detail("Segment B", "Common label", price=400),
         detail("Segment C", "Other", price=200)]
    )
    assert selection["path"] == []


def test_aggregate_repeated_rows_before_ranking_products():
    selection = choose(
        [detail("Segment A", "Product A1", price=100),
         detail("Segment A", "Product A1", price=100),
         detail("Segment A", "Product A2", price=80)]
    )
    assert selection["path"][-1] == ("SlideSubSegment", "Product A1")
    assert selection["value"] == pytest.approx(200)
    assert selection["share"] == pytest.approx(200 / 280)


def test_gross_denominator_aggregates_opposing_records_of_the_same_product():
    details = pd.DataFrame(
        [detail("Segment A", "Product A1", price=100),
         detail("Segment A", "Product A1", price=-90),
         detail("Segment A", "Product A2", price=80)]
    )
    evidence = build_evidence(row(price=90), details)
    selection = evidence["primary"]
    assert selection["path"][-1] == ("SlideSubSegment", "Product A2")
    assert selection["value"] == pytest.approx(80)
    assert selection["share"] == pytest.approx(80 / 90)


def test_net_cancellation_does_not_inflate_concentration():
    selection = choose(
        [detail("Segment A", "Product A1", price=100),
         detail("Segment A", "Product A2", price=-99),
         detail("Segment B", "Product B1", price=2)]
    )
    assert selection["path"] == []


def test_small_product_is_not_promoted_by_small_country_net():
    assert choose([detail("Segment A", "Noise", price=0.3)])["path"] == []


def test_absolute_floor_is_in_thousands_not_euros():
    selection = choose([detail("Segment A", "Product A1", price=25)])
    assert selection["path"][-1] == ("SlideSubSegment", "Product A1")


def test_negative_driver_concentration_uses_signed_value_and_positive_share():
    selection = choose(
        [detail("Segment A", "Product A1", price=-700),
         detail("Segment A", "Product A2", price=-100),
         detail("Segment B", "Product B1", price=-200)], sign=-1
    )
    assert selection["value"] == pytest.approx(-700)
    assert selection["share"] == pytest.approx(0.7)


def test_tie_breaking_does_not_depend_on_input_order():
    records = [detail("Segment B", "Product B1", price=100),
               detail("Segment A", "Product A1", price=100)]
    policy = Policy(concentration=0.4)
    forward = choose(records, policy=policy)
    reverse = choose(records[::-1], policy=policy)
    assert forward["path"] == reverse["path"]
    assert forward["path"][0] == ("Final_Segment", "Segment A")


def test_primary_attributes_price_to_price_product_not_largest_net_product():
    # Product A grows through volume. Product B supplies the entire price
    # improvement while its larger volume loss hides that behind a net decline.
    details = pd.DataFrame(
        [detail("Segment A", "Volume product", volume=200),
         detail("Segment B", "Price product", price=600, volume=-650)]
    )
    evidence = build_evidence(row(price=600, volume=-450), details)
    assert evidence["diagnosis"]["top"]["name"] == "Price"
    assert evidence["primary"]["path"][-1] == ("SlideSubSegment", "Price product")
    assert evidence["primary"]["value"] == pytest.approx(600)


def test_country_scope_cannot_pick_another_countrys_product():
    details = pd.DataFrame(
        [detail("Segment A", "Local product", price=100),
         detail("Segment A", "Foreign product", price=900, country="Country B")]
    )
    evidence = build_evidence(row(price=100), details)
    assert evidence["primary"]["path"][-1] == ("SlideSubSegment", "Local product")
    assert evidence["primary"]["value"] == pytest.approx(100)


def test_reconciliation_plug_is_never_a_named_business_driver():
    details = pd.DataFrame(
        [detail("Segment A", "Actual product", price=100),
         detail("Misc.", "Reconciliation", price=900, plug=True)]
    )
    evidence = build_evidence(row(price=1000), details)
    path = evidence["primary"]["path"]
    assert path == []
    assert all(label not in {"Misc.", "Reconciliation"} for _, label in path)
    # The raw hierarchy can reconcile including plugs, while the amount
    # excluded from named business attribution must remain visible.
    assert evidence["unattributed_delta"] == pytest.approx(900)


def test_opposing_business_branches_trigger_divergence_at_150_keuro_scale():
    details = pd.DataFrame(
        [detail("Segment A", "Growing product", price=200),
         detail("Segment B", "Declining product", price=-180)]
    )
    evidence = build_evidence(row(price=20), details)
    assert evidence["divergence"]


def test_divergence_bubbles_up_to_segment_when_each_product_is_small():
    details = pd.DataFrame(
        [detail("Segment A", f"Product A{i}", price=100) for i in range(4)]
        + [detail("Segment B", f"Product B{i}", price=-95) for i in range(4)]
    )
    evidence = build_evidence(row(price=20), details)
    assert evidence["divergence"]
    story = render_story(evidence, "Country A", fmt)
    assert "Segment A" in story and "+400" in story
    assert "Segment B" in story and "-380" in story


@pytest.mark.parametrize("net", [0, 0.3])
def test_flat_pvm_totals_do_not_suppress_material_product_divergence(net):
    details = pd.DataFrame(
        [detail("Segment A", "Product A1", price=400),
         detail("Segment B", "Product B1", price=-400 + net)]
    )
    evidence = build_evidence(row(price=net), details)
    assert evidence["divergence"]
    story = render_story(evidence, "Country A", fmt)
    assert "Product A1" in story and "+400" in story
    assert "Product B1" in story and fmt(-400 + net) in story


def test_regional_story_preserves_offsetting_countries_in_same_product():
    first = detail("Segment A", "Common product", price=500, country="REGION")
    first["ViewName_Orig"] = "Country A"
    second = detail("Segment A", "Common product", price=-450, country="REGION")
    second["ViewName_Orig"] = "Country B"
    evidence = build_evidence(row(price=50, label="REGION"), pd.DataFrame([first, second]))
    assert evidence["divergence"]
    story = render_story(evidence, "REGION", fmt)
    assert "Country A" in story and "+500" in story
    assert "Country B" in story and "-450" in story


@pytest.mark.parametrize("label", ["Country A", "Country 2", "Country Z"])
def test_story_always_retains_a_material_opposing_driver(label):
    details = pd.DataFrame(
        [detail("Segment A", "Product A1", price=500, country=label),
         detail("Segment B", "Product B1", volume=-300, mix=-100, country=label)]
    )
    evidence = build_evidence(row(500, -300, -100, label), details)
    story = render_story(evidence, label, fmt)
    assert "+500" in story
    assert "-300" in story
    assert "+100" in story
    assert story.count("(") == story.count(")")


def test_subtitle_preserves_complete_tokens_at_requested_length():
    diagnosis = diagnose(row(price=1234567, volume=-1000000, mix=1))
    subtitle = render_subtitle(diagnosis, fmt, max_len=120)
    assert len(subtitle) <= 120
    assert subtitle.count("(") == subtitle.count(")")


def test_configured_materiality_applies_to_subtitle_as_well_as_diagnosis():
    diagnosis = diagnose(row(price=10), policy=Policy(eps=20))
    assert diagnosis["pattern"] == "flat"
    subtitle = render_subtitle(diagnosis, fmt)
    assert "no material" in subtitle.lower()
