# Design

## Context

动机与阶段范围见 `proposal.md`。当前系统已完成 M1（家庭云端学习）与儿童端森林改版：
- `apps/web/public/data/index.json` 共收录语、数、英、科 84 套教材（数学 31、语文 15、英语 15、科学 23），包含 4,448 节普通课（`lessons_total = 4448`，100% 具备 `knowledge.point` 与 27,669 道普通课题目，每题均带 `knowledge_point`）、629 个单元挑战（6,339 道题，其中 5,511 题匹配本单元课时知识点、64 题匹配同书课时知识点、764 题为本单元综合挑战知识点）、284 篇阅读故事（1,226 道理解题，带 `skill` 或单元阅读属性）以及 6 组一年级数感题库（`number-review.json`，按 `count` / `compare` / `apply` 技能组织）。
- `apps/api/app/content/` 已将容器版本与不可变题目版本（`question_identities`、`question_versions`）导入 PostgreSQL，但尚未提取结构化知识点表与题目关联表。
- `apps/api/app/learning/models.py` 中的 `Attempt`（`learning_attempts`）已记录 `student_id`、`session_id`、`ordinal`、`question_uid`、`question_version`、`correct`、`first_attempt`、`grading_rule_version`、`client_at`、`received_at`、`declared_duration_ms` 及 `evidence`（`hint_level`、`sentence_indices`）。
- 家长端 `StudentOverview.tsx` 目前仅请求 `/api/v1/students/{student_id}/summary` 展示完成课数、XP、申报用时与最近 7 天计数，缺少知识点掌握度诊断与依据展示。

## Goals / Non-Goals

**Goals:**
- 在不改动原教材 JSON 文件的前提下，为 84 套教材建立确定性的知识点目录与题目版本多对多映射。
- 提供纯函数化、带显式规则版本（`diag-v1`）且可随时从 `learning_attempts` 重算的掌握度诊断计算，严防同会话刷题或错题回炉虚增掌握度。
- 在家长端学生总览提供清晰的按学科/教材知识点诊断面板、待巩固薄弱项及可核查的证据明细。

**Non-Goals:**
- 不在 M2 自动生成每日排课或改写学生首页学习路线（留给 M3 个性化学习计划）。
- 不凭知识点名称相似性自动跨年级、跨学科或跨学制合并知识点。
- 不修改现有判分规则（`grading.py`）、学习会话状态机或经济奖励账本（`reward_ledger`）。

## Decisions

### 1. 稳定知识点目录与受控跨版关联

在 `apps/api/app/diagnostics/models.py`（通过迁移 `0012_knowledge_diagnostics.py`）新增知识目录与关联表：

| 表名 | 关键字段与约束 |
| --- | --- |
| `knowledge_points` | `id` (PK, 确定性哈希 `kp-...`), `subject_code` (FK `subjects.code`), `book_id` (FK `textbooks.id`), `unit_number` (int), `unit_title` (str), `lesson_id` (nullable str), `scope_kind` (`lesson` / `unit_challenge` / `story_skill` / `number_skill`), `code` (教材内稳定标识), `title` (可读名称), `description` (核心概念摘要), `sort_order` (int), `provenance` (JSONB) |
| `knowledge_point_relations` | `source_kp_id` (FK), `target_kp_id` (FK), `relation_kind` (`restores_lesson` / `supersedes_exact_title`), `provenance` (JSONB)，复合主键 `(source_kp_id, target_kp_id, relation_kind)` |
| `question_knowledge_links` | `question_uid` (str), `question_version` (str), `kp_id` (FK `knowledge_points.id`), `mapping_role` (`primary` / `secondary`), `mapping_source` (`lesson_primary` / `challenge_unit_match` / `challenge_book_match` / `challenge_unit_topic` / `story_skill` / `number_skill`), `mapping_version` (str), `provenance` (JSONB)；复合外键指向 `question_versions(uid, version)`，复合主键 `(question_uid, question_version, kp_id)` |

**生成与关联规则（`kp-map-v1`）**：
1. **普通课知识点（`scope_kind = "lesson"`）**：每本教材 `outline.json` 中的普通课对应一个主知识点，`id = digest(["kp-v1", "lesson", book_id, lesson_id])[:40]`，`title` 取课时 `knowledge.point`（若无则回退课时 `title`），`description` 取 `knowledge.core_concept`。
2. **单元挑战题映射**：
   - 若挑战题的 `knowledge_point` 文本与本单元某普通课的 `knowledge.point` 精确一致，直接关联到该普通课知识点（`mapping_source = "challenge_unit_match"`）；
   - 若与同教材其他单元唯一普通课的 `knowledge.point` 精确一致，关联到该普通课知识点（`mapping_source = "challenge_book_match"`）；
   - 若属于单元综合或专有考查点（共 764 题），生成本单元受控挑战知识点 `id = digest(["kp-v1", "unit_challenge", book_id, str(unit_number), normalized_kp])[:40]`（`scope_kind = "unit_challenge"`，`mapping_source = "challenge_unit_topic"`），不丢弃任何挑战题证据。
