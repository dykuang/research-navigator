# #6 — Local proposal bridge and security model

## Architecture
The optional service uses Python standard library and binds only to `127.0.0.1` on an ephemeral port by default. The project root is fixed at launch. Browser HTTP requests cannot choose filesystem paths.

| Endpoint | HTTP method | Operation |
|---|---|---|
| `/` | GET | Standalone local proposal form; no research mutations |
| `/api/state` | GET | Token-protected and Host-checked minimal read-only projection |
| `/api/proposals` | POST | Token, exact Host, Origin and Fetch-Site checks; enqueue draft only |
| Any approval URL | Any | Not implemented (404/405) |

The printed URL includes a random bearer capability in the URL fragment; the fragment is removed from the address bar by JavaScript and is never sent in the HTTP request URL. JS uses the X-RN-Token header. CSP nonces, X-Frame-Options, no-store caching, JSON-only POST, tight body size, strict origin/host checks, and no CORS guard against ordinary cross-site attacks. Capability exposure to another local process remains possible; this is NOT enterprise identity authentication.

## How to use

First check schema and migrate existing v0.1 projects explicitly:

~~~bash
python scripts/migrate_state.py preview /PATH/TO/PROJECT
python scripts/migrate_state.py apply /PATH/TO/PROJECT
~~~

Launch the local proposal UI in terminal 1:

~~~bash
python scripts/local_editor.py serve /PATH/TO/PROJECT
~~~

Open the private printed URL in your browser. Use the form to submit add-item, add-relation or limited workflow/outcome status proposals. Each proposal has a reason, expected canonical revision and random ID. Proposals live in `research/canvas/proposals` rather than `research/state`. Queuing does not increment project revision or append canonical research events.

Inspect and confirm a specific proposal in terminal 2:

~~~bash
python scripts/local_editor.py inspect /PATH/TO/PROJECT PROPOSAL_ID
python scripts/local_editor.py approve /PATH/TO/PROJECT PROPOSAL_ID
# or
python scripts/local_editor.py reject /PATH/TO/PROJECT PROPOSAL_ID
~~~

The terminal CLI requires an interactive TTY and the exact string `APPROVE PROPOSAL_ID` or `REJECT PROPOSAL_ID`; piped responses are rejected. Every approval revalidates expected project revision, project ID, current schema, typed edges and cycles under the existing workspace lock. Successful application passes through the canonical write engine, recording proposal_id in its audit event and incrementing revision once. Repeated attempts fail. A stale proposal must be recreated from fresh state.

### Deliberately excluded

The browser cannot propose lifecycle transitions, review/epistemic promotions, resurrection from archive, completion or retirement, and cannot self-approve. These require the primary Agent/CLI workflow and genuine human authorization. The `--actor`/`confirmed=True` fields alone are not authentication; a malicious local filesystem writer remains outside this safeguard's threat model.

### Threat model and operational limitations

- Loopback-only IPv4 interface, no remote/0.0.0.0 binding, no TLS or multi-user service.
- Exact Host + Origin + Fetch-Site checks and bearer capability reduce DNS rebinding / CSRF / cross-site requests.
- The HTTP API does not expose any raw-filesystem or approval endpoint; proposal filenames are server-generated, and project path never comes from requests.
- Current undo journal can recover an interrupted canonical write via `python scripts/migrate_state.py recover PROJECT_ROOT`. An applied-but-unacknowledged proposal is rejected as stale, never blindly reapplied.
- The read-only state API returns scoped ID/type/title/status/relations, not session contents, events or source full text.
- No cryptographic human identity, no multi-machine transaction guarantees, no protection against hostile local processes with project filesystem write permission.

### Offline fallback

The existing generated `research/dashboard/index.html` remains standalone and readonly, even if the service is absent. There are no inactive or misleading approval buttons in the offline dashboard. The future #8/#10 canvas must treat a 202 proposal response as pending, never a committed research change.

### Test

~~~bash
python -m unittest discover -s evals -p 'test_*.py' -v
~~~

Security regression covers Host/Origin/token rejection, absence of HTTP approval, stale revisions, invalid typed relations, proposal-only operation, CLI TTY enforcement and audit event exactly-once behavior.