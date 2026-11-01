# 家庭学习系统跨电脑交接

更新时间：2026-11-01。分支：`codex/family-learning-platform`。当前按用户要求在完成本阶段测试后暂停，提交代码和文档供另一台电脑继续；没有归档 OpenSpec 变更，也没有宣称 M1 全部完成。

## 当前进度与下一步

变更为 `add-family-cloud-learning`，spec-driven，**21/32 完成，11 项未完成**。任务状态以 `openspec/changes/add-family-cloud-learning/tasks.md` 及 CLI 为准。继续时先执行：

```sh
openspec instructions apply --change add-family-cloud-learning --json
```

项目已附带 `.agents/skills/openspec-*` 技能。没有同版本 CLI 时可安装已验证的版本：

```sh
npm install -g @fission-ai/openspec@1.16.0
```

推荐从 **5.4 LearningClient 与学生上下文** 开始，再连接儿童页面。剩余任务：

| 任务 | 尚需完成 |
| --- | --- |
| 2.3 | 将学习、导入导出删除的最终授权范围一起验收；不能凭已有账号权限测试提前勾选 |
| 3.3 | 家庭首页的真实学习总览与最终家庭设置/角色流程浏览器验收；已有档案和教材管理 UI 可复用 |
| 5.4 | local/cloud LearningClient、学生上下文、投影缓存、UI 状态、取消旧响应、退出清理、待提交权限检查 |
| 5.5 | 普通课和复习接入服务端题目、判分、回炉、检查点、离线提示和原键重试 |
| 5.6 | 挑战、跳级、故事、听读、数感、商店和其他旧入口；逐项核对联赛奖励、题目报错等写入口 |
| 6.1–6.3 | 本地档案预览导入、家庭导出、学生/家庭删除及恢复后的删除清单重放 |
| 7.1–7.3 | HTTPS 部署、完整两家庭/两设备验收、最终全套验证及交付 |

用户指定后续部署域名为 **`study.lacknb.com`**。尚未部署 Web/API 到该域名，也未验证 DNS、HTTPS、代理或生产回滚。

## 已完成的主要能力

- 三角色统一登录，关闭公开注册；配置驱动初始化管理员，管理员首次必须改密。
- 管理员创建、关联、停用和重置家长/学生账号；普通家长/学生首次与重置后均不强制改密。
- 建号账号即时查重，创建/重置/改密共用密码确认；停用/重置撤销旧会话。
- 家庭学生档案、归档、家长代入、独立学生登录、教材目录及选书历史。
- 私有题库、稳定题目身份与不可变版本；84 册完整导入验证通过。
- `cstf-grading-2`：修复分数及数字前缀误判，TS/Python 共用向量，不重判历史成绩。
- 授权学习会话、固定题目版本、服务端判分、逐次作答、反馈/草稿/队列恢复、学生变化游标。
- 事务奖励账本、唯一领取记录、课程结算、红心、SRS、宝箱、每日奖励、成就、任务和商店操作。
- 听读/跟读/故事完成、数感提示与隔天证据、申报用时检查点、重叠区间去重及事件重建。
- local/cloud 独立构建与扫描；云端产物不包含原公开题库、音频索引和解释媒体。

**当前浏览器的云端学习页仍是接入提示。** 后端能力不等于儿童前端已经连接。原 local 学习流程仍可运行。

为 5.4 只提前准备了账号响应 `context_id` 和 `X-CSF-Learning-Context` 校验：它们是非凭据的缓存范围约束，旧登录上下文不能继续发送待提交请求。前端 LearningClient、缓存及待提交队列尚未实现，5.4 保持未勾选。

## 另一台电脑准备

```sh
git clone --branch codex/family-learning-platform git@github.com:umuo/congcong-school.git
cd congcong-school
npm ci
```

使用 Node.js 22、Python 3.12 和 uv。Git 不包含下列本机内容：`.env`、虚拟环境、完整教材/音频/图片、私有数感导出、构建目录、测试截图及报告。数据库与管理员凭据通过安全渠道另行配置，不从 Git 恢复。

本机已安装 `v1.8.2` 全部资源：22 个分包，约 23.2 GB，逐包 SHA-256 和最终 546,399 文件核对通过。另一台电脑需要重新安装，或安全复制并校验资源：

```sh
python3 scripts/install-release.py --tag v1.8.2
python3 scripts/install-release.py --tag v1.8.2 --verify-only
```

不要加 `--with-source`，该选项会替换开发源码。准备/更新生成数据时执行 `npm run build:data --workspace=china-study-free`；音频转换需要可用的 FFmpeg。本机曾因 Homebrew 动态库损坏使用临时独立 FFmpeg，新电脑不能依赖本机临时可执行文件。

在仓库根目录生成被忽略的私有数感输入：

```sh
node --import tsx scripts/cloud/export-number-review.mts
```

然后按 `apps/api/.env.example` 创建自己的 `apps/api/.env`。使用已有专用 PostgreSQL 时，服务器地址、SSH 密钥和密码另行配置；连接应经回环 SSH 隧道，不开放数据库公网端口：

