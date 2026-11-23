"""Research Navigator durable state engine. Stdlib-only, no network or implicit AI decisions."""
from __future__ import annotations
import contextlib
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

SCHEMA_VERSION = "0.2.0"
LEGACY_SCHEMA_VERSION = "0.1.0"
MODULES = ("topic", "literature", "experiment", "pivot", "synthesis")
TYPES = ("ResearchQuestion", "Idea", "Method", "Hypothesis", "Concept", "Source", "PriorWork", "Baseline", "DatasetOrMaterial", "Experiment", "ExperimentPath", "Result", "Claim", "Decision", "Task", "Risk", "Artifact", "ResearchBranch", "Milestone")
PREFIXES = {"ResearchQuestion":"RQ", "Idea":"IDEA", "Method":"METH", "Hypothesis":"HYP", "Concept":"CON", "Source":"SRC", "PriorWork":"WORK", "Baseline":"BASE", "DatasetOrMaterial":"DATA", "Experiment":"EXP", "ExperimentPath":"PATH", "Result":"RES", "Claim":"CLAIM", "Decision":"DEC", "Task":"TASK", "Risk":"RISK", "Artifact":"ART", "ResearchBranch":"BR", "Milestone":"MILE"}
WORKFLOW = ("to-be-determined", "ready-for-agent", "to-be-implemented", "in-progress", "blocked", "done", "no-further-considered")
EPISTEMIC = ("uncertain", "hypothesis", "source-backed", "experimentally-supported", "contradicted", "not-applicable")
REVIEW = ("needs-user-confirmation", "user-confirmed", "not-required", "rejected")
OUTCOME = ("unknown", "positive", "mixed", "negative", "inconclusive")
LIFECYCLE = ("active", "parked", "quarantined", "retired", "under-revival-review")
IMPACT = ("current", "needs-review", "stale", "blocked")
RELATIONS = ("depends-on", "supports", "contradicts", "tests", "implements", "supersedes", "derived-from", "revives", "blocks", "member-of", "contributes-to")
ARCHIVED = ("parked", "quarantined", "retired")
ACTORS = ("agent", "user", "mentor", "tool")
ACCESS = ("full-text", "abstract", "secondary", "user-provided", "unavailable")
VERIFICATIONS = ("unverified", "metadata-checked", "primary-inspected")
FAILURE = ("theory", "method", "implementation", "data", "evaluation", "resources", "unknown")
CRITICAL_TYPES = ("ResearchQuestion", "Idea", "Method", "Hypothesis", "PriorWork", "Baseline", "Experiment", "Claim", "Result", "ResearchBranch", "Milestone")
CANDIDATE_TYPES = ("ResearchQuestion", "Idea", "Method", "Hypothesis", "Baseline", "ExperimentPath", "Task", "ResearchBranch")

class ResearchError(ValueError):
    pass

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def paths(root):
    root = Path(root).expanduser().resolve()
    st = root / "research" / "state"
    return {"root":root, "state":st, "project":st/"project.json", "items":st/"items.json", "relations":st/"relations.json", "sources":st/"sources.json", "events":st/"events.jsonl", "session_refs":st/"session_refs.json", "evidence_links":st/"evidence_links.json", "journal":st/"pending-transaction.json", "lock":st/".research-navigator.lock", "dash":root/"research"/"dashboard"/"index.html"}

def read_json(p):
    with Path(p).open(encoding="utf-8") as f:
        return json.load(f)

def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".rn-", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

@contextlib.contextmanager
def workspace_lock(root):
    p = paths(root)
    p["state"].mkdir(parents=True, exist_ok=True)
    with p["lock"].open("a+b") as file:
        try:
            import fcntl
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        except ImportError:
            # Windows: best-effort use the platform's byte-range lock.
            import msvcrt
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if os.name == "nt":
                file.seek(0); msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)

