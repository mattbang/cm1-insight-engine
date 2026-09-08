# How the engine chooses the story

A useful management summary explains **what changed, where it changed, and what offset it**. The difficult part is choosing the right level of detail: a product when the movement is concentrated, a segment when it is spread across products, or a broader view when no branch dominates.

This repository contains the deterministic commentary layer. It accepts calculated price, volume and residual mix effects; the original reporting workflow also calculated those effects and prepared the Excel feeds used by linked PowerPoint reports.

## 1. Identify the leading effect and its offset

The engine considers price, volume and residual mix separately. It selects the largest effect aligned with the net change and the largest opposing effect, while preserving every material effect in the story and subtitle. A flat result with large opposing effects is explicitly described as offsetting.

Each selected effect is traced to **its own contributors**. A product with the largest net improvement is not automatically the source of the price improvement: its growth might come entirely from volume. The primary effect and its offset may therefore lead to different products or segments.

## 2. Descend only while the evidence supports it

Repeated records are consolidated by their complete country, segment and product key. Identical product labels in different countries or segments stay separate.

For a country, the path is **segment → product**. A consolidated regional view can use **country → segment → product**. At each level, the engine compares the leading branch with the gross movement in the relevant direction:

```text
share = absolute net effect of the candidate branch
        / sum of same-direction effects across consolidated leaf rows
```

The denominator covers the whole reporting scope and stays fixed throughout the descent. It is neither the small net country variance nor a shrinking parent total. Positive and negative effects use separate denominators.

By default, a branch must contribute at least **€25k** and **60%** of the relevant gross movement. If it fails either condition, the explanation stops at the last supported level. Stable tie-breaking makes the result independent of input order.

For example, Segment A contributes +€800k through two products of +€400k each; Segment B contributes +€200k. Segment A explains 80% of gains, but neither product explains 60%. The useful story stays at **Segment A**.

## 3. Reveal important movements hidden by cancellation

A separate check searches for material opposing branches across the hierarchy. Each side must reach **€150k** and **25%** of its corresponding gross positive or negative movement. The engine chooses the most specific qualifying branch on each side.

A hypothetical country with **+€400k in Segment A and −€380k in Segment B** has a net improvement of just €20k. If those movements are distributed across smaller products, both segment stories still appear. A near-flat parent does not suppress them.

## 4. Keep the explanation auditable

The evidence record retains the selected paths, signed contributions, shares, policy settings and selection reasons. It also exposes reconciliation gaps and unallocated movement. Reconciliation adjustments cannot become named product drivers; they remain in the attribution denominator so that excluding them does not inflate a product's importance.

The story uses only calculated relationships. **Residual mix is an accounting residual, not proof of a commercial cause.** The engine does not infer a promotion, competitor action or customer decision from the bridge alone.

All monetary inputs and absolute thresholds use **thousands of euros**. The defaults are explicit reporting-policy choices, configurable in [narrative_policy.json](../config/narrative_policy.json), rather than universal definitions of significance.

See [validation](validation.md) for what is tested and the boundaries of the public example.
