# v0.4.1 Persistent Research Grilling · Lifecycle Contract

**Purpose:** an explicitly started, durable, project-local conversation interview that continues questioning until the *researcher explicitly confirms* exit. This is **not** a globally active skill, a guarantee that a new Codex Session inherits the old Skill activation, or a scientific evidence database.

## Lifecycle

```text
not-started --start--> active <--resume-- paused
                     | ^             ^
          request-exit | | reject-exit| pause
                     v |             |
              consensus-review ------+
                     |
           confirm-exit (user/mentor only)
                     v
                 completed --reopen (explicit human)--> active

active / paused / consensus-review --abandon (explicit human)--> abandoned
abandoned --reopen (explicit human)--> active
completed / abandoned --start --restart--> archive previous interview, start new
```

The canonical scientific truth store remains `research/state/*.json`. The interview sidecar is `research/interviews/current.json`, archives under `research/interviews/archive/<interview-id>.json`, and all changes are project-locked and atomically written. Interview `revision` is independent of the canonical project revision. `--expected-revision` refuses stale writes; a crash should not overwrite an earlier interview or modify scientific truth.

### Question model and progression

Each question has a stable `Q-0001` ID, text, why it matters, options/tradeoffs, recommendation, lowest-cost check, and explicit `depends_on` IDs. A question is `pending`, `answered` (confirmed by user/mentor), `deferred` (needs information), or `unresolved` (lack of consensus). A dependent question becomes eligible only after its direct prerequisites are `answered`. Revising a confirmed premise explicitly invalidates confirmed downstream answers.

`add-questions` adds 1–5 questions per invocation. The Grilling Agent should choose 2–5 high-value independent questions per round (or 1 when necessary), not a complete unsorted checklist.

The model records **who the CLI caller declares** as the confirming actor, but this is not identity authentication. An AI agent must not call human approval commands unless the human actually gave explicit permission; the CLI cannot independently prove a human is at the keyboard.

### Consensus and exit

After sufficient progress, Agent summarizes research definition, hypotheses, evaluation protocol, constraints, remaining uncertainties, and lowest-cost validation steps, then uses `request-exit`. This transitions to `consensus-review`, *not* `completed`. User/mentor may call `reject-exit` to continue asking questions, or explicitly `confirm-exit`. Every still-open question must be individually named via `--accept-open Q-NNNN`; otherwise completion fails.

After `completed`, the assistant operates normally; no mandatory interrogation unless the user explicitly `reopen`s or starts a new interview after archival.

### Cross-session recovery and activation limitations

A different independent Codex/Agent chat normally **does not inherit the prior chat's Skill invocation**. Persistence and instruction activation are different.

To resume: in the new chat explicitly invoke `$research-navigator`, identify the **same project root**, then run `status` and `next` (or `handoff`). For an optional project-local context hint, run `python scripts/install_interview_guidance.py PROJECT_ROOT --apply` *only after explicit user consent*. It appends bounded text to the project's `AGENTS.md` without overwriting existing instructions; this is a project-level reminder, not an always-on skill injection, and actual client behavior varies.

No global `AGENTS.md` or Skill folder is modified by default. No browser process continuously monitors research sessions.

## CLI examples

Run from installed Research Navigator Skill directory. Initialize the research project **separately** using existing `update_project.py init`, after getting permission.

```bash
python scripts/interview.py PROJECT_ROOT start --topic "Does method A improve out-of-domain F1?"
python scripts/interview.py PROJECT_ROOT status
python scripts/interview.py PROJECT_ROOT add-questions --questions-json '[{"text":"Which held-out domain?","why":"Defines transfer scope","options":"A or B, limited sample sizes","recommendation":"Start with A","lowest_cost_check":"Inspect split metadata","depends_on":[]}]'
python scripts/interview.py PROJECT_ROOT next
python scripts/interview.py PROJECT_ROOT answer --question Q-0001 --text "Dataset A, same split for all baselines" --actor user
python scripts/interview.py PROJECT_ROOT pause --actor user
# In a fresh independent session: explicitly re-invoke the installed Skill.
python scripts/interview.py PROJECT_ROOT handoff
python scripts/interview.py PROJECT_ROOT resume --actor user
python scripts/interview.py PROJECT_ROOT request-exit --reason "Task and metric agreed; experiments unverified" --actor agent
# User can reject and resume:
python scripts/interview.py PROJECT_ROOT reject-exit --reason "Need to clarify comparison budget" --actor user
# ... or, after a new request-exit, explicitly confirm and accept remaining questions:
python scripts/interview.py PROJECT_ROOT confirm-exit --accept-open Q-0002 --actor user
python scripts/build_dashboard.py PROJECT_ROOT
# Open PROJECT_ROOT/research/canvas/interview.html (read-only snapshot)
python scripts/install_interview_guidance.py PROJECT_ROOT             # preview only
python scripts/install_interview_guidance.py PROJECT_ROOT --apply      # explicit opt-in
```

**CLI stdout JSON** describes durable state or a read-only frontier. Exit codes: `0` success, `2` invalid state/command; scientific state remains unchanged. `status`, `next` and `handoff` are read-only. No implicit project init, no automatic experiment execution, no unverified paper authentication.

## Safety and compatibility

- v0.4.0 canonical schema remains `0.2.0`; no migration of existing research data or automatic parsing of historic chats.
- Absence of `research/interviews/current.json` simply means no persisted interview. The regular Canvas still works; no interview link is shown.
- A deleted/corrupt/mismatched sidecar fails closed; it must not silently create a new interview, overwrite existing data, or modify canonical state.
- The offline `interview.html` embeds project interview metadata and *confirmed answers*, not a full transcript; treat it as potentially sensitive local research data. Text is escaped before embedding; no external scripts or network needed.
- Existing v0.4 scientific planning, archive isolation, Milestone review, and local protected Canvas proposal approval remain untouched.
- Refusal of a CLI command is different from whether an LLM obeys the conversational protocol; realistic agent multi-turn behavior still requires testing in the actual Codex client.

## Minimum real-client acceptance

1. Start Grilling from one actual Codex Session with explicit Skill invocation and answer multiple rounds.
2. Close the Session, open another independent Session attached to the same project, explicitly invoke Skill or use opted-in `AGENTS.md`, and confirm `status/next` recovers all known facts and unresolved questions.
3. Reject exit once; confirm exit explicitly later, verify ordinary conversation no longer persists questioning.
4. Validate `research/state/` scientific records are not silently altered and archive/revival approvals are unaffected.
5. Test Windows native path quoting, Codex Skills discovery and optional AGENTS.md instruction reading; these are environment-dependent and not proven by synthetic GitHub CI.
