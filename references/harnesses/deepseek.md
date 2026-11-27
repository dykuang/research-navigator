# DeepSeek Harness (v0.5 development)

DSH is a developer-preview project. Activate the installed skill explicitly in the current session; discoverability does not establish that a tool or UI is exposed. Default documented filesystem roots: project .dsh/skills, project .agents/skills, user DSH_HOME/skills (default ~/.dsh/skills), user DSH_AGENTS_HOME/skills (default ~/.agents/skills). Use the nearest Git root. Custom presets may disable filesystem discovery. See https://github.com/deepseek-ai/deepseek-harness/blob/4b399c39a6d1479cd84ca591b4d7c88e24d38a96/packages/skill/skill-filesystem/README.md.

## Install and inspect

From the v0.5 source checkout (not an already installed skill):
```sh
python scripts/install_harness.py install --provider deepseek --scope project --project PROJECT_ROOT
python scripts/install_harness.py install --provider deepseek --scope project --project PROJECT_ROOT --apply
python scripts/install_harness.py doctor --provider deepseek --scope project --project PROJECT_ROOT
```
Shared root: use --provider shared. User scope: --scope user. Explicit custom path: --skills-dir PATH. Doctor observes files and hashes, not live skill discovery. Installer refuses existing destinations; update by backing up and explicitly uninstalling unmodified owned bundles before reinstalling. Uninstall previews unless --apply is passed. Never removes project research data. Existing manually installed skills must be moved manually after backup. Do not run installer concurrently with unrelated changes to the target directory. An installed skill alone is not a complete installer source checkout (the separate help bundle is a sibling).

## Continue existing project

In a live DSH session explicitly load research-navigator, then run:
```sh
python /PATH/TO/SKILL/scripts/validate_state.py PROJECT_ROOT
python /PATH/TO/SKILL/scripts/interview.py PROJECT_ROOT status
python /PATH/TO/SKILL/scripts/interview.py PROJECT_ROOT handoff
python /PATH/TO/SKILL/scripts/interview.py PROJECT_ROOT next
```
Use the same canonical research project, do not init again. If no interview exists, do not create one without user request. If completed, do not silently reopen. The handoff is local and contains confirmed answers (including supplemental notes), frontier and blocked questions; do not transmit restricted data or entire chat history. Cross-harness handoff is explicit, not automatic background synchronization.

## Ask a question

Only if the live DSH runtime exposes a compatible blocking ask_user_question schema:
```sh
python scripts/interview.py PROJECT_ROOT present --question Q-0001 --harness deepseek --capability ask-user
python scripts/interview.py PROJECT_ROOT resolve-deepseek --question Q-0001 --response-json '{"answers":[{"id":"Q-0001","selected":["ACTUAL DISPLAY LABEL"]}]}'
```
The first command returns a preview, not a tool invocation; the second returns a candidate, not a persisted answer. Confirm the real response before calling the existing answer command. Ask for supplemental notes separately when appropriate. If the capability is missing/failed, use --harness deepseek without a capability or with --failure and ask fallback_text. Deliberate skip is not a confirmation; respect it, mark deferred only with user's actual intent, do not advance dependent questions or immediately re-ask. A pending reply is not consent; this version does not implement durable late-call correlation. For timed mode, prefer normal chat until a compatible blocking schema is confirmed.

## Sessions and safety

Use v02_project.py session-create PROJECT_ROOT --provider deepseek --workspace WORKSPACE --session-id ACTUAL_ID only with real user-provided/verified metadata. No guessed IDs, deep links, automatic transcript ingestion or native session launch. Same session ID under different providers is distinct. Preserve CLI revision checks, archive review, terminal approval, evidence policy and restricted data rules.

Before sending unpublished or restricted research context to a remote model, inspect the runtime sandbox, logging/upload configuration and model data policy; turning off telemetry alone does not stop model API data transfer. No real Windows/DSH Web/Desktop UAT is claimed by this document.
