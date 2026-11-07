# parent-dashboard-experience Specification

## Purpose

规范家长端工作台（`/parent/`）的信息架构、零内联提示交互（悬浮 Toast、气泡说明 Popover、模态详情与确认弹窗 Modal）及视觉按钮层次，确保家长在管理多孩子档案、查看学习与诊断数据、配置教材和执行备份导入时界面清爽、分类清晰且无布局抖动。

## ADDED Requirements

### Requirement: Structured child workspace navigation
家长端工作台 SHALL 采用「顶栏家庭操作区 + 顶部孩子切换栏 + 四大分类分段标签页（学习概况、知识点诊断、教材配置、档案与数据）」的信息架构；家庭设置与添加孩子操作 MUST 通过独立模态弹窗承载，不在首屏主文档流内平铺堆叠。

#### Scenario: Switch child and inspect categorized tabs
- **WHEN** 家长在顶部孩子切换栏点击某个孩子胶囊卡片并在四大分类分段标签页间切换
- **THEN** 主工作区仅渲染当前选中分类模块的内容，切换孩子时保持或平滑刷新当前分类模块且不混入其他孩子数据

#### Scenario: Open family settings in modal
- **WHEN** 家长点击顶栏右侧的「家庭设置」按钮
- **THEN** 系统以独立模态弹窗展示家庭名称、时区、默认地区编辑表单及全家数据导出入口，关闭弹窗后主工作区保持原状态

### Requirement: Floating toast feedback without layout shift
家长端所有操作状态反馈（保存成功、参数校验错误、接口异常、文件导出就绪等）MUST 通过脱离文档流的悬浮通知浮框（Toast）展示，支持自动消散与手动关闭，禁止在表单或卡片 DOM 文档流内插入内联状态段落导致页面跳动。

#### Scenario: Display save or error feedback as floating toast
- **WHEN** 家长保存家庭设置、教材配置、孩子档案或触发校验/网络错误
- **THEN** 系统在视口悬浮层展示对应成功或错误浮框并提供关闭按钮，页面主文档流高度与排版不发生位移

### Requirement: On-demand rule explanations via popover
家长端所有静态业务规则与边界说明（时区与申报用时规则、诊断证据边界、教材手动绑定规则、选填档案说明、备份保留策略）MUST 默认收起到模块标题旁的「说明」触发按钮中，仅在点击或聚焦时以气泡浮框（Popover）展示，主界面默认不直接露出大段说明文字。

#### Scenario: Toggle rule explanation popover
- **WHEN** 家长点击模块标题旁的「`? 说明`」按钮，随后点击外部区域或按 `Escape`
- **THEN** 系统先以悬浮气泡框展示该模块的完整规则说明，随后关闭气泡框且不影响下方卡片布局

### Requirement: Modal dialogs for deep evidence and high-risk confirmations
家长端的深度明细（如知识点作答证据详情、备份导入预检报告）与高危操作确认（如归档孩子档案、永久删除孩子数据）MUST 通过独立模态弹窗（Modal Dialog）承载，禁止在当前卡片流内直接展开内联抽屉或确认块。

#### Scenario: Confirm archive or permanent delete in modal
- **WHEN** 家长在「档案与数据」模块点击「归档档案」或「永久删除孩子数据」
- **THEN** 系统打开独立模态确认弹窗展示影响说明与确认操作，取消或关闭弹窗后原页面不残留内联确认块

#### Scenario: Preview backup import in modal
- **WHEN** 家长选择备份 JSON 文件并触发导入预览
- **THEN** 系统在独立模态弹窗中展示备份文件预检摘要与「确认导入」按钮，不在卡片内联插入预览文本块

### Requirement: Parent console visual isolation and button hierarchy
家长端与管理端工作台 MUST 使用独立的清爽工作台背景，不得透出孩子端森林插画背景；按钮与导航控件 SHALL 区分主操作按钮、次操作描边按钮、轻量图标按钮、危险操作按钮及一体式分段标签控制器，并在桌面端与移动端均保持零横向溢出。

#### Scenario: Render parent dashboard on desktop and mobile viewports
- **WHEN** 家长在桌面端（`1440x900`）或移动端（`390x844`）打开家长端工作台
- **THEN** 页面使用清爽浅色工作台背景，顶部孩子切换栏与四大分类分段控制器主次分明且无横向滚动溢出
