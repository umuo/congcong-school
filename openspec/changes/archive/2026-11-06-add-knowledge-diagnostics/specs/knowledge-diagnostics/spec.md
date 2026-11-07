# knowledge-diagnostics Specification

## Purpose

为语、数、英、科全部 84 套教材建立稳定的知识点身份与不可变题目版本映射，并基于学生的权威逐次作答证据提供带规则版本、可确定性重算的知识点掌握度诊断与家长端透明证据视图。

## ADDED Requirements

### Requirement: Stable knowledge point catalog across textbooks
系统 SHALL 为语、数、英、科全部在册教材建立稳定的知识点目录，记录所属学科、教材、单元、课时或技能来源及可读名称；不同教材、不同学制（六三制与五四制）或修订版之间的知识点 MUST 保持各自教材范围内的稳定身份，仅在存在显式审核依据（如修订版承接关系或受控跨版关联）时建立关联，不得仅凭同名字符串跨学科或跨年级自动合并。

#### Scenario: Query knowledge catalog for a textbook
- **WHEN** 已授权家长或学习上下文按教材 ID 查询知识点目录
- **THEN** 系统按该教材的单元与课时顺序返回稳定的知识点 ID、名称、单元信息和来源类型

#### Scenario: Keep distinct editions separate without explicit mapping
- **WHEN** 两本不同版本或不同学制的教材包含同名知识点且无显式等价映射
- **THEN** 系统保留各自独立的知识点身份与教材归属，不自动混算两本教材的掌握度

### Requirement: Versioned question-to-knowledge mapping
系统 MUST 将不可变题目版本（`question_uid` + `question_version`）关联到一个或多个知识点，并记录映射角色、映射来源（如课时主知识点、单元挑战标签、阅读技能或数感技能）及映射规则版本；题库重新导入或内容版本新增时，既有题目版本的知识点映射语义 MUST 保持可追溯。

#### Scenario: Map ordinary lesson and unit challenge questions
- **WHEN** 系统导入 84 套教材的普通课、单元挑战、故事阅读与数感题目
- **THEN** 每个可诊断题目版本均绑定对应的稳定知识点及映射来源，挑战题优先匹配本单元对应课时知识点，专有挑战标签生成或关联本单元受控知识点

#### Scenario: Inspect unmapped or non-question content
- **WHEN** 某学习容器属于纯朗读/跟读或不含可判分题目
- **THEN** 系统不为其伪造题目级知识点映射，也不把纯完成状态算作知识点答题证据

### Requirement: Evidence-based recomputable mastery diagnosis
系统 MUST 仅依据学生已确认的权威作答记录（`learning_attempts`）及关联会话上下文，按显式诊断规则版本（`diagnostic_rule_version`）计算每个知识点的诊断状态（`unassessed`、`insufficient_evidence`、`needs_review`、`developing`、`mastered`）；诊断计算 MUST 区分会话首次作答与同会话错题回炉重做，结合不同题目覆盖度、提示使用情况和按家庭时区计算的跨日表现，确保从同一作答历史重算结果完全一致。

#### Scenario: Same-session retry does not inflate mastery
- **WHEN** 学生在同一学习会话中首答错误后经回炉重做答对，且总独立作答证据不足或未达到稳定标准
- **THEN** 诊断结果不得直接判定为 `mastered`，并在证据明细中如实区分首答结果与重做结果

#### Scenario: Hint-assisted or single-attempt answer
- **WHEN** 学生在某知识点仅有单次作答，或仅在开启解题提示（`hint_level > 0`）后答对
- **THEN** 系统将该知识点标记为 `insufficient_evidence` 或 `developing`，不会因单题或依赖提示而直接判定为 `mastered`

#### Scenario: Multi-question and cross-day mastery confirmation
- **WHEN** 学生在某知识点的多道不同题目或跨日练习中保持高首答正确率且最近无未解决错题
- **THEN** 系统将该知识点诊断为 `mastered`，并附带首答正确率、独立题目数、覆盖天数与最近练习日期

#### Scenario: Recent repeated errors trigger needs review
- **WHEN** 学生在某知识点出现多次首答错误或最近作答连续出错
- **THEN** 系统将该知识点诊断为 `needs_review`，并归入待巩固薄弱项列表

### Requirement: Non-diagnostic records exclusion
系统 MUST 排除经验值（XP）、宝石、连续打卡天数、课程通关标记、纯听读/跟读完成事件以及旧本地档案导入摘要（`legacy_imports`）作为知识点掌握度的计算依据；诊断重算 SHALL 不修改任何历史作答判分、学习进度或奖励账本。

#### Scenario: Imported legacy summary without cloud attempts
- **WHEN** 学生仅导入了旧本地档案的完成摘要而尚无云端逐次作答记录
- **THEN** 各知识点诊断状态保持 `unassessed`，系统明确提示旧导入摘要不含逐题作答证据

### Requirement: Authorized parent and student diagnostic views
系统 SHALL 提供受角色与家庭边界保护的知识点诊断查询接口，并在家长端学生总览中展示各学科/教材的掌握分布、待巩固知识点及每个知识点的结构化证据明细（覆盖题数、首答正确数、总作答数、提示辅助次数、练习天数、最近练习时间及代表性错题/练习来源）；不同家庭、同家庭未授权兄弟姐妹及管理员日常后台 MUST 遵循既有访问隔离。

#### Scenario: Parent views subject and textbook diagnostics with evidence
- **WHEN** 已登录家长在学生总览中查看某孩子的知识点诊断并切换学科或教材
- **THEN** 页面展示该教材各单元知识点的诊断状态统计、优先待巩固列表及每项的具体作答依据，不展示无依据的分数排名

#### Scenario: Cross-family or sibling unauthorized access rejected
- **WHEN** 某家庭家长或独立登录学生请求其他家庭学生或非本人绑定学生的知识点诊断接口
- **THEN** 服务端拒绝访问并返回未找到或权限错误，不泄露任何诊断统计或作答证据
