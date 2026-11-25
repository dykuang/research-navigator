"""v0.4.2 structured choices and native fallback regression."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))

from rn_core import init_project,load,ResearchError
from rn_interview import start,add_questions,answer,read,frontier,request_exit,confirm_exit,pause,resume,handoff
from rn_interview_choices import (validate_choices,answer_fields,codex_request,
                                  codex_async_request,resolve_async_reply,
                                  resolve_codex_answer,text_prompt,delivery_plan)
from build_canvas import build_canvas

def choices():
    return [
        {"id":"accuracy","label":"提高精度","description":"提升目标指标，可能增加计算成本"},
        {"id":"cost","label":"降低成本","description":"维持性能，降低 GPU 时间"},
        {"id":"interpret","label":"增强可解释性","description":"评估机制与可解释指标"},
    ]
def q(deps=None,structured=True,title="你希望主要优化什么？"):
    d={"text":title,"why":"研究目标影响实验指标",
       "options":"准确率或成本或解释性",
       "recommendation":"基于现有问题优先精度",
       "lowest_cost_check":"做小规模对照评估",
       "depends_on":list(deps or [])}
    if structured:
        d["choices"]=choices()
        d["recommended_choice_id"]="accuracy"
    return d

class ChoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="rn-042-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"toy"
        init_project(self.root,"SYNTHETIC toy fixture")
        start(self.root,topic="SYNTHETIC study")
    def add(self,d=None):
        add_questions(self.root,[d or q()])
        return read(self.root)["questions"][-1]
    def test_typed_selection_persists_and_no_science_write(self):
        prior=load(self.root)
        self.add()
        answer(self.root,"Q-0001",choice_id="accuracy")
        x=read(self.root)["questions"][0]
        self.assertEqual(x["selected_option_id"],"accuracy")
        self.assertEqual(x["answer"],"提高精度")
        self.assertEqual(x["answer_source"],"choice")
        self.assertIsNone(x["custom_answer"])
        self.assertEqual(load(self.root),prior)
    def test_other_custom_answer_exact_text_recovered(self):
        self.add()
        msg="我更重视跨域鲁棒性，而非已列出的指标"
        answer(self.root,"Q-0001",choice_id="other",custom_answer=msg)
        reloaded=read(self.root)["questions"][0]
        self.assertEqual(reloaded["selected_option_id"],"other")
        self.assertEqual(reloaded["custom_answer"],msg)
        self.assertEqual(reloaded["answer"],msg)
        self.assertEqual(reloaded["answer_source"],"other")
        pause(self.root);resume(self.root)
        self.assertEqual(read(self.root)["questions"][0]["custom_answer"],msg)
    def test_cross_session_handoff_preserves_custom_and_selected_id(self):
        self.add()
        text="我想研究新的范式"
        answer(self.root,"Q-0001",choice_id="other",custom_answer=text)
        packet=handoff(self.root)
        self.assertEqual(packet["confirmed"][0]["selected_option_id"],"other")
        self.assertEqual(packet["confirmed"][0]["custom_answer"],text)
        self.assertEqual(packet["confirmed"][0]["answer_source"],"other")
    def test_typed_question_without_legacy_options_string(self):
        spec=q()
        del spec["options"]
        self.add(spec)
        saved=read(self.root)["questions"][0]
        self.assertIn("提高精度",saved["options"])
        self.assertEqual(len(saved["choices"]),3)
    def test_native_recommended_label_round_trip(self):
        item=self.add()
        req=codex_request(item)
        self.assertEqual(req["questions"][0]["options"][0]["label"],
                         "提高精度 (Recommended)")
        result=resolve_codex_answer(item,{
            "answers":{"q_0001":{"answers":["提高精度 (Recommended)"]}}})
        self.assertEqual(result["choice_id"],"accuracy")
    def test_other_without_text_cannot_confirm(self):
        self.add()
        for c in ("", "   "):
            with self.assertRaises(ResearchError):answer(self.root,"Q-0001",choice_id="other",custom_answer=c)
        self.assertEqual(read(self.root)["questions"][0]["status"],"pending")
    def test_unknown_id_and_mixed_selection_fail_closed(self):
        self.add()
        for kwargs in ({"choice_id":"none"},
                       {"choice_id":"accuracy","answer_text":"free"},
                       {"choice_id":"other","custom_answer":"idea","answer_text":"other"},
                       {"custom_answer":"idea"},
                       {"choice_id":"other","custom_answer":"x"*12001}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ResearchError):answer(self.root,"Q-0001",**kwargs)
        self.assertEqual(read(self.root)["questions"][0]["status"],"pending")
    def test_legacy_string_questions_continue_to_work(self):
        self.add(q(structured=False))
        answer(self.root,"Q-0001","A: any free text")
        v=read(self.root)["questions"][0]
        self.assertEqual(v["answer"],"A: any free text")
        self.assertIsNone(v["selected_option_id"])
        self.assertEqual(v["answer_source"],"free-text")
        self.assertIn("其他／自定义",text_prompt(v))
        with self.assertRaises(ResearchError):codex_request(v)
    def test_old_041_sidecar_without_new_metadata_still_reads(self):
        self.add(q(structured=False))
        answer(self.root,"Q-0001","user-supplied result")
        p=self.root/"research"/"interviews"/"current.json"
        obj=json.loads(p.read_text(encoding="utf-8"))
        for x in obj["questions"]:
            for key in ("selected_option_id","custom_answer","answer_source","choices","recommended_choice_id"):
                x.pop(key,None)
        p.write_text(json.dumps(obj),encoding="utf-8")
        v=read(self.root)
        self.assertEqual(v["questions"][0]["answer"],"user-supplied result")
    def test_revised_choice_invalidates_downstream(self):
        self.add()
        self.add(q(["Q-0001"],title="如何测试这个目标？"))
        answer(self.root,"Q-0001",choice_id="accuracy")
        answer(self.root,"Q-0002",choice_id="accuracy")
        answer(self.root,"Q-0001",choice_id="other",custom_answer="改变目标",revise=True)
        after=read(self.root)["questions"][1]
        self.assertEqual(after["status"],"unresolved")
        self.assertIsNone(after["selected_option_id"])
        self.assertIsNone(after["custom_answer"])
        self.assertEqual(after["answer_source"],"unanswered")
    def test_malformed_choice_specs_rejected_atomically(self):
        samples=[
            [{"id":"other","label":"A","description":"x"},{"id":"b","label":"B","description":"y"}],
            [{"id":"a","label":"A","description":"x"},{"id":"a","label":"B","description":"y"}],
            [{"id":"a","label":"A","description":"x"},{"id":"b","label":"A","description":"y"}],
            [{"id":"a","label":"A","description":"x"}],
        ]
        for sample in samples:
            x=q();x["choices"]=sample
            with self.assertRaises(ResearchError):add_questions(self.root,[x])
        self.assertEqual(len(read(self.root)["questions"]),0)
    def test_recommended_id_requires_real_choice(self):
        data=q();data["recommended_choice_id"]="absent"
        with self.assertRaises(ResearchError):add_questions(self.root,[data])
    def test_native_payload_and_other_generated_by_codex_not_manual(self):
        x=self.add()
        out=codex_request(x)
        items=out["questions"][0]["options"]
        self.assertEqual(len(items),3)
        self.assertFalse(any(k["label"].lower()=="other" for k in items))
        self.assertEqual(out["questions"][0]["id"],"q_0001")
        self.assertLessEqual(len(out["questions"][0]["header"]),12)
    def test_native_response_map_and_free_other(self):
        x=self.add()
        selected=resolve_codex_answer(x,{"answers":{"q_0001":{"answers":["提高精度"]}}})
        self.assertEqual(selected,{"choice_id":"accuracy","custom_answer":None})
        other=resolve_codex_answer(x,{"answers":{"q_0001":{"selected":["Other"],"other":"不一样的研究方向"}}})
        self.assertEqual(other,{"choice_id":"other","custom_answer":"不一样的研究方向"})
    def test_default_mode_async_payload_and_later_user_reply(self):
        item=self.add()
        packet=codex_async_request(item)
        self.assertEqual(packet["questions"][0]["options"][0],"提高精度")
        self.assertNotIn("Other",packet["questions"][0]["options"])
        self.assertEqual(resolve_async_reply(item,"降低成本"),
                         {"choice_id":"cost","custom_answer":None})
        self.assertEqual(resolve_async_reply(item,"新的科研目标"),
                         {"choice_id":"other","custom_answer":"新的科研目标"})
        self.assertEqual(read(self.root)["questions"][0]["status"],"pending")
    def test_async_ack_is_not_user_confirmation(self):
        self.add()
        argv=[sys.executable,str(Path(__file__).resolve().parents[1]/"scripts"/"interview.py"),
              str(self.root)]
        before=read(self.root)["revision"]
        result=subprocess.run(argv+["async-request","--question","Q-0001"],
                              capture_output=True,text=True,check=True)
        d=json.loads(result.stdout)
        self.assertEqual(d["tool_name"],"request_user_input_async")
        self.assertTrue(d["async_ack_is_not_user_answer"])
        self.assertFalse(d["tool_called"])
        self.assertEqual(read(self.root)["revision"],before)
    def test_async_legacy_free_text_does_not_invent_choice(self):
        question=self.add(q(structured=False))
        self.assertEqual(codex_async_request(question)["questions"][0],
                         {"title":question["text"]})
        self.assertEqual(resolve_async_reply(question,"Original idea"),
                         {"choice_id":None,"custom_answer":None,
                          "answer_text":"Original idea"})
    def test_native_ambiguous_values_refused(self):
        x=self.add()
        bad=[
            {"answers":{"q_0001":{"answers":["unknown"]}}},
            {"answers":{"q_0001":{"selected":["提高精度","降低成本"]}}},
            {"answers":{"q_0001":{"selected":["Other"],"other":""}}},
            {"answers":{"other_id":{"selected":["提高精度"]}}},
        ]
        for item in bad:
            with self.subTest(item=item):
                with self.assertRaises(ResearchError):resolve_codex_answer(x,item)
        self.assertEqual(read(self.root)["questions"][0]["status"],"pending")
    def test_fallback_more_than_three_choices(self):
        x=q();x["choices"].append({"id":"speed","label":"加快训练","description":"优化训练性能"})
        item=self.add(x)
        self.assertIn("其他／自定义",text_prompt(item))
        with self.assertRaises(ResearchError):codex_request(item)
        answer(self.root,"Q-0001",choice_id="speed")
        self.assertEqual(read(self.root)["questions"][0]["selected_option_id"],"speed")
    def test_exit_after_other_preserves_consensus(self):
        self.add()
        answer(self.root,"Q-0001",choice_id="other",custom_answer="新的研究目标")
        request_exit(self.root,"用户确定原建议外的新研究目标")
        confirm_exit(self.root)
        self.assertEqual(frontier(read(self.root))["ready"],[])
        self.assertEqual(read(self.root)["questions"][0]["custom_answer"],"新的研究目标")
    def test_cli_preview_is_read_only_even_with_response(self):
        x=self.add()
        argv=[sys.executable,str(Path(__file__).resolve().parents[1]/"scripts"/"interview.py"),str(self.root)]
        before=read(self.root)["revision"]
        r=subprocess.run(argv+["native-request","--question","Q-0001"],capture_output=True,text=True,check=True)
        data=json.loads(r.stdout)
        self.assertFalse(data["tool_called"])
        self.assertTrue(data["must_check_runtime_capability"])
        response=json.dumps({"answers":{"q_0001":{"answers":["提高精度"]}}},ensure_ascii=False)
        r=subprocess.run(argv+["resolve-native","--question","Q-0001","--response-json",response],
                         capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(r.stdout)["resolved"]["choice_id"],"accuracy")
        self.assertEqual(read(self.root)["revision"],before)
    def test_no_native_tool_plan_uses_normal_chat_with_other_and_supplement(self):
        question=self.add()
        data=delivery_plan(question,capability="none")
        self.assertEqual(data["mode"],"chat")
        self.assertFalse(data["native_tool_called"])
        self.assertIsNone(data["native_tool"])
        self.assertIn("其他／自定义",data["fallback_text"])
        self.assertIn("补充说明（可选）",data["fallback_text"])
        self.assertIn("A. 提高精度",data["fallback_text"])
        self.assertTrue(data["requires_explicit_user_confirmation"])
    def test_native_failure_or_cancel_always_falls_back(self):
        item=self.add()
        for capability in ("none","sync","async"):
            for fail in ("unavailable","error","timeout","cancelled","no-answer"):
                with self.subTest(capability=capability,reason=fail):
                    plan=delivery_plan(item,capability=capability,failure=fail)
                    self.assertEqual(plan["mode"],"chat")
                    self.assertIsNone(plan["native_arguments"])
                    self.assertIn("其他／自定义",plan["fallback_text"])
                    self.assertIn("补充说明",plan["fallback_text"])
        self.assertEqual(read(self.root)["questions"][0]["status"],"pending")
    def test_native_synchronous_and_asynchronous_are_only_candidates(self):
        item=self.add()
        for mode,tool in (("sync","request_user_input"),("async","request_user_input_async")):
            plan=delivery_plan(item,capability=mode)
            self.assertEqual(plan["mode"],"native-candidate")
            self.assertEqual(plan["native_tool"],tool)
            self.assertFalse(plan["native_tool_called"])
            self.assertFalse(plan["user_answer_received"])
            self.assertIn("其他／自定义",plan["fallback_text"])
    def test_four_choices_fallback_preserves_all_choices(self):
        data=q()
        data["choices"].append({"id":"speed","label":"训练速度","description":"减少等待"})
        item=self.add(data)
        result=delivery_plan(item,capability="sync")
        self.assertEqual(result["mode"],"chat")
        self.assertIn("D. 训练速度",result["fallback_text"])
        self.assertIn("其他／自定义",result["fallback_text"])
        self.assertIn("补充说明",result["fallback_text"])
    def test_preset_choice_with_supplement_persists_across_sessions(self):
        self.add()
        original="但我希望在保证准确率的前提下控制预算"
        answer(self.root,"Q-0001",choice_id="accuracy",supplement=original)
        selected=read(self.root)["questions"][0]
        self.assertEqual(selected["selected_option_id"],"accuracy")
        self.assertEqual(selected["supplement"],original)
        self.assertEqual(selected["answer"],"提高精度")
        packet=handoff(self.root)
        self.assertEqual(packet["confirmed"][0]["supplement"],original)
        pause(self.root);resume(self.root)
        self.assertEqual(read(self.root)["questions"][0]["supplement"],original)
    def test_other_and_free_text_can_include_extra_explanation(self):
        self.add()
        answer(self.root,"Q-0001",choice_id="other",
               custom_answer="研究数据漂移",supplement="要先收集各站点分布")
        result=read(self.root)["questions"][0]
        self.assertEqual(result["custom_answer"],"研究数据漂移")
        self.assertEqual(result["supplement"],"要先收集各站点分布")
        answer(self.root,"Q-0001",answer_text="新思路",
               supplement="原因是基线无法比较",revise=True)
        result=read(self.root)["questions"][0]
        self.assertEqual(result["answer_source"],"free-text")
        self.assertEqual(result["supplement"],"原因是基线无法比较")
        self.assertIsNone(result["selected_option_id"])
    def test_blank_invalid_supplement_rejected_without_writes(self):
        self.add()
        before=read(self.root)
        for val in ("", "   ", "x"*12001):
            with self.subTest(value_length=len(val)):
                with self.assertRaises(ResearchError):
                    answer(self.root,"Q-0001",choice_id="cost",supplement=val)
        self.assertEqual(read(self.root),before)
    def test_revision_clears_dependent_supplement(self):
        self.add()
        self.add(q(["Q-0001"]))
        answer(self.root,"Q-0001",choice_id="accuracy",supplement="初始约束")
        answer(self.root,"Q-0002",choice_id="cost",supplement="依赖初始假设")
        answer(self.root,"Q-0001",choice_id="other",custom_answer="换新的目标",revise=True)
        dep=read(self.root)["questions"][1]
        self.assertEqual(dep["status"],"unresolved")
        self.assertIsNone(dep["supplement"])
        self.assertIsNone(dep["selected_option_id"])
    def test_cli_present_fallback_is_read_only(self):
        self.add()
        argv=[sys.executable,str(Path(__file__).resolve().parents[1]/"scripts"/"interview.py"),
              str(self.root),"present","--question","Q-0001"]
        rev=read(self.root)["revision"]
        proc=subprocess.run(argv,capture_output=True,text=True,check=True)
        result=json.loads(proc.stdout)
        self.assertEqual(result["mode"],"chat")
        self.assertIn("补充说明",result["fallback_text"])
        proc=subprocess.run(argv+["--capability","sync","--failure","error"],
                            capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(proc.stdout)["mode"],"chat")
        self.assertEqual(read(self.root)["revision"],rev)
    def test_canvas_is_still_read_only_and_escapes(self):
        d=q(title='<script>alert("x")</script>')
        self.add(d)
        revision=read(self.root)["revision"]
        output=build_canvas(self.root)
        rendered=(output.parent/"interview.html").read_text(encoding="utf-8")
        self.assertNotIn('<script>alert("x")</script>',rendered)
        self.assertIn("\\u003cscript\\u003e",rendered)
        self.assertIn("生成回答草案",rendered)
        self.assertEqual(read(self.root)["revision"],revision)

if __name__=="__main__":
    unittest.main()
