"""Persistent Research Navigator grilling interview lifecycle (v0.4.1).

Separate, locked, project-scoped sidecar. This is a record of conversational
decisions, NOT scientific proof, an authenticated identity or a Skill activation
token. Only explicitly invoked commands modify interview state.
"""
from __future__ import annotations
import copy
import re
import uuid
from pathlib import Path

from rn_core import ResearchError, atomic_json, load, now, paths, read_json, workspace_lock
from rn_interview_choices import validate_choices, answer_fields

VERSION = "interview-v1"
STATUSES = ("active", "paused", "consensus-review", "completed", "abandoned")
QUESTION_STATES = ("pending", "answered", "deferred", "unresolved")
ACTORS = ("user", "mentor", "agent")
ID_RE = re.compile(r"^Q-[0-9]{4,}$")
MAX_QUESTIONS_PER_ROUND = 5
MAX_QUESTION_TEXT = 2000
MAX_ANSWER_TEXT = 12000

def interview_path(root):
    return paths(root)["root"]/"research"/"interviews"/"current.json"

def _actor(actor):
    if actor not in ACTORS:
        raise ResearchError("interview actor must be user, mentor or agent")

def _human(actor):
    _actor(actor)
    if actor not in ("user", "mentor"):
        raise ResearchError("此操作需要用户/导师明确同意，Agent 不得代为确认")

def _project(root):
    s = load(root)
    return s["project"]

def _read(root):
    p = interview_path(root)
    if not p.exists():
        raise ResearchError("没有持久化访谈；先显式执行 interview start")
    try:
        value = read_json(p)
    except (ValueError, OSError) as exc:
        raise ResearchError("访谈状态无效或损坏，请先备份恢复") from exc
    _validate(value, _project(root))
    return value

def _validate(doc, project):
    if not isinstance(doc, dict) or doc.get("schema_version") != VERSION:
        raise ResearchError("invalid interview sidecar schema")
    if doc.get("project_id") != project["project_id"]:
        raise ResearchError("访谈与当前研究项目 ID 不匹配")
    if doc.get("status") not in STATUSES:
        raise ResearchError("invalid interview status")
    if not isinstance(doc.get("revision"),int) or isinstance(doc["revision"],bool) or doc["revision"]<0:
        raise ResearchError("invalid interview revision")
    if not isinstance(doc.get("interview_id"),str) or not doc["interview_id"]:
        raise ResearchError("missing interview identifier")
    qlist = doc.get("questions")
    if not isinstance(qlist,list):
        raise ResearchError("interview questions must be a list")
    byid = {}
    for q in qlist:
        if not isinstance(q,dict) or not isinstance(q.get("id"),str) or not ID_RE.fullmatch(q["id"]):
            raise ResearchError("invalid question ID")
        if q["id"] in byid:
            raise ResearchError("duplicate question ID")
        byid[q["id"]]=q
        if not isinstance(q.get("text"),str) or not 1<=len(q["text"].strip())<=MAX_QUESTION_TEXT:
            raise ResearchError("invalid question text")
        guidance_keys=("why","recommendation","lowest_cost_check")
        if "choices" not in q: guidance_keys+=("options",)
        for k in guidance_keys:
            if not isinstance(q.get(k),str) or not q[k].strip():
                raise ResearchError("question missing guidance: "+k)
        if "choices" in q and ("options" in q and
                                (not isinstance(q["options"],str) or not q["options"].strip())):
            raise ResearchError("legacy options summary must be nonempty when supplied")
        if "choices" in q:
            validate_choices(q["choices"], q.get("recommended_choice_id"))
        if "supplement" in q and q["supplement"] is not None:
            extra=q["supplement"]
            if (q.get("status")!="answered" or not isinstance(extra,str)
                or not extra.strip() or len(extra)>12000):
                raise ResearchError("unconfirmed/invalid supplementary explanation")
        if "selected_option_id" in q:
            selected=q["selected_option_id"]
            origin=q.get("answer_source")
            if selected is not None:
                if q.get("status")!="answered":
                    raise ResearchError("unconfirmed question must clear selected choice")
                if origin not in ("choice","other"):
                    raise ResearchError("invalid answer source")
                normalized=answer_fields(q,"",choice_id=selected,
                    custom_answer=q.get("custom_answer"),
                    supplement=q.get("supplement"))
                if normalized["answer"]!=q.get("answer"):
                    raise ResearchError("selected answer does not match option or custom answer")
            elif origin not in (None,"free-text","unanswered"):
                raise ResearchError("invalid free-text answer source")
        if q.get("status") not in QUESTION_STATES:
            raise ResearchError("invalid question state")
        if not isinstance(q.get("depends_on"),list) or len(set(q["depends_on"]))!=len(q["depends_on"]):
            raise ResearchError("invalid question prerequisites")
        if q["status"]=="answered":
            if not isinstance(q.get("answer"),str) or not q["answer"].strip() or q.get("confirmed_by") not in ("user","mentor"):
                raise ResearchError("answered question requires explicit human confirmation")
        elif q.get("confirmed_by") is not None:
            raise ResearchError("unanswered question cannot be confirmed")
    for q in qlist:
        if any(d not in byid or d==q["id"] for d in q["depends_on"]):
            raise ResearchError("dangling or self-dependent interview question")
    gray=set(); black=set()
    def visit(x):
        if x in gray:raise ResearchError("question dependency cycle")
        if x in black:return
        gray.add(x)
        for dep in byid[x]["depends_on"]:visit(dep)
        gray.remove(x);black.add(x)
    for x in byid:visit(x)
    if not isinstance(doc.get("history"),list):
        raise ResearchError("missing interview audit history")
    if doc.get("status")=="completed":
        accepted=doc.get("accepted_open_questions")
        if not isinstance(accepted,list):
            raise ResearchError("completed interview must record accepted open questions")
        actual={q["id"] for q in qlist if q["status"]!="answered"}
        if set(accepted)!=actual or len(accepted)!=len(actual):
            raise ResearchError("completion cannot silently hide unresolved questions")
        if doc.get("exit_confirmed_by") not in ("user","mentor"):
            raise ResearchError("completion requires human confirmed exit")
    return True

