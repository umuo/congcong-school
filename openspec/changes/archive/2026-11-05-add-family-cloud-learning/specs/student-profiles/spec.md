# Spec Delta

## Purpose

为每个家庭中的孩子建立稳定且相互隔离的长期档案，使年级调整、设备切换和档案归档不会丢失已有学习记录，并为后续成长分析提供一致的学生身份。

## ADDED Requirements

### Requirement: Student profile lifecycle
系统 SHALL 支持家长创建、编辑、查看及归档自己的学生，使用稳定学生 ID，保存昵称、预置头像、地区、学段年级、学年学期、每日时长目标；出生年月、学校和家长备注 SHALL 为可选字段。归档不得删除历史数据。

家长创建学生档案 SHALL 不自动创建登录账号；管理员 SHALL 可在明确家庭下创建档案并开通账号，或为已有档案开通账号。账号和档案 MUST 分离，开通账号不得改变原学生身份与学习记录。

#### Scenario: Grade change
- **WHEN** 家长将学生从三年级调整至四年级
- **THEN** 学生 ID、历史课程、作答和原教材记录保持可查询

#### Scenario: Archive student
- **WHEN** 家长归档学生
- **THEN** 该学生从默认学习选择中移除，家长仍可查看历史，其独立账号不能再登录或继续学习，原有孩子会话及新的学习写入均被拒绝，记录和账号关联保留

### Requirement: Independent student login binding
每个学生登录账号 MUST 只绑定一个家庭内的一个学生档案，每个档案至多一个登录账号。绑定 MUST 由管理员校验并受数据库唯一性与家庭一致性约束保护；学生和家长不得通过请求字段改绑账号或授予角色。

#### Scenario: Enable login without replacing profile
- **WHEN** 管理员为已配置教材且有学习历史的学生创建登录账号
- **THEN** 独立登录读取同一学生的数据，学生 ID、教材和历史不变，不复制为另一个孩子

#### Scenario: Duplicate or foreign binding
- **WHEN** 管理员重复为已绑定学生建号，或提交学生与家庭不一致的关联
- **THEN** 整笔创建失败，不留下孤立账号、不修改原绑定或学习记录

### Requirement: Independent student context
系统 MUST 将学习记录、配置、奖励和未完成会话归属到明确学生；切换学生时不得复用另一学生的缓存或待提交请求，已开始的请求不得被重新标记为新学生。

#### Scenario: Manage two children
- **WHEN** 家长创建两个孩子，分别配置教材并完成不同课程，然后切换和刷新
- **THEN** 每个孩子仅显示自己的教材、进度、错题、奖励和未完成会话

#### Scenario: Switch during delayed response
- **WHEN** 学生 A 的提交尚未返回时界面切换到学生 B
- **THEN** A 的返回结果不污染 B 的界面或数据，提交仍只属于 A

#### Scenario: Switch login accounts
- **WHEN** 学生 A 退出并由学生 B 在同一设备登录
- **THEN** 清理 A 的敏感缓存并取消或忽略旧请求，B 仅显示自身记录，A 的待提交数据不能改标为 B

### Requirement: Parent overview
系统 SHALL 提供移动端可用的家庭首页、学生列表、档案编辑、孩子学习总览、教材配置及家庭设置入口；M1 总览 SHALL 展示真实已记录的进度、最近学习和时间，不展示尚未实现的知识诊断结论。

#### Scenario: Inspect a student
- **WHEN** 家长打开某个孩子的学习总览
- **THEN** 系统展示该孩子的真实学习摘要并提供进入其学习模式的入口，不混入其他孩子数据
