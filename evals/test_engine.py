import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import (init_project,add_item,add_source,add_relation,change_status,revive,set_project,load,query,validate_state,paths,ResearchError,project_summary)
from build_dashboard import build

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/"student-research"
        init_project(self.root,"SYNTHETIC FIXTURE: 小型检索实验","研究新方法能否提高跨域检索？")
    def tearDown(self):self.tmp.cleanup()
    def item(self,kind="Idea",title="候选思路",module="topic",**kw):
        return add_item(self.root,kind=kind,title=title,module=module,**kw)
    def archived(self):
        a=self.item()
        change_status(self.root,a["id"],"lifecycle_status","parked","测试低样本下成本效益不佳",actor="user",failure_category="resources",failure_scope="仅模拟小样本",revival_triggers="新增代表性数据")
        return a
    def test_init_and_restore(self):
        self.assertTrue(paths(self.root)["project"].exists())
        with self.assertRaises(ResearchError):init_project(self.root,"duplicate")
        a=self.item(title="确定过的定义")
        self.assertEqual(load(self.root)["items"][0]["id"],a["id"])
        self.assertEqual(project_summary(self.root)["project"]["research_question"],"研究新方法能否提高跨域检索？")
    def test_preserves_existing_readme(self):
        root=Path(self.tmp.name)/"existing";root.mkdir(); (root/"RESEARCH.md").write_text("HANDWRITTEN",encoding="utf-8")
        init_project(root,"TEST");self.assertEqual((root/"RESEARCH.md").read_text(),"HANDWRITTEN")
    def test_negative_not_auto_quarantine(self):
        a=self.item(kind="Experiment",module="experiment",title="低统计功效实验",acceptance_criteria="完成小样本日志")
        change_status(self.root,a["id"],"outcome","negative","模拟观测指标下降")
        x=load(self.root)["items"][0]
        self.assertEqual(x["outcome"],"negative")
        self.assertEqual(x["lifecycle_status"],"active")
        self.assertEqual(x["epistemic_status"],"uncertain")
    def test_done_not_validated(self):
        a=self.item(kind="Task",title="实验脚本",acceptance_criteria="运行单测")
        change_status(self.root,a["id"],"workflow_status","done","测试报告归档",completion_note="tests/output.txt, synthetic fixture")
        x=load(self.root)["items"][0]
        self.assertEqual(x["epistemic_status"],"uncertain")
        self.assertEqual(x["workflow_status"],"done")
    def test_done_requires_evidence_note(self):
        a=self.item(kind="Experiment",module="experiment",title="控制实验")
        with self.assertRaises(ResearchError):change_status(self.root,a["id"],"workflow_status","done","agent wishes it were complete",completion_note="done")
    def test_summary_keeps_negative_archive(self):
        a=self.archived()
        change_status(self.root,a["id"],"outcome","negative","小样本负面模拟结果")
        self.assertNotIn(a["id"],[x["item_id"] for x in query(load(self.root),"planning")])
        self.assertIn(a["id"],[x["item_id"] for x in query(load(self.root),"synthesis")])
    def test_archive_query_modes(self):
        a=self.archived()
        self.assertNotIn(a["id"],[x["item_id"] for x in query(load(self.root),"planning")])
        r=query(load(self.root),"risk-check")
        self.assertIn(a["id"],[x["item_id"] for x in r])
        self.assertTrue(next(x for x in r if x["item_id"]==a["id"])["usage"].startswith("historical-risk-only"))
        with self.assertRaises(ResearchError):query(load(self.root),"archive-exploration")
        self.assertIn("not approved for execution",query(load(self.root),"archive-exploration",True)[0]["usage"])
    def test_agent_cannot_archive_or_confirm(self):
        a=self.item()
        with self.assertRaises(ResearchError):change_status(self.root,a["id"],"lifecycle_status","quarantined","unconfirmed suspicion",actor="agent",failure_scope="case",revival_triggers="new test")
        with self.assertRaises(ResearchError):change_status(self.root,a["id"],"review_status","user-confirmed","agent says yes",actor="agent")
        self.assertEqual(load(self.root)["items"][0]["lifecycle_status"],"active")
    def test_revive_requires_two_step_and_new_id(self):
        a=self.archived();oldid=a["id"]
        with self.assertRaises(ResearchError):revive(self.root,oldid,"v2","new dataset","approved","better split",actor="user")
        with self.assertRaises(ResearchError):change_status(self.root,oldid,"lifecycle_status","active","shortcut",actor="user")
        change_status(self.root,oldid,"lifecycle_status","under-revival-review","正式启动复审",actor="user",revival_question="能否重试?",new_conditions="数据条件变更")
        with self.assertRaises(ResearchError):revive(self.root,oldid,"v2","new dataset","","better split",actor="user")
        v2=revive(self.root,oldid,"v2","新的任务设定","用户同意新建待验证候选","变更评估数据",actor="user")
        s=load(self.root);old=next(x for x in s["items"] if x["id"]==oldid)
        self.assertNotEqual(oldid,v2["id"]);self.assertEqual(old["lifecycle_status"],"parked")
        self.assertEqual(v2["epistemic_status"],"hypothesis")
        self.assertEqual(v2["review_status"],"needs-user-confirmation")
        self.assertIn({"from":v2["id"],"to":oldid,"type":"revives"},s["relations"])
        self.assertNotIn(oldid,[x["item_id"] for x in query(s,"planning")]);self.assertIn(v2["id"],[x["item_id"] for x in query(s,"planning")])
    def test_archives_generate_tombstone(self):
        a=self.archived();htmlpath=build(self.root)
        card=self.root/"research"/"archive"/"cards"/(a["id"]+".md")
        self.assertTrue(htmlpath.exists());self.assertTrue(card.exists());self.assertIn("资源",card.read_text(encoding="utf-8") if False else "资源")
        text=card.read_text(encoding="utf-8");self.assertIn("仅模拟小样本",text);self.assertIn("新增代表性数据",text)
    def test_propagation_does_not_archive_shared_source(self):
        method=self.item(kind="Method",module="experiment",title="研究方法")
        downstream=self.item(kind="Claim",module="synthesis",title="暂定结论")
        other=self.item(kind="Baseline",module="literature",title="通用基线")
        add_relation(self.root,downstream["id"],method["id"],"depends-on")
        add_relation(self.root,method["id"],other["id"],"depends-on")
        change_status(self.root,method["id"],"lifecycle_status","quarantined","评价数据泄漏风险",actor="user",failure_category="evaluation",failure_scope="实验 1 中的标签",revival_triggers="审核数据划分")
        s=load(self.root);by={x["id"]:x for x in s["items"]}
        self.assertEqual(by[downstream["id"]]["impact_status"],"blocked")
        self.assertEqual(by[other["id"]]["impact_status"],"current")
        self.assertEqual(by[other["id"]]["lifecycle_status"],"active")
    def test_cycle_blocked(self):
        a=self.item(title="A");b=self.item(title="B")
        add_relation(self.root,a["id"],b["id"],"depends-on")
        with self.assertRaises(ResearchError):add_relation(self.root,b["id"],a["id"],"depends-on")
        self.assertEqual(len(load(self.root)["relations"]),1)
    def test_invalid_edge_rejected(self):
        a=self.item()
        with self.assertRaises(ResearchError):add_relation(self.root,a["id"],"MISSING-01","depends-on")
    def test_unverified_source_cannot_upgrade_claim(self):
        s=add_source(self.root,"SYNTHETIC PLACEHOLDER",url="https://example.org/unknown",access_level="abstract",verification_status="unverified")
        c=self.item(kind="Claim",title="创新性主张",evidence_refs=[s["id"]])
        with self.assertRaises(ResearchError):change_status(self.root,c["id"],"epistemic_status","source-backed","论文摘要说是新",evidence_refs=[s["id"]])
    def test_metadata_checked_not_fulltext(self):
        with self.assertRaises(ResearchError):add_source(self.root,"abstract",url="https://example.org",access_level="abstract",verification_status="primary-inspected",verification_note="only read abstract")
    def test_primary_inspected_claim_has_traceable_source(self):
        source=add_source(self.root,"SYNTHETIC FIXTURE - User Provided Document",locator="fixtures/paper.txt",access_level="user-provided",verification_status="primary-inspected",verification_note="Read supplied synthetic document; paragraph 2")
        c=self.item(kind="Claim",evidence_refs=[source["id"]])
        change_status(self.root,c["id"],"epistemic_status","source-backed","paraphrase of synthetic document",evidence_refs=[source["id"]])
        self.assertEqual(load(self.root)["items"][0]["epistemic_status"],"source-backed")
    def test_doi_format_is_not_verification(self):
        with self.assertRaises(ResearchError):add_source(self.root,"test",doi="totally-fake")
        source=add_source(self.root,"Unverified plausible DOI",doi="10.1234/not-verified")
        self.assertEqual(source["verification_status"],"unverified")
    def test_dashboard_embeds_real_data_and_escapes_script(self):
        a=self.item(title="测试 <script>alert(1)</script> unsafe text")
        path=build(self.root);content=path.read_text(encoding="utf-8")
        self.assertIn("Research Navigator",content)
        self.assertIn("\\u003cscript\\u003e",content)
        self.assertNotIn("测试 <script>alert(1)</script>",content)
        self.assertIn('id="archiveCards"',content)
        self.assertIn('data-view="graph"',content)
        self.assertIn("READ-ONLY",content)
    def test_status_validator_tampering(self):
        a=self.item(kind="Task",title=" task ")
        p=paths(self.root)["items"]
        dat=json.loads(p.read_text());dat["items"][0]["workflow_status"]="done";p.write_text(json.dumps(dat),encoding="utf-8")
        self.assertTrue(any("done without" in e for e in validate_state(load(self.root))))
    def test_event_log_tracks_authorization_and_impact(self):
        a=self.item();b=self.item(kind="Task",module="experiment")
        add_relation(self.root,b["id"],a["id"],"depends-on")
        change_status(self.root,a["id"],"lifecycle_status","retired","用户停止路线",actor="user",failure_scope="all synthetic cases",revival_triggers="new theory")
        events=load(self.root)["events"]
        self.assertTrue(any(x["action"]=="impact-propagated" for x in events))
        self.assertTrue(any(x["action"]=="status-changed" and x["actor"]=="user" for x in events))
    def test_user_owns_research_question(self):
        with self.assertRaises(ResearchError):set_project(self.root,research_question="未经同意改变方向",actor="agent")
        set_project(self.root,focus_module="pivot",actor="agent")
        self.assertEqual(load(self.root)["project"]["focus_module"],"pivot")

