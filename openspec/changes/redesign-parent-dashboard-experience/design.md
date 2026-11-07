# Design

## Context

参见 [proposal.md](./proposal.md) 中的背景说明。当前家长端工作台（`apps/web/src/components/account/`）是随着 M1（家庭与孩子档案、教材配置、学习总览、数据导入导出）和 M2（知识点诊断）逐步叠加而成的：
- 所有提示与错误信息通过 `<Message text={...} />`（`<p className="account-message" role="status">`）直接插入 DOM 文档流；
- 所有业务规则解释通过 `<p className="account-hint">` 和 `<div className="diag-boundary-note">` 常驻渲染在各个卡片顶部；
- `StudentOverview` 内部直接嵌套了完整的 `StudentDiagnosticsPanel`，而 `ParentDashboard` 的「学习总览」标签页又将 `StudentOverview`、`PortabilityPanel`（含永久删除按钮）和底部归档/配置按钮塞在同一个 `.account-card` 中；
- `forest.css` 对 `.account-root` 直接设置了 `forest-welcome.webp` 背景图，导致孩子端的森林卡通背景透入家长端与管理端。

## Goals / Non-Goals

**Goals:**
- 建立统一的家长端三层浮框体系（`FloatingToast`、`InfoPopover`、`ModalDialog`），彻底消除家长端文档流内的 `<Message />`、`.account-hint`、`.diag-boundary-note` 和内联展开块。
- 将家长端重构为「顶栏（含家庭设置弹窗入口）+ 顶部孩子切换栏 + 四大分类分段标签页（`overview` / `diagnostics` / `curriculum` / `manage`）」的清晰架构。
- 建立现代、清爽的工作台视觉规范与四级按钮体系，兼容 SSR / `renderToStaticMarkup` 与客户端交互测试。

**Non-Goals:**
- 不修改后端 FastAPI 接口路径、请求响应 Schema 或数据库表结构。
- 不改变孩子端（`/child/`）已通过验收的森林主题视觉与 `FloatingNotice` 交互。
- 不改变管理员端（`/admin/`）的核心业务逻辑（仅共享基础工作台背景修复与通用浮框原语）。

## Decisions

### 1. 三层浮框原语设计（`AccountShell.tsx`）
- **决策**：在 `AccountShell.tsx` 中提供并导出三个轻量、零外部依赖的浮框组件：
  1. `FloatingToast`（及 `useToast` / 受控属性）：固定在视口右上角（移动端顶部居中）的悬浮通知层，区分 `success`、`error`、`info` 语义色，默认 4 秒自动消散（错误或带下载链接的通知可保留更长或手动关闭），完全脱离文档流（`position: fixed; z-index: 120`）。
  2. `InfoPopover`：渲染为标题旁的轻量胶囊按钮 `(? 说明)`，点击或键盘触发时在锚点旁绝对定位展开 `.account-popover-card`（`role="dialog"`，支持点击外部或按 `Escape` 关闭）。在服务端/静态渲染或默认初始状态下仅渲染触发按钮，展开态渲染气泡浮框，主界面文档流永远不出现长段说明文字。
  3. `ModalDialog`：基于受控 `open` 属性渲染固定遮罩层与居中模态框（`.account-modal-backdrop` + `.account-modal-card`，`role="dialog" aria-modal="true"`，支持 `Escape` 与遮罩点击关闭），兼容 React 18 客户端渲染与 `renderToStaticMarkup` 静态断言。
- **备选方案**：完全依赖浏览器原生 `HTMLDialogElement.showModal()`。
- **取舍理由**：虽然原生 `<dialog>` 很好，但在 Node 环境下的 `renderToStaticMarkup` / 轻量 DOM 检查脚本中没有完整浏览器布局引擎，使用受控条件渲染 + `role="dialog" aria-modal="true"` 既能保证无障碍语义与键盘 `Escape` 交互，又能让自动化测试脚本直接断言弹窗打开/关闭时的 DOM 结构。

