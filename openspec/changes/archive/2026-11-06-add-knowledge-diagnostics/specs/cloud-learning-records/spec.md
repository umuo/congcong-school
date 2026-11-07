# Spec Delta

## MODIFIED Requirements

### Requirement: Recomputable summaries
新增成长摘要与知识点诊断 MUST 来源于保留的学习事件及权威逐次作答记录；展示时间与跨日巩固计算 SHALL 区分客户端声明用时与服务端接收时间，并使用家庭时区。系统不得将旧导入摘要、单次答题、课程通关标记或奖励积分直接包装为统一知识点已掌握的证据，且诊断重算不得改写历史作答判分或奖励账本。

#### Scenario: Rebuild summary
- **WHEN** 系统从新学习事件重新计算学生进度、每日学习和周报
- **THEN** 得到一致结果，旧导入摘要单独标注来源，不生成不存在的历史作答

#### Scenario: Recompute diagnostics without mutating scores or rewards
- **WHEN** 系统基于学生已确认的逐次作答记录重新计算知识点诊断结果
- **THEN** 输出一致的知识点状态与证据汇总，学生的历史作答结果、经验值、宝石余额和领取记录均保持不变
