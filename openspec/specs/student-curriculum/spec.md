# student-curriculum Specification

## Purpose

将每个学生启用的学科及教材选择独立保存，允许不同学科使用不同出版社，并保存教材更换历史，使后续跨教材知识映射能够建立在稳定的内容身份之上。

## Requirements

### Requirement: Configurable subject catalog
系统 SHALL 从学科目录读取可用学科，支持按学生启用或停用；初始目录 SHALL 保留原有数学、语文、英语、科学，学生不必全部启用。新增目录项不得要求修改核心学生业务中的固定学科枚举。

#### Scenario: Disable a subject
- **WHEN** 家长停用某个孩子的英语
- **THEN** 该孩子默认学习入口不再推荐英语，已有英语记录仍然保留，其他孩子配置不变

### Requirement: Versioned textbook metadata
教材目录 SHALL 保留原有教材 ID，并表达出版社、名称、版本或修订年份、学段年级、学制、册次和单元课时；ISBN SHALL 可空。未知元数据 MUST 标为未知，不得从年级或名称臆造出版年份。

#### Scenario: Legacy and revised editions
- **WHEN** 家长查看同一教材的旧版和修订版
- **THEN** 系统分别展示版本，课程记录仍以原身份归属，不自动覆盖旧版成绩

### Requirement: Independent textbook selection history
系统 SHALL 支持每个学生按学科选择教材、当前学习章节并保存选择生效历史；地区仅提供有来源的推荐，不得强制绑定出版社。停用、换书及升年级 MUST 保留原记录。

#### Scenario: Choose a different publisher
- **WHEN** 家长选择与地区推荐不同的出版社，并为另一学科选择另一出版社
- **THEN** 两个选择均被保存，重新登录后仍正确显示，原教材历史可查看

#### Scenario: No regional recommendation available
- **WHEN** 某地区没有可信的教材推荐数据
- **THEN** 系统允许从适用教材目录手动选择，并明确没有推荐依据