def init_project(root, name, question=""):
    p = paths(root)
    with workspace_lock(root):
        if p["project"].exists():
            raise ResearchError("项目已初始化；请直接 resume，不能重复初始化或覆盖")
        if any(p[key].exists() for key in ("items", "relations", "sources", "session_refs", "evidence_links", "events", "journal")):
            raise ResearchError("检测到部分已有状态文件；为避免覆盖，停止初始化，请先检查/备份")
        stamp = now()
        project = {"schema_version":SCHEMA_VERSION, "project_id":str(uuid.uuid4()), "name":name, "research_question":question, "focus_module":"topic", "next_decision":"明确问题对象、研究目标与资源约束", "revision":0, "created_at":stamp, "updated_at":stamp}
        atomic_json(p["project"],project)
        atomic_json(p["items"],{"items":[]})
        atomic_json(p["relations"],{"relations":[]})
        atomic_json(p["sources"],{"sources":[]})
        atomic_json(p["session_refs"],{"session_refs":[]})
        atomic_json(p["evidence_links"],{"evidence_links":[]})
        p["events"].touch(exist_ok=False)
        append_events(p, [{"action":"project-initialized", "actor":"user", "reason":"explicit initialization", "after":{"name":name, "research_question":question}}])
        intro = p["root"]/"RESEARCH.md"
        if not intro.exists():
            intro.write_text("# " + name + "\n\n研究问题：" + (question or "未确定") + "\n\n> 项目状态以 `research/state/*.json` 为准；浏览器只读看板位于 `research/dashboard/index.html`。\n\n## 恢复会话\n\n请让 research-navigator 读取项目状态并继续 frontier 访谈。\n", encoding="utf-8")
        return project

def load(root):
    p = paths(root)
    if p["journal"].exists():
        raise ResearchError("存在未完成的状态写入事务；先运行 migrate_state.py recover")
    if not p["project"].exists():
        raise ResearchError("未初始化项目；先执行 init")
    return {"project":read_json(p["project"]), "items":read_json(p["items"])["items"], "relations":read_json(p["relations"])["relations"], "sources":read_json(p["sources"])["sources"], "session_refs":read_json(p["session_refs"])["session_refs"] if p["session_refs"].exists() else [], "evidence_links":read_json(p["evidence_links"])["evidence_links"] if p["evidence_links"].exists() else [], "events":read_events(p["events"])}

def read_events(path):
    if not path.exists(): return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]

def append_events(p, events):
    with p["events"].open("a", encoding="utf-8") as f:
        for evt in events:
            rec = {"event_id":str(uuid.uuid4()), "timestamp":now(), **evt}
            f.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+"\n")
        f.flush()
        os.fsync(f.fileno())

def write(root, state, events, expected_revision=None):
    """Caller holds workspace lock. Crash-safe rollback journal, not a multi-file ACID database."""
    validate_state(state, strict=True)
    p=paths(root)
    current=read_json(p["project"])
    if current.get("schema_version") != SCHEMA_VERSION:
        raise ResearchError("旧版项目只读；请先执行 migrate_state.py apply")
    if expected_revision is not None and current["revision"] != expected_revision:
        raise ResearchError(f"stale write: expected revision {expected_revision}, actual {current['revision']}")
    if state["project"]["revision"] != current["revision"]:
        raise ResearchError("loaded state revision is stale; reload before modifying")
    if p["journal"].exists():
        raise ResearchError("存在未恢复的事务；请运行 migrate_state.py recover")
    saved={}
    for key in ("project","items","relations","sources","session_refs","evidence_links"):
        saved[key]=p[key].read_text(encoding="utf-8") if p[key].exists() else None
    saved["events"]=p["events"].read_text(encoding="utf-8") if p["events"].exists() else None
    # Record undo journal before changing state; explicit recovery is required after a crash.
    atomic_json(p["journal"], {"project_id":current["project_id"],
       "revision":current["revision"],"before":saved})
    try:
        state["project"]["updated_at"]=now()
        state["project"]["revision"]+=1
        atomic_json(p["items"],{"items":state["items"]})
        atomic_json(p["relations"],{"relations":state["relations"]})
        atomic_json(p["sources"],{"sources":state["sources"]})
        atomic_json(p["session_refs"],{"session_refs":state.get("session_refs",[])})
        atomic_json(p["evidence_links"],{"evidence_links":state.get("evidence_links",[])})
        atomic_json(p["project"],state["project"])
        append_events(p, events)
        p["journal"].unlink()
    except Exception:
        rollback_transaction(root, expected_id=current["project_id"])
        raise


