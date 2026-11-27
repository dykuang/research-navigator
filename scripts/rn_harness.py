"""Harness-neutral, read-only question delivery and reply interpretation."""
from rn_core import ResearchError
from rn_interview_choices import delivery_plan, display_choices

PROVIDERS = ("codex", "deepseek", "generic")
CAPABILITIES = {"codex": ("none", "sync", "async"),
                "deepseek": ("none", "ask-user"), "generic": ("none",)}

def plan(question, provider="codex", capability="none", failure=None):
    """Capability is caller-observed, not detected from installed files."""
    if provider not in CAPABILITIES or capability not in CAPABILITIES[provider]:
        raise ResearchError("unsupported harness/capability pair")
    if provider == "codex":
        return delivery_plan(question, capability, failure)
    result = delivery_plan(question, "none", failure)
    if failure or capability == "none":
        return result
    choices = display_choices(question)
    if not choices or len(choices) > 3:
        result["reason"] = "text fallback preserves all options"
        return result
    # Use stable question ID; do not rely on localized choice labels as IDs.
    # Put recommended choice first, but never auto-confirm it.
    recommended = question.get("recommended_choice_id")
    ordered = sorted(choices, key=lambda c: c["id"] != recommended)
    labels = [c["label"] + (" (Recommended)" if c["id"] == recommended else "")
              for c in ordered]
    if len(set(labels)) != len(labels):
        result["reason"] = "ambiguous native labels"
        return result
    options = [{"label": label, "description": c["description"]}
               for label, c in zip(labels, ordered)]
    result.update(mode="native-candidate", native_tool="ask_user_question",
                  native_arguments={"questions": [{"id": question["id"],
                    "question": question["text"], "header": question["id"],
                    "options": options, "multi_select": False}]},
                  reason="preview only; verify live DSH schema and user interaction")
    return result

def resolve_deepseek(question, response):
    """Return an unconfirmed draft, or an explicit non-answer status.

    Only the blocking answer batch is interpreted. Timed/late envelopes
    must not be accepted as consent or replayed without call correlation.
    """
    if not isinstance(response, dict):
        raise ResearchError("invalid DSH response")
    if response.get("pending") is True:
        if "answers" in response:
            raise ResearchError("conflicting pending and answer")
        return {"status": "pending", "resolved": None}
    if response.get("accepted") is True:
        raise ResearchError("delivery acknowledgement is not an answer")
    if set(response) != {"answers"}:
        raise ResearchError("unsupported DSH response envelope")
    if plan(question, "deepseek", "ask-user")["mode"] != "native-candidate":
        raise ResearchError("question is not eligible for DSH native choices")
    rows = response.get("answers")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ResearchError("expected exactly one DSH answer")
    item = rows[0]
    if item.get("id") != question["id"]:
        raise ResearchError("question ID mismatch")
    selected, custom = item.get("selected"), item.get("custom")
    if not isinstance(selected, list) or len(selected) > 1 or any(not isinstance(x, str) for x in selected):
        raise ResearchError("expected zero or one selected label")
    if custom is not None and (not isinstance(custom, str) or len(custom) > 12000):
        raise ResearchError("invalid custom answer")
    custom = custom.strip() if custom else ""
    if not selected:
        if not custom:
            return {"status": "skipped", "resolved": None}
        return {"status": "candidate", "resolved": {"choice_id": "other", "custom_answer": custom}}
    if custom:
        raise ResearchError("ambiguous selection with custom text; clarify supplement")
    choices = display_choices(question)
    recommended = question.get("recommended_choice_id")
    mapping = {c["label"] + (" (Recommended)" if c["id"] == recommended else ""): c["id"]
               for c in choices}
    if selected[0] not in mapping:
        raise ResearchError("unknown DSH choice; clarify with user")
    return {"status": "candidate", "resolved": {"choice_id": mapping[selected[0]], "custom_answer": None}}
