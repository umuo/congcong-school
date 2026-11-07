# Spec Delta

## Purpose

提供适用于孩子、家长和管理员的内置 Canvas 头像及统一选择体验，让账号、孩子档案与学习页面在刷新和设备切换后保持同一身份展示，同时维护学生范围隔离、旧头像兼容和未同步学习数据的完整性。

## ADDED Requirements

### Requirement: Built-in avatar catalog
系统 SHALL 提供包含稳定 ID、中文名称和目录版本的内置头像目录，首期包含 16 款。已有 `panda`、`fox`、`rabbit`、`bear` ID MUST 保持有效。所有身份 SHALL 可选择目录中相同的头像，不要求购买或上传图片。

#### Scenario: Open the preset library
- **WHEN** 已登录用户打开头像选择面板
- **THEN** 显示 16 款具名预览并标识当前选择，包含原有四种动物

#### Scenario: Reject an unknown selection
- **WHEN** 客户端提交未知 ID、图片 URL、Data URL 或超长值
- **THEN** 服务端拒绝保存且原头像不变，不请求该值指向的外部资源

### Requirement: Canvas rendering and fallback
系统 SHALL 使用 Canvas 绘制内置头像，同一 ID 在资料、学习及选择器中保持相同设计，并在不同像素密度下清晰显示。头像 MUST 有可访问名称或等价的相邻文本。绘制不可用或遇到未知旧 ID 时 SHALL 提供默认外观，不阻断页面或覆盖原值。

#### Scenario: Show a saved avatar at different sizes
- **WHEN** 同一头像分别显示在小尺寸列表及大尺寸预览中
- **THEN** 图案和颜色一致、比例正常，移动端高像素密度下不因固定低分辨率而模糊

#### Scenario: Drawing is unavailable
- **WHEN** Canvas 上下文不可用，或客户端暂不认识服务端保存的头像 ID
- **THEN** 页面显示具名默认外观并继续可用，读取及打开选择器本身不改写服务端头像

### Requirement: Effective profile ownership
系统 MUST 根据服务端当前身份和模式解析头像主体。家长/家长模式及管理员/管理员模式使用本人账号头像；独立学生和家长代入模式使用绑定孩子的档案头像。学生登录、家长档案及排名 SHALL 读取同一孩子头像，不维护另一份学生账号头像。

#### Scenario: Parent enters child mode
- **WHEN** 家长拥有自己的头像并代入孩子 A
- **THEN** 学习区显示 A 的头像，恢复家长模式后显示家长头像，两个保存值不互相覆盖

#### Scenario: Student and parent inspect the same child
- **WHEN** 学生修改自己的头像，家长随后刷新该孩子档案
- **THEN** 双方显示相同头像，学生 ID、账号绑定及学习记录保持不变

### Requirement: Authorized avatar updates
孩子、家长和管理员 SHALL 能更新当前头像主体。家长 SHALL 能通过本家庭档案编辑为未归档孩子设置头像。头像修改 MUST 校验身份、模式、当前上下文、账号状态、学生归属及写请求来源；学生不得借此编辑家庭、兄弟姐妹或其他资料。

#### Scenario: Restricted student update
- **WHEN** 学生或家长孩子模式提交自己的有效头像选择
- **THEN** 只更新当前孩子头像和资料版本，不修改昵称、备注、角色、绑定或其他孩子

#### Scenario: Reject a foreign or stale context
- **WHEN** 用户尝试指定其他主体、跨家庭写入，或旧页面在身份切换后提交头像
- **THEN** 请求被拒绝，任何新旧主体的头像均不因该请求改变

#### Scenario: Unavailable account or archived child
- **WHEN** 停用或会话撤销的账号、已归档或已删除孩子发起头像更新
- **THEN** 更新失败，不恢复账号、档案或原会话权限

#### Scenario: Initial administrator password restriction
- **WHEN** 尚未完成首次改密的管理员尝试修改头像
- **THEN** 仍受首次改密限制，头像接口不能绕过该限制

### Requirement: Preview save and concurrent edits
选择面板 SHALL 支持预览、取消和显式保存，并可通过触摸及键盘操作。保存 MUST 使用读取时的版本；陈旧版本 SHALL 返回冲突而不覆盖新值。只有服务端成功确认后，页面才 SHALL 表示保存成功；失败保留可重试状态，不错误切换其他主体。

#### Scenario: Cancel a preview
- **WHEN** 用户预览其他头像后取消或关闭面板
- **THEN** 服务端和所有已保存展示仍保留原头像

#### Scenario: Two devices edit one profile
- **WHEN** 两个设备读取同一版本，设备一保存后设备二用旧版本保存
- **THEN** 设备二得到冲突提示并可读取最新头像，不静默覆盖设备一

#### Scenario: Response arrives after account switching
- **WHEN** A 的读取或保存响应迟到，而界面已切换到 B
- **THEN** A 的响应不会更新 B 的头像或成功提示，也不会将 A 的选择重新提交给 B

### Requirement: Consistent profile display and learning isolation
账号区、家长孩子列表与总览、学习首页 SHALL 显示对应主体的服务端已保存头像；刷新和重新登录 SHALL 保留选择。换头像 MUST 不清空待同步作答、改变学习会话或影响 XP、宝石、装扮权益及奖励账本。

#### Scenario: Update while learning has pending writes
- **WHEN** 孩子存在未同步学习操作并保存头像
- **THEN** 头像保存不清理或重新归属这些操作，其原幂等键和学生范围保持不变

#### Scenario: Reload another device
- **WHEN** 用户保存头像后在另一设备刷新对应账号或孩子页面
- **THEN** 显示最新已保存头像，不显示其他家庭或孩子的缓存头像

### Requirement: Avatar compatibility and portability
升级 SHALL 为现有家长和管理员提供有效默认头像并保留原孩子头像。家庭导出 SHALL 包含本家庭的非敏感头像 ID；学生账号关联中的头像 SHALL 与对应孩子一致，不导出认证秘密、管理员头像或其他家庭数据。删除账号或孩子 SHALL 一并清理其头像归属。

#### Scenario: Upgrade and export an existing family
- **WHEN** 既有四种动物头像的家庭升级并导出数据
- **THEN** 原孩子选择保持有效，家庭成员与孩子头像可追溯，导出不包含密码、令牌或其他家庭身份

#### Scenario: Delete a child with a student login
- **WHEN** 家长删除孩子及关联登录账号
- **THEN** 不遗留可继续读写该孩子头像的绑定或缓存权限，其他孩子及家长头像保留
