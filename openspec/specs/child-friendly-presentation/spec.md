# child-friendly-presentation Specification

## Purpose

为儿童学习提供统一的熊猫森林探险视觉，使背景、人物、字体、卡片和控件形成连贯体验，并在手机、平板和桌面保持清晰层级与可操作性，让孩子专注学习，同时让家长和管理员能够识别同一产品。

## Requirements

### Requirement: Approved visual baseline
系统改造 SHALL 在应用代码实现前向用户展示同一熊猫森林主题的三份手机首页视觉稿并取得明确选择。选定稿 SHALL 作为关键页面和响应式实现的视觉基线；提案完成、主题偏好或用户沉默 MUST 不被当作已选择具体视觉稿。

#### Scenario: No visual option has been selected
- **WHEN** 三份首页稿已展示但用户尚未选择
- **THEN** 继续设计讨论或修订稿件，应用代码实现尚不开始

#### Scenario: Implement the selected direction
- **WHEN** 用户明确选择一稿且开始实现
- **THEN** 实际首页、答题、头像面板和排行沿用该稿的视觉语言，并提供对应视口的对照证据

### Requirement: Coherent panda forest presentation
儿童页面 SHALL 统一采用熊猫森林探险的角色、绘本场景、层次和控件语言，默认使用奶油白、嫩绿、天蓝与清晰正文。已拥有/装备的头像、装扮和其他主题 SHALL 在同一结构中继续有效，装饰 MUST 不承载唯一操作提示或拦截输入。

#### Scenario: Move between child pages
- **WHEN** 孩子在首页、课程、故事、排行和小屋间切换
- **THEN** 识别到同一套字体、卡片、角色与状态表达，背景和角色不遮挡内容

#### Scenario: Use an existing equipped theme
- **WHEN** 孩子已装备其他主题或熊猫装扮
- **THEN** 保留其装备和权益并清晰显示页面，不因森林改版强制重置选择

### Requirement: Clear control hierarchy
每个任务区域 SHALL 有明确的主要行动，其余行动以次要或图标加文字方式区分。系统 SHALL 收敛普通控件的视觉体量，同时保留至少 44×44 CSS px 的触摸区域、可见焦点和不依赖颜色的状态说明。

#### Scenario: Review a normal learning screen
- **WHEN** 孩子查看可学习页面
- **THEN** 能区分主要学习行动、导航和设置，不出现同等醒目的消费/设置按钮群压过学习任务

#### Scenario: Touch or use a keyboard
- **WHEN** 用户用触摸或键盘操作紧凑按钮
- **THEN** 触摸区域与焦点可见性保持可用，图标操作有可理解名称

### Requirement: Responsive surfaces and safe areas
页面 SHALL 在 360、390、430px 手机宽度及平板/桌面重排，处理底部安全区、软键盘、横屏、长文本与 200% 文本放大。底部导航和固定操作区 MUST 不遮挡最后一项内容、题面、输入或提交控件。

#### Scenario: Answer with the mobile keyboard open
- **WHEN** 手机软键盘打开或关闭
- **THEN** 当前输入与提交动作可见且可触达，页面不因固定底栏产生不可恢复遮挡

#### Scenario: Read long content on multiple screens
- **WHEN** 390px 页面显示长昵称/教材名，或使用横屏、平板、桌面和放大文字
- **THEN** 内容自然重排且不产生页面级横向溢出，大屏有适当密度和可读行宽

### Requirement: Compact avatar entry and bounded picker
同一页面对当前头像主体 SHALL 提供一个紧凑修改入口。手机头像选择 SHALL 在限定高度的面板中完成，桌面使用相应对话框；预览、选项、保存/取消和错误 SHALL 可达，并继续遵守已有头像的服务端归属、Canvas 外观和版本冲突契约。

#### Scenario: Open and cancel the picker
- **WHEN** 孩子点击头像并预览其他选项后取消或按 Escape
- **THEN** 不保存预览值，页面恢复原展示且焦点回到入口，背景控件不与面板同时操作