def rollback_transaction(root, expected_id=None):
    """Only call while the workspace lock is held. Restores pre-write bytes exactly."""
    p=paths(root)
    if not p["journal"].exists():
        return False
    journal=read_json(p["journal"])
    if expected_id and journal.get("project_id") != expected_id:
        raise ResearchError("事务的项目 ID 与当前项目不匹配")
    original=journal["before"]
    for key in ("project","items","relations","sources","session_refs","evidence_links","events"):
        dest=p[key]
        content=original.get(key)
        if content is None:
            if dest.exists():dest.unlink()
        else:
            atomic_text(dest,content)
    p["journal"].unlink()
    return True


def atomic_text(path, text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".rn-restore-",dir=path.parent,text=True)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            out.write(text);out.flush();os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def require(value, allowed, label):
    if value not in allowed: raise ResearchError(f"{label}={value!r} 无效，可选: {', '.join(allowed)}")

def item_by_id(state, ident):
    obj=next((x for x in state["items"] if x["id"]==ident),None)
    if obj is None: raise ResearchError(f"找不到实体 {ident}")
    return obj

def unique_id(state, kind):
    pre=PREFIXES[kind]
    existing={x["id"] for x in state["items"]}
    i=1
    while f"{pre}-{i:04d}" in existing: i+=1
    return f"{pre}-{i:04d}"

def new_item(state, kind, title, module, description="", actor="agent", workflow="to-be-determined", epistemic=None, review=None, outcome="unknown", lifecycle="active", evidence_refs=None, acceptance_criteria="", next_action="", owner="", observation="", artifact_path="", completion_note="", derived_from=None):
    require(kind,TYPES,"type"); require(module,MODULES,"module"); require(actor,ACTORS,"actor")
    require(workflow,WORKFLOW,"workflow"); require(outcome,OUTCOME,"outcome"); require(lifecycle,LIFECYCLE,"lifecycle")
    if lifecycle!="active": raise ResearchError("新增对象必须从 active 开始；归档需先解释理由并经过状态变更")
    epistemic = epistemic or ("hypothesis" if kind in ("Idea","Hypothesis","ResearchQuestion", "ExperimentPath") else "uncertain")
    review = review or ("needs-user-confirmation" if kind in CRITICAL_TYPES else "not-required")
    require(epistemic,EPISTEMIC,"epistemic"); require(review,REVIEW,"review")
    if review=="user-confirmed" and actor not in ("user","mentor"): raise ResearchError("Agent 不得代用户确认")
    if workflow=="done" and (not acceptance_criteria.strip() or not completion_note.strip()): raise ResearchError("done 需要验收标准与完成证据说明")
    if kind=="Result" and not observation: raise ResearchError("Result 必须记录实际观察或显式标为模拟")
    if kind=="Result" and not artifact_path: raise ResearchError("Result 必须有结果文件/日志路径；可标注 synthetic fixture")
    evidence_refs=evidence_refs or []
    validate_evidence_level(state, epistemic, evidence_refs, observation, artifact_path)
    stamp=now()
    item={"id":unique_id(state,kind), "type":kind,"title":title,"module":module,"description":description,"workflow_status":workflow,"epistemic_status":epistemic,"review_status":review,"outcome":outcome,"lifecycle_status":lifecycle,"impact_status":"current","owner":owner,"created_by":actor,"evidence_refs":list(evidence_refs),"depends_on":[],"acceptance_criteria":acceptance_criteria,"next_action":next_action,"observation":observation,"artifact_path":artifact_path,"completion_note":completion_note,"revision":1,"created_at":stamp,"updated_at":stamp,"archive":None,"archive_history":[],"revival":None,"derived_from":derived_from}
    state["items"].append(item)
    return item

