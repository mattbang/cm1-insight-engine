"""Run the public decision-layer demonstration with invented PVM inputs.

This runner aggregates supplied effects. It does not calculate price, volume,
or residual-mix effects from transactions or connect to source systems.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cm1_narratives import (  # noqa: E402
    DRIVERS, build_evidence, load_policy, render_story, render_subtitle,
)

LABELS = ("ViewName", "Final_Segment", "SlideSubSegment")
AMOUNTS = ("Base_CM1", "Comp_CM1", *DRIVERS.values())
FEED_FIELDS = (
    "scope", "scope_type", "units", "cm1_change", "price", "volume",
    "residual_mix", "subtitle", "management_story",
)


def money(value: float) -> str:
    """Keep the sign and unit visible in every narrative amount."""
    if abs(value) < 1e-9:
        return "0 kEUR"
    return f"{value:+,.0f} kEUR" if float(value).is_integer() else f"{value:+,.2f} kEUR"


def read_inputs(path: Path) -> tuple[dict, pd.DataFrame]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("synthetic") is not True or payload.get("units") != "kEUR":
        raise ValueError("Demo inputs must explicitly declare synthetic=true and units=kEUR")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Demo inputs must contain at least one leaf record")
    for position, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {position} must be an object")
        for key in LABELS:
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"Record {position}: {key} must be a nonempty label")
        for key in AMOUNTS:
            value = record.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Record {position}: {key} must be a finite number")
        delta = record["Base_CM1"] - record["Comp_CM1"]
        if not math.isclose(delta, sum(record[key] for key in DRIVERS.values()), abs_tol=0.01, rel_tol=0):
            raise ValueError(f"Record {position}: supplied PVM effects do not reconcile to the CM1 change")
    details = pd.DataFrame(records, columns=[*LABELS, *AMOUNTS])
    for key in LABELS:
        details[key] = details[key].str.strip()
    details["Rollup_Level"] = 2
    details["_is_plug"] = False
    return payload, details


def summarize_scope(details: pd.DataFrame, label: str) -> pd.Series:
    totals = {key: float(details[key].sum()) for key in AMOUNTS}
    return pd.Series({"ViewName": label, **totals,
                      "Total_Segment": totals["Base_CM1"] - totals["Comp_CM1"]})


def generate(input_path: Path, output_dir: Path, policy_path: Path | None = None) -> dict:
    metadata, details = read_inputs(input_path)
    active_policy_path = policy_path or ROOT / "config" / "narrative_policy.json"
    if not active_policy_path.is_file():
        raise ValueError(f"Narrative policy file does not exist: {active_policy_path}")
    policy = load_policy(active_policy_path)
    reports = []
    for country, country_details in details.groupby("ViewName", sort=True):
        row = summarize_scope(country_details, country)
        evidence = build_evidence(row, details, policy=policy)
        reports.append({"scope": country, "scope_type": "country",
                        "story": render_story(evidence, country, money),
                        "subtitle": render_subtitle(evidence["diagnosis"], money, policy.subtitle_max),
                        "evidence": evidence})

    # Preserve country identity so the regional view cannot merge equal product
    # names in different markets or suppress their opposing movements.
    region_label = "Synthetic region"
    regional_details = details.assign(ViewName_Orig=details["ViewName"], ViewName=region_label)
    region_row = summarize_scope(regional_details, region_label)
    evidence = build_evidence(region_row, regional_details, policy=policy)
    reports.insert(0, {"scope": region_label, "scope_type": "region",
                      "story": render_story(evidence, region_label, money),
                      "subtitle": render_subtitle(evidence["diagnosis"], money, policy.subtitle_max),
                      "evidence": evidence})

    result = {"synthetic": True, "units": "kEUR", "scope": "decision layer",
              "input_record_count": len(details), "country_count": len(reports) - 1,
              "reports": reports}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evidence.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    lines = ["# Generated management commentary", "",
             "**Entirely synthetic example. All amounts are in kEUR (thousands of euros).**", "",
             "The following paragraphs and subtitles are generated directly from the decision layer; "
             "they have not been manually rewritten. The inputs supply already calculated PVM effects.", ""]
    for report in reports:
        lines.extend([f"## {report['scope']}", "", f"**{report['subtitle']}**", "", report["story"], ""])
    lines.extend(["## Reading the examples", ""])
    for country, note in metadata.get("scenario_notes", {}).items():
        lines.append(f"- **{country}:** {note}")
    lines.append("")
    (output_dir / "management-commentary.md").write_text("\n".join(lines), encoding="utf-8")

    with (output_dir / "reporting-feed.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FEED_FIELDS, lineterminator="\n")
        writer.writeheader()
        for report in reports:
            diag = report["evidence"]["diagnosis"]
            effects = {item["name"]: item["value"] for item in diag["effects"]}
            writer.writerow({"scope": report["scope"], "scope_type": report["scope_type"],
                             "units": "kEUR", "cm1_change": diag["total"],
                             "price": effects["Price"], "volume": effects["Volume"],
                             "residual_mix": effects["Mix"], "subtitle": report["subtitle"],
                             "management_story": report["story"]})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "examples/input/synthetic-pvm.json")
    parser.add_argument("--output", type=Path, default=ROOT / "examples/generated")
    parser.add_argument("--policy", type=Path, default=ROOT / "config/narrative_policy.json")
    args = parser.parse_args()
    result = generate(args.input, args.output, args.policy)
    print(f"Generated {result['country_count']} country stories and one regional story in {args.output}")
    print("Outputs: management-commentary.md, evidence.json, reporting-feed.csv")


if __name__ == "__main__":
    main()
