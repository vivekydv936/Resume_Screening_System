# Fairness Audit Report

## Data availability
The supplied eight-column dataset contains no validated gender, age, or name fields. Group-level demographic parity, equal opportunity, and related metrics were therefore not calculated.

## Controlled counterfactual method
4 pairs were created. Each pair kept the same explicit job-relevant qualifications and changed only a name, pronoun, or gender cue. The files were temporary and deleted after scoring.

## Results
- Pairs with a non-zero final-score difference: **0 of 4**.

| Pair | TF-IDF difference | Final-score difference | Matched skills equal |
|---|---:|---:|---|
| name_pair_1 | 0.0 | 0.0 | True |
| name_pair_2 | 0.0 | 0.0 | True |
| cue_pair_1 | 0.0 | 0.0 | True |
| cue_pair_2 | 0.0 | 0.0 | True |

## Interpretation and limitations
- The supplied dataset has no validated gender, age, or name attributes, so group-level fairness metrics are not valid.
- These are controlled text counterfactuals, not evidence about real demographic groups.
- Name and pronoun tokens can change lexical TF-IDF similarity even when qualifications are identical.
- No protected attribute is intentionally used by the scoring formula.

## Recommendations
- Keep demographic cues out of the scoring features where they are not job-relevant.
- Consider redacting names and pronouns before lexical similarity scoring if operationally appropriate.
- Re-run group-level metrics only after obtaining lawful, consented, validated demographic data and an approved evaluation protocol.
- Preserve human review and record overrides; this prototype must not make autonomous hiring decisions.