def validate_evidence_level(state, epistemic, refs, observation="", artifact=""):
    if epistemic=="source-backed":
        sources={s["id"]:s for s in state["sources"]}
        if not refs: raise ResearchError("source-backed 必须提供一手来源引用")
        if not any(x in sources and sources[x]["verification_status"]=="primary-inspected" for x in refs):
            raise ResearchError("source-backed 需要至少一项已实际查阅的原始来源；摘要/未查验来源不能冒充")
    if epistemic=="experimentally-supported" and not (observation.strip() and artifact.strip()):
        raise ResearchError("experimentally-supported 需要实际实验观察与工件路径；用户确认不能代替实验")

def add_item(root, *, expected_revision=None, proposal_id=None, **kwargs):
    with workspace_lock(root):
        state=load(root)
        item=new_item(state,**kwargs)
        write(root,state,[{"action":"item-created","actor":kwargs.get("actor","agent"),"item_id":item["id"],"reason":"new research item","after":copy.deepcopy(item),"proposal_id":proposal_id}],expected_revision=expected_revision)
        return item

def add_source(root, title, actor="agent", url="", doi="", authors="", year="", access_level="unavailable", verification_status="unverified", verification_note="", locator="", summary=""):
    require(actor,ACTORS,"actor"); require(access_level,ACCESS,"access level"); require(verification_status,VERIFICATIONS,"verification")
    if verification_status!="unverified" and not verification_note.strip(): raise ResearchError("来源标记已核实需写明核实动作")
    if verification_status=="primary-inspected" and access_level not in ("full-text","user-provided"):
        raise ResearchError("不能把仅看摘要/二手转述的论文标为 primary-inspected")
    if doi and not re.fullmatch(r"10\.\d{4,9}/\S+",doi): raise ResearchError("DOI 格式无效；格式有效不等于 DOI 真实存在")
    if not title.strip() or not (url or doi or locator): raise ResearchError("来源须有标题及可定位的 URI/DOI/路径")
    with workspace_lock(root):
        s=load(root)
        existing={x["id"] for x in s["sources"]}
        i=1
        while f"SRC-{i:04d}" in existing:i+=1
        row={"id":f"SRC-{i:04d}","title":title,"url":url,"doi":doi,"authors":authors,"year":year,"access_level":access_level,"verification_status":verification_status,"verification_note":verification_note,"locator":locator,"summary":summary,"recorded_by":actor,"accessed_at":now()}
        s["sources"].append(row)
        write(root,s,[{"action":"source-added","actor":actor,"item_id":row["id"],"reason":"source catalogued; bibliographic accuracy not independently guaranteed","after":row}])
        return row

