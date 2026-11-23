"""Synthetic v0.4 research journeys. Every fixture is temporary and removed."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,add_relation,change_status,load,ResearchError
from rn_domain import create_milestone,link_evidence
from rn_reasoning import create_run,record_run
from rn_decision import mentor_brief, archive_watchlist, opportunities, gaps

def main():
    with tempfile.TemporaryDirectory(prefix="rn-v04-uat-") as folder:
        root=Path(folder)/"study"
        init_project(root,"SYNTHETIC FIXTURE — toy research journey","Does gated fusion outperform baseline B?")
        hyp=add_item(root,kind="Hypothesis",title="Unproven fusion hypothesis",module="topic")
        experiment=add_item(root,kind="Experiment",title="Mock discriminating experiment",
                            module="experiment")
        add_relation(root,experiment["id"],hyp["id"],"tests")
        milestone=create_milestone(root,"Reproducible comparison",["verified run artifact",
                                  "human-reviewed interpretation"])
        before={g["code"] for g in gaps(load(root))}
        assert "EXPERIMENT_NO_REGISTERED_RUN" in before
        assert "MILESTONE_GATE_PENDING" in before
        run=create_run(root,experiment["id"],"Toy run",1)
        still={g["code"] for g in gaps(load(root))}
        assert "EXPERIMENT_ONLY_PLANNED_RUNS" in still
        artifact=root/"toy-fixture.log"
        artifact.write_text("SYNTHETIC FIXTURE — fictional observations only",encoding="utf-8")
        data=record_run(root,run["id"],dataset="synthetic-toy",protocol="toy-split",
                        code_revision="fixture",seed=1,
                        artifact_path="toy-fixture.log",
                        observation="Toy outcome did not outperform baseline",
                        outcome="negative",
                        metrics=[{"name":"F1","value":0.61,"unit":"ratio",
                                  "direction":"higher"}],
                        started_at="2026-11-23T01:00:00+00:00",
                        ended_at="2026-11-23T01:01:00+00:00",synthetic=True)
        assert data["result"]["outcome"]=="negative"
        assert load(root)["items"][0]["lifecycle_status"]=="active"
        claim=add_item(root,kind="Claim",title="Fusion improves transfer",module="synthesis")
        link_evidence(root,claim["id"],data["result"]["id"],
                      "contradicts","only synthetic toy split",
                      quality="experiment-observed")
        new={g["code"] for g in gaps(load(root))}
        assert "DEPENDENCY_NEEDS_REVIEW" in new
        change_status(root,hyp["id"],"lifecycle_status","parked",
                      "Toy negative observation; insufficient power for conclusion",
                      actor="user",failure_category="unknown",
                      failure_scope="toy data single seed",
                      revival_triggers="new independently verified data and more repeats")
        watch=archive_watchlist(load(root))
        assert any(w["id"]==hyp["id"] and not w["automatic_reactivation"] for w in watch)
        assert all(o["subject_id"]!=hyp["id"] for o in opportunities(load(root)))
        report=mentor_brief(load(root))
        assert report["milestones"][0]["accepted"] is False
        assert report["proposed_next_checks"] is not None
        assert report["archive_review_watchlist"]
        assert any(g["code"]=="MILESTONE_GATE_PENDING" for g in report["pending_gaps"])
        assert load(root)["items"][0]["lifecycle_status"]=="parked"
        print("PASS: uncertain question → pending Run → synthetic negative → scoped evidence → human park → mentor review; no contamination or unapproved revival")
    print("PASS: synthetic project directory automatically deleted")

if __name__=="__main__":
    main()
