# Tasks

## 1. 知识点目录模型与全教材题目映射

- [x] 1.1 新增 `apps/api/app/diagnostics/models.py` 与 Alembic 迁移 `0012_knowledge_diagnostics.py`（包含 `knowledge_points`、`knowledge_point_relations`、`question_knowledge_links` 表及外键/索引），在 `apps/api/app/models.py` 注册模型；通过临时库验证 `0011 -> 0012 -> 0011 -> 0012` 升降级幂等通过。
- [x] 1.2 实现 `apps/api/app/diagnostics/catalog_builder.py` 并在 `apps/api/app/content/import_content.py` 接入，为语、数、英、科全部 84 套教材生成稳定知识点目录、受控跨版关联（`restores_lesson` 与 `supersedes_exact_title`）及题目版本映射（覆盖普通课、单元挑战、故事阅读技能与数感练习，排除纯朗读）；编写测试验证 84 套教材全部可判分题目 100% 映射、不同版本/学制不误合并且重复导入幂等。

## 2. 可重算掌握度诊断引擎

- [x] 2.1 实现 `apps/api/app/diagnostics/engine.py`（规则版本 `diag-v1`），按家庭时区聚合学生的 `learning_attempts` 与会话上下文，区分会话首答与同会话错题回炉重做、无提示首答与提示辅助作答、同日重复与跨日巩固，输出 `unassessed`、`insufficient_evidence`、`needs_review`、`developing`、`mastered` 五态及结构化原因说明；编写单元测试覆盖同会话重做不虚增、单日单题提示不足、提示依赖降级、跨日多题掌握、最近连错转待加强，以及排除 XP/通关/阅读/legacy 摘要。

## 3. 诊断 API、家庭隔离与数据可移植性

- [x] 3.1 新增 `apps/api/app/diagnostics/schemas.py`、`service.py` 与 `router.py`（挂载到 `apps/api/app/main.py`），提供 `GET /api/v1/textbooks/{book_id}/knowledge-points`、`GET /api/v1/students/{student_id}/diagnostics` 和 `GET /api/v1/students/{student_id}/diagnostics/knowledge-points/{kp_id}`；扩展 `apps/api/app/portability/privacy.py` 的 `export_family` 纳入学生知识点诊断快照与规则版本。
- [x] 3.2 编写 `apps/api/tests/test_diagnostics.py` 并更新文档 `docs/knowledge-diagnostics.md`，验证家长（本家庭/代入模式）与绑定学生可读取诊断及证据明细、未作答题不泄露答案、同家庭兄弟姐妹与跨家庭及管理员越权拒绝、诊断重算不改动成绩与奖励账本，以及家庭导出包含诊断快照且学生/家庭删除后无残留。

## 4. 家长端知识点诊断视图与前端回归

- [x] 4.1 新增 `apps/web/src/components/account/StudentDiagnosticsPanel.tsx` 并接入 `StudentOverview.tsx` 与 `account.css`，支持按语数英科学科及当前/历史教材切换查看五态掌握分布、优先待巩固薄弱项、各单元知识点状态及单点证据明细抽屉/展开区，并对存在 `legacy_imports` 的学生显示来源边界说明。
- [x] 4.2 新增前端组件检查脚本 `scripts/checks/knowledge-diagnostics.tsx`（并在 `package.json` 注册 `check:diagnostics`），验证学科/教材切换、迟到响应丢弃、五态统计、待巩固列表、证据明细展开及移动端/桌面端无横向溢出。

## 5. 集成构建与隔离环境验证

- [x] 5.1 执行 API 全量测试、前端类型检查、`check:diagnostics`、`check:learning-client` 及独立 `local` / `cloud` 生产构建与答案泄露扫描；将 0012 迁移与新版前后端发布到隔离测试环境（保持 `cstf_dev` 不变），验证真实 HTTPS 下的知识点诊断接口与家长端总览页面并记录验收结果。

## Workflow follow-up

- 完成全部任务并通过审阅后，同步主规格并归档 `add-knowledge-diagnostics` 变更。