def _event(doc,action,actor,detail):
    doc["history"].append({"event_id":str(uuid.uuid4()),"at":now(),
                           "action":action,"actor":actor,"detail":detail})
    doc["updated_at"]=now()
    doc["revision"]+=1

def _save(root,doc,project):
    _validate(doc,project)
    atomic_json(interview_path(root),doc)
    return copy.deepcopy(doc)

def _mutate(root,fn,*,expected_revision=None):
    with workspace_lock(root):
        project=_project(root)
        doc=_read(root)
        if expected_revision is not None and doc["revision"]!=expected_revision:
            raise ResearchError("stale interview revision: expected %s actual %s"%
                                (expected_revision,doc["revision"]))
        result=fn(doc)
        doc["last_seen_project_revision"]=project["revision"]
        saved=_save(root,doc,project)
        return saved if result is None else result

def start(root, *, topic, actor="user", restart=False):
    _human(actor)
    if not isinstance(topic,str) or not topic.strip():
        raise ResearchError("访谈必须指定研究话题，不能隐式启动")
    with workspace_lock(root):
        project=_project(root)
        p=interview_path(root)
        if p.exists():
            previous=_read(root)
            if not restart or previous["status"] not in ("completed","abandoned"):
                raise ResearchError("已有访谈；先 resume/status，结束后显式 --restart 才可开始新访谈")
            archive=p.parent/"archive"/(previous["interview_id"]+".json")
            if archive.exists():
                raise ResearchError("旧访谈归档已存在，拒绝覆盖")
            atomic_json(archive,previous)
        stamp=now()
        doc={"schema_version":VERSION,"interview_id":str(uuid.uuid4()),
             "project_id":project["project_id"],"project_root":str(paths(root)["root"]),
             "topic":topic.strip(),"status":"active","revision":0,
             "last_seen_project_revision":project["revision"],
             "created_at":stamp,"updated_at":stamp,
             "questions":[],"history":[],"round":0,
             "resume_to":None,"accepted_open_questions":[],
             "exit_confirmed_by":None,"consensus_note":""}
        _event(doc,"started",actor,{"topic":topic.strip(),"restart":bool(restart)})
        return _save(root,doc,project)

