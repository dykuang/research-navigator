# CLI recipes

Assume current directory is `research-navigator` Skill installation root. Replace `/PROJECT/ROOT` with the actual student project (not this Skill directory).

```bash
python scripts/update_project.py init /PROJECT/ROOT --name '新型检索方法研究' --question '我们能否在固定预算下提高跨域检索质量？'
python scripts/update_project.py add-item /PROJECT/ROOT --type ResearchQuestion --title '跨域检索' --module topic --description '尚需精确定义领域和指标' --next-action '明确样本、预算、评估规则'
python scripts/update_project.py add-item /PROJECT/ROOT --type Hypothesis --title '门控方法能改善泛化' --module topic --epistemic hypothesis --next-action '找到合适对照并做 MVE'
python scripts/update_project.py add-source /PROJECT/ROOT --title '有待核验的论文标题' --url 'https://example.org/paper' --access-level abstract --verification-status unverified
python scripts/update_project.py add-item /PROJECT/ROOT --type Baseline --title '公开方法 B' --module literature --description '协议兼容性待检查'
python scripts/update_project.py add-item /PROJECT/ROOT --type Experiment --title '控制变量预实验' --module experiment --acceptance-criteria '完成三次运行并检查划分与随机种子'
python scripts/update_project.py link /PROJECT/ROOT EXP-0001 HYP-0001 --relation tests
python scripts/update_project.py set-status /PROJECT/ROOT HYP-0001 --field lifecycle_status --value parked --actor user --reason '预算受限且初步结果不稳定' --failure-category resources --failure-scope '仅单一小型数据集' --revival-triggers '取得代表性数据和复现实验资源'
python scripts/query_research_items.py /PROJECT/ROOT --mode planning
python scripts/query_research_items.py /PROJECT/ROOT --mode risk-check
python scripts/query_research_items.py /PROJECT/ROOT --mode archive-exploration --user-authorized
python scripts/update_project.py set-status /PROJECT/ROOT HYP-0001 --field lifecycle_status --value under-revival-review --actor user --reason '用户正式请求回收复审' --revival-question '能否迁移门控机制' --new-conditions '新数据集和更严格评估'
python scripts/update_project.py revive /PROJECT/ROOT HYP-0001 --title '门控方法 v2 待验证候选' --reason '原小样本失败不代表新的数据条件不可行' --approval-note '导师批准创建新候选，仅授权规划不是执行昂贵实验' --new-conditions '新数据集与预注册评估' --actor mentor
python scripts/validate_state.py /PROJECT/ROOT
python scripts/build_dashboard.py /PROJECT/ROOT
```

**Important**: the example URL is placeholder metadata, *not* a real verified paper. It should not be used in real student projects as evidence. Source verification can only be upgraded after checking real primary documents. The `--actor` CLI option is declarative and does not authenticate the caller. Do not execute `park`, `review` or `revive` before getting the stated human decision.