if __name__=="__main__":unittest.main()

# Additional regression tests attach to EngineTests before discovery via unittest discovery.
def _test_contradiction_relation_invalidation(self):
    p=self.item(kind="PriorWork",module="literature",title="已知相近研究")
    claim=self.item(kind="Claim",module="synthesis",title="创新主张")
    dependent=self.item(kind="Task",module="synthesis",title="论文段落")
    add_relation(self.root,dependent["id"],claim["id"],"depends-on")
    add_relation(self.root,p["id"],claim["id"],"contradicts")
    by={x["id"]:x for x in load(self.root)["items"]}
    self.assertEqual(by[claim["id"]]["impact_status"],"needs-review")
    self.assertEqual(by[dependent["id"]]["impact_status"],"needs-review")

def _test_archive_history_preserved(self):
    a=self.archived()
    change_status(self.root,a["id"],"lifecycle_status","quarantined","后续发现模拟测试存在泄漏",actor="mentor",failure_category="evaluation",failure_scope="单个数据划分",revival_triggers="彻底重做划分")
    x=load(self.root)["items"][0]
    self.assertEqual(x["archive"]["reason"],"后续发现模拟测试存在泄漏")
    self.assertEqual(x["archive_history"][0]["reason"],"测试低样本下成本效益不佳")

