"""Synthetic cross-process handoff; no live harness or scientific approvals."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
from rn_core import init_project,load,ResearchError
from rn_interview import start,add_questions,read,answer,frontier

def question(text,depends=()):
    return {"text":text,"why":"Synthetic dependency","options":"A or B",
            "recommendation":"A","lowest_cost_check":"Synthetic check",
            "depends_on":list(depends),"choices":[
                {"id":"a","label":"Accuracy","description":"F1"},
                {"id":"b","label":"Robustness","description":"Shift"}]}

class HandoffTests(unittest.TestCase):
    def test_cross_process_handoff(self):
        with tempfile.TemporaryDirectory(prefix="v05-synthetic-") as tmp:
            root=Path(tmp)/"project"
            init_project(root,"SYNTHETIC cross-harness project")
            science=load(root)
            start(root,topic="Synthetic goal")
            add_questions(root,[question("Goal?")])
            def cli(*args):
                return json.loads(subprocess.check_output([sys.executable,str(SCRIPTS/"interview.py"),str(root),*args],encoding="utf-8"))
            before=read(root)
            self.assertEqual(cli("present","--question","Q-0001","--capability","sync")["native_tool"],"request_user_input")
            self.assertEqual(cli("present","--question","Q-0001","--harness","deepseek","--capability","ask-user")["native_tool"],"ask_user_question")
            for payload,status in [({"pending":True,"callId":"synthetic"},"pending"),({"answers":[{"id":"Q-0001","selected":[]}]},"skipped")]:
                self.assertEqual(cli("resolve-deepseek","--question","Q-0001","--response-json",json.dumps(payload))["status"],status)
            draft=cli("resolve-deepseek","--question","Q-0001","--response-json",json.dumps({"answers":[{"id":"Q-0001","selected":[],"custom":"Cross-site"}]}))
            self.assertEqual(read(root),before)
            answer(root,"Q-0001",choice_id=draft["resolved"]["choice_id"],custom_answer=draft["resolved"]["custom_answer"],supplement="Synthetic constraint",expected_revision=before["revision"])
            with self.assertRaises(ResearchError):
                answer(root,"Q-0001",choice_id="a",revise=True,expected_revision=before["revision"])
            add_questions(root,[question("Metric?",["Q-0001"])])
            h=cli("handoff")
            self.assertEqual(h["confirmed"][0]["custom_answer"],"Cross-site")
            self.assertEqual(h["confirmed"][0]["supplement"],"Synthetic constraint")
            self.assertEqual(frontier(read(root))["ready"][0]["id"],"Q-0002")
            answer(root,"Q-0002",choice_id="a")
            answer(root,"Q-0001",choice_id="b",revise=True)
            self.assertEqual(read(root)["questions"][1]["status"],"unresolved")
            self.assertEqual(load(root),science)
        self.assertFalse(Path(tmp).exists())
