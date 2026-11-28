# v0.5 Harness contract (#57, #59–#61)

Research state, interview sidecars, CLI validation, and terminal-only proposal approval are unchanged. The harness adapter is a pure read-only formatter and response interpreter. No installation, tool execution, identity verification, approval, or state write is implied by a returned payload.

Providers: codex (none/sync/async), deepseek (none/ask-user), generic (none). The caller must inspect the actual tool schema; default is none. Existing Codex CLI flags and responses stay compatible. The DSH adapter targets the documented blocking question schema, not a pinned released client; real-client UAT is required. Timed pending results and skipped questions are never answers. Late envelopes must be correlated by the real client and explicitly discussed with the user; this adapter rejects them. Do not re-prompt a deliberate skip without user request. Unknown/ambiguous replies require clarification. Preserve all choices with ordinary chat fallback and collect supplementary notes in chat.

Upstream: https://github.com/deepseek-ai/deepseek-harness/blob/4b399c39a6d1479cd84ca591b4d7c88e24d38a96/packages/interaction/tool-ask-user/src/index.ts ; https://github.com/deepseek-ai/deepseek-harness/blob/4b399c39a6d1479cd84ca591b4d7c88e24d38a96/docs/tool-catalog.md

Upstream source contract inspected at commit `4b399c39a6d1479cd84ca591b4d7c88e24d38a96`; not a verified installed client version.
