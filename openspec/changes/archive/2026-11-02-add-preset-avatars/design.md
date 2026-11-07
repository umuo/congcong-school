# Design

## Context

动机和功能范围见 proposal.md。此变更跨身份、档案、学习展示和联赛，包含新增权限路径及迁移，因此需要设计文件。

已核对的实现基础：

| 位置 | 当前行为 | 接入方式 |
| --- | --- | --- |
| `apps/api/app/students/models.py`、`schemas.py` | `Student.avatar` 字符串，四值校验；有整体 `revision` | 保留原字段与 ID，扩展为统一目录白名单 |
| `apps/api/app/auth/models.py`、`schemas.py` | User 没有头像，`/me` 修改仅限家长昵称 | 新增账号头像字段和独立的受限头像接口，不放宽 `/me` |
| `apps/api/app/auth/service.py` | `client_context()` 生成非凭据上下文标识；孩子模式隐藏家长资料 | 头像请求使用同一上下文校验，响应只返回当前有效主体 |
| `apps/api/app/learning/authorization.py` | `X-CSF-Learning-Context` 校验，身份变化返回 `LEARNING_CONTEXT_CHANGED` | 复用标识与错误语义，不把令牌或其摘要作为头像主体 ID |
| `apps/web/src/components/account/StudentForm.tsx`、`ParentDashboard.tsx` | 下拉选动物、散落 Emoji 映射 | 用共享选择器和 Canvas 展示替换 |
| `apps/web/src/components/account/AccountShell.tsx`、`app/learn/page.tsx` | 账号区和学习首页无统一头像控件 | 当前身份头像入口及有效主体展示 |
| `apps/api/app/learning/league.py`、`learning/router.py` | 行只有姓名、XP、名次和本人标记；排序前有影子同学索引 | 增加稳定行 ID 和头像字段，原计分与结算不变 |
| `apps/web/src/components/learning/CloudEconomy.tsx` | 云端模拟联赛文字列表，按 rank 作 key | 共用头像组件，按稳定 ID 作 key |
| `apps/api/app/portability/privacy.py` | 孩子字段已导出，账号关联和成员为显式白名单 | 补充非敏感账号头像，学生头像从档案读取 |

M1 仍为未归档变更，主规格为空，相关业务也有未提交工作区改动。实现以当前 M1 数据和接口为基础；不能把这些基础误认为远端 main 已包含，也不能为头像改写 M1 的任务状态。M2 全学科诊断另行计划。

## Goals / Non-Goals

**Goals:** 单一头像来源、受限的三角色修改路径、稳定联赛展示、旧数据兼容；避免头像交互影响学习请求或奖励。

**Non-Goals:** 任意上传或绘制编辑、头像付费权益、真实用户排名、替换吉祥物装扮、离线账号系统、原生 UI 重写及安卓默认站点切换。

## Decisions

### 1. 目录与绘制分离，首期 16 款

在 `apps/api/app/avatars/catalog.json` 维护版本化公开目录，由构建导出器生成 Web 可用的 ID/中文名称/目录版本数据，并检查每个 ID 都有 Canvas 绘制器。参考现有 `scripts/cloud/export-learning-policy.mts` 的跨端目录导出方式，但新导出器只处理头像，不读取题库。API 通过 `GET /api/v1/avatar-presets` 向已登录且完成首次改密的身份返回同一目录。

默认首期名单为：panda（熊猫）、fox（狐狸）、rabbit（兔子）、bear（小熊）、cat（猫咪）、dog（小狗）、tiger（老虎）、lion（狮子）、koala（考拉）、penguin（企鹅）、owl（猫头鹰）、frog（青蛙）、robot（机器人）、astronaut（宇航员）、star（星星）、planet（星球）。这属于未指定数量和题材时的设计默认值；原四个 ID 不重命名，不按姓名或角色猜测头像。所有身份共用目录，后续添加不得重新解释旧 ID。

使用几何形状和曲线绘制静态圆形头像，风格统一，不采用 emoji、外链图片或生成图片替代用户要求的 Canvas。客户端仅绘制内置函数，不接受服务端任意脚本或用户提交的绘制指令。与保存 PNG/Data URL 相比，保存 ID 不需要上传、图片存储及设备间字节同步。

### 2. 头像主体由服务器解析

- 家长/家长模式、管理员/管理员模式：`User.avatar` 与独立 `avatar_revision`。
- 独立学生、家长/孩子模式：绑定的 `Student.avatar` 与现有 `Student.revision`。
- 不为学生账号另存一份有效头像。新增 User 头像字段允许学生行为空；现有和新建学生账号均从档案解析。管理员账号列表如展示学生头像，也必须关联 Student 读取。

家长为孩子编辑头像继续使用明确学生 ID 的既有档案接口，校验统一白名单及 revision；归档档案的头像只读。账号头像初始采用 panda，不依赖昵称、密码、账号 ID 的哈希。其他业务 DTO 不为提供头像而额外公开家长身份或兄弟姐妹资料。

### 3. 受限接口与并发

新增 `GET/PUT /api/v1/me/avatar`。GET 返回 `{scope_kind, subject_id, avatar_id, revision, catalog_version}`。PUT 只接受 `{avatar_id}`，要求 `If-Match` 及当前 `X-CSF-Learning-Context`，由服务器用 `client_context()` 校验，不接受客户端指定 user、student、family、role 或额外档案字段。

