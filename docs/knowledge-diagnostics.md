# 语数英科全教材知识点诊断（M2）

本文档说明 M2 变更 `add-knowledge-diagnostics` 的知识点目录构建、题目版本映射、掌握度诊断规则（`diag-v1`）、API 契约与数据可移植性边界。

## 1. 稳定知识点目录与题目映射 (`kp-map-v1`)

`apps/api/app/diagnostics/catalog_builder.py` 在不改动原始教材 JSON 的前提下，从 `apps/web/public/data/index.json` 的全部 84 套教材（数学 31、语文 15、英语 15、科学 23）与私有数感题库构建三张核心表：

1. `knowledge_points`：
   - **普通课知识点（`scope_kind = "lesson"`）**：4,448 节普通课一一对应各自教材内的稳定知识点 ID（`kp-` + `sha256(["kp-v1", "lesson", book_id, lesson_id])[:36]`），保留学科、教材、单元、课时与核心概念描述。
   - **单元挑战知识点（`scope_kind = "unit_challenge"`）**：单元挑战题优先匹配本单元同名普通课知识点（5,511 题）或同教材唯一同名普通课知识点（48 题）；属于单元综合或专有考查标签的题目（780 题）绑定到本单元受控挑战知识点（763 个）。
   - **阅读理解技能知识点（`scope_kind = "story_skill"`）**：284 篇故事的 1,226 道理解题按教材、单元与理解技能分类关联到 441 个阅读技能知识点。
   - **数感技能知识点（`scope_kind = "number_skill"`）**：`count`、`compare`、`apply` 三类共 12 道固定题版本关联到一年级上册数学的 3 个数感技能知识点。
   - 纯朗读/跟读内容（`passages.json`）无判分题，不伪造题目级知识点映射。
2. `knowledge_point_relations`：
   - 仅在存在明确教材来源依据时建立受控关系：同教材内 `restores_lesson`（6 条）与修订版教材 `supersedes_exact_title`（8 条）。
   - 不同教材版本、不同学制（六三制与五四制）或跨学科/跨年级的同名知识点保持独立身份，不自动合并掌握度。
3. `question_knowledge_links`：
   - 绑定不可变题目版本 `(question_uid, question_version)` 到 `kp_id`，记录 `mapping_role`、`mapping_source` 与 `mapping_version = "kp-map-v1"`，全库 35,246 个题目版本 100% 映射。

## 2. 可重算掌握度诊断规则 (`diag-v1`)

`apps/api/app/diagnostics/engine.py` 直接基于学生的权威逐次作答（`learning_attempts`）与家庭时区（默认 `Asia/Shanghai`）实时计算，不修改任何历史判分、进度或奖励账本：

| 状态 | 中文标签 | 判定条件（按优先级顺序） |
| --- | --- | --- |
| `unassessed` | 未练习 | `total_attempts == 0` |
| `needs_review` | 待加强 | 最近连续 2 次会话首答错误；或全部会话首答均错误（即使同会话回炉订正答对，仍需隔次验证）；或 `first_attempts_total >= 2` 且无提示首答正确率 `< 60%` |
| `insufficient_evidence` | 证据不足 | 不属于 `needs_review`，且总首答次数 `< 2`；或仅在单一学习日练习了单一道题（`distinct_questions_attempted < 2 and distinct_days < 2`）；或所有正确首答均依赖解题提示（`unassisted_first_correct == 0`） |
| `mastered` | 已掌握 | 不属于前两类，无提示首答正确率 `>= 80%`，最近一次首答无提示正确，且满足 `distinct_questions_attempted >= 3` 或 `(distinct_questions_attempted >= 2 and distinct_days >= 2)` |
| `developing` | 巩固中 | 其余已有作答记录、正处于巩固过渡阶段的知识点 |

**排除项**：经验值（XP）、宝石、连续打卡、课程通关标记、纯听读完成事件及 `legacy_imports` 旧本地档案摘要均不作为知识点掌握证据。

## 3. API 契约与家庭数据导出