def read(root):
    return copy.deepcopy(_read(root))

def _questions(doc):
    return {q["id"]:q for q in doc["questions"]}

def add_questions(root,questions,*,actor="agent",expected_revision=None):
    _actor(actor)
    if not isinstance(questions,list) or not 1<=len(questions)<=MAX_QUESTIONS_PER_ROUND:
        raise ResearchError("每轮应新增 1–5 个高价值问题")
    def op(doc):
        if doc["status"]!="active":
            raise ResearchError("仅 active 访谈可提出新问题")
        current=_questions(doc); ids=set(current)
        doc["round"]+=1
        newly=[]
        for data in questions:
            if not isinstance(data,dict):
                raise ResearchError("question must be an object")
            dependencies=data.get("depends_on",[])
            if not isinstance(dependencies,list) or any(d not in ids for d in dependencies):
                raise ResearchError("新问题依赖必须引用已有的前置问题")
            required=("text","why","recommendation","lowest_cost_check")
            if "choices" not in data: required+=("options",)
            for k in required:
                if not isinstance(data.get(k),str) or not data[k].strip():
                    raise ResearchError("missing question guidance: "+k)
            if len(data["text"])>MAX_QUESTION_TEXT:
                raise ResearchError("question too long")
            n=1
            while "Q-%04d"%n in ids:n+=1
            qid="Q-%04d"%n
            if "choices" in data:
                validate_choices(data["choices"],data.get("recommended_choice_id"))
            elif "recommended_choice_id" in data:
                raise ResearchError("recommended choice requires structured choices")
            q={"id":qid,"text":data["text"].strip(),"why":data["why"].strip(),
               "options":(data.get("options") or
                          "；".join(c["label"] for c in data["choices"])).strip(),
               **({"choices":copy.deepcopy(data["choices"]),
                   "recommended_choice_id":data.get("recommended_choice_id")}
                  if "choices" in data else {}),
               "recommendation":data["recommendation"].strip(),
               "lowest_cost_check":data["lowest_cost_check"].strip(),
               "depends_on":list(dependencies),"status":"pending","answer":"",
               "confirmed_by":None,"round":doc["round"],"answered_at":None,
               "selected_option_id":None,"custom_answer":None,
               "answer_source":"unanswered","supplement":None}
            ids.add(qid)
            doc["questions"].append(q);newly.append(qid)
        _event(doc,"questions-added",actor,{"ids":newly,"round":doc["round"]})
    return _mutate(root,op,expected_revision=expected_revision)

