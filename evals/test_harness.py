import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rn_core import ResearchError
from rn_harness import plan, resolve_deepseek
from rn_interview_choices import delivery_plan

Q = {"id":"Q-0001","text":"Research goal?",
     "choices":[{"id":"a","label":"Accuracy","description":"Improve F1"},
                {"id":"b","label":"Robustness","description":"Cross-site"}],
     "recommended_choice_id":"b"}

class HarnessTests(unittest.TestCase):
    def test_codex_compatibility(self):
        for capability in ("none","sync","async"):
            self.assertEqual(plan(Q,"codex",capability),delivery_plan(Q,capability))
    def test_dsh_preview(self):
        p = plan(Q,"deepseek","ask-user")
        self.assertEqual(p["native_tool"],"ask_user_question")
        self.assertFalse(p["native_tool_called"])
        self.assertFalse(p["user_answer_received"])
        self.assertFalse(p["native_arguments"]["questions"][0]["multi_select"])
    def test_fallback(self):
        for failure in ("unavailable","error","timeout","cancelled","no-answer"):
            p = plan(Q,"deepseek","ask-user",failure)
            self.assertEqual(p["mode"],"chat")
            self.assertIn("Accuracy",p["fallback_text"])
            self.assertTrue(p["fallback_includes_supplement"])
        self.assertEqual(plan(Q,"deepseek")["mode"],"chat")
        self.assertEqual(plan(Q,"generic")["mode"],"chat")
    def test_answers(self):
        for selected,custom,expected in [(["Robustness (Recommended)"],None,"b"),([], "new idea","other")]:
            item={"id":"Q-0001","selected":selected}
            if custom is not None: item["custom"]=custom
            r=resolve_deepseek(Q,{"answers":[item]})
            self.assertEqual(r["status"],"candidate")
            self.assertEqual(r["resolved"]["choice_id"],expected)
        self.assertEqual(resolve_deepseek(Q,{"answers":[{"id":"Q-0001","selected":[]} ]})["status"],"skipped")
        self.assertEqual(resolve_deepseek(Q,{"pending":True,"callId":"x"})["status"],"pending")
    def test_reject_bad_answers(self):
        for response in ({"accepted":True},{"answers":[{"id":"Q-0002","selected":["Accuracy"]}]},{"answers":[{"id":"Q-0001","selected":["unknown"]}]},{"answers":[{"id":"Q-0001","selected":["Accuracy"],"custom":"ambiguous"}]}):
            with self.assertRaises(ResearchError): resolve_deepseek(Q,response)
