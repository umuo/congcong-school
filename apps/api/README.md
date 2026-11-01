# 家庭学习 API

模块化单体后端，使用 Python 3.12、FastAPI、SQLAlchemy、Alembic 与 PostgreSQL 16。当前已提供三角色认证、学生与教材、私有内容、服务端学习会话、逐次作答、奖励账本和事件重建；儿童云端前端、导入导出删除和完整部署仍按 OpenSpec 任务接入。

私有题库导入、稳定身份与不可变版本、内容读取契约见 [云端内容服务](../../docs/cloud-content-service.md)，跨语言判分规则见 [判分规则](../../docs/cloud-grading-rules.md)。

## 本地启动

在本目录执行：

```sh
uv sync --frozen
cp .env.example .env
# 修改 .env 的 CSF_DATABASE_URL，填写实际数据库密码。
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

访问 `/health/live` 检查 API 存活，`/health/ready` 检查数据库连接与迁移版本。数据库不可用时返回 503、业务错误码与 request_id，不返回连接凭据。应用启动不自动迁移数据库。

依赖由 `uv.lock` 固定，更新时重新执行兼容检查。生产启动不启用 reload；部署时通过同源 HTTPS 代理访问 API。

## 独立 PostgreSQL

本目录的 Compose 是独立开发环境，不与仓库根目录的原 Web Compose 合并。启动前设置随机 `CSF_POSTGRES_PASSWORD`，然后执行：

```sh
docker compose -p congcong-family up -d --wait
```

密码通过环境或本地 `.env` 提供，禁止写入受版本控制文件。此开发容器的初始化用户用于创建测试数据库；生产环境应单独设置迁移角色与受限运行角色，不能沿用开发管理账号。

远端部署同一配置后，本地通过隧道访问：

```sh
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:15432:127.0.0.1:15432 <user>@<host>
```

数据库只绑定服务器回环地址，不开放公网端口。项目使用独立数据卷；`docker compose down` 保留卷，除非明确需要删除测试数据，不使用 `down -v`。远端的真实地址和密码只存本地配置，不写入公开文档。

## 配置

| 参数 | 语义 | 默认值与空值 |
| --- | --- | --- |
| `CSF_DATABASE_URL` | SQLAlchemy PostgreSQL URL，驱动必须为 `postgresql+psycopg` | 必填；空值或其他数据库驱动报错 |
| `CSF_ENVIRONMENT` | 环境标签 | `development` |
| `CSF_PUBLIC_ORIGIN` | 浏览器写入请求允许的精确 Origin，不含尾部斜杠 | `http://localhost:3000` |
| `CSF_BOOTSTRAP_ADMIN_LOGIN` | 显式初始化管理员的登录名 | 无默认值；初始化时必填，普通启动可空 |
| `CSF_BOOTSTRAP_ADMIN_PASSWORD` | 显式初始化管理员的初始密码 | 无默认值；12–128 字符，首次必须修改，不覆盖已有管理员 |
| `CSF_COOKIE_SECURE` | 会话 Cookie 仅通过 HTTPS 发送 | `true`；仅本机 HTTP 测试可设 `false` |
| `CSF_SESSION_LIFETIME_SECONDS` | 数据库会话有效期，单位秒 | `604800`，至少 60 秒 |
| `CSF_PARENT_VERIFICATION_SECONDS` | 敏感操作最近密码验证窗口，单位秒 | `300`，至少 1 秒 |
| `CSF_AUTH_RATE_LIMIT` | 每 IP+账号每窗口认证次数；同 IP 总上限为 5 倍 | `10`，至少 1 次 |
| `CSF_AUTH_RATE_WINDOW_SECONDS` | 认证限流窗口，单位秒 | `300`，至少 1 秒 |
| `CSF_POSTGRES_PASSWORD` | Compose 初始化数据库密码 | 必填；禁止留空，仅在容器初次初始化时生效 |
| `CSF_POSTGRES_PORT` | Compose 本机回环端口 | `15432`，单位为 TCP 端口号 |
| `CSF_TEST_ADMIN_DATABASE_URL` | 集成测试管理连接，仅创建和删除 `cstf_test_<随机值>` 数据库 | 不设置时跳过 PostgreSQL 集成测试，跳过不等于验收通过 |