3. **故事阅读理解题映射（`scope_kind = "story_skill"`）**：按教材与阅读理解技能（如细节理解、主旨归纳、词义推断、文本证据定位等 `skill` 字段，无 `skill` 时归为本教材阅读理解综合）生成教材内阅读技能知识点并绑定对应故事题。
4. **数感练习题映射（`scope_kind = "number_skill"`）**：`number_review` 的 `count`、`compare`、`apply` 题库分别映射到 `g1up` 下的数感技能知识点。
5. **跨课与修订版受控关联（`knowledge_point_relations`）**：
   - 同书内课时若声明 `restoresLessonId` / `legacyPracticeLessonId`，建立 `restores_lesson` 关系；
   - 若教材声明 `supersedes`（如 2026 修订版承接旧版），仅当新旧教材同单元或全书存在唯一同名 `knowledge.point` 时建立 `supersedes_exact_title` 关系，并在 provenance 中记录双方 `book_id` 与 `lesson_id`。诊断时默认按当前教材独立计算，同时在知识点详情中提示可参考的同源修订版记录。

### 2. 带规则版本的可重算掌握度诊断引擎 (`DIAGNOSTIC_RULE_VERSION = "diag-v1"`)

诊断采用实时可重算服务（`apps/api/app/diagnostics/engine.py`），直接基于学生的 `Attempt`、`LearningSession` 和 `question_knowledge_links` 计算，无需引入容易与事件流失步的可变积分缓存表：

- **证据去重与统计口径**：
  - 按家庭时区（`Family.timezone`，默认 `Asia/Shanghai`）将 `Attempt.received_at` 折算为本地学习日 `study_day`。
  - 区分 **会话首答**（`Attempt.first_attempt == True`）与 **同会话错题回炉重做**（`Attempt.first_attempt == False`）：同一学习会话内答错后的回炉重做仅计入 `retry_attempts_total` / `retry_attempts_correct`，证明当次订正完成，但**不计入** `first_attempts_correct`，防止同会话刷重做把错误覆盖为“已掌握”。
  - 区分 **无提示独立首答**（`first_attempt == True and correct == True and hint_level == 0`）与 **提示辅助作答**（`hint_level > 0`）。
  - 防止同日同题反复开新会话刷分：对同一 `(question_uid, study_day)` 的多次会话首答，跨会话独立证据计数（`effective_independent_checks`）按不同题目数（`distinct_questions_attempted`）与不同学习日数（`distinct_days`）综合评估。

- **五级诊断状态判定规则（`diag-v1`）**：
  1. `unassessed`（未练习）：`total_attempts == 0`。
  2. `needs_review`（待加强）：满足以下任一条件：
     - 最近连续 2 次会话首答均错误；
     - `first_attempts_total >= 2` 且无提示首答正确率 `unassisted_first_correct / first_attempts_total < 0.6`；
     - 仅有 1 次或多次会话首答且首答全部错误（即使同会话回炉订正答对，仍需隔次或新题验证，标记为 `needs_review` 并提示“首答出错，虽已完成当堂订正，建议再次巩固”）。
  3. `insufficient_evidence`（证据不足）：不满足 `needs_review`，且满足以下任一条件：
     - `first_attempts_total < 2`（例如仅作答 1 次且答对）；
     - 仅在单一学习日作答了单一道题目（`distinct_questions_attempted < 2 and distinct_days < 2`），即使同一天重开会话重复答对同一题，也判定为 `insufficient_evidence`（提示“仅在单日练习同一题目，需更多题目或隔天验证”）；
     - 所有正确首答均依赖解题提示（`unassisted_first_correct == 0`）。
  4. `mastered`（已掌握）：不满足 `needs_review` 与 `insufficient_evidence`，且同时满足：
     - 无提示首答正确率 `unassisted_first_correct / first_attempts_total >= 0.8`；
     - 最近一次会话首答为无提示正确（`latest_first_correct_unassisted == True`）；
     - 至少覆盖 3 道不同题目（`distinct_questions_attempted >= 3`），或覆盖至少 2 道不同题目且跨至少 2 个不同学习日（`distinct_questions_attempted >= 2 and distinct_days >= 2`）。
  5. `developing`（巩固中）：其余已有作答记录但尚未达到 `mastered` 标准的知识点（如无提示首答正确率在 60%–79% 之间、最近一次使用提示或刚从错误中恢复但样本数尚少）。