def answer(root,question_id,answer_text="",*,status="answered",actor="user",
           revise=False,expected_revision=None,choice_id=None,custom_answer=None,
           supplement=None):
    _human(actor)
    if status not in ("answered","deferred","unresolved"):
        raise ResearchError("answer status must be answered, deferred or unresolved")
    if not isinstance(answer_text,str) or len(answer_text)>MAX_ANSWER_TEXT:
        raise ResearchError("answer text too long or invalid")
    if status=="answered" and choice_id is None and not answer_text.strip():
        raise ResearchError("请给出具体回答，或标记 deferred/unresolved")
    def op(doc):
        if doc["status"]!="active":
            raise ResearchError("仅 active 访谈可记录回答")
        q=_questions(doc).get(question_id)
        if not q:raise ResearchError("unknown interview question")
        if q["status"]=="answered" and not revise:
            raise ResearchError("已确认回答不可静默覆盖；请使用 --revise")
        prior=_questions(doc)
        if any(prior[d]["status"]!="answered" for d in q["depends_on"]):
            raise ResearchError("前置问题尚未得到确认，不能回答依赖问题")
        old=q["status"]
        if status=="answered":
            fields=answer_fields(q,answer_text,choice_id,custom_answer,supplement)
        else:
            if choice_id is not None or custom_answer is not None or supplement is not None:
                raise ResearchError("deferred/unresolved cannot select or supplement a confirmed choice")
            fields={"answer":answer_text.strip(),"selected_option_id":None,
                    "custom_answer":None,"answer_source":"unanswered",
                    "supplement":None}
        q["status"]=status
        q["answer"]=fields["answer"]
        q["selected_option_id"]=fields["selected_option_id"]
        q["custom_answer"]=fields["custom_answer"]
        q["answer_source"]=fields["answer_source"]
        q["supplement"]=fields["supplement"]
        q["confirmed_by"]=actor if status=="answered" else None
        q["answered_at"]=now()
        affected=[]
        if old=="answered":
            children={question_id}
            while children:
                parent=children.pop()
                for other in doc["questions"]:
                    if parent not in other["depends_on"] or other["id"] in affected:continue
                    # A changed confirmed premise invalidates downstream answers.
                    if other["status"]=="answered":
                        other["status"]="unresolved";other["confirmed_by"]=None
                        other["selected_option_id"]=None
                        other["custom_answer"]=None
                        other["answer_source"]="unanswered"
                        other["supplement"]=None
                        affected.append(other["id"])
                    children.add(other["id"])
        _event(doc,"answer-"+status,actor,
               {"question_id":question_id,"revise":revise,
                "invalidated_dependents":affected,
                "selected_option_id":q["selected_option_id"],
                "answer_source":q["answer_source"],
                "has_supplement":bool(q["supplement"])})
    return _mutate(root,op,expected_revision=expected_revision)

def frontier(doc,limit=MAX_QUESTIONS_PER_ROUND):
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=MAX_QUESTIONS_PER_ROUND:
        raise ResearchError("frontier limit must be 1–5")
    _validate_frontier_input(doc)
    # Completed/abandoned interviews are historic, not an active question queue.
    # Paused and consensus-review interviews still expose pending context for
    # human review and explicit resumption.
    if doc.get("status") in ("completed", "abandoned"):
        return {"interview_id":doc["interview_id"],"status":doc["status"],
                "revision":doc["revision"],"topic":doc["topic"],
                "ready":[],"blocked":[],
                "open_count":sum(q["status"]!="answered" for q in doc["questions"]),
                "accepted_open_questions":list(doc.get("accepted_open_questions",[])),
                "requires_explicit_exit_confirmation":False}
    byid=_questions(doc)
    ready=[copy.deepcopy(q) for q in doc["questions"]
           if q["status"] in ("pending","deferred","unresolved")
           and all(byid[d]["status"]=="answered" for d in q["depends_on"])]
    blocked=[{"id":q["id"],"depends_on":
              [d for d in q["depends_on"] if byid[d]["status"]!="answered"]}
             for q in doc["questions"] if q["status"]!="answered"
             and any(byid[d]["status"]!="answered" for d in q["depends_on"])]
    return {"interview_id":doc["interview_id"],"status":doc["status"],
            "revision":doc["revision"],"topic":doc["topic"],
            "ready":ready[:limit],"blocked":blocked,
            "open_count":sum(q["status"]!="answered" for q in doc["questions"]),
            "requires_explicit_exit_confirmation":True}

def _validate_frontier_input(doc):
    if not isinstance(doc,dict) or not isinstance(doc.get("questions"),list):
        raise ResearchError("invalid interview data")

def pause(root,actor="user",expected_revision=None):
    _human(actor)
    def op(doc):
        if doc["status"] not in ("active","consensus-review"):
            raise ResearchError("仅进行中的访谈可以暂停")
        doc["resume_to"]=doc["status"];doc["status"]="paused"
        _event(doc,"paused",actor,{})
    return _mutate(root,op,expected_revision=expected_revision)

def resume(root,actor="user",expected_revision=None):
    _human(actor)
    def op(doc):
        if doc["status"]!="paused":
            raise ResearchError("仅暂停的访谈可以恢复")
        doc["status"]=doc.get("resume_to") if doc.get("resume_to") in ("active","consensus-review") else "active"
        doc["resume_to"]=None
        _event(doc,"resumed",actor,{})
    return _mutate(root,op,expected_revision=expected_revision)

