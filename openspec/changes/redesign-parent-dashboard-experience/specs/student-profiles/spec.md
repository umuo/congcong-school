# student-profiles Specification

## MODIFIED Requirements

### Requirement: Parent overview
系统 SHALL 提供桌面端与移动端可用的家长工作台，采用顶部孩子切换栏、四大分类模块标签页（学习概况、知识点诊断、教材配置、档案与数据）以及独立弹窗入口（家庭设置、添加孩子）；学习概况模块 SHALL 展示真实已记录的进度、最近学习和申报时间，并提供一键进入当前孩子学习模式的入口。

#### Scenario: Inspect a student
- **WHEN** 家长在顶部孩子切换栏选中某个孩子并查看「学习概况」「知识点诊断」「教材配置」或「档案与数据」标签页
- **THEN** 系统按所选分类模块展示该孩子的真实学习摘要或配置并提供进入其学习模式的入口，不混入其他孩子数据