`CSF_DATABASE_URL` 从进程环境或本目录 `.env` 读取，环境变量优先。数据库密码包含 URL 特殊字符时必须百分号编码。不要把连接 URL 粘贴到日志或提交记录中。

## 验证

```sh
uv run ruff check .
uv run pytest
```

PostgreSQL 集成测试需要设置 `CSF_TEST_ADMIN_DATABASE_URL`，使用新建的独立临时数据库，验证空库升级、模型一致性、降级、再次升级与数据库就绪状态，不清空管理 URL 指向的数据库。迁移的 upgrade/downgrade 手工命令只对自己创建的开发或测试数据库执行。

直接与传递依赖的许可登记见 `dependency-licenses.json`；该文件只登记依赖包元数据，不构成教材内容或第三方素材的授权证明。

## 统一登录与管理员建号

公开注册已关闭，`POST /api/v1/auth/register` 固定拒绝且不产生任何账号或家庭。家长和学生账号由最近验证密码的管理员通过专用接口创建；不能通过客户端提交角色或库的通用用户端点提权。

先在本地 `.env` 填写 `CSF_BOOTSTRAP_ADMIN_LOGIN`、`CSF_BOOTSTRAP_ADMIN_PASSWORD`，然后显式执行：

```sh
uv run alembic upgrade head
uv run python -m app.auth.bootstrap
```

无内置默认密码，初始密码为 12–128 字符。初始化使用数据库事务锁；仅首次创建管理员，重复或并发运行不改密、不提升既有普通账号、不复活停用账号。账号重名或配置缺失明确失败。API 普通启动不自动建管理员。只有初始管理员必须先修改初始密码，只可查询最小会话、修改密码及退出；普通家长/学生首次和重置后均直接进入获准业务。迁移 0006 解除已有普通账号的旧改密标记，保留密码哈希、账号状态与管理员标记。

| 接口（前缀 `/api/v1`） | 行为 |
| --- | --- |
| POST `/auth/login` | JSON login、password；兼容旧家长 email 字段，按真实角色/模式返回 destination，不接受角色字段 |
| GET `/auth/session` | 最小身份与改密状态；管理员 `/admin`、家长 `/parent`、学习模式 `/learn`、初始改密 `/change-password` |
| POST `/auth/change-password` | 当前 password 和 new_password，密码不能与原值相同；撤销旧会话并轮换 Cookie |
| POST `/auth/logout` | 撤销当前会话、清 Cookie；204；初始改密前也可退出 |
| POST `/auth/reauth` | 校验当前管理员或家长密码并轮换会话；学生不能升级权限 |
| GET/PATCH `/me`、GET `/family` | 家长本人昵称和家庭资料，修改要求最近验证；孩子模式禁止访问 |
| POST `/mode/child`、`/mode/parent` | 家长代入指定学生或校验原家长密码恢复；独立学生不可恢复为家长 |
| GET `/learning/profile`、`/learning/curriculum` | 学习模式读取当前学生最小资料及当前启用教材配置，排除家长备注和选书历史 |
| GET/POST `/admin/parents` | 管理员列出或创建家长；新家庭创建 owner，关联已有家庭创建 guardian，不替换 owner |
| GET/POST `/admin/students` | 管理员列出或创建独立学生账号，明确 family_id，并选择 student_id 或 profile 新档案 |
| GET `/admin/login-availability?login_name=...` | 最近验证的管理员查询归一后的账号是否可用，跨角色和停用账号统一查重；普通用户及未登录用户不可访问 |
| GET `/admin/families`、`/admin/student-profiles?family_id=...` | 管理员建号所需的最小关联目录，不提供学习明细 |
| POST `/admin/users/{id}/disable` | 停用普通账号、撤销其全部会话；保留档案和学习历史，不可停用管理员 |
| POST `/admin/users/{id}/reset-password` | JSON password，设置新密码并撤销全部旧会话；普通用户下次直接登录，不强制改密 |

