# local / cloud 独立构建

默认启动及构建为 cloud。两种模式使用各自的 Next 工作目录、页面树和发布目录，不能把原 `public/`、旧 `out/` 或 local 产物叠加到云端站点。

## 命令

在仓库根目录执行：

```sh
# 第一次使用，先按原资源安装说明准备完整教材；需要更新生成数据时再运行此命令。
npm run build:data --workspace=china-study-free

# 默认云端开发，API 同源转发由 CSF_DEV_API_URL 配置，默认 127.0.0.1:8000。
npm run dev -- --port 3010

# 保留原离线档案和本地学习流程。
npm run dev:local --workspace=china-study-free -- --port 3012

npm run build:cloud --workspace=china-study-free
npm run build:local --workspace=china-study-free
```

| 模式 | 工作目录 | 唯一对应的发布目录 |
| --- | --- | --- |
| cloud | `apps/web/.build/cloud` | `apps/web/.build/cloud/out` |
| local | `apps/web/.build/local` | `apps/web/.build/local/out` |

开发服务使用独立的 `cloud-dev` / `local-dev` 目录，避免生产构建覆盖正在运行的开发缓存。目录全部被 Git 和 Docker 构建上下文忽略。没有新增一套 npm 依赖或复制教材源文件；共享组件与核心逻辑仍在原位置维护。

普通 cloud `next build` / `next dev` 被配置阻止，须通过项目入口准备隔离目录；这样不能误把原页面树和公开题库作为默认云端产物。此保护不是对主动绕开构建约定的防护。

## 云端边界

云端页面树位于 `apps/web/src/cloud/app/`，共享统一登录、管理员、家长和学生入口组件。课程静态参数只从索引及 outline 提取 URL，不读取完整 Lesson，不把题目、答案或解析放进页面 props。学习会话的公开题目和作答后反馈采用不同 DTO。

当前 cloud 已提供账号页面，课程客户端仍按后续任务接入；原课程 URL 暂先返回身份入口。云端产物仅装配必要图标，不装配原课程 JSON、故事题库、数感题库、音频索引、解释音频、课本图片或原 service worker。媒体须在相应授权学习入口接入，不能为修复缺图或缺音频而复制整个原公开目录。

每次 cloud 构建结束自动运行 `scripts/cloud/scan-artifact.py`，覆盖 JSON、HTML、RSC `.txt`、JS、source map 和媒体索引路径，发现原题库目录、私有题目结构、源码或缓存脚本即失败。扫描器也可独立执行：

```sh
python3 scripts/cloud/scan-artifact.py apps/web/.build/cloud/out
python3 scripts/checks/cloud-artifact.py
```

该扫描是构建回归检查，不是形式化的保密证明；新入口仍须检查依赖图和真实响应，不能仅靠搜索答案字段判断整个功能安全。部署必须提供 `/api` 同源代理及 `404.html` 回退，静态导出本身不携带 API 服务；完整 HTTPS 部署与旧 CDN/service worker 缓存清理仍在部署任务中验收。

## 本地兼容

local 使用原完整路由、Zustand 本地档案与媒体资源。构建阶段只提供静态数据和图标，导出后通过硬链接装配原媒体，避免再次复制二十余 GB 的资源；跨文件系统则复制。产物不是符号链接目录，可正常打包。不要直接修改装配后的媒体文件：硬链接与源文件共享内容。需要修改时修改源资源并重新构建。

两种模式的产物不能使用同一个发布目录，也不要把 local 放在 cloud 域名的可枚举子目录里。旧 `apps/web/out` 仅作为旧构建/基线保留，不是当前 cloud 的部署输入。

## 打包与验证

`prepare-site.py` 默认只接受经扫描的独立 cloud 产物；原完整媒体检查仅用于明确的 local 模式。目的目录必须尚不存在：

```sh
python3 scripts/deploy/prepare-site.py --mode cloud
python3 scripts/deploy/prepare-site.py --mode local
```

Docker 默认读取 cloud 构建，`--build-arg CSF_APP_MODE=local` 选择本地版本，COPY 路径跟随模式，不再从旧 `out` 取站点。Docker 镜像和 API 代理尚未在本阶段演练，不能将文件调整当作容器部署验收。

2026-11-01：两种生产构建通过。cloud 扫描 10,191 个文本文件，无私有目录或答案结构；扫描器的 7 类拒绝用例通过。真实 cloud 产物在 390px 与 1440px 浏览器完成首页、课程及旧 URL 共 6 项入口检查（认证 401 为受控响应），原数据/音频索引/service worker 请求均为 404，无页面脚本错误或横向溢出。local 产物使用受控旧档案完成 6 题课程、一次错误回炉、刷新保留反馈和实际音频播放，无脚本错误。证据位于 Git 忽略的 `deploy-output/family-cloud-content/`，浏览器模拟不等同于实体手机验证。