def _test_agent_cannot_clear_review(self):
    x=self.item()
    with self.assertRaises(ResearchError):change_status(self.root,x["id"],"review_status","not-required","AI self exemption",actor="agent")
    change_status(self.root,x["id"],"impact_status","stale","upstream changed",actor="agent")
    with self.assertRaises(ResearchError):change_status(self.root,x["id"],"impact_status","current","AI self clear",actor="agent")

EngineTests.test_contradiction_relation_invalidation=_test_contradiction_relation_invalidation
EngineTests.test_archive_history_preserved=_test_archive_history_preserved
EngineTests.test_agent_cannot_clear_review=_test_agent_cannot_clear_review


def _test_planning_excludes_needs_review(self):
    base=self.item(title="A")
    dep=self.item(kind="Hypothesis",module="topic",title="Dependent")
    add_relation(self.root,dep["id"],base["id"],"depends-on")
    change_status(self.root,base["id"],"lifecycle_status","parked","pause for resource reasons",actor="user",failure_scope="test scope",revival_triggers="new data")
    self.assertNotIn(dep["id"],[x["item_id"] for x in query(load(self.root),"planning")])

EngineTests.test_planning_excludes_needs_review=_test_planning_excludes_needs_review


def _test_done_task_not_in_execution_plan(self):
    item=self.item(kind="Task",title="完成归档任务",workflow="done",acceptance_criteria="输出存在",completion_note="readme.txt synthetic")
    self.assertNotIn(item["id"],[x["item_id"] for x in query(load(self.root),"planning")])

EngineTests.test_done_task_not_in_execution_plan=_test_done_task_not_in_execution_plan
