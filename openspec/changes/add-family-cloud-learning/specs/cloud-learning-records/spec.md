# Spec Delta

## Purpose

将学生的学习活动转换为服务端可验证、可追溯且可跨设备读取的记录，确保题目版本、判分与奖励有明确来源，重试和并发不会造成重复记账或学生数据污染。

## ADDED Requirements

### Requirement: Protected question delivery
云端学习 MUST 在服务端保存题目答案及判分版本；作答前的响应、静态文件、页面数据、源码包和缓存不得无条件包含正确答案、答案解析或可直接揭示答案的题目音频。题目 MUST 具有稳定身份和不可变版本。

#### Scenario: Inspect published assets
- **WHEN** 用户在作答前读取云端站点响应、静态课程和预渲染资源
- **THEN** 不能直接取得正确答案或提前解析，题干与必要选项仍可使用

### Requirement: Authoritative attempt history
系统 MUST 在服务端校验会话、学生、题目及版本后判分，记录每次作答的答案、结果、判分版本、时间、用时、来源、题目难度和知识关联。客户端不得决定正确率、经验和奖励；内容修订不得改变历史记录的含义。

#### Scenario: Forged correctness
- **WHEN** 客户端提交答案时夹带 isCorrect、经验或其他学生 ID
- **THEN** 服务端不采信这些字段并依据已授权会话判分，返回权威结果与允许展示的解析

#### Scenario: Repeated mistakes
- **WHEN** 同一道题在多次练习中答错
- **THEN** 历次作答均可追溯，错题汇总关联到同一道题而非生成互不关联的重复错题

### Requirement: Idempotent transactional settlement
提交和结算 MUST 使用幂等标识；相同标识和相同内容的重试返回原结果，不重复新增作答或奖励；相同标识与不同内容 MUST 返回冲突。并发领取和结算 MUST 保持余额、进度与领取账本一致。

#### Scenario: Lost response and retry
- **WHEN** 服务端已接收作答但响应丢失，客户端用原标识重试
- **THEN** 返回相同作答结果且仅记账一次

#### Scenario: Concurrent lesson completion
- **WHEN** 两台设备同时重复完成或领取同一项首次奖励
- **THEN** 两个合法会话的作答历史可保留，但一次性奖励只发一次且余额不丢失

### Requirement: Cross-device synchronization
系统 SHALL 让同一家庭的授权设备读取最新学生记录和单调递增的变化游标；旧版本配置更新 MUST 报告冲突。待提交作答必须明确显示未同步状态，退出、撤销或学生归档后不得继续提交。

#### Scenario: Resume on another device
- **WHEN** 设备 A 完成课程并同步成功，设备 B 刷新该学生
- **THEN** B 显示服务端最新进度和错题；相同学习会话可恢复至已确认的服务端检查点

#### Scenario: Stale configuration edit
- **WHEN** 设备 B 根据旧版本更新已被设备 A 修改的教材配置
- **THEN** 系统返回版本冲突和刷新提示，不静默覆盖 A 的修改

### Requirement: Existing learning flows remain usable
系统 SHALL 保留课程讲解、原有题型、错题回炉、复习、挑战、跳级、数感、故事答题与听读，并将相应学习结果归属当前学生。阅读、学习时间、任务和奖励 MUST 使用去重事件或服务端账本，不能只接受客户端统计数字。

#### Scenario: Complete existing paths
- **WHEN** 学生分别完成普通课、挑战、跳级、复习、数感练习、故事答题和听读
- **THEN** 原有交互可完成，对应记录和奖励按该入口原有语义产生，刷新后可恢复正确状态

### Requirement: Recomputable summaries
新增成长摘要 MUST 来源于保留的学习事件；展示时间 SHALL 区分客户端声明用时与服务端接收时间，并使用家庭时区。M1 不得将旧摘要或一次答题包装为统一知识点已掌握的证据。

#### Scenario: Rebuild summary
- **WHEN** 系统从新学习事件重新计算学生进度、每日学习和周报
- **THEN** 得到一致结果，旧导入摘要单独标注来源，不生成不存在的历史作答
