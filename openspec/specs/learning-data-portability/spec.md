# learning-data-portability Specification

## Purpose

让已有本地用户能够在知情确认后迁入家庭云端，并允许家长导出和删除自己的数据；迁移保留教材身份与历史摘要来源，避免伪造历史证据或重复发放学习奖励。

## Requirements

### Requirement: Previewed legacy import
系统 SHALL 支持家长逐档案预览导入到明确学生，校验格式版本、大小、题目和教材关联，显示可迁移与无法还原的数据及冲突；确认前不得改写云端或删除本地记录。

#### Scenario: Import old profile
- **WHEN** 家长预览并确认将一个旧本地档案导入指定孩子
- **THEN** 系统仅导入该档案的已确认数据，保留原教材和课程 ID，并保留本地备份

#### Scenario: Invalid or unresolved content
- **WHEN** 导入包含损坏数据、不支持版本或无法识别教材题目
- **THEN** 系统明确报告错误或未映射项，不静默套用其他教材的题目

### Requirement: Import provenance and replay safety
导入 MUST 标记 legacy 来源和导入批次，旧汇总不得转成虚构作答；相同导入重复请求不得重复覆盖或发奖。旧档案可查看为历史摘要，但新奖励和权威余额 MUST 由服务端新事件决定。

#### Scenario: Reimport same backup
- **WHEN** 家长重试已经成功的导入批次
- **THEN** 返回原结果，不重复生成摘要或奖励，不覆盖导入后新增的学习记录

### Requirement: Authorized export
系统 SHALL 允许通过最近家长验证的用户导出自己的家庭和学生资料、配置、历史摘要、学习记录及当前规则版本下的知识点诊断快照，排除密码哈希、会话凭据及其他家庭数据；导出中的诊断快照 MUST 标注诊断规则版本与数据来源边界。

管理员建号权限 SHALL 不自动授予家庭导出权限，学生独立账号 SHALL 不得导出家庭资料；导出中的学生账号关联信息 MUST 排除密码、重置凭据及认证内部状态。

#### Scenario: Export two students
- **WHEN** 家长验证身份后导出家庭数据
- **THEN** 导出包含本家庭两个孩子各自的数据、知识点诊断快照和来源版本，不包含认证秘密

### Requirement: Account and student data deletion
系统 SHALL 提供验证家长身份后的学生数据及账户家庭数据删除流程，清晰列明范围并要求确认；完成后撤销相关会话，停止接收旧请求并清理活动数据与设备缓存。备份保留与清理时限 MUST 在操作前说明。

家庭整体删除 MUST 仅限最近验证的家庭 owner，guardian、独立学生和仅具备管理员身份的账号不得触发家庭连带删除。

#### Scenario: Delete one student
- **WHEN** 家长验证并确认删除一个孩子的数据
- **THEN** 该孩子的活动资料、记录及关联学生登录账号被删除，家长代入和独立账号的旧会话请求均被拒绝，其他孩子及账号不受影响

#### Scenario: Delete account and family
- **WHEN** M1 家庭所有者确认删除其账户及家庭
- **THEN** 关联家庭活动数据及学生登录账号被删除，会话全部撤销，并提示设备清理和备份到期策略；部署管理员账号不属于该家庭且不被连带删除
