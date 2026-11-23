"""v0.3 additive reasoning validation. No silent project schema migration.

Scientific proof is NOT inferred from records or synthetic logs.
"""
from __future__ import annotations
from datetime import datetime
import math

VERSION = "0.3.0"  # additive feature contract; canonical project format remains 0.2.0
RUN_STATES = ("planned", "running", "recorded", "invalidated")
TRACE_STATES = ("documented", "incomplete", "disputed")
METRIC_DIRECTIONS = ("higher", "lower", "target", "descriptive")


def validate_v03(state):
    errors = []
    items = {x.get("id"): x for x in state.get("items", [])}
    events = {x.get("event_id"): x for x in state.get("events", [])}
    sessions = {x.get("id"): x for x in state.get("session_refs", [])}
    run_artifacts = set()
    for item in state.get("items", []):
        ident = item.get("id", "<unknown>")
        if item.get("type") == "ExperimentRun":
            run = item.get("run")
            if not isinstance(run, dict):
                errors.append(f"{ident}: missing run metadata")
                continue
            experiment = items.get(run.get("experiment_id"))
            if not experiment or experiment.get("type") != "Experiment":
                errors.append(f"{ident}: experiment_id must reference an Experiment")
            if run.get("status") not in RUN_STATES:
                errors.append(f"{ident}: invalid run status")
            if not isinstance(run.get("attempt"), int) or isinstance(run.get("attempt"), bool) or run["attempt"] < 1:
                errors.append(f"{ident}: attempt must be a positive integer")
            if isinstance(run.get("attempt"), int) and not isinstance(run["attempt"], bool) and run["attempt"] > 0:
                key = (run.get("experiment_id"), run["attempt"])
                if key in run_artifacts:
                    errors.append(f"{ident}: duplicate experiment attempt {key}")
                run_artifacts.add(key)
            if run.get("status") in ("recorded", "invalidated"):
                for key in ("dataset", "protocol", "code_revision", "artifact_path", "artifact_sha256", "started_at", "ended_at"):
                    if not isinstance(run.get(key), str) or not run[key].strip():
                        errors.append(f"{ident}: recorded run needs {key}")
                if not isinstance(run.get("seed"), int) or isinstance(run.get("seed"), bool):
                    errors.append(f"{ident}: recorded run needs integer seed")
                if not isinstance(run.get("artifact_verified"), bool) or not run["artifact_verified"]:
                    errors.append(f"{ident}: recorded run must have locally checked artifact")
                if not isinstance(run.get("synthetic"), bool):
                    errors.append(f"{ident}: explicit synthetic flag required")
                result = items.get(run.get("result_id"))
                if not result or result.get("type") != "Result" or not result.get("observation") or not result.get("artifact_path"):
                    errors.append(f"{ident}: recorded run must link to an observed Result")
                for date_key in ("started_at", "ended_at"):
                    text = run.get(date_key)
                    if isinstance(text, str) and text.strip():
                        try:
                            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                            if parsed.tzinfo is None:
                                raise ValueError("timezone missing")
                        except ValueError:
                            errors.append(f"{ident}: {date_key} must be timezone-aware ISO 8601")
                result = items.get(run.get("result_id"))
                if result and result.get("type") == "Result":
                    if result.get("artifact_path") != run.get("artifact_path"):
                        errors.append(f"{ident}: Result artifact must match verified Run artifact")
                    if not any(r.get("from") == result["id"] and r.get("to") == ident and
                               r.get("type") == "depends-on" for r in state.get("relations", [])):
                        errors.append(f"{ident}: missing Result-to-Run provenance relation")
                metrics = run.get("metrics")
                if not isinstance(metrics, list):
                    errors.append(f"{ident}: metrics must be an explicit list")
                else:
                    names = set()
                    for metric in metrics:
                        if not isinstance(metric, dict) or not isinstance(metric.get("name"), str) or not metric["name"].strip() or metric.get("name") in names:
                            errors.append(f"{ident}: duplicate or invalid metric name")
                            continue
                        names.add(metric["name"])
                        if metric.get("direction") not in METRIC_DIRECTIONS or not isinstance(metric.get("unit"), str):
                            errors.append(f"{ident}: invalid metric unit/direction")
                        value=metric.get("value")
                        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                            errors.append(f"{ident}: metric must contain measured numeric value")
            if run.get("status") == "invalidated" and not run.get("invalidation_reason"):
                errors.append(f"{ident}: invalidated run needs a reason")
        if item.get("type") == "DecisionTrace":
            trace = item.get("decision_trace")
            if not isinstance(trace, dict):
                errors.append(f"{ident}: missing decision trace")
                continue
            decision = items.get(trace.get("decision_id"))
            if not decision or decision.get("type") != "Decision":
                errors.append(f"{ident}: decision_id must reference a Decision")
            if trace.get("status") not in TRACE_STATES:
                errors.append(f"{ident}: invalid trace status")
            if not isinstance(trace.get("scope"), str) or not trace["scope"].strip():
                errors.append(f"{ident}: explicit trace scope required")
            if not isinstance(trace.get("options"), list) or not trace["options"]:
                errors.append(f"{ident}: document considered options")
            else:
                if not all(isinstance(v, str) and v.strip() for v in trace["options"]):
                    errors.append(f"{ident}: invalid option")
            if trace.get("status") == "documented" and trace.get("selected") not in trace.get("options", []):
                errors.append(f"{ident}: documented trace must select a recorded option")
            if not isinstance(trace.get("rationale"), str) or not trace["rationale"].strip():
                errors.append(f"{ident}: decision needs rationale or an explicit unknown")
            for key,valid in (("event_ids", events),("session_ref_ids",sessions),("claim_ids",items),("run_ids",items)):
                values=trace.get(key,[])
                if (not isinstance(values,list) or
                    any(not isinstance(v,str) for v in values) or
                    len(values)!=len(set(values)) or any(v not in valid for v in values)):
                    errors.append(f"{ident}: invalid {key}")
            for rid in trace.get("run_ids",[]):
                if rid in items and items[rid].get("type")!="ExperimentRun":
                    errors.append(f"{ident}: run_ids must reference ExperimentRun")
            for cid in trace.get("claim_ids",[]):
                if cid in items and items[cid].get("type")!="Claim":
                    errors.append(f"{ident}: claim_ids must reference Claim")
            approval=trace.get("approval_event_id")
            if approval:
                evt=events.get(approval)
                if not evt or evt.get("actor") not in ("user","mentor"):
                    errors.append(f"{ident}: approval must reference an existing human-attributed event")
                if evt and evt.get("action") not in ("status-changed","milestone-accepted","revival-candidate-created"):
                    errors.append(f"{ident}: approval event kind is not an approval")
    return errors