def request_exit(root,note,actor="agent",expected_revision=None):
    _actor(actor)
    if not isinstance(note,str) or not note.strip():
        raise ResearchError("先整理已达共识与仍不确定的事项")
    def op(doc):
        if doc["status"]!="active":raise ResearchError("仅 active 可提出退出共识审核")
        doc["consensus_note"]=note.strip()
        doc["status"]="consensus-review"
        _event(doc,"exit-requested",actor,{"note":note.strip()})
    return _mutate(root,op,expected_revision=expected_revision)

def reject_exit(root,reason,actor="user",expected_revision=None):
    _human(actor)
    if not reason.strip():raise ResearchError("请指出需要继续澄清的内容")
    def op(doc):
        if doc["status"]!="consensus-review":
            raise ResearchError("不在共识审核阶段")
        doc["status"]="active";doc["consensus_note"]=""
        _event(doc,"exit-rejected",actor,{"reason":reason.strip()})
    return _mutate(root,op,expected_revision=expected_revision)

def confirm_exit(root,accepted_open_questions=None,actor="user",expected_revision=None):
    _human(actor)
    accepted_open_questions=accepted_open_questions or []
    def op(doc):
        if doc["status"]!="consensus-review":
            raise ResearchError("先 request-exit 并展示共识摘要")
        if len(accepted_open_questions)!=len(set(accepted_open_questions)):
            raise ResearchError("duplicate accepted open question")
        unresolved={q["id"] for q in doc["questions"] if q["status"]!="answered"}
        if set(accepted_open_questions)!=unresolved:
            raise ResearchError("必须逐项明确接受所有仍未回答的问题，不能静默视为共识")
        doc["accepted_open_questions"]=list(accepted_open_questions)
        doc["exit_confirmed_by"]=actor
        doc["status"]="completed"
        _event(doc,"exit-confirmed",actor,{"accepted_open_questions":list(accepted_open_questions),
                                           "consensus_note":doc["consensus_note"]})
    return _mutate(root,op,expected_revision=expected_revision)

def abandon(root,reason,actor="user",expected_revision=None):
    _human(actor)
    if not reason.strip():raise ResearchError("abandon requires reason")
    def op(doc):
        if doc["status"] in ("completed","abandoned"):
            raise ResearchError("访谈已关闭")
        doc["status"]="abandoned"
        _event(doc,"abandoned",actor,{"reason":reason.strip()})
    return _mutate(root,op,expected_revision=expected_revision)

def reopen(root,reason,actor="user",expected_revision=None):
    _human(actor)
    if not reason.strip():raise ResearchError("reopen requires reason")
    def op(doc):
        if doc["status"] not in ("completed","abandoned"):
            raise ResearchError("仅已结束访谈可重新打开")
        doc["status"]="active";doc["exit_confirmed_by"]=None
        doc["accepted_open_questions"]=[]
        _event(doc,"reopened",actor,{"reason":reason.strip()})
    return _mutate(root,op,expected_revision=expected_revision)

def handoff(root):
    doc=read(root)
    f=frontier(doc)
    resolved=[{"id":q["id"],"question":q["text"],"answer":q["answer"],
               "selected_option_id":q.get("selected_option_id"),
               "custom_answer":q.get("custom_answer"),
               "answer_source":q.get("answer_source","free-text"),
               "supplement":q.get("supplement")}
              for q in doc["questions"] if q["status"]=="answered"]
    return {"project_root":str(paths(root)["root"]),
            "interview_id":doc["interview_id"],
            "status":doc["status"],"revision":doc["revision"],
            "topic":doc["topic"],"confirmed":resolved,
            "frontier":f["ready"],"blocked":f["blocked"],
            "consensus_note":doc["consensus_note"],
            "accepted_open_questions":doc["accepted_open_questions"],
            "startup_hint":"在新 Codex Session 中明确调用 $research-navigator 并读取 "
                           "scripts/interview.py PROJECT_ROOT status/next。"
                           "新会话不保证继承前一个会话的 Skill 激活状态。"}