### 3. API 契约与权限隔离

在 `apps/api/app/diagnostics/router.py` 新增 `/api/v1` 路由：
- `GET /api/v1/textbooks/{book_id}/knowledge-points`：返回指定教材的知识点目录与单元分组（需已登录会话）。
- `GET /api/v1/students/{student_id}/diagnostics`：
  - 查询参数：`subject_code`（可选）、`book_id`（可选）。未传 `book_id` 时优先选用该学生在对应学科（或首个启用学科）当前生效的教材；若学生曾更换教材，同时在 `available_books` 中返回当前与历史教材列表供家长切换查看。
  - 权限：复用 `authorized_student` 与学习读取权限边界——家长在 `parent` 模式（需属本家庭）或代入该孩子的 `child` 模式可读，独立学生仅可读本人 `student_id`，管理员日常后台无权读取家庭学生诊断明细，跨家庭或兄弟姐妹越权返回 404/403。
  - 响应包含：`diagnostic_rule_version`、`mapping_version`、`student_id`、`timezone`、`available_books`、`selected_book`、`summary`（五类状态计数、已评估占比、legacy 导入排除说明）、`priority_review`（按 `needs_review` → `developing` 排序的重点关注知识点列表）和 `units`（按单元组织的知识点诊断与证据指标）。
- `GET /api/v1/students/{student_id}/diagnostics/knowledge-points/{kp_id}`：
  - 返回该学生在该知识点下的详细证据记录（关联题目总数、已练题目数、各次作答的时间、会话类型、题目题干摘要、首答/重做标记、正确性、提示使用等级，以及关联的同源修订版知识点参考状态），绝不返回未作答或未完成题目的标准答案。

### 4. 家长端诊断界面与数据导出集成

- **家长端总览（`apps/web/src/components/account/StudentOverview.tsx` & `StudentDiagnosticsPanel.tsx`）**：
  - 在家长端孩子总览中嵌入“知识点掌握诊断”模块；
  - 支持一键切换语、数、英、科及该生已配置/历史教材；
  - 顶部展示五态统计卡片（已掌握、巩固中、待加强、证据不足、未练习）与规则说明（明确标注“基于云端逐题首答、提示与跨日表现计算；XP、通关与旧本地摘要不计入掌握证据”）；
  - 突出展示“优先待巩固”列表（含诊断结论原因，如“首答正确率 33%（1/3），最近连续答错”）；
  - 支持按单元展开全部知识点，点击任一知识点可查看最近作答证据明细。
- **数据导出与删除（`apps/api/app/portability/privacy.py`）**：
  - `export_family` 在 `data["diagnostics"]` 中为每个学生导出当前已选教材与历史有记录教材的知识点诊断快照（含 `diagnostic_rule_version`、`mapping_version` 和证据汇总）；
  - 由于诊断直接来源于 `learning_attempts` 与 `learning_sessions`，删除学生或家庭时级联清除全部作答与会话后，诊断结果自然清零，无残留隐私数据。

## Risks / Trade-offs

- **[同日重复刷同一题虚增掌握度]** → 在 `diag-v1` 规则中强制要求 `distinct_questions_attempted >= 2`（跨日）或 `distinct_questions_attempted >= 3`（同日多题），单一题目无论同日重开多少次会话均保持 `insufficient_evidence`。
- **[84 套教材题量大导致导入耗时]** → `import_content` 采用批量 `insert(...).on_conflict_do_update/nothing`（每批 250–500 条），并在内容导入事务中一并写入 `knowledge_points` 与 `question_knowledge_links`。
- **[查询学生诊断时的 N+1 查询风险]** → 诊断计算按 `(student_id, book_id)` 一次性批量读取该书知识点、关联题目及该生在这些题目上的全部 `Attempt` 记录，在内存中完成聚合与规则判定，单次请求仅需常数次 SQL 查询。

## Migration Plan

1. 新增 Alembic 迁移 `0012_knowledge_diagnostics.py`，创建 `knowledge_points`、`knowledge_point_relations` 和 `question_knowledge_links` 表及索引，支持完整 `upgrade` 与 `downgrade`。
2. 扩展 `python -m app.content.import_content`（并提供独立幂等同步入口），从 84 套教材与私有数感题库构建知识点目录和题目映射。
3. 先在本地临时库验证 `0011 -> 0012 -> 0011 -> 0012` 升降级与 84 套教材导入完整性，再对隔离测试库 `cstf_cloud_mac_3f7024bd` 执行迁移与内容映射导入（绝不触碰原 `cstf_dev`）。
