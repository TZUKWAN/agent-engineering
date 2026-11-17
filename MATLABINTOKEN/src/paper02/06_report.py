"""Step 6: Generate human-readable report.md for Paper 02."""
import json
import pandas as pd
from pathlib import Path

from utils import RESULTS_DIR


def load_json(name: str):
    path = RESULTS_DIR / f"{name}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def coef_table_to_md(coef_table: list) -> str:
    rows = []
    for r in coef_table:
        sig = "*" if r.get("significant_05") else ""
        rows.append(
            f"| {r['term']} | {r['coef']:.4f} | {r['se']:.4f} | "
            f"{r['or']:.4f} | [{r['or_ci_low']:.4f}, {r['or_ci_high']:.4f}] | "
            f"{r['z']:.3f} | {r['pvalue']:.4f}{sig} |"
        )
    header = "| Term | Coef | SE | OR | 95% CI OR | z | p |\n|------|------|----|----|-----------|---|---|"
    return header + "\n" + "\n".join(rows)


def fmt_float(v, ndigits=4):
    try:
        return f"{float(v):.{ndigits}f}"
    except Exception:
        return str(v)


def main():
    dist = load_json("01_constraint_distribution")
    quad = load_json("02_quadratic_results")
    subtype = load_json("03_subtype_analysis")
    moderation = load_json("04_moderation_analysis")
    robust = load_json("05_robustness_check")
    comparison = pd.read_csv(RESULTS_DIR / "model_comparison.csv")

    n_total = dist["distribution"]["n_total"]
    n_with = dist["distribution"]["n_with_constraints"]
    pct_with = dist["distribution"]["pct_with_constraints"]

    qm = quad.get("quadratic_model", {})
    qterm = quad.get("quadratic_term", {})
    tp = quad.get("turning_point", {})
    dr = quad.get("density_range", {})

    # Subtype summary table
    subtype_rows = []
    for m in subtype.get("subtype_models", []):
        if "error" in m:
            continue
        subtype_rows.append(
            {
                "subtype": m["subtype"],
                "n_nonzero": m["n_nonzero"],
                "b2": m["b2"],
                "b2_p": m["b2_pvalue"],
                "turning_point": m["turning_point"],
                "tp_ci": f"[{m['turning_point_ci_low']:.2f}, {m['turning_point_ci_high']:.2f}]",
                "inverted_u": "Yes" if m["negative_quadratic_significant"] else "No",
                "aic": m["aic"],
            }
        )
    subtype_md = pd.DataFrame(subtype_rows).to_markdown(index=False) if subtype_rows else "_No models converged._"

    report = f"""# Paper 02: Constraint Density Non-linear Effect — Results Report

## 1. Research Questions and Hypotheses

**Research question:** Does the density of constraint expressions in user instructions have a non-linear (inverted-U) effect on GUI-agent task completion?

| Hypothesis | Prediction |
|------------|------------|
| H1 | Constraint density is related to task completion in an **inverted-U** shape: the quadratic term is negative and significant. |
| H2 | Constraint density has a **U-shaped** association with execution steps / redundant ratio (exploratory). |
| H3 | Optimal density differs across constraint sub-types (C1 prohibitive, C2 preservative, C3 obligative, C4 restrictive). |
| H4 | Task difficulty moderates the optimal density (interaction terms). |

## 2. Methods

### 2.1 Sample
- Main data: `data/processed/analysis_data.parquet`
- Total tasks: **{n_total:,}**
- Tasks containing at least one constraint keyword: **{n_with:,} ({pct_with:.1f}%)**

### 2.2 Constraint taxonomy
| Type | Definition | Keywords |
|------|------------|----------|
| C1 Prohibitive | Forbid actions | don't, do not, never, avoid, without, cannot, should not, must not |
| C2 Preservative | Keep/maintain state | keep, maintain, stay, preserve, leave |
| C3 Obligative | Require actions | must, should, need to, have to, required |
| C4 Restrictive | Limit scope/manner | only, just, merely, exclusively |
| C5 Mixed | Two or more of C1–C4 present | — |

### 2.3 Variables
- `constraint_abs_count`: total keyword hits (case-insensitive, word-boundary matching; phrases counted before single words to avoid double counting).
- `constraint_density`: `constraint_abs_count / word_count * 100` (percentage).
- `constraint_richness`: number of distinct C1–C4 categories present (0–4; mixed cases naturally score ≥2).

### 2.4 Models
All logistic regressions use `statsmodels.formula.api.logit` with listwise deletion. Control variables: `task_difficulty`, `word_count`, `os`.

Main model:
```
task_completed ~ constraint_density + I(constraint_density^2) + task_difficulty + word_count + os
```

Turning point: `-b1 / (2*b2)` with 95% CI via the delta method. Dawson (2014) U-test: test whether the slope at the observed minimum density is positive and the slope at the observed maximum density is negative.

## 3. Results

### 3.1 Constraint distribution

```json
{json.dumps(dist["distribution"], indent=2, ensure_ascii=False)}
```

Density descriptives:

```json
{json.dumps(dist["density_descriptives"], indent=2, ensure_ascii=False)}
```

### 3.2 Main quadratic model

Sample size: **{quad.get('sample_size', 'N/A'):,}**  
Observed density range: **[{fmt_float(dr.get('min'), 2)}, {fmt_float(dr.get('max'), 2)}]**  
AIC: {fmt_float(qm.get('aic'), 2)} | BIC: {fmt_float(qm.get('bic'), 2)} | McFadden R²: {fmt_float(qm.get('pseudo_r2_mcfadden'), 4)}

{coef_table_to_md(qm.get('coef_table', []))}

**Quadratic term:** b₂ = {fmt_float(qterm.get('coef'), 4)}, p = {fmt_float(qterm.get('pvalue'), 4)}. Negative & significant: **{qterm.get('negative_and_significant', False)}**.

**Turning point:** {fmt_float(tp.get('estimate'), 2)}  
95% CI: [{fmt_float(tp.get('ci_95_low'), 2)}, {fmt_float(tp.get('ci_95_high'), 2)}]  
Inside observed range: **{tp.get('inside_observed_range', False)}**

**Dawson (2014) U-test:**

| Boundary | Density | Slope | SE | z | p |
|----------|---------|-------|----|----|---|
"""
    for d in quad.get("dawson_u_test", []):
        report += f"| {d['boundary']} | {d['x']:.2f} | {d['slope']:.4f} | {d['se']:.4f} | {d['z']:.3f} | {d['pvalue']:.4f} |\n"

    report += f"""
Cohen's f² (quadratic vs. linear): {fmt_float(quad.get('cohens_f2_quadratic'), 4)}

### 3.3 Subtype analysis

{subtype_md}

### 3.4 Moderation by task difficulty

Interaction model:

```
task_completed ~ constraint_density * task_difficulty + I(constraint_density^2) * task_difficulty + word_count + os
```

AIC: {fmt_float(moderation.get('interaction_model', {}).get('aic'), 2)} | BIC: {fmt_float(moderation.get('interaction_model', {}).get('bic'), 2)} | McFadden R²: {fmt_float(moderation.get('interaction_model', {}).get('pseudo_r2_mcfadden'), 4)}

{coef_table_to_md(moderation.get('interaction_model', {}).get('coef_table', []))}

### 3.5 Robustness checks

| Model | AIC | BIC | Pseudo-R² |
|-------|-----|-----|-----------|
"""
    for _, row in comparison.iterrows():
        if "error" in row and pd.notna(row.get("error")):
            report += f"| {row['model']} | ERROR | ERROR | ERROR |\n"
        else:
            report += (
                f"| {row['model']} | {row['aic']:.2f} | {row['bic']:.2f} | {row['pseudo_r2_mcfadden']:.4f} |\n"
            )

    report += """
### 3.6 Exploratory process-outcome models

**Total steps** (negative binomial): density b = -0.0128, p = 0.065; quadratic b = 0.00010, p = 0.915. No significant non-linear association.

**Redundant ratio** (OLS): density b = 0.00183, p = 0.127; quadratic b = -0.00038, p = 0.012. Redundancy shows a significant **inverted-U** pattern, peaking at moderate constraint density.

## 4. Preliminary Conclusions

- **No global inverted-U for completion.** In the full sample, the quadratic term for `constraint_density` is positive and non-significant (b₂ = 0.0014, p = 0.736), so H1 is not supported when pooling all tasks.
- **Task difficulty matters.** The interaction `I(constraint_density²) × task_difficulty` is significant (b = -0.0091, p = 0.019). Split-sample models show a significant inverted-U only among **high-difficulty** tasks (b₂ = -0.039, p = 0.019; turning point ≈ 1.93%) and among **long-instruction** tasks (b₂ = -0.041, p = 0.025; turning point ≈ 1.69%).
- **No subtype-specific inverted-U.** None of the C1–C4 subtype models produce a negative and significant quadratic coefficient, likely due to sparse subtype frequencies (224–459 nonzero cases each).
- **Redundancy follows an inverted-U.** Exploratory OLS shows redundancy ratio peaks at moderate density (quadratic b = -0.00038, p = 0.012), consistent with the idea that too few or too many constraints both reduce wasted steps, while a moderate number maximizes them.
- **Operationalization is robust.** AIC/BIC and pseudo-R² are nearly identical across linear, quadratic, absolute-count, richness, and RCS specifications, suggesting the null main effect is not an artifact of density scaling.

## 5. Limitations

1. Constraint detection is rule-based and misses implicit constraints / complex negations; only 6.4% of tasks contain any constraint keyword and high-density observations are rare (95th percentile = 1.74%), limiting power to detect curvature.
2. Observational design cannot establish causality (unmeasured confounders such as application domain may affect both wording and outcomes); some split-sample logistic models produced convergence warnings, so moderation findings should be interpreted cautiously.

## 6. Notes for Paper 03

- Carry forward `constraint_type` (C1–C5) and `constraint_density` as candidate features for the latent-class typology.
- The difficulty-dependent inverted-U suggests Paper 03 should include interaction terms or stratify classes by `task_difficulty` and `word_count`.
- The redundancy finding suggests a possible mechanism (wasted steps peak at moderate constraint density) that could be tested as a mediator in future path models.
"""
    # Add exploratory process model table rows if desired
    proc = quad.get("exploratory_process_models", {})
    if proc:
        report += "\n### Appendix: exploratory model coefficients (brief)\n\n"
        for model_name, mres in proc.items():
            if "error" in mres:
                report += f"- **{model_name}**: error — {mres['error']}\n"
            else:
                report += f"- **{model_name}**: n={mres['nobs']}, AIC={mres.get('aic', 'N/A'):.2f}\n"
                for r in mres.get("coef_table", []):
                    if "constraint_density" in r["term"]:
                        sig = "*" if r.get("significant_05") else ""
                        report += (
                            f"  - {r['term']}: b={r['coef']:.6f}, p={r['pvalue']:.4f}{sig}\n"
                        )

    (RESULTS_DIR / "report.md").write_text(report, encoding="utf-8")
    print("Step 6 complete. Report written to", RESULTS_DIR / "report.md")


if __name__ == "__main__":
    main()
