# Cross-module propagation and research re-evaluation

1. **Literature contradicts novelty**: a new inspected PriorWork can `contradicts` the relevant Idea/Claim; mark novelty claim for human review. Do not call abstract-only matches confirmed duplication.
2. **Baseline protocol incompatibility**: tie Baseline to affected Experiment using `depends-on` or `implements` as appropriate. Mark experiment comparison not ready; do not rewrite all previously completed results.
3. **Experiment protocol/data changes**: attach Experiment → Hypothesis `tests`, Result → Claim `supports` or `contradicts`. If the original result becomes invalid, change its epistemic status with reasons; propagation flags dependent claims.
4. **Pivot / Park / Retire**: mark downstream active dependents as needing review or blocked; upstream independent Source/Dataset remains valid. Add a Decision with options considered and trade-offs.
5. **Synthesis**: claims can be grouped by supported / contradicted / unresolved; negative and inconclusive results are reported with original scope. `done` drafts may still contain `uncertain` claims.
6. **Revival**: keep old branch and add fresh branch; do not silently turn the old failed idea into a success or let it appear as a normal planning candidate.

Use stable IDs and explicit relation semantics. Inspect the direction of each edge before adding it: `A depends-on B` means A requires B. Never add a relation solely because two records mention the same name.