#### Scenario: Edit while another device saves
- **WHEN** 面板打开后另一设备更新同一头像
- **THEN** 原面板仍使用打开时版本，陈旧保存显示冲突而不覆盖，并能读取最新值

### Requirement: Focused learning and readable states
题干、答案、故事文本、阅读控制及反馈 SHALL 使用清楚可读的表面。森林背景、导航和庆祝效果 MUST 不干扰题型专属键盘、连线、证据选择、音频控制或错误恢复；重要状态 SHALL 同时有文字或等价可访问表达。

#### Scenario: Work with an interactive question
- **WHEN** 孩子使用填词键盘、连线或证据选择
- **THEN** 场景装饰和页面控件不覆盖交互目标，当前选择和判分状态清楚可辨

#### Scenario: Encounter an error
- **WHEN** 页面读取、提交或同步失败
- **THEN** 用可理解提示与恢复行动呈现实际状态，不显示虚假的完成或隐藏未同步操作

### Requirement: Consistent account presentation
登录、家长和管理员页面 SHALL 使用与儿童端同源的字体、颜色、控件层级和反馈规范，同时保持管理表单、列表、验证提示和敏感操作确认的清晰性。卡通化 MUST 不降低账号和家庭权限边界。

#### Scenario: Switch to a parent or administrator
- **WHEN** 用户切换到家长或管理员入口
- **THEN** 视觉仍属于同一产品，所见功能与实际身份匹配，验证及敏感操作继续明确

### Requirement: Streamlined child interactions
儿童输入 SHALL 即时更新本机草稿，检查或主动返回时才同步相关答案，不因逐键联网保存阻断输入。小屋 SHALL 按装扮、任务和设置分区，目标直接点选，家长和退出入口默认收起。

#### Scenario: Type without waiting for draft network writes
- **WHEN** 孩子连续输入答案或短暂停顿
- **THEN** 输入仅更新当前题目的本机草稿，不逐键发送云端保存或锁住键盘；检查答案同步完整作答，主动返回先保存脏草稿，保存失败保留恢复操作

#### Scenario: Browse a simple cottage
- **WHEN** 孩子打开小屋
- **THEN** 仅展示所选装扮、任务或设置分区，每日目标用直接选择按钮，退出置于家长与账号区域而非页头

### Requirement: Stable transient feedback and confirmed equipment
儿童端操作反馈 SHALL 使用不参与正文排版的可访问浮层，成功提示自动消失且可主动关闭；尚未同步操作 SHALL 继续有恢复入口，不因关闭提示清除待提交字节。装扮按钮 SHALL 根据服务端各类别装备字段显示已穿上，提交期间仅当前物品显示进行中，按钮文字与禁用变化 MUST 不改变卡片布局。

#### Scenario: Equip an owned outfit
- **WHEN** 孩子点击未装备的已拥有装扮
- **THEN** 当前按钮显示穿上中，确认成功后显示已穿上并禁止重复操作；原装备保持到服务端确认，失败不伪造新装备

#### Scenario: Show a successful operation notice
- **WHEN** 成功提示出现和自动消失
- **THEN** 提示浮于底部导航上方，不推移分区、装扮行或按钮；键盘和辅助技术可以理解、关闭提示

### Requirement: Visual cosmetic collections
儿童衣柜和商店 SHALL 区分熊猫装扮、界面主题及答题背景并提供无购买副作用的真实外观预览。手机使用两列卡片、大屏使用适当密度；普通装扮操作 SHALL 保持触摸尺寸，且不无限横向拉伸。未知物品仍提供可读回退，不丢弃服务端条目。

#### Scenario: Browse owned and available cosmetics
- **WHEN** 孩子查看衣柜或商店
- **THEN** 能区分各装备类别、预览与当前已装备状态，浏览不自动购买、装备或改变权益，按钮状态变更不推移卡片
