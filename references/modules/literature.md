# M2 · 前人文献与基线 (Literature & Baselines)

**Entry**: a searchable question or task definition, even if tentative. **Exit**: a justified shortlist of relevant prior works and representative, fair, feasible baselines; all major evidence gaps and source-access limits recorded.

**Frontier interview**: target task and variants; what counts as a relevant predecessor; available academic subscriptions and repositories; comparison criteria (protocol, metric, budget, licensing); whether reproduction or a simpler sanity-check baseline is needed first. Challenge the use of "SOTA" as a synonym for "appropriate baseline".

**Agent investigates**: construct a bilingual/English search protocol with exact terms, synonyms, negative keywords, years and citation chain. Read primary papers/repositories if tools allow, recording page/section, full text vs abstract, DOI/URL, date. Never invent citations or quantitative results. If only abstract available, record an abstract claim but not a verified full-method description. Compare baseline code, license, data splits, metric comparability, reproducibility and effort.

**Human decisions**: which sources are important to read fully, whether a baseline can be fairly adapted, which baselines are required for advisor expectations, whether the proposed novelty survives literature comparison.

**Artifacts**: `research/02-literature/search-strategy.md`, `literature-matrix.md` (work ID, goal, method, data/metric, claim, access level, location, limitations), `baseline-shortlist.md`, `gap-map.md`, source registry in state. Link prior work → claims with `supports`/`contradicts` only when actual claims are known.

**Rollback/links**: novelty conflict triggers M1 re-evaluation; incompatible data/metric blocks specific M3 comparison; conclusions in M5 remain uncertain until evidence resolved. Never promote source-backed merely because a DOI string looks real.