管理员建号的共同字段为 login_name、password、nickname、可选 email。家长选择 family_name 新建家庭或 family_id 关联已有家庭，二者必须选一个；学生选择 family_id，并在 student_id 与 profile 中二选一。用户名去除两端空白并 casefold，3–320 个字母、数字或 `._@+-`，无空格；学生无需邮箱，不生成假邮箱。完整字段可查看 `/openapi.json`。

所有写接口都校验 Origin，已认证写接口还要求 `X-CSF-CSRF` 与登录发放的 `csf_csrf` Cookie 一致；主 Cookie `csf_session` 为 HttpOnly、SameSite=Lax、默认 Secure，数据库只存令牌及 CSRF 的 SHA-256 摘要。FastAPI Users 的 Argon2/密码升级和数据库令牌策略继续复用，应用适配层替换按登录名查找并支持可选邮箱。不能把继承模型中的 is_superuser 当作业务角色。

错误统一为 `{code, message, request_id}`；校验错误只给字段位置及类型，不回显输入密码。主要错误码为 `REGISTRATION_CLOSED`、`INVALID_CREDENTIALS`、`AUTH_REQUIRED`、`PASSWORD_CHANGE_REQUIRED`、`ADMIN_REQUIRED`、`PARENT_REQUIRED`、`PARENT_REAUTH_REQUIRED`、`CSRF_REJECTED`、`ORIGIN_REJECTED`、`ACCOUNT_CONFLICT` 和 `AUTH_RATE_LIMITED`。未知账号、错误密码与停用登录返回一致的认证错误。

限流状态存 PostgreSQL，多个 worker 共享；不信任任意客户端 X-Forwarded-For。代理部署时只允许受信任代理解析来源，不能允许公网伪造转发头。停用和重置与写请求通过账号行锁串行；旧会话撤销后不能继续写入。

角色升级迁移保留旧家长及其家庭/学生 ID、原邮箱登录与密码哈希，同时撤销旧会话。存在新管理员或学生账号时，数据库不能无损降级到仅家长模型，迁移会明确阻止；部署回滚应使用兼容角色模型的 API 版本，不能重新开放公开注册。空库及仅旧家长数据的迁移往返在临时库测试。

## 学生档案和模式边界

`GET/POST /api/v1/students` 列出或创建本家庭学生；`GET/PATCH /api/v1/students/{id}` 查看或修改，`POST /api/v1/students/{id}/archive` 归档。以上接口都要求家长模式及最近密码验证，所有写入还需要 CSRF。`include_archived=true` 可查看归档档案；归档保留资料，不删除成绩。学习记录接入属于后续任务，目前不伪造或推导新学习记录。

学生有稳定 UUID、昵称、预置头像、可选出生年月/学校/家长备注、地区、学段年级、学年学期及每日时长目标；响应不公开 family_id，归属由服务端的成员关系确定，客户端提交 family_id 等额外字段会被拒绝。默认省市为空，不强迫收集学校、生日等信息。年级 1–12，时长目标 1–240 分钟，预置头像为 panda/fox/rabbit/bear，出生年月格式 YYYY-MM，学年格式为连续两年。

PATCH 与归档使用 `If-Match: <revision>`：缺失为 428 `REVISION_REQUIRED`，非法为 422 `INVALID_REVISION`，陈旧版本为 409 `REVISION_CONFLICT`。成功修改后 revision 增加；PATCH 未提供字段保持原值，可选字段可显式设 null 清空。跨家庭与不存在的学生统一返回 404 `STUDENT_NOT_FOUND`，不会透露外部资源是否存在。