### 2. 家长端信息架构：顶部孩子切换栏 + 四大分类分段标签页
- **决策**：
  - **顶栏（Header）**：左侧展示品牌标识与「家长工作台」徽章；右侧放置「家庭设置」按钮（点击打开家庭设置与全家备份弹窗）、「我的头像」与「退出登录」。
  - **孩子切换栏（Child Switcher Bar）**：位于工作台顶部，横向排列每个孩子的胶囊卡片（头像、昵称、年级/学期标签、今日目标），右侧集成「`+ 添加孩子`」按钮（打开新建孩子弹窗）、「显示已归档」开关，以及醒目的主操作按钮「进入孩子模式」。
  - **四大分类分段标签页（Segmented Tabs）**：
    - `overview`（**学习概况**）：仅负责展示 4 项核心学习指标卡片、近 7 日学习分布列表、旧本地档案导入摘要，标题旁配 `InfoPopover` 说明时区与申报时间口径。
    - `diagnostics`（**知识点诊断**）：直接承载 `StudentDiagnosticsPanel`，使知识点诊断成为一级模块；内部顶栏提供学科分段胶囊、教材下拉选择与 `InfoPopover`（诊断证据边界说明）；点击任一知识点的「查看证据」打开 `ModalDialog` 展示完整证据指标与最近错题，不再在单元列表上方内联挤开页面。
    - `curriculum`（**教材配置**）：承载 `CurriculumForm`，标题旁配 `InfoPopover`（手动指定教材与历史保留规则）；4 个学科采用 2x2 卡片网格布局，历史教材记录收起到按需弹窗或折叠详情中。
    - `manage`（**档案与数据**）：上半部分为孩子档案编辑表单（`StudentForm`）与备份导入/单孩导出卡片（`PortabilityPanel`，导入预览通过 `ModalDialog` 展示）；下半部分为独立的「危险操作区（Danger Zone）」卡片，包含「归档该孩子档案」与「永久删除孩子数据」，点击后均弹出独立 `ModalDialog` 进行二次确认。

### 3. 工作台背景隔离与四级按钮视觉规范
- **决策**：
  - 在 `forest.css` 中移除 `.account-root` 上的全局 `forest-welcome.webp` 背景声明（保留 `.account-root:has(.forest-child)::before` 专供孩子端使用），让 `account.css` 的清爽现代浅灰蓝工作台背景（`#f4f7f5` 搭配柔和顶部渐变）在家长端与管理端生效。
  - 建立四级按钮体系：
    1. **主操作按钮（`.btn-primary` / 默认主按钮）**：深森林绿渐变实心按钮，用于「进入孩子模式」「保存修改」。
    2. **次操作描边按钮（`.secondary`）**：白底细边框按钮，悬停微浮起，用于「查看证据」「导出数据」「家庭设置」。
    3. **轻量说明/图标按钮（`.account-info-trigger`）**：紧凑胶囊图标按钮，用于「`? 说明`」。
    4. **危险操作按钮（`.danger-outline` / `.danger`）**：平时在危险区展示为红字红框描边按钮，在确认弹窗内展示为实心警示红按钮。
  - 将 `.account-tabs` 与 `.diag-subject-tabs` 升级为带浅灰底槽与白色滑块激活态的 **一体式分段控制器（Segmented Control）**。

## Risks / Trade-offs

- **[Risk] 现有自动化检查脚本依赖旧的组件结构或内联说明文本** → **Mitigation**：保留 `StudentOverview` 与 `StudentDiagnosticsPanel` 的核心导出签名，`StudentOverview` 支持可选渲染或由 `ParentDashboard` 直接切分模块；同步更新 `scripts/checks/knowledge-diagnostics.tsx` 并验证 `InfoPopover` 与 `ModalDialog` 交互。
- **[Risk] 导出文件下载链接原先以内联 `<p role="status">` 渲染，改为浮框后用户可能错过点击下载** → **Mitigation**：当生成导出文件 Blob URL 时，除自动触发隐藏 `<a download>` 点击外，在 `FloatingToast`（持久显示直到手动关闭）及对应导出卡片按钮旁提供清晰的下载触发反馈。
