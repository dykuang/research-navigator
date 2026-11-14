# M3 · 实验方案确定 (Experiment Design)

**Entry**: at least a working hypothesis, evaluation construct and feasible test unit, even if literature is incomplete. **Exit**: a reproducible test protocol capable of falsifying the specified hypothesis with acceptable resources and fair comparison.

**Frontier interview**: concrete dependent/independent variables; appropriate controls and baseline fairness; data/samples and split policy; metric formula/direction and meaningful effect size; replication/uncertainty plan; budget, seeds, compute, ethical/data constraints and potential leaks. Ask user what result would change their mind.

**Agent investigates**: requirements to run relevant repo or equipment; feasible smallest discriminating experiment; possible failure modes; evaluation contamination; baseline protocol compatibility. Clearly distinguish "planned" vs "executed" and "observed" vs "inferred". No fabricated metrics, run confirmations or code outcomes.

**Human decisions**: expensive resource commitment, experimental design choices likely to bias results, submission/approval, data access and ethics. Only execute authorized work in available environments.

**Artifacts**: `research/03-experiments/experiment-plan.md`, `protocols/<experiment-id>.md`, `experiment-registry.md`, `risks.md`, and acceptance checklist. Register Experiment IDs, link `tests` → hypothesis and `depends-on` → baseline/data. Every result includes metric unit, dataset/version, n/seed, observed values, failure logs, artifact path, and whether synthetic fixture.

**Rollback/links**: non-reproducible baseline forces M2 reevaluation, data invalidity may challenge M1 feasibility, negative/inconclusive triggers M4 diagnosis, results propagate into M5 without automatic truth upgrades.
