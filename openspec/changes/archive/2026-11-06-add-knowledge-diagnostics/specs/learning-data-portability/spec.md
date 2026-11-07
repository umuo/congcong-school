# Spec Delta

## MODIFIED Requirements

### Requirement: Authorized export
系统 SHALL 允许通过最近家长验证的用户导出自己的家庭和学生资料、配置、历史摘要、学习记录及当前规则版本下的知识点诊断快照，排除密码哈希、会话凭据及其他家庭数据；导出中的诊断快照 MUST 标注诊断规则版本与数据来源边界。

管理员建号权限 SHALL 不自动授予家庭导出权限，学生独立账号 SHALL 不得导出家庭资料；导出中的学生账号关联信息 MUST 排除密码、重置凭据及认证内部状态。

#### Scenario: Export two students
- **WHEN** 家长验证身份后导出家庭数据
- **THEN** 导出包含本家庭两个孩子各自的数据、知识点诊断快照和来源版本，不包含认证秘密