def add_relation(root, source, target, relation, actor="agent", reason="", *, expected_revision=None, proposal_id=None):
    require(relation,RELATIONS,"relation"); require(actor,ACTORS,"actor")
    with workspace_lock(root):
        s=load(root)
        item_by_id(s,source); item_by_id(s,target)
        if source==target: raise ResearchError("禁止自链接")
        row={"from":source,"to":target,"type":relation}
        if row in s["relations"]: raise ResearchError("关系已存在")
        s["relations"].append(row)
        if relation=="member-of" and item_by_id(s,target)["type"]!="ResearchBranch":
            raise ResearchError("member-of must target ResearchBranch")
        if relation=="contributes-to" and item_by_id(s,target)["type"]!="Milestone":
            raise ResearchError("contributes-to must target Milestone")
        if relation=="depends-on": item_by_id(s,source)["depends_on"].append(target)
        events=[{"action":"relation-added","actor":actor,"item_id":source,"reason":reason or "explicit relation","after":row,"proposal_id":proposal_id}]
        if relation in ("contradicts","blocks"):
            affected=item_by_id(s,target)
            before=affected["impact_status"]
            affected["impact_status"]="blocked" if relation=="blocks" else "needs-review"
            affected["revision"]+=1;affected["updated_at"]=now()
            events.append({"action":"impact-propagated","actor":actor,"item_id":target,"reason":f"incoming {relation} relation from {source}","before":{"impact_status":before},"after":{"impact_status":affected["impact_status"]}})
            events+=propagate(s,target,actor,f"upstream {relation} {source}",block=(relation=="blocks"))
        write(root,s,events,expected_revision=expected_revision)
        return row

def dependents(state, ident):
    """Incoming positive dependencies only; no collateral impact to shared prerequisites."""
    out=set()
    for r in state["relations"]:
        a,b,t=r["from"],r["to"],r["type"]
        if t=="depends-on" and b==ident:out.add(a)
        elif t in ("supports","tests","implements","contributes-to","member-of") and a==ident:out.add(b)
        elif t=="supersedes" and b==ident:out.add(a)
    for rel in state.get("evidence_links", []):
        if rel.get("evidence_id") == ident:
            out.add(rel["claim_id"])
    return out

def propagate(state, ident, actor, reason, block=False):
    events=[]; seen={ident}; queue=[ident]
    while queue:
        current=queue.pop(0)
        for did in sorted(dependents(state,current)):
            if did in seen:continue
            seen.add(did); queue.append(did)
            item=item_by_id(state,did)
            old=item["impact_status"]
            item["impact_status"]="blocked" if block and item["lifecycle_status"]=="active" else "needs-review"
            if item["impact_status"]!=old:
                item["updated_at"]=now();item["revision"]+=1
                events.append({"action":"impact-propagated","actor":actor,"item_id":did,"reason":f"{reason}; upstream={ident}","before":{"impact_status":old},"after":{"impact_status":item["impact_status"]}})
    return events

