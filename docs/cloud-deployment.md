# Cloud 隔离部署与恢复

状态：2026-11-02 用户完成域名解析并指定使用 Caddy，已恢复部署验证。测试入口为 https://study.lacknb.com:8443/ ，经 Cloudflare 代理；Caddy 已通过 HTTP-01 自动签发 Let's Encrypt 证书，源站证书和公网 TLS 均验证通过。现有 Xray 保留 443，原 `cstf_dev` 不用于演练。完整流程与回滚是否验收，以任务清单和交接记录为准。

## 构建和私有输入

在已安装完整资源的仓库中执行 `npm run build:cloud --workspace=china-study-free`，仅发布 `apps/web/.build/cloud/out`。构建会扫描产物；不要发布原 public、旧 out、local 产物或 source map。独立镜像入口为 `deploy/cloud/api.Dockerfile`，Python 依赖采用 `apps/api/uv.lock` 的生产集合。

把 `deploy/cloud/.env.example` 复制到实际的私有 Compose 环境文件（0600），所有路径使用绝对路径。内容导入由 owner 离线执行，读取教材目录、来源审核和数感输入；运行时仅挂载 `CSF_CONTENT_ROOT/apps/web/public` 到 `/content/apps/web/public`，不挂整个工作区、凭据或 SSH 目录。Caddy 只挂扫描后的独立发布目录。`CSF_PRIVATE_DIRECTORY` 仅存删除清单，UID/GID 10001 可写，目录 0700，不放在数据库备份卷内。