进入孩子模式会在数据库中降低当前会话权限，共享 Cookie 的标签页一起受限；其他设备的独立会话保持不变。孩子模式不能读取 `/me`、`/family` 或学生管理接口，不能仅通过前端导航切换成家长。再次输入正确家长密码后才恢复权限并轮换令牌；验证窗口默认 5 分钟、会话默认 7 天。归档学生不能再进入学习模式，已有孩子模式访问学习入口也会被拒绝。统一登录、管理员和家长管理页面已接入；云端课程及权威学习记录继续按后续任务实施。

2026-11-01：学生权限与迁移组合检查通过 5 项测试，包含两家庭、每家两孩子的双向越权读写，伪造 family_id、资源枚举保护、数据库复合外键、修订冲突、字段校验和归档保留。

孩子模式独立集成测试也已通过，验证服务端降权、共享 Cookie、混合凭据不可提权、独立设备不受影响、归档拒学、错误密码不恢复权限、正确密码恢复并轮换令牌、过期验证窗口和旧令牌重放。

## 当前验证记录

以下早期认证记录针对原方案，不能代表三角色功能已完成；三角色当前测试与浏览器验收证据按后续段落登记。

2026-11-01：专用远端 Docker PostgreSQL 已安装，容器 `congcong-family-postgres`，数据在独立持久卷 `congcong-family_family-postgres`，服务端仅监听 `127.0.0.1:15432`。密码使用随机值，服务器配置文件权限为 0600。本地通过 SSH 转发连接，未开放数据库公网访问。该环境用于开发和临时集成测试，不代表生产部署已验收；当前方案不需要 Redis 或消息队列。

2026-11-01：已在项目专用 Docker PostgreSQL 16.15 上通过 3 项后端基础测试，包含空库迁移往返及健康状态变化；认证部分另通过 3 项集成测试，覆盖注册、并发重复注册、家庭创建失败回滚、会话过期、限流、CSRF、资料修改和退出重放。临时数据库结束后自动删除。镜像在 Compose 中按摘要固定。运行依赖和开发工具均由锁文件固定，许可清单包含 50 个包，通过 `pip-licenses --with-system --with-urls --format=json` 生成；其中包括 Psycopg 的 LGPL-3.0-only 与 cryptography 的 Apache/BSD 许可，分发时需保留对应许可材料，不能统一标记为 MIT。

## 学科与教材配置

先执行迁移，再从已有生成目录导入元数据：

```sh
uv run alembic upgrade head
uv run python -m app.curriculum.import_catalog
```

导入读取仓库原索引、教材目录和已核对的版次记录，保留全部 84 册教材 ID 与四个初始学科。重复执行按 ID 更新目录，不重复创建教材，不改写已保存的选书历史快照。原版、新版、五四制与六三制保持各自身份；缺乏来源的出版年份、ISBN 保持空值。目录包含章节标题与引用，不导入题目答案。`CSF_CONTENT_ROOT` 可覆盖内容仓库根目录，默认自动定位本仓库；独立部署时需指向含 `scripts/quiz/`、`data/` 和 `apps/web/public/data/` 的资源目录。

| 接口 | 行为 |
| --- | --- |
| GET `/api/v1/subjects` | 已登录用户读取学科目录，学生配置不限制为固定四科枚举 |
| GET `/api/v1/textbooks` | 按 subject_code、grade、publisher_label 筛选；当前没有已验证的地区推荐，返回空 recommendations 和明确原因，仍可手选 |
| GET `/api/v1/students/{id}/curriculum` | 最近验证的家长读取当前学科配置及教材历史 |
| PUT `/api/v1/students/{id}/curriculum` | 最近验证的家长按 subjects 数组修改所列学科，带 CSRF 与 `If-Match`；未列出的学科保持原状 |

学科配置项包含 subject_code、enabled、book_id、current_unit_number。未提供 book_id 或设为 null 时保留已选教材；换书或调整当前章节会结束旧选择并生成新快照，停用保留选择历史。教材必须属于对应学科，章节必须存在。学生资料与教材配置共用 revision，并发陈旧写入返回 409，归档学生拒绝更新。升年级不自动换书，也不改动历史。

