# Proposal

## Why

当前家长端（`/parent/`）将家庭设置、所有孩子列表、选中孩子的学习统计、知识点诊断、教材配置、档案编辑、备份导入和危险删除全部堆叠在同一纵向滚动流中，分类混乱且视觉割裂；同时大量操作反馈（`<Message />`）、静态规则说明（`.account-hint` / `.diag-boundary-note`）、诊断证据抽屉与二次确认块直接渲染在页面 DOM 文档流内，不仅挤压核心内容空间，还导致交互时页面频繁跳动、按钮主次不清。

## What Changes

- **全量提示与次级详情浮框化（零内联提示）**：
  - 移除家长端文档流内直接展示的 `<Message />`、`.account-hint`、`.diag-boundary-note` 及内联展开块。
  - 所有操作状态反馈（保存成功、校验失败、网络异常、导出就绪等）统一通过右上角悬浮 `FloatingToast` 展示并支持自动消散与手动关闭。
  - 所有静态业务规则说明（时区与申报时间说明、知识点诊断证据边界、教材手动绑定说明、选填档案说明、备份保留期说明）全部收起到模块标题旁的「`? 说明`」图标按钮，点击或聚焦时以气泡浮框（`InfoPopover`）展示，主界面默认不露说明文字。
  - 所有深度详情与高危/复杂交互（知识点作答证据明细、添加孩子档案、家庭设置与全家备份、备份导入预览确认、归档/永久删除二次确认）统一收起到独立模态浮窗（`ModalDialog`）。
- **重构家长端信息架构与四大分类标签页**：
  - **顶栏与家庭设置分离**：顶栏右侧提供「家庭设置」「我的头像」「退出登录」胶囊入口；家庭名称/时区/地区配置及全家备份导出收进「家庭设置」独立模态弹窗，不再占据首屏左侧主栏。
  - **顶部孩子切换栏**：以横向紧凑胶囊卡片展示当前家庭的孩子列表（头像、昵称、年级、每日目标），右侧提供「`+ 添加孩子`」弹窗按钮、「已归档」开关及主操作按钮「进入孩子模式」。
  - **四大分类分段标签页（Segmented Tabs）**：将选中孩子的功能严格划分为四个平级标签页：
    1. **学习概况（`overview`）**：4 项核心指标卡片、近 7 日学习分布列表、旧本地档案导入摘要。
    2. **知识点诊断（`diagnostics`）**：从学习概况中拆出为独立一级模块，提供学科分段切换、教材选择器、掌握度筛选卡片、优先巩固清单、单元折叠列表及知识点证据明细弹窗。
    3. **教材配置（`curriculum`）**：2x2 学科卡片网格、启用开关、教材与当前单元选择器，以及收起到弹窗/折叠抽屉的历史教材记录。
    4. **档案与数据（`manage`）**：孩子基础档案表单、备份导入与单孩导出卡片、以及底部独立「危险操作区」（归档档案弹窗确认、永久删除弹窗确认）。
- **重塑家长端视觉与按钮交互层次**：
  - 隔离孩子端森林背景图（`forest-welcome.webp`），为家长端与管理端工作台提供清爽的现代浅色工作台背景。
  - 建立四级按钮与控件规范（主操作实心按钮、次操作描边按钮、轻量图标胶囊按钮、危险操作红框/红底按钮），将松散的标签按钮升级为一体式分段控制器（Segmented Control），美化文件上传区与开关控件。

## Capabilities

### New Capabilities
- `parent-dashboard-experience`: 家长端工作台的信息架构（顶部孩子切换栏、四大分类模块标签页、家庭设置独立弹窗）、零内联提示与浮框交互规范（Toast 浮框、气泡说明 Popover、模态详情与确认弹窗 Modal）以及按钮与控件视觉层次。

### Modified Capabilities
- `student-profiles`: 更新 `Parent overview` 需求，明确家长端采用顶部孩子切换栏、四大分类标签页（学习概况、知识点诊断、教材配置、档案与数据）与独立弹窗承载家庭设置和孩子创建。
- `knowledge-diagnostics`: 更新 `Authorized parent and student diagnostic views` 需求，明确家长端知识点诊断作为独立一级模块展示，诊断规则说明通过标题旁浮框展示，知识点证据明细通过模态弹窗展示。

## Impact

- **前端组件**：
  - `apps/web/src/components/account/AccountShell.tsx`（新增/导出 `ParentToastProvider` / `InfoPopover` / `ModalDialog` 等通用浮框原语，优化顶栏动作区）
  - `apps/web/src/components/account/ParentDashboard.tsx`（重构为顶部孩子切换栏 + 四大分类模块标签页 + 家庭设置弹窗 + 添加孩子弹窗 + 归档确认弹窗）
  - `apps/web/src/components/account/StudentOverview.tsx`（精简为纯粹的学习概况视图，移除内嵌的诊断大面板，静态说明改为 `InfoPopover`）
  - `apps/web/src/components/account/StudentDiagnosticsPanel.tsx`（升级为独立标签页模块，边界说明改为 `InfoPopover`，证据抽屉改为 `ModalDialog`）
  - `apps/web/src/components/account/CurriculumForm.tsx`（静态说明改为 `InfoPopover`，反馈改为 Toast，历史记录收起，2x2 卡片网格化）
  - `apps/web/src/components/account/StudentForm.tsx`（静态说明改为 `InfoPopover`，反馈改为 Toast，适配弹窗新增与内嵌编辑两种模式）
  - `apps/web/src/components/account/PortabilityPanel.tsx`（美化上传区，导入预览与永久删除确认改为 `ModalDialog`，状态反馈改为 Toast）
  - `apps/web/src/components/account/account.css` & `apps/web/src/components/learning/forest.css`（工作台背景隔离、浮框与弹窗样式、分段控制器、四级按钮规范）
- **验证脚本**：
  - `scripts/checks/knowledge-diagnostics.tsx`（同步验证家长端四大标签页、诊断独立模块、说明 Popover 与证据 Modal）
- **后端与数据库**：无后端 API 契约破坏性变更，无数据库迁移。
