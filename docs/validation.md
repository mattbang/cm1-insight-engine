# Validation and scope

The public repository lets a reviewer inspect and exercise the commentary logic with hypothetical data. Its **49 automated cases** comprise **31 narrative contracts** from the original project review and **18 demo contracts** for the synthetic inputs and exported reports. These cases test analytical requirements rather than matching a saved paragraph word for word.

## Reproducible in this repository

After installing the repository's dependencies, run:

```bash
python -m pytest
```

The contracts cover:

- Selecting a product, stopping at a segment, or keeping an explanation broad according to concentration and materiality.
- Attributing the primary effect to its own contributors, with country and segment boundaries preserved.
- Aggregating repeated records and maintaining stable results when input order changes.
- Avoiding inflated concentration from a small net variance or reconciliation adjustment.
- Surfacing offsetting segments, products and countries, including flat or nearly flat headline results.
- Preserving material opposing effects and complete numeric values in management text and subtitles.

The demo contracts also check reconciliation of supplied effects, country and regional totals, preservation of exact generated text across exports, stable output when rows are reordered, and rejection of malformed inputs or missing policy files. The synthetic demo provides a readable example of this decision layer. Its figures and entities are hypothetical; it does not reproduce a production reporting period.

## Earlier review of the full reporting workflow

The original project review, completed in September 2026, passed **46 regression tests** and **522 integration checks**. The regression suite included a 343-case price/volume/mix matrix. The integration checks covered prepared historical data, synthetic workbook output and rejection of erroneous source input.

That broader review exercised PVM calculation, commentary, reporting-cell contracts and chart-package output. **Its production pipeline, operational fixtures and full verification suite are not included here.** The public 31-case suite is a subset of the 46 regression tests, not an additional 31 tests, and does not reproduce the 522 integration checks.

## What the evidence establishes

The tests verify repeatable decision rules and reporting contracts. They do not establish that every generated story is the preferred interpretation of financial reviewers across many reporting periods. Commercial context and management judgment remain part of the reporting process.

The earlier workbook integrations used prepared data and did not independently validate fresh source ingestion or hierarchy reconciliation. The final live PowerPoint refresh through Empower was not executed in that review. Public slides are standalone, sanitized showcase examples from the earlier workflow, rather than a fresh rendering of the revised engine.

Any historical time-saving figure describes a documented workflow estimate, not a controlled benchmark. Source refresh and management review sit outside the processing run.
