# knowledge-diagnostics Specification

## MODIFIED Requirements

### Requirement: Authorized parent and student diagnostic views
系统 SHALL 提供受角色与家庭边界保护的知识点诊断查询接口，并在家长端工作台的「知识点诊断」独立分类模块中展示各学科/教材的掌握分布、优先巩固清单及按需弹窗查看的知识点证据明细（覆盖题数、首答正确数、总作答数、提示辅助次数、练习天数、最近练习时间及代表性错题来源）；诊断边界说明 SHALL 收起到标题旁说明浮框，不同家庭、同家庭未授权兄弟姐妹及管理员日常后台 MUST 遵循既有访问隔离。

#### Scenario: Parent views subject and textbook diagnostics with evidence
- **WHEN** 已登录家长在「知识点诊断」标签页查看某孩子的知识点诊断、切换学科或教材并点击某知识点的「查看证据」
- **THEN** 页面展示该教材各单元知识点的诊断状态统计与优先待巩固列表，并以独立模态弹窗展示每项的具体作答依据，不展示无依据的分数排名且不在文档流内插入内联说明段落

#### Scenario: Cross-family or sibling unauthorized access rejected
- **WHEN** 某家庭家长或独立登录学生请求其他家庭学生或非本人绑定学生的知识点诊断接口
- **THEN** 服务端拒绝访问并返回未找到或权限错误，不泄露任何诊断统计或作答证据