2026-11-01：教材目录结构测试通过，另在 PostgreSQL 上通过教材配置集成测试和三项迁移基础测试，覆盖重复导入、84 个 ID、26 册五四制来源、动态增加学科、不同孩子配置隔离、无地区推荐手选、非法请求整笔回滚、换书快照、并发冲突、停用和升年级保留历史、归档拒写。结构测试按 JSON 字段检查无答案与解析，避免把英语课名中的普通单词误判为敏感字段。


## 三角色实现验收

2026-11-01：当前 14 项 API/数据库测试已分批通过。首次全套 12 项通过后，针对写入串行、初始化缺失配置及重名、旧家长角色迁移、既有教材历史关联、学生删除后身份撤销执行了对应专项回归，均通过。覆盖空库迁移往返、旧家长升级/降级/再升级及模型比较、并发初始化与重复建号、事务回滚、首次改密、Cookie/CSRF、失败限流、同家庭兄弟姐妹及跨家庭范围、学生本人密码不能提权、归档拒登拒学、账号停用重置撤销以及删除后另一学生不受影响。测试仅操作自动创建并清理的临时数据库。

已使用桌面 1440px 与移动 390px 浏览器，验证旧版首次改密策略、建号、为已有学生开通登录、家长创建/编辑/归档两个孩子、按学科手工选书、重置、越权页面跳转及停用后旧页面退出，无页面脚本错误或横向溢出。截图与结果在 Git 忽略的 `deploy-output/family-accounts/`；测试账号与临时库已删除。前端类型检查与原有 Web 体验检查通过。未将浏览器模拟等同于实体手机验收，未宣称本轮完成云端课程、学习摘要或生产部署。

FastAPI Users 15.0.5 的源码核对结论：默认 `authenticate` 按邮箱查找，默认 ORM email 非空；DatabaseStrategy 按 user ID 读取令牌并不要求邮箱。应用覆写 ORM 的 email 可空性及 UserManager.authenticate 的查找部分，沿用 PasswordHelper 的 Argon2、校验升级、DatabaseStrategy 的随机令牌/到期语义及 SQLAlchemy 查询适配；公开契约使用应用自身 Pydantic 模型，避免使用必填邮箱的库注册模型。无邮箱学生的真实登录及改密、撤销流程已通过集成测试，未生成假邮箱或引入另一套认证框架。

## 普通账号密码策略与表单校验更新

2026-11-01：根据最新需求，普通家长和学生在新建及密码重置后均直接登录，不再强制改密；仅初始管理员保留首次改密要求。`0006_regular_password_policy` 解除已有普通账号的旧标记，不修改密码、账号启用状态或家庭关系。重置密码仍撤销全部旧会话；降级不会猜测并重建历史改密标记。

新增管理员专用账号可用性查询，按与建号相同的 trim/casefold 规则检查所有角色及停用账号，不返回账号详情；公开登录不提供此查询。前端短暂防抖后查重，取消旧请求并比较输入版本；校验失败可重试。数据库唯一约束和保存时检查仍是最终依据。

创建、重置及管理员改密共用前端密码确认，输入或修改时即时核对，不一致时原生表单校验及提交函数均阻止写请求；确认字段不会传给服务端，保存后清空两处输入。6 项受影响的管理员/学生、账号查重权限和迁移集成测试通过；独立浏览器站点完成 13 项检查，验证初始管理员仍需改密、普通首次/重置直接登录、三处确认不一致不发写请求、跨角色重名、大小写归一、延迟响应隔离、表单清空及重置旧会话撤销，无页面脚本错误。证据见 Git 忽略的 `deploy-output/family-accounts/password-validation-result.json` 与手机截图。前述旧规则验收记录保留为历史，以本段最新策略为准。

学习奖励与操作约束见 [奖励账本](../../docs/cloud-learning-rewards.md)，阅读/数感/申报用时及汇总重建见 [学习事件](../../docs/cloud-learning-events.md)。跨电脑继续开发前先读 [交接记录](../../docs/family-learning-handoff.md)。
