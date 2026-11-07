# Spec Delta

## Purpose

让儿童进入系统后能迅速知道接下来学什么，并通过一致、可访问的单元路线和清楚分区的导航找到课程、探索内容、排行与个人空间，同时保持原有教材、深链接、学习会话及跨身份隔离的有效性。

## ADDED Requirements

### Requirement: Learning action in the first viewport
正常配置且可连接时，儿童首页 SHALL 在 390×844 CSS px 的首屏完整展示一项可操作的主要学习行动，优先当前教材的可恢复会话，其次按目录顺序选择未完成课程，全部完成时提供复习。浏览首页 MUST 不自动创建学习会话、领奖或执行消费。

#### Scenario: Resume a current activity
- **WHEN** 当前教材存在可恢复的已授权活跃会话
- **THEN** 首屏提供明确继续入口，恢复原会话及已确认进度

#### Scenario: Start a new course or review
- **WHEN** 当前教材没有可恢复会话
- **THEN** 按未完成课程或全部完成后的复习状态显示真实下一行动，主要入口不会被奖励/消费/设置按钮推到首屏以外

#### Scenario: Recover an unavailable learning state
- **WHEN** 未配置教材、无法连接或存在未同步操作
- **THEN** 首屏显示对应的配置提示或恢复行动，不伪造可学状态，不丢掉原待同步操作

### Requirement: Distinct child navigation destinations
儿童端 SHALL 提供“学习 / 探索 / 排行 / 小屋”四个具名导航入口和明确当前状态。学习集中课程，探索提供当前教材的故事/听读等入口，排行以简短模拟标识直接呈现榜单、不提供普通刷新按钮，小屋分区承载头像、装扮、任务奖励、设置及商店入口；消费与管理入口 SHALL 不挤占正常首页的主要学习行动。

#### Scenario: Visit the league or shop
- **WHEN** 孩子打开排行或商店
- **THEN** 到达各自明确的内容区域，不再次看到无区分的通用工具按钮集合，打开页面本身不结算或购买

#### Scenario: Open exploration without a configured book
- **WHEN** 孩子打开探索但当前没有可用教材
- **THEN** 显示可理解的配置提示和返回路径，不生成无效教材地址或显示其他学生内容

### Requirement: Unit routes reflect actual learning state
课程 SHALL 按当前授权教材及单元顺序形成森林路线，区分已完成、当前项和可学习项，并提供可理解的阅读顺序或等价列表。路线 MUST 不额外制造服务器尚未要求的锁关，不改变原课程、挑战、跳级、复习或数感入口的学习权限。

#### Scenario: Navigate a unit with touch or assistive input
- **WHEN** 孩子通过触摸、键盘或辅助技术浏览课程路线
- **THEN** 能识别单元、课程名称和状态，并执行与其实际权限一致的行动

#### Scenario: Switch to another configured subject
- **WHEN** 孩子在学习或探索顶部选择语文、数学、英语或科学
- **THEN** 使用家长为该学科配置的授权教材，展示相应名称、课程和进度；切换期间不显示旧学科内容，迟到响应不覆盖当前选择，不修改教材配置

#### Scenario: Discover available subjects
- **WHEN** 孩子进入或滚动学习与探索页面
- **THEN** 显眼的四学科切换保持可达，未配置学科标明待配置且不可进入，儿童不需选择教材版本；主要学习入口仍完整出现在手机首屏

### Requirement: Preserve learning addresses and recovery
已有教材、课程、故事、听读、挑战、跳级、复习、数感、排行、商店与个人页面的有效地址 SHALL 继续可用。导航返回、刷新和直达 SHALL 恢复当前主体的服务端状态，不用新会话覆盖原会话或把另一孩子的状态带入页面。

#### Scenario: Return to an existing learning session
- **WHEN** 孩子从已有深链接进入学习或导航返回原课程
- **THEN** 页面使用原已授权会话和进度，输入/恢复规则与当前学习流程兼容

#### Scenario: Change identity between pages
- **WHEN** 用户切换孩子、恢复家长或退出后登录另一账号
- **THEN** 页面只显示新有效主体的可访问内容，旧请求或选择不会被重标到新主体

### Requirement: Preserve pending operations and economy semantics
导航、头像面板、视觉及偏好设置 SHALL 不清空或重新归属未同步学习操作，不更换原幂等键。展示数据 SHALL 继续来自当前云端主体；只读页面和视觉反馈 MUST 不产生 XP、宝石、装扮权益或周结算副作用，实际变更继续由已有显式行为确认。

#### Scenario: Change appearance with a pending write
- **WHEN** 孩子有未同步操作并打开头像或调整界面设置
- **THEN** 原操作保留原范围、内容和幂等键，仍能从可见入口重试，余额和学习投影不被界面动作改写

#### Scenario: Read the redesigned league
- **WHEN** 孩子打开或刷新新版排行页面
- **THEN** 显示本人及稳定影子同学头像，保留模拟说明，仅读取不领取奖励或改变结算状态

#### Scenario: Recover interrupted foreground-time receipts
- **WHEN** 页面恢复同一有效身份，并存在导航中断后留下的用时回执
- **THEN** 可以补发原范围、原内容和原幂等键的回执，不自动重放答案、开始课程或奖励操作；失败仍保留可见恢复入口，非题目用时回执不阻止孩子练习

#### Scenario: Navigate within the verified child space
- **WHEN** 同一已验证孩子在学习、探索、排行、小屋和商店之间进行站内导航
- **THEN** 保留身份与学习客户端，不因换页展示整屏登录检查或清空原待保存操作；首次打开与身份过期/变化仍校验并撤销旧主体内容

### Requirement: Actionable empty exploration
当前已配置教材没有故事或听读材料时，探索页 SHALL 在390×844首屏主卡片说明缺少的材料类型并提供返回当前教材课程的入口，不以材料介绍插画挤掉下一步行动。浏览和返回 SHALL 不自动换教材、创建会话或产生奖励。

#### Scenario: Return from an empty story or listening collection
- **WHEN** 孩子查看当前教材且选中的故事/听读没有条目
- **THEN** 首屏能找到返回课程学习的行动，另一种材料仍可切换，返回保持当前授权教材

#### Scenario: Resume an activity without a catalogue title
- **WHEN** 最新可恢复会话为复习、数感或跳级等没有普通课程条目的活动
- **THEN** 首页显示可读的练习类型并恢复同一会话ID，目录标题匹配同时检查种类与source_id
