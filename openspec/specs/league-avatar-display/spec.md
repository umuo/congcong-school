# league-avatar-display Specification

## Purpose

在现有模拟联赛中展示本人选择的头像以及影子同学的稳定内置头像，使用户能在排名和个人学习档案之间辨认同一身份，并确保头像展示不会改变名次计算、周结算、奖励或家庭数据隔离。

## Requirements

### Requirement: Current student avatar in standings
模拟联赛本人行 SHALL 展示当前学习孩子服务端已保存的头像。独立学生与家长代入同一孩子时 SHALL 取得相同头像；本人行 MUST 不使用家长账号头像、另一孩子缓存或固定的“我”字圆片替代有效头像选择。

#### Scenario: Change the current student avatar
- **WHEN** 孩子保存新头像并重新读取联赛
- **THEN** 本人行显示新头像，与学习首页和家长查看的该孩子档案一致

#### Scenario: Parent impersonates a child
- **WHEN** 家长代入孩子查看其联赛
- **THEN** 本人行使用孩子头像，家长自己的头像保持不变

### Requirement: Stable simulated participant avatars
每位影子同学 SHALL 有稳定行身份和有效内置头像 ID。相同学生、联赛周期与段位下，同一影子同学的头像 MUST 不随名次、XP、读取顺序、刷新或设备变化而改变。行身份 MUST 不以当前名次代替。

#### Scenario: Participants exchange positions
- **WHEN** 两位影子同学 XP 变化后交换名次
- **THEN** 各自头像仍与原同学对应，用户不会看到头像随排序位置互换

#### Scenario: Refresh on another device
- **WHEN** 同一孩子在同一联赛周期和段位刷新另一设备
- **THEN** 相同影子同学继续显示相同头像，不依赖客户端随机数或本机存储

### Requirement: Shared rendering with readable standings
联赛 SHALL 使用与头像库一致的 Canvas 外观；头像与名次、姓名、XP 并列呈现，缺失或未知头像使用默认外观。头像 MUST 不遮挡信息，页面在 390px 视口可用；屏幕阅读器 SHALL 能理解行身份和排名，不依赖头像颜色传递唯一信息。

#### Scenario: Narrow layout and unknown avatar
- **WHEN** 390px 页面出现长名字或暂不支持的头像 ID
- **THEN** 头像保持合理尺寸，名次和 XP 可读取，页面不产生由头像引起的横向溢出，未知头像不使整张榜单失败

### Requirement: Preserve simulated league semantics
头像展示 MUST 保留模拟联赛提示、原解锁门槛、XP、排序、段位及奖励规则，不新增真实跨家庭排名。读取或修改头像 MUST 不领取联赛奖励、不修改周结算状态或暴露其他真实用户资料。

#### Scenario: Compare the same league before and after avatar support
- **WHEN** 相同原状态和业务时间生成支持头像的榜单并执行周结算
- **THEN** 原名称、XP、名次、段位变化及奖励与既有规则一致，仅增加身份和头像展示字段

#### Scenario: Refresh only the avatar display
- **WHEN** 本人保存头像后刷新榜单
- **THEN** 不因此改变 XP 或重复领取奖励，也不返回其他家庭的头像和身份记录
