# v0.2 Windows / Codex installation and release acceptance matrix

This checklist distinguishes **executed CI tests** from steps which still require a user's actual Windows/Codex installation. No ChatGPT session content, real user projects or real credentials are required to run synthetic CI.

## Automatic checks

GitHub Actions `.github/workflows/validate-v02.yml` runs Python 3.10 and 3.12 on Ubuntu, Playwright Chromium on Ubuntu, and native `windows-latest` Python 3.12 unit/regression and synthetic offline HTML generation. `evals/test_v02_end_to_end.py` exercises three branches sharing one Baseline, negative synthetic Result, scoped contradicting evidence, Claim review, SessionRef many-to-many, archive and distinct two-stage revival, journalled migration, stale conflict, dependency cycle, static HTML and graph immutability.

These are *synthetic* fixtures; `actor=user` / `confirmed=True` in tests emulate an approved local state transition, **not identity verification**.

## Manual Windows checklist — not automatically passed

Prerequisites: Windows 10/11, Python 3.10+ on PATH, cloned `v0.2` branch, ordinary local folder with write permission; optional installed Codex Desktop/CLI if the user wants manual navigation.

~~~powershell
git clone --branch v0.2 https://github.com/dykuang/research-navigator.git
cd research-navigator
python --version
python -m unittest discover -s evals -p 'test_*.py' -v
$project = Join-Path $env:TEMP 'research-navigator-v02-manual-synthetic'
python evals/make_demo.py $project
python scripts/validate_state.py $project
python scripts/build_dashboard.py $project
start (Join-Path $project 'research/canvas/index.html')
~~~

Expected: all tests pass, `research/canvas/index.html` opens with draggable cards, wheel zoom, minimap, search, offline draft JSON export, and `research/dashboard/index.html` remains available. Browser file URL layout localStorage may be unavailable; use export JSON and `canvas_views.py save` as the documented fallback. **Do not claim this has been run on the user's Windows computer unless the user supplies the outcome.**

Interactive local Bridge:

~~~powershell
python scripts/local_editor.py serve $project
~~~

Open the private `http://127.0.0.1:PORT/#token=...` URL printed in that same terminal, then choose *Open interactive Research Canvas*. Select a synthetic Idea, propose an in-progress Task or Branch, review the simulated diff, queue the proposal. In a second interactive PowerShell terminal:

~~~powershell
python scripts/local_editor.py inspect $project PROPOSAL_ID
python scripts/local_editor.py approve $project PROPOSAL_ID
~~~

Expected: operator sees before/after/impact, types the required exact `APPROVE PROPOSAL_ID`, and the Canvas shows the committed research revision only after Refresh. Missing token / origin mismatch / stale revision / archive shortcut must fail. Closing the Bridge server returns Canvas to offline-only operation. Do **not** expose loopback service through public tunnels or proxies.

## Codex real-client check — **unverified until performed in real environment**

1. Open a genuine Codex conversation belonging to a workspace and **obtain its actual Session ID from the installed client, if available**. Do not fabricate the ID or guess URL schemes.
2. On the connected Canvas, register a SessionRef with the real provider, workspace, session ID; queue and approve it in terminal. Add roles `idea-origin` and `decision` to two separate research entities using separate proposals and approvals.
3. Select each card: both show the single stable SessionRef with explicit role, creation time and workspace. Copy Session ID.
4. Navigate to Codex **manually using your installed client's supported UI**. No verified Codex deep-link adapter ships in v0.2. Absence of such an adapter is an intentional unsupported feature, not test success.
5. Test a deleted/unknown Session ID: the Canvas continues displaying the reference and a manual copy fallback, without claiming that the conversation exists or is accessible.
6. Record OS, client/CLI version, whether IDs and workspace are exposed, screenshots without private discussions, and any error output. An optional supported future provider adapter must be separately designed, permissioned and tested.

## Manual verification record

| Check | CI verification | Real user Windows/Codex validation |
|---|---|---|
| State schema, archive/revival, migration | Automated Python regression | Not performed on user PC |
| Python on native Windows runner | GitHub Actions `windows-latest` | Not performed on user PC |
| Canvas drag/zoom/filter, offline fallback | Chromium on Linux CI | Not performed on user PC |
| Localhost token/approval/stale conflict | Synthetic HTTP / Chromium CI | Not performed on user PC |
| Codex installed client Session ID discovery and manual navigation | Not automatically verifiable | **Open / requires real client** |
| Automatic Codex deeplink | **Unsupported in v0.2** | N/A |

## Remaining security limits

Local terminal confirmation is not cryptographic authentication. Scientific evidence is not validated merely by writing a metadata link. The old archive tombstone remains and negative experimental data remain visible, even after creating a new hypothetical candidate. A pending proposal is not a scientific-state write. Native GitHub Milestones (repository planning) are different from scientific `Milestone` research entities.

The release gate should not be marked universally complete until any required real Windows/Codex manual checks have supplied their evidence; record CI coverage separately from site-dependent checks.
