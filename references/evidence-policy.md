# Scientific evidence and anti-hallucination policy

For every scientific claim distinguish **source metadata**, **author's claim**, **user-provided fact**, **agent hypothesis**, **verified tool observation**, **actual experimental measurement**, and **researcher's interpretation**. The labels are not interchangeable.

- A source is not verified merely because a plausible DOI is formatted correctly. Verify metadata from a reputable catalogue/venue, follow to the original publication or source repository; record exact claim location, access level, time and verification action.
- Abstract-only access supports at most "abstract states X"; it does not validate implementation detail, experimental protocol or the paper's truth. Add `--access-level abstract` and leave `verification-status` below `primary-inspected`.
- An unavailable file or repository cannot count as a run. `Result` requires an observation and log/artifact path; Agent must inspect these artifacts before claiming experimental support.
- Do not record simulated outcomes as real. For evaluations, put `SYNTHETIC FIXTURE` in project and every mock artifact. When reporting, use "virtual demonstration".
- Disagreement: preserve both sides, cite conflicting IDs and ask for discriminating evidence. `user-confirmed` only confirms the user's decision, not the scientific premise.
- For experimental research include data selection, grouping/splits, metrics with formulas and direction, controls, ablations, evaluation leakage, sample count, repetition, uncertainty estimation, and budget when applicable. Avoid blindly applying ML standards to qualitative/theoretical disciplines.
- Expensive, human-subject, regulated or sensitive experiments require prior human approval and applicable ethics/privacy controls.