Caddy 使用独立持久卷保存证书与 ACME 账户，不手工复制私钥。`CSF_PUBLIC_HOST` 配置域名，`CSF_PUBLIC_ADDRESS` 配置域名与 HTTPS 端口（当前 study.lacknb.com:8443）。保留公网 80 供 HTTP-01 验证并重定向至 8443；TLS-ALPN 挑战关闭，避免触碰 Xray 的 443。首次获取证书需要 DNS 和 80 回源可用，客户端仍必须通过 HTTPS 访问。不绕过浏览器证书警告。相关行为见 [Caddy 自动 HTTPS](https://caddyserver.com/docs/automatic-https)。

运行环境文件至少配置：

```dotenv
CSF_DATABASE_URL=postgresql+psycopg://csf_runtime:REPLACE@postgres:5432/csf_cloud
CSF_PUBLIC_ORIGIN=https://YOUR_TEST_DOMAIN:8443
CSF_COOKIE_SECURE=true
CSF_ENVIRONMENT=isolated-test
CSF_BACKUP_RETENTION_DAYS=7
```

密码须随机生成并经 URL 编码。不要把密码放进命令行、提交文件或打印 `docker compose config` 的展开结果。迁移环境使用独立 owner 凭据文件；运行账号必须 `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION`。在 `csf_cloud` 中创建 `csf_runtime` 后，以 owner 执行 `deploy/cloud/runtime-grants.sql`，每次迁移后重新应用。运行账号可维护家庭学习数据，但不能改教材、题目版本或迁移版本表。

## 初始化和升级顺序

以下 `<compose-env>`、`<owner-api-env>` 是服务器上的私有绝对路径；不要直接复制占位符运行。始终使用独立项目名：

```sh
docker compose --env-file <compose-env> -f deploy/cloud/compose.yaml build api
docker compose --env-file <compose-env> -f deploy/cloud/compose.yaml up -d postgres
```

在 API 目录使用 owner 环境（可以通过受控的环境加载器注入，禁止 echo 密码）依次执行：

```sh
uv sync --frozen
uv run alembic upgrade head
uv run python -m app.curriculum.import_catalog
uv run python -m app.content.import_content
uv run python -m app.auth.bootstrap
```

初始化管理员仅显式命令创建；设置 `CSF_BOOTSTRAP_ADMIN_LOGIN` 与随机初始密码，首次登录强制修改。重复执行不会重设密码或提升普通账号权限。启动 Web/API 前移除运行环境中的 bootstrap 密码，并切换到受限运行账号：

```sh
docker compose --env-file <compose-env> -f deploy/cloud/compose.yaml up -d api web
```

上线时在 API 容器内检查 `/health/ready`；公网学习 API 为 `/api/v1/`。就绪检查要求数据库版本恰好等于当前代码 head。关闭公开注册是代码路由契约，不能在代理上重新接入旧版注册后端。

## 缓存迁移

首选全新的专用 cloud 域名，从一开始就没有旧 service worker/CDN 缓存。若复用 local 域名，先维护窗口下停止旧产物分发，清空 CDN 的旧 HTML/RSC、`/data/*`、媒体、`/sw.js` 与旧构建缓存，禁止旧版本回源；保留私有备份与 localStorage，不清除用户学习档案。

模板 Caddy 对旧公开题库/媒体目录返回 404，对 `/sw.js` 返回一个只清理 `ctsf-*` CacheStorage、注销自身并刷新窗口的退役脚本。仅返回 404/410 不能移除已安装 worker。cloud 布局另外在挂载学习界面前注销本站 `/sw.js` 并清理该项目缓存；不注册新的学习缓存，不缓存 API 响应。该域名的公开私有内容路径已验证 404；真实旧版离线安装迁移仍需单独复验。

## 本次服务器布局

`deploy/cloud/compose.yaml` 用于全新独立数据库。当前服务器使用 `compose.existing-postgres.yaml`，复用既有回环 PG16 服务内的新隔离库 `cstf_cloud_mac_3f7024bd`；仅为该库建立受限角色 `cstf_cloud_preview`，没有修改原开发库。API 以 UID 10001 和只读根文件系统运行，仅监听回环 18010；Caddy 监听公网 80/8443，管理 API 关闭。

服务器私有配置位于验收目录 `.deployment/compose.env` 与 `.deployment/runtime.env`，均 0600。不将实际内容打印或提交。Caddy 镜像已固定为 `caddy@sha256:36c24ad91a7ff7bc4c87fe22bfa8df3c4b18da0773d73fc12ee2c52b98c0bb7e`，API 使用本项目独立镜像标签。使用如下命令管理当前测试部署：

```sh
docker compose --env-file .deployment/compose.env -f deploy/cloud/compose.existing-postgres.yaml up -d api web
```

不可直接在 Caddy 正挂载的目录内构建。每次构建及扫描后，在同一文件系统把 out 原子移动到全新的 `.deployment/releases/<version>`，确认移动成功再更新 `CSF_CLOUD_SITE`，最后重建 Caddy 容器以切换只读挂载。若跨文件系统必须复制，完整复制与校验成功前禁止启动下次构建。保留旧目录和对应 API 镜像用于回滚，证书卷不随应用切换删除。

## 备份与恢复

备份只写到受控私有目录，在 Mac 上优先 `/Volumes/Nas`，运行前确认挂载和空间。以下命令在服务器将自定义格式转储写入当前目录，先进入已确认的备份目录并设置 `umask 077`：

```sh
docker compose --env-file <compose-env> -f <repo>/deploy/cloud/compose.yaml exec -T postgres \
  sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > family-before-upgrade.dump
```

另行保留镜像不可变标识、cloud 发布目录、迁移版本与转储校验和。删除清单持续保存在独立私有卷，不得恢复成旧副本。按实际配置的保留天数清除过期备份，导出文件不视为可直接恢复的数据库备份。

恢复必须先停 **本项目** Web/API（不停止共用 PostgreSQL 或其他服务），在新的隔离数据库恢复，不覆盖当前库：

```sh
docker compose --env-file <compose-env> -f <repo>/deploy/cloud/compose.yaml exec -T postgres \
  createdb -U csf_owner csf_restore_REPLACE_UNIQUE_ID
docker compose --env-file <compose-env> -f <repo>/deploy/cloud/compose.yaml exec -T postgres \
  pg_restore -U csf_owner -d csf_restore_REPLACE_UNIQUE_ID --exit-on-error < family-before-upgrade.dump
```

将 owner 环境指向恢复库，升级迁移并执行 `uv run python -m app.portability.replay`。检查学生删除未复活、事件/奖励/幂等收据完整、管理员保留，再配置受限运行角色。清单重放失败保持服务关闭。详见[数据迁移与删除](cloud-data-portability.md)。

## 版本回滚演练

2026-11-02 已执行前端发布 B → A → B，API 保持同一兼容镜像 r2、数据库保持 0010：46 个学习事件、7 次作答和 1 条奖励均保留，原会话可读、注册持续关闭、公开题库持续 404。已恢复最新 B。备份在全新临时数据库恢复并重放最小删除清单，通过后清理了该临时库。这不代表任意不兼容 API 镜像均可直接回滚。

保留升级前后的 cloud 发布目录与 API 镜像摘要。回滚使用**兼容当前迁移 head、仍关闭注册且保留学习写入契约**的前一构建；只切换应用和静态产物，不降级数据库、不删除已收到事件。若旧代码不兼容 head，选择前向修复，不能为让旧代码启动而盲目执行 Alembic downgrade。

后续演练同样应在两次发布之间写入合成学习事件，记录其标识、学生游标、奖励账本和收据数量；切回兼容镜像和 cloud 目录后核对原事件仍在、同键重试不重发奖、旧注册请求仍拒绝、私有题库路径仍 404，然后恢复访问。不要把模板或镜像标签存在视为任意版本回滚已通过。