- `GET /api/v1/textbooks/{book_id}/knowledge-points`：返回指定教材按单元排序的知识点目录、题目数量与关联关系。
- `GET /api/v1/students/{student_id}/diagnostics?subject_code=...&book_id=...`：返回学生在该学科/教材下的五态汇总、优先待巩固列表及各单元知识点诊断指标。
- `GET /api/v1/students/{student_id}/diagnostics/knowledge-points/{kp_id}`：返回单个知识点的诊断详情、同源修订版参考及最近作答证据明细（不含未作答题目的私有答案或解析）。
- `GET /api/v1/family/export`：在 `data.diagnostics` 下导出本家庭各学生的知识点诊断快照、`diagnostic_rule_version` 与 `mapping_version`；删除学生或家庭时级联清除全部作答与诊断记录。

## 4. 前端家长诊断面板与回归检查

- `apps/web/src/components/account/StudentDiagnosticsPanel.tsx` 集成于家长端 `StudentOverview.tsx`，支持在数学、语文、英语、科学及当前/历史教材间切换，展示五态掌握汇总卡片、优先待巩固薄弱项、各单元知识点状态与单点证据明细抽屉，并对旧本地档案导入显示明确边界说明。
- `scripts/checks/knowledge-diagnostics.tsx`（`npm run check:diagnostics`）覆盖五态统计、来源边界说明、学科/教材切换竞态保护（迟到响应丢弃）、单点证据明细展开、学生切换状态清空及响应式防溢出 CSS 契约。

## 5. 集成构建与隔离环境验收记录（2026-11-06）

- **测试与静态检查**：
  - `ruff check`：0 错误。
  - `pytest tests/test_foundation.py tests/test_diagnostics.py tests/test_content.py tests/test_portability.py`：全部通过（含 `0011 -> 0012 -> base -> 0012` 升降级幂等、84 套教材 35,246 题目版本 100% 映射、诊断规则与重算一致性、跨家庭/同家庭兄弟姐妹/管理员越权拒绝、无写副作用与删除后无残留）。
  - `npm run type-check`、`npm test --workspace=@cstf/core`（315/315）、`npm run check:diagnostics`、`npm run check:learning-client`：全部通过。
  - `npm run build:cloud --workspace=china-study-free`（7,593 静态页，扫描 15,229 个文本文件 `issues: []`）与 `npm run build:local --workspace=china-study-free`（7,468 静态页）：全部通过。
- **隔离测试环境发布与真实 HTTPS 验证（`https://study.lacknb.com:8443/`）**：
  - 数据库备份：`.deployment/backups/diagnostics-before-20261105T105940.dump`（`pg_restore --list` 校验通过）。
  - 数据库版本：原库 `cstf_dev` 保持 `0006_regular_password_policy` 未变动；隔离库 `cstf_cloud_mac_3f7024bd` 升级至 `0012_knowledge_diagnostics`，同步写入 `5,655` 个知识点、`14` 条受控关联与 `35,246` 条题目映射，受限运行角色 `cstf_cloud_preview` 仅具 `SELECT` 权限。
  - 发布版本：API 镜像 `congcong-cloud-api:diagnostics-20261105-r1`，前端发布目录 `.deployment/releases/20261105-diagnostics-r1`（合并兼容静态块后扫描 15,512 个文件，`issues: []`）。
  - 真实 HTTPS 验收结果（详见远端 `.deployment/diagnostics-deployment-audit.json`）：
    - `GET /api/v1/textbooks/g1up/knowledge-points` 返回 39 个知识点与 `kp-map-v1` 版本。
    - `验收孩子A1`（`567b8099-f2ff-4cff-b447-7aa5111af5c4`）：在 `g1up` 下已评估 3 项（`lesson:g1up-u1-kp1`、`lesson:g1up-u1-kp2`、`lesson:g1up-u2-kp3` 均为 `mastered`），累计 25 次权威作答；单点明细接口返回 13 条近期作答证据；诊断读取前后 XP/宝石（`190 XP / 119 宝石`）完全不变。
    - `验收孩子A2`（`fe363d93-0bc5-4b36-90af-a45d3a5dfa98`）：在 `g1up` 下已评估 2 项（`lesson:g1up-u1-kp1` 为 `mastered`，`number-skill:count` 为 `developing`）。
    - `GET /api/v1/family/export` 包含 `data.diagnostics` 快照；跨家庭家长 B 访问 A1 诊断返回 `404`。
