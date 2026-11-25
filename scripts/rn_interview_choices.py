"""Choice projection for v0.4.2 interviews.

Pure validation/formatting; no Codex tool invocation or scientific state writes.
Native requests are capability-dependent. Codex clients provide free-form Other.
"""
from __future__ import annotations
import re
from rn_core import ResearchError

CHOICE_ID=re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,39}$")
MAX_CHOICES=12
OTHER="other"

def validate_choices(choices, recommended=None):
    if not isinstance(choices,list) or not 2<=len(choices)<=MAX_CHOICES:
        raise ResearchError("structured choices require 2-12 choices")
    ids=set();labels=set()
    for item in choices:
        if not isinstance(item,dict) or not CHOICE_ID.fullmatch(str(item.get("id",""))):
            raise ResearchError("invalid choice ID")
        ident=item["id"]
        if ident.lower()==OTHER or ident.lower() in ids:
            raise ResearchError("reserved or duplicate choice ID")
        ids.add(ident.lower())
        for key,limit in (("label",150),("description",600)):
            val=item.get(key)
            if not isinstance(val,str) or not val.strip() or len(val)>limit:
                raise ResearchError("invalid choice "+key)
        if item["label"].casefold() in labels:
            raise ResearchError("duplicate choice label")
        labels.add(item["label"].casefold())
    if recommended is not None and (not isinstance(recommended,str) or recommended.lower() not in ids):
        raise ResearchError("recommended_choice_id missing from choices")
    return True

def display_choices(question):
    choices=question.get("choices")
    if isinstance(choices,list) and choices:
        validate_choices(choices,question.get("recommended_choice_id"))
        return [{"id":c["id"],"label":c["label"],"description":c["description"]}
                for c in choices]
    return []

def answer_fields(question,answer_text,choice_id=None,custom_answer=None):
    """Return normalized fields. Legacy free text remains compatible."""
    choices=display_choices(question)
    if choice_id is None:
        if custom_answer is not None:raise ResearchError("--custom-answer requires --choice other")
        if not isinstance(answer_text,str) or not answer_text.strip():
            raise ResearchError("free-text answer must be nonempty")
        return {"answer":answer_text.strip(),"selected_option_id":None,
                "custom_answer":None,"answer_source":"free-text"}
    if not choices:
        raise ResearchError("typed selection requires structured question choices")
    if not isinstance(choice_id,str):raise ResearchError("invalid choice ID")
    if choice_id.lower()==OTHER:
        if not isinstance(custom_answer,str) or not custom_answer.strip() or len(custom_answer)>12000:
            raise ResearchError("Other requires nonempty custom answer")
        if answer_text:
            raise ResearchError("do not combine --text and --custom-answer")
        return {"answer":custom_answer.strip(),"selected_option_id":OTHER,
                "custom_answer":custom_answer.strip(),"answer_source":"other"}
    if custom_answer is not None or answer_text:
        raise ResearchError("choice selection cannot also provide free text")
    match=next((c for c in choices if c["id"]==choice_id),None)
    if match is None:raise ResearchError("unknown question choice ID")
    return {"answer":match["label"],"selected_option_id":match["id"],
            "custom_answer":None,"answer_source":"choice"}

def codex_request(question):
    """Build a *suggested* request_user_input request, never execute it.

    The Codex tool is not necessarily offered in the current client/mode.
    Caller must check actual tool availability; never emulate successful call.
    """
    choices=display_choices(question)
    if not 2<=len(choices)<=3:
        raise ResearchError("native Codex picker requires 2-3 structured choices")
    if len({x["label"] for x in choices})!=len(choices):
        raise ResearchError("ambiguous native choice labels")
    header="研究问题 "+question["id"].replace("Q-","")
    suggested=question.get("recommended_choice_id")
    ordered=sorted(choices,key=lambda c: 0 if c["id"]==suggested else 1)
    options=[]
    for c in ordered:
        native_label=c["label"]+(" (Recommended)" if c["id"]==suggested else "")
        options.append({"label":native_label,"description":c["description"][:200]})
    return {"questions":[{
        "id":question["id"].lower().replace("-","_"),
        "header":header[:12],
        "question":question["text"],
        "options":options,
    }]}

def text_prompt(question):
    choices=display_choices(question)
    preface=question["id"]+" "+question["text"]
    if choices:
        lines=[preface]+[f"{chr(65+i)}. {c['label']} — {c['description']}"
                          for i,c in enumerate(choices)]
        lines.append("其他／自定义：直接输入自己的想法（不限于上述备选项）。")
        lines.append("也可以暂缓回答，或说明目前仍存在分歧。")
    else:
        lines=[preface,question.get("options",""),"其他／自定义：直接输入自己的答案。"]
    return "\n".join(lines)

def resolve_codex_answer(question, response):
    """Strictly interpret one Codex native answer, without writing project state.

    Supports common {answers:{q_id:{answers:[label]}}} and
    {answers:{q_id:{selected:[label],other:text}}} response variants.
    """
    payload=codex_request(question)
    qid=payload["questions"][0]["id"]
    if not isinstance(response,dict) or not isinstance(response.get("answers"),dict):
        raise ResearchError("malformed Codex answer")
    item=response["answers"].get(qid)
    if not isinstance(item,dict):raise ResearchError("native answer missing")
    selected=item.get("answers",item.get("selected"))
    if not isinstance(selected,list) or len(selected)!=1 or not isinstance(selected[0],str):
        raise ResearchError("expected exactly one native answer")
    raw=selected[0]
    mapping={c["label"]:c["id"] for c in display_choices(question)}
    recommended=question.get("recommended_choice_id")
    if recommended is not None:
        recommended_label=next(c["label"] for c in display_choices(question)
                               if c["id"]==recommended)
        mapping[recommended_label+" (Recommended)"]=recommended
    if raw in mapping:
        if item.get("other"):raise ResearchError("unexpected Other alongside a selected choice")
        return {"choice_id":mapping[raw],"custom_answer":None}
    other=item.get("other")
    if raw.casefold()=="other" and isinstance(other,str) and other.strip():
        return {"choice_id":OTHER,"custom_answer":other.strip()}
    # Client may return the literal Other text in the selection list instead.
    if isinstance(other,str) and other.strip() and raw==other:
        return {"choice_id":OTHER,"custom_answer":other.strip()}
    raise ResearchError("ambiguous or unknown native choice; ask for confirmation")