def change_status(root, ident, field, value, reason, actor="agent", evidence_refs=None, completion_note="", failure_category="unknown", failure_scope="", confidence="uncertain", revival_triggers="", lesson="", cost="", revival_question="", new_conditions="", *, expected_revision=None, proposal_id=None):
    fields={"workflow_status":WORKFLOW,"epistemic_status":EPISTEMIC,"review_status":REVIEW,"outcome":OUTCOME,"lifecycle_status":LIFECYCLE,"impact_status":IMPACT}
    if field not in fields: raise ResearchError("不可修改的字段")
    require(value,fields[field],field); require(actor,ACTORS,"actor")
    if not reason.strip():raise ResearchError("状态变更须明确理由")
    with workspace_lock(root):
        s=load(root); obj=item_by_id(s,ident)
        old=obj[field]
        if old==value:raise ResearchError("状态未变化；不会制造重复日志")
        events=[]
        if field=="review_status" and (value=="user-confirmed" or old=="needs-user-confirmation") and actor not in ("user","mentor"):
            raise ResearchError("Agent 不能自行确认或撤销待用户确认的审核门槛")
        if field=="impact_status" and old!="current" and value=="current" and actor not in ("user","mentor"):
            raise ResearchError("需经人工复核才能清除失效影响标记")
        if field=="epistemic_status":
            validate_evidence_level(s,value,evidence_refs or obj["evidence_refs"],obj["observation"],obj["artifact_path"])
            if evidence_refs: obj["evidence_refs"]=evidence_refs
        if field=="workflow_status" and value=="done":
            if not obj["acceptance_criteria"] or not completion_note:raise ResearchError("done 需要验收标准及完成情况/工件说明")
            obj["completion_note"]=completion_note
        if field=="lifecycle_status":
            if obj["type"] not in ("ResearchQuestion","Idea","Method","Hypothesis","ExperimentPath","Baseline","Experiment","ResearchBranch"):
                raise ResearchError("该实体类型不能按研究路线归档")
            if old=="active" and value=="under-revival-review": raise ResearchError("活跃想法无需回收审查")
            if old in ARCHIVED and value=="active":raise ResearchError("禁止从归档状态直接恢复 active；先复审并创建新版本")
            if old=="under-revival-review" and value=="active":raise ResearchError("旧失败历史不得改写为 active；新建派生候选")
            if old=="under-revival-review" and value not in ARCHIVED:raise ResearchError("回收复审只能回到档案状态，新版本另建")
            if value in ARCHIVED:
                if actor not in ("user","mentor"):raise ResearchError("路线搁置/隔离/终止须用户或导师授权")
                if not failure_scope.strip() or not revival_triggers.strip(): raise ResearchError("归档必须记录失败/限制范围与回收条件")
                require(failure_category,FAILURE,"failure category")
                if obj.get("archive"):
                    obj.setdefault("archive_history",[]).append(copy.deepcopy(obj["archive"]))
                obj["archive"]={"reason":reason,"failure_category":failure_category,"failure_scope":failure_scope,"diagnostic_confidence":confidence,"revival_triggers":revival_triggers,"lesson":lesson,"cost":cost,"decided_by":actor,"decided_at":now(),"evidence_refs":evidence_refs or obj["evidence_refs"],"previous_state":old}
                obj["revival"]=None
            if value=="under-revival-review":
                if old not in ARCHIVED:raise ResearchError("只有已归档想法可进入回收复审")
                if actor not in ("user","mentor"):raise ResearchError("用户必须明确批准开始复审")
                if not revival_question.strip() or not new_conditions.strip():raise ResearchError("需要复审问题和新条件")
                obj["revival"]={"original_lifecycle":old,"question":revival_question,"new_conditions":new_conditions,"requested_by":actor,"requested_at":now(),"approved_candidate":None}
            if old=="under-revival-review" and value in ARCHIVED:
                obj["revival"] = None
        obj[field]=value; obj["revision"]+=1; obj["updated_at"]=now()
        events.append({"action":"status-changed","actor":actor,"item_id":ident,"reason":reason,"evidence_refs":evidence_refs or [],"before":{field:old},"after":{field:value},"proposal_id":proposal_id})
        if field in ("epistemic_status","lifecycle_status","outcome"):
            events+=propagate(s,ident,actor,reason,block=(field=="lifecycle_status" and value in ("quarantined","retired")))
        write(root,s,events,expected_revision=expected_revision)
        return obj,events

def revive(root, ident, title, reason, approval_note, new_conditions, actor="user", *, expected_revision=None, proposal_id=None):
    if actor not in ("user","mentor") or not approval_note.strip():raise ResearchError("新候选回收需要明确用户/导师批准说明")
    if not reason.strip() or not new_conditions.strip():raise ResearchError("回收需说明变化、风险和新的测试条件")
    with workspace_lock(root):
        s=load(root);old=item_by_id(s,ident)
        if old["lifecycle_status"]!="under-revival-review" or not old["revival"]:
            raise ResearchError("原想法未进入正式回收复审")
        previous=old["revival"]["original_lifecycle"]
        candidate=new_item(s,old["type"],title,old["module"],description=f"由 {ident} 派生；变化：{new_conditions}；待验证：{reason}", actor=actor,workflow="to-be-determined",epistemic="hypothesis",review="needs-user-confirmation",next_action="制定最低成本反证/复现实验",derived_from=ident)
        s["relations"].extend([{"from":candidate["id"],"to":ident,"type":"derived-from"},{"from":candidate["id"],"to":ident,"type":"revives"}])
        old["lifecycle_status"]=previous
        old["revival"]=None
        old["updated_at"]=now();old["revision"]+=1
        write(root,s,[{"action":"revival-candidate-created","actor":actor,"item_id":candidate["id"],"reason":reason,"approval":approval_note,"before":{"parent_id":ident,"parent_lifecycle":"under-revival-review"},"after":{"candidate_id":candidate["id"],"parent_lifecycle":previous,"new_conditions":new_conditions},"proposal_id":proposal_id}],expected_revision=expected_revision)
        return candidate