接口复用认证状态、首次管理员改密、CSRF/Origin、停用与撤销检查。账号模式的写入继续要求最近验证；孩子模式验证绑定和未归档状态，但不会要求孩子提供家长密码来换自己的头像。学生仅得到头像写权限，不能因此调用完整家长资料编辑。归档/删除及角色切换与写事务正确串行。

使用条件更新原子增加对应 revision；缺失版本返回 428、无效输入 422、版本冲突 409，沿用已有冲突提示。上下文不符沿用 `LEARNING_CONTEXT_CHANGED`，不能用新 Cookie 将旧头像提交改标为新主体。失败不改变数据库，重试前读取最新版本，不自动覆盖冲突值。

独立端点优于直接放宽 `/me` 或 `PATCH /students/{id}`，可以复用 M1 权限边界并只允许更新头像。Student 的整体 revision 避免家长编辑表单用旧版本覆盖孩子刚选的头像。

### 4. 共享组件与保存体验

新增共享 `Avatar` Canvas 组件及 `AvatarPicker` 选择器，接入 AccountShell、AdminDashboard 的本人入口、ParentDashboard 本人/孩子列表和总览、StudentForm、学习首页及 CloudEconomy 榜单。选择器具有具名 radio 或等价语义、当前选中提示、预览、取消、保存、处理中/失败/冲突反馈；触摸目标至少 44 CSS px，不依赖颜色判断选择。

Canvas 按 CSS 尺寸与设备像素比设置画布，ID、尺寸或像素比变化时重绘，不持续运行动画循环。16 款在列表小图和预览大图共用绘制逻辑。SSR、无绘制上下文、未知 ID 和前后端目录短暂不同步时提供具名默认外观；不能在读取时覆写原 ID，也不能让未知选项作为有效新值提交。

读取与保存按上下文和主体 ID 隔离，卸载或切换后取消/忽略旧响应。成功后发布专用头像更新通知或只失效头像缓存，并重新读取本人行；**不调用会清空待同步学习操作的 `announceSessionChange()`**。不通过退出重登刷新头像，不修改学习投影或奖励余额。另一设备刷新后从服务端读取最新值，不要求新增 WebSocket。

### 5. 联赛追加显示字段，不改计分

云端行增加 `id` 和 `avatar_id`。本人行 ID 对应当前学生，头像读取 Student；影子同学 ID 基于排序前的稳定索引，在相同周/段位/学生联赛种子下保持稳定。头像分配使用独立命名空间和固定 v1 头像候选池，不消费或改变现有姓名/XP 生成序列，不以 rank 或数组排序后位置选头像。允许影子同学使用同款头像，不增加唯一性要求。

新目录追加款式时不重排既有 v1 候选池。保留 `simulated: true` 与说明。Avatar GET/PUT 及读取榜单均不调用经济 action、推进周结算或发奖；原显式联赛结算按钮继续执行原规则。local 的旧联赛页不引入云端身份，仅做构建和旧行为兼容检查。

### 6. 迁移、导出与删除

在当前 Alembic head 后增加迁移，保留已有 users、students、登录关联、学习记录和四种旧 ID。给现有家长/管理员填 panda 和版本 1，学生 User 行不回填另一份头像。账号创建和管理员初始化复用默认策略，不修改已有密码或会话。

学生字段已在家庭导出中；成员白名单追加其账号头像，学生账号关联如追加头像字段必须从对应 Student 派生，不泄露原始 User ORM 认证列或管理员资料。头像列跟随原账户/学生删除，无新增外部文件、头像删除队列或图片备份策略。旧导入仍遵循既有摘要语义，不覆盖云端当前头像或凭头像导入发奖。

## Risks / Trade-offs

- [学生档案与账号双头像] → 子模式一律以 Student 为准，覆盖独立登录、代入和管理员学生列表的契约测试。
- [旧请求作用到新主体] → 当前上下文与条件更新同时验证；前端取消/忽略迟到响应，不改写请求主体。
- [头像保存误清学习队列] → 专用头像通知；加入存在待提交作答时换头像的回归。
- [新增 ID 与旧四值 API 不兼容] → 先部署扩展读取和校验能力，再启用新选择器；不能把旧四值 API 当成可直接回滚目标。
- [Canvas 模糊或无可访问文本] → 1/2/3 倍像素密度与 390px/桌面截图检查，具名控件及禁用绘制降级检查。
- [排行榜排序后头像漂移或奖励改变] → 稳定行 ID、独立头像分配序列；复用 `test_league.py` 及黄金向量比较去除新增字段后的原结果。

## Migration Plan

1. 在独立临时库验证当前迁移 head、升级及迁移往返，再对隔离部署备份；不操作原 `cstf_dev` 数据库。新迁移不能与后续 M2 产生未处理的并行 head。
2. 先发布兼容 API、迁移、目录与明确的 runtime 新列权限，再发布头像目录导出和 Web 组件；旧四种头像全程可读取。
3. 用两个家庭、三角色和家长代入验证保存、冲突、排名与跨设备读取；对比学习事件、待同步操作及奖励不变。
4. 回滚仅选择仍能读取新 ID 的兼容 API/前端；必要时暂时关闭头像写入并保留数据。数据库破坏性降级仅用于临时库测试；生产降级须另行制定备份恢复方案，禁止静默把新头像全部改回旧值。
5. 保留 M1 的录音未验收状态和 M2 全学科诊断选择。本变更的完成不代表实体 iOS/Android 头像展示已经验证，未验证设备必须在交付说明标记。
