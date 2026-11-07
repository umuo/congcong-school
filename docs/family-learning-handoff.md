# 家庭云端学习交接

2026-11-02，分支 `codex/family-learning-platform`，OpenSpec `add-family-cloud-learning`，spec-driven。**31/32 完成，仅 5.6 的实体跟读录音专项待验收**。用户已明确选择“先交付其余结果，录音实测保留待办”。未归档，未提交 Git。

完整实现、数据库/API 变化、测试、浏览器截图索引、局限和 M2 边界见 [交付验收报告](family-cloud-acceptance.md)；实际文件见 [变更清单](family-cloud-files.txt)。

## 可访问环境

[隔离测试站](https://study.lacknb.com:8443/login/) 使用 Caddy + 有效 HTTPS 证书。443 原 Xray 保持不变；8443 为本项目。最终前端 `.deployment/releases/20261102-e`，API 镜像 `congcong-cloud-api:preview-20261102-r3`，compose 项目 `congcong-cloud-preview`，远端根目录 `/home/ubuntu/congcong-school-api-test`。

用户授权 SSH `ubuntu@129.221.255.114` 及题库同步，仅用于本项目隔离测试。新数据库 `cstf_cloud_mac_3f7024bd` 版本 0010；**原 `cstf_dev` 仍为 0006，不能迁移或清空它**。远端 `apps/api/.env` 是原管理连接，仅供测试创建随机临时库，不能拿来启动业务。运行服务使用私有 `.deployment/runtime.env` 和受限角色，API 仅回环 18010。

外置盘 `/Volumes/Nas` 已挂载，所有大资源和依赖保留在外置盘；v1.8.2 全资源已安装，不需重复下载。Python `apps/api/.venv` 指向外置环境，npm 缓存位于 `/Volumes/Nas/envs/npm-cache`。不修改用户要求保留的宿主机服务。

管理员 `cloud-test-admin` 已按用户授权改密；初始密码失效。当前凭据只保存在本机 `deploy-output/family-cloud-final/admin-current-credentials.json`（0600，Git 忽略），不要输出到日志或文档。隔离测试原合成账号为 `cloud-e2e-parent-a/b` 和 `cloud-e2e-student-a1/a2/b1/b2`，凭据按本机已有测试记录使用，不在文档散布。

## 已验证

- 两独立浏览器上下文：内置浏览器和原生 Chrome。家长创建/编辑/归档与选书、降权/恢复、学生登录、兄弟姐妹及跨家庭隔离，390px 和桌面布局。
- 普通英语与数学、错误回炉、复习、挑战所有现有题型、逐对连线检查点、跳级、故事证据、完整听读、隔天数感，完成及刷新收据。
- API 受控断连、刷新保留待同步操作、原键重试，不提前判分/发奖。两浏览器刷新同步进度。
- 任务/每日奖励与装扮、学生归属的问题记录；原生 Chrome 合成备份预览确认，旧摘要与云端余额分离；家庭备份实际下载。
- 真实 HTTPS 40 项合成验收（权限及 401/403/409、建号、重置、停用、删除和重放）；新增临时家庭全部清理，原 A/B 保留。
- core 315；API/PG 133；最新 LearningClient 13；类型、Provider/本地档案兼容、web-experience、learning-quality、visual-controls、Ruff 通过。Provider 存在 act 警告但断言通过。
- local 7,468 页与公共资源硬链接装配完成；cloud 7,592 页，15,222 文本文件答案扫描通过；扫描器 10 个拒绝向量通过；OpenSpec strict 和 diff 检查通过。

截图、合成夹具脚本、真实 HTTPS 结果及日志保存在忽略目录 `deploy-output/family-cloud-final/`。隔天夹具只对空白合成 A2 用独立测试进程的昨日业务时钟完成课程，未修改运行服务或系统时钟。

## 唯一保留专项

5.6 功能已接入，但实体跟读录音与回放实测未完成。系统 `SPAudioDataType` 的 CoreAudio 设备为空；内置浏览器和 Chrome 都无法录音。站点麦克风权限曾按授权允许，测试后恢复询问。失败时确认完成按钮禁用，无完成事件或奖励；生命周期与取消回归通过。

有可用麦克风后，用合成账号进入已选英语教材的“听读与跟读”→跟读。验证三句逐句播放/录音、回放、录音仅页面保存、确认后服务端收据、刷新清除录音且保留完成、重复完成不发奖。现有跟读会话可以恢复，录音失败本身不算完成。通过后按最新任务行勾选 5.6，重新核对进度，再进行 M1 审阅与归档。

实体手机、Android WebView、移动后台音频和系统录音行为未验证；390px 仅是视口模拟。不得将 Mac 浏览器通过写成实体移动设备通过。

## 继续与运维

先运行 `openspec instructions apply --change add-family-cloud-learning --json` 获取最新位置。原管理数据库只用于创建/删除 `cstf_test_<随机值>`；不对它执行新迁移。服务器 Node 位于项目 `.tools/node22/bin`，非交互 SSH 要显式加入 PATH。

部署、受限角色、迁移、备份、恢复删除重放及回滚步骤见 [部署说明](cloud-deployment.md)。保留旧发布目录和 API 镜像，不能原地覆盖 Caddy 正挂载目录。备份策略当前 7 天，需要运营者清理；恢复前重放删除清单。

M2 延续追加事件、固定题目与规则版本，不重新判历史或重放奖励；旧摘要不能伪装成逐次证据。M2/M3/M4/M5 各建后续变更，本变更不包含它们。