def set_project(root, focus_module=None, research_question=None, next_decision=None, actor="user", reason=""):
    require(actor,ACTORS,"actor")
    if focus_module is not None:require(focus_module,MODULES,"focus_module")
    with workspace_lock(root):
        s=load(root); before={};after={}
        for k,v in (("focus_module",focus_module),("research_question",research_question),("next_decision",next_decision)):
            if v is not None and v!=s["project"].get(k):
                if k=="research_question" and actor not in ("user","mentor"):raise ResearchError("修改核心研究问题需用户/导师同意")
                before[k]=s["project"].get(k);s["project"][k]=v;after[k]=v
        if not after:return s["project"]
        write(root,s,[{"action":"project-updated","actor":actor,"reason":reason or "explicit project metadata edit","before":before,"after":after}]);return s["project"]

def query(state, mode, user_authorized=False):
    modes=("planning","task-generation","recommendation","risk-check","novelty-check","failure-avoidance","archive-exploration","creative-recombination","revival-review","synthesis")
    require(mode,modes,"query mode")
    if mode in ("archive-exploration","creative-recombination","revival-review") and not user_authorized:
        raise ResearchError("读取归档灵感/回收模式需要用户明确授权（只读授权不等于执行批准）")
    out=[]
    for i in state["items"]:
        lc=i["lifecycle_status"]
        if mode in ("planning","task-generation","recommendation"):
            if lc!="active" or i["impact_status"]!="current" or i["workflow_status"] in ("no-further-considered","done") or i["type"] not in CANDIDATE_TYPES:continue
            usage="positive-candidate; evidence not automatically validated"
        elif mode in ("archive-exploration","creative-recombination"):
            if lc=="active":continue
            usage="archived inspiration / not validated / not approved for execution"
        elif mode=="revival-review":
            if lc not in ARCHIVED+("under-revival-review",):continue
            usage="historical candidate / requires human review / not execution-ready"
        elif mode=="synthesis":
            usage="historical evidence allowed; negative outcomes must remain visible"
        else:
            usage="historical-risk-only; do not use as positive support" if lc!="active" else "current evidence; independently verify claims"
        out.append({"item_id":i["id"],"title":i["title"],"type":i["type"],"lifecycle_status":lc,"epistemic_status":i["epistemic_status"],"outcome":i["outcome"],"impact_status":i["impact_status"],"usage":usage})
    return out