```sh
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:15432:127.0.0.1:15432 <user>@<middleware-host>
```

本机退出前只读确认：共享开发库仍为 **`0006_regular_password_policy`**；代码最新迁移为 **`0009_economy`**。0007–0009 已在临时库升级/降级/再升级和模型一致性检查通过，尚未应用到共享开发库。本机 8000 端口旧 API 进程也未重启到最新学习后端。继续开发时确认目标数据库并升级，再启动新 API：

```sh
cd apps/api
uv sync --frozen
uv run alembic upgrade head
uv run python -m app.curriculum.import_catalog
uv run python -m app.content.import_content
# 仅在管理员尚不存在、且本地配置已填好时显式初始化；重复执行不会改密。
uv run python -m app.auth.bootstrap
CSF_COOKIE_SECURE=false CSF_PUBLIC_ORIGIN=http://localhost:3010 \
  uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

另一个终端从仓库根目录启动：

```sh
npm run dev -- --hostname 127.0.0.1 --port 3010
```

浏览器使用 `http://localhost:3010/`，Origin 必须与 API 配置一致。正式 HTTPS 必须恢复 `CSF_COOKIE_SECURE=true`。

## 验证结果与复验

本阶段分组共 25 项后端/领域检查通过，覆盖私有内容后的学习、奖励、活动、数感、基础迁移及认证上下文；最后补测了任务/宝箱并发领取和认证上下文变化。没有把未设置数据库而跳过的集成测试算作通过。

- core 全套：315 项、15 个测试文件通过。
- Web/core 类型检查通过，API Ruff 检查通过，OpenSpec strict 校验通过。
- 真实 PostgreSQL 临时库中：并发首次奖励、原键重试、每日目标、购物余额、红心、SRS、任务/宝箱、事件重建、数感提示与到期检验、登录上下文，以及迁移往返通过。
- 内容完整导入：6,678 个内容容器、35,240 个题目身份、35,246 个题目版本，未映射文件为空。
- cloud/local 生产构建通过；cloud 扫描 10,191 个文本文件，无私有题库或答案结构。cloud 的 390px/1440px 浏览器入口检查、local 的课程/错误回炉/刷新/实际音频播放通过。
- 截图和机器报告在被忽略的 `deploy-output/family-cloud-content/`、`deploy-output/family-accounts/`、`deploy-output/family-learning-m0/`，没有提交到远端。实体手机、麦克风和生产容器尚未验收。

常用复验：

```sh
npm test
npm run type-check
python3 scripts/checks/cloud-artifact.py
npm run build:cloud --workspace=china-study-free
npm run build:local --workspace=china-study-free
openspec validate add-family-cloud-learning --strict
```

API 在 `apps/api/` 执行 `uv run ruff check .` 和 `uv run pytest -q --tb=short`。PostgreSQL 集成测试需通过进程环境设置 `CSF_TEST_ADMIN_DATABASE_URL`；仅创建/删除 `cstf_test_<随机值>` 临时数据库，不清空连接指向的开发库。不要在日志里输出数据库 URL 或密码。

## 接入时的重要边界

1. 云端入口为 `apps/web/src/cloud/app/`，目前只挂账号及身份入口；普通课 static params 只读取索引/outline。不要重新把完整 Lesson 传进云端 props。
2. 云端产物没有原媒体目录，部分 API DTO 仍返回原媒体引用。5.5/5.6 需完成受保护媒体读取与 URL 适配，不能为解决缺音频/图片直接复制整个旧 `public`。
3. 原 `apps/web/src/store/progress.ts` 仍是 local 权威逻辑。云端接入时必须使用服务端结果，不能先本地判分/发奖再覆盖；也不能无意初始化本地档案或挂本地奖励 watcher。
4. 退出、账号/学生切换、停用、归档与会话撤销必须取消/忽略旧响应，清理敏感缓存；离线请求保留原幂等键并绑定原上下文，不自动改键重发。
5. 学习游标与配置 revision 是不同概念。旧配置应报 409，已确认学习事件不被整个 store JSON 覆盖。
6. 原题库存在控制字符；JSONB 无法存转义 NUL，题目及公开元数据用 JSON 无损保存。不要静默修掉文本或覆盖历史题目版本。
7. 本地导入只能成为明确标注的历史摘要/legacy 权益，不得伪造作答、重放奖励或覆盖新云端记录。
8. 不发布旧 `apps/web/out`；默认隔离产物为 `apps/web/.build/cloud/out`。完整 HTTPS 代理、旧缓存清理、备份/删除重放和回滚仍待 7.1 验收。

详细契约见 [账号说明](family-account-guide.md)、[内容服务](cloud-content-service.md)、[判分规则](cloud-grading-rules.md)、[学习会话](cloud-learning-session-api.md)、[奖励账本](cloud-learning-rewards.md)、[学习事件](cloud-learning-events.md) 和 [构建隔离](local-cloud-builds.md)。
