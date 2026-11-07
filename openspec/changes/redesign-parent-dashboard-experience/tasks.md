# Tasks

## 1. 通用三层浮框原语与工作台视觉体系

- [x] 1.1 在 `apps/web/src/components/account/AccountShell.tsx` 中实现并导出 `FloatingToast`（含自动消散、手动关闭与可选下载动作）、`InfoPopover`（标题旁 `? 说明` 按钮 + 点击/聚焦气泡浮框 + `Escape`/外部点击关闭）和 `ModalDialog`（模态遮罩弹窗 + `Escape` 关闭），并在 `AccountShell` 顶栏支持右侧自定义动作区（如「家庭设置」入口），通过 `npm run type-check` 验证类型无误。
- [x] 1.2 更新 `apps/web/src/components/learning/forest.css` 与 `apps/web/src/components/account/account.css`，移除 `.account-root` 全局森林背景图对家长端/管理端的渗透，实现三层浮框样式、顶部孩子切换栏、一体式分段控制器（Segmented Control）、2x2 学科网格、美化上传区及四级按钮规范，确保桌面端（`1440x900`）与移动端（`390x844`）无横向溢出。

## 2. 家长端信息架构与四大分类模块重构

- [x] 2.1 重构 `apps/web/src/components/account/StudentOverview.tsx` 与 `apps/web/src/components/account/StudentDiagnosticsPanel.tsx`：将「学习概况」与「知识点诊断」解耦为平级模块；将时区/申报时间说明与诊断证据边界说明全部收起到 `InfoPopover`；将知识点「查看证据」内联抽屉改为 `ModalDialog` 独立弹窗，确保主界面零内联说明段落。
- [x] 2.2 重构 `apps/web/src/components/account/CurriculumForm.tsx`、`apps/web/src/components/account/StudentForm.tsx` 与 `apps/web/src/components/account/PortabilityPanel.tsx`：移除所有内联 `<Message />` 与 `.account-hint` 段落，接入 `FloatingToast` 与 `InfoPopover`；将教材历史记录、备份导入预检报告和永久删除孩子确认全部改为 `ModalDialog` 弹窗；将 4 个学科配置升级为 2x2 卡片网格并美化文件上传区。
- [x] 2.3 重构 `apps/web/src/components/account/ParentDashboard.tsx`：实现顶栏「家庭设置」独立弹窗（含家庭名称/时区/地区设置与全家备份导出）、顶部孩子切换栏（含孩子胶囊卡片、`+ 添加孩子` 弹窗、显示已归档开关与「进入孩子模式」主按钮）以及四大分类分段标签页（`学习概况`、`知识点诊断`、`教材配置`、`档案与数据` 含底部独立危险操作区与归档确认弹窗），消除全部文档流内联 `<Message />` 与 `.account-hint`。

## 3. 自动化回归测试与远程隔离环境部署验收

- [x] 3.1 更新 `scripts/checks/knowledge-diagnostics.tsx` 并扩展家长端 UI 回归断言（覆盖顶部孩子切换栏、四大分类分段标签页切换、零内联 `.account-hint`/`.account-message`、`InfoPopover` 展开收起、知识点证据 `ModalDialog`、家庭设置与危险操作确认弹窗），运行 `npm run check:diagnostics`、`npm run check:learning-client`、`npm run type-check` 与 `npm test --workspace=@cstf/core` 全部通过。
- [x] 3.2 执行 `npm run build:cloud --workspace=china-study-free` 与 `npm run build:local --workspace=china-study-free` 并通过 `scan-artifact.py` 零问题扫描，将最新前端静态产物发布至 `https://study.lacknb.com:8443/` 远程隔离测试环境，验证线上 `/parent/` 页面加载与响应正常且原数据库 `cstf_dev` 未受触碰。