def validate_state(s,strict=False):
    errors=[]
    p=s["project"]
    if p.get("schema_version") not in (SCHEMA_VERSION, LEGACY_SCHEMA_VERSION):errors.append("schema_version mismatch")
    ids=[i.get("id") for i in s["items"]]; source_ids=[x.get("id") for x in s["sources"]]
    if len(ids)!=len(set(ids)):errors.append("duplicate item IDs")
    if len(source_ids)!=len(set(source_ids)):errors.append("duplicate source IDs")
    valid_ids=set(ids)
    for i in s["items"]:
        ident=i.get("id","<missing>")
        for key,choices in (("type",TYPES),("module",MODULES),("workflow_status",WORKFLOW),("epistemic_status",EPISTEMIC),("review_status",REVIEW),("outcome",OUTCOME),("lifecycle_status",LIFECYCLE),("impact_status",IMPACT)):
            if i.get(key) not in choices: errors.append(f"{ident}: invalid {key}")
        if i.get("workflow_status")=="done" and (not i.get("acceptance_criteria") or not i.get("completion_note")):errors.append(f"{ident}: done without criteria/evidence")
        if i.get("epistemic_status")=="source-backed":
            trusted={x["id"] for x in s["sources"] if x.get("verification_status")=="primary-inspected"}
            if not set(i.get("evidence_refs",[])) & trusted:errors.append(f"{ident}: source-backed without primary source inspected")
        if i.get("epistemic_status")=="experimentally-supported" and not (i.get("observation") and i.get("artifact_path")):errors.append(f"{ident}: experimentally-supported missing actual observation/artifact")
        if i.get("lifecycle_status") in ARCHIVED and not i.get("archive"):errors.append(f"{ident}: archived without tombstone")
        if i.get("lifecycle_status")=="under-revival-review" and not i.get("revival"):errors.append(f"{ident}: review missing request")
        if i.get("type")=="Result" and not (i.get("observation") and i.get("artifact_path")):errors.append(f"{ident}: Result missing observation/log")
        for ref in i.get("evidence_refs",[]):
            if ref not in source_ids and ref not in valid_ids:errors.append(f"{ident}: unknown evidence ref {ref}")
        if len(i.get("depends_on",[]))!=len(set(i.get("depends_on",[]))):errors.append(f"{ident}: duplicate depends_on")
    seen=set()
    for r in s["relations"]:
        key=(r.get("from"),r.get("to"),r.get("type"))
        if key in seen:errors.append(f"duplicate relation {key}")
        seen.add(key)
        if r.get("from") not in valid_ids or r.get("to") not in valid_ids:errors.append(f"invalid relation endpoint {key}")
        if r.get("type") not in RELATIONS:errors.append(f"invalid relation type {key}")
        if r.get("from")==r.get("to"):errors.append(f"self reference {key}")
    depmap={i["id"]:set() for i in s["items"]}
    for r in s["relations"]:
        if r.get("type")=="depends-on" and r.get("from") in depmap:
            depmap[r["from"]].add(r["to"])
    for i in s["items"]:
        if set(i.get("depends_on",[]))!=depmap.get(i["id"],set()):errors.append(f"{i['id']}: depends_on diverged from graph")
    gray=set(); black=set()
    def visit(v):
        if v in gray:
            errors.append(f"dependency cycle involving {v}");return
        if v in black:return
        gray.add(v)
        for w in depmap.get(v,[]):
            if w in depmap:visit(w)
        gray.remove(v);black.add(v)
    for v in depmap:visit(v)
    for src in s["sources"]:
        if src.get("verification_status") not in VERIFICATIONS:errors.append(f"{src.get('id')}: invalid source verification")
        if src.get("access_level")=="abstract" and src.get("verification_status")=="primary-inspected":errors.append(f"{src.get('id')}: abstract masquerading as full text")
        if src.get("verification_status")!="unverified" and not src.get("verification_note"):errors.append(f"{src.get('id')}: verified without verification note")
    # v0.2 domain validators inspect additive, optional sidecars.
    from rn_v02 import validate_v02
    errors.extend(validate_v02(s))
    if strict and errors:raise ResearchError("状态校验失败:\n- "+"\n- ".join(errors))
    return errors

def project_summary(root):
    s=load(root)
    return {"project":s["project"], "items":len(s["items"]),"relations":len(s["relations"]),"sources":len(s["sources"]),"events":len(s["events"]),"pending_reviews":[x["id"] for x in s["items"] if x["review_status"]=="needs-user-confirmation" or x["impact_status"]!="current"],"next_actions":[{"id":x["id"],"next_action":x["next_action"]} for x in s["items"] if x["lifecycle_status"]=="active" and x["next_action"] and x["impact_status"]=="current"][:8]}
