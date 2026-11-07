# 家庭云端学习交付与验收

2026-11-02，变更 `add-family-cloud-learning`，分支 `codex/family-learning-platform`。代码尚未提交或归档。测试站：[聪聪学堂](https://study.lacknb.com:8443/login/)。

## 本次结果

普通课、复习、挑战、跳级、故事、听读、隔天数感、任务奖励、装扮购买、本地问题记录及家庭数据导入导出删除均已接入服务端授权与学习事件体系。成绩和可消费奖励由服务端确认，浏览器仅保留投影、界面偏好和可原键重试的待同步操作。

用户明确选择“先交付其余结果，录音实测保留待办”。**5.6 保持未勾选**，唯一剩余验收是可用实体麦克风上的完整跟读录音与回放。当前 Mac 的 CoreAudio 设备列表为空；内置浏览器及原生 Chrome 均无法录音。Chrome 站点权限允许后仍失败，测试结束已恢复“询问（默认）”。失败时没有开放阅读完成按钮或发奖。录音重复停止、卸载、权限拒绝、取消及迟到 Blob URL 清理回归均通过，不能将这些模拟测试称为实体录音验收。

## 浏览器证据

两个独立 Cookie 上下文使用内置浏览器与原生 Chrome；均在同一台 Mac 上，不是两台实体设备。390px 是视口模拟，实体手机、Android WebView、移动端音频后台及系统麦克风行为尚未验证。

| 路径 | 验收结果 | 忽略目录中的截图 |
| --- | --- | --- |
| 家长档案与教材 | 两浏览器分别创建孩子，编辑年级/目标，归档后只读；数学青岛五四制和英语 PEP 独立选书，刷新保留；孩子降权与家长密码恢复 | parent-curriculum-390.png、parent-archived-desktop-chrome.png |
| 兄弟姐妹 | A1 原 1 课/50 XP，新孩子 0 课/0 XP；B2 保持 0 课/0 XP | parent-sibling-isolation.png、family-b2-final-390.png |
| 普通英语课 | 首答故意错一道，队尾回炉；7 次作答，5/6，50 XP/48 宝石，刷新原收据 | english-lesson-refresh.png |
| 错题复习 | 1/1，5 XP、恢复 1 心，刷新原收据 | review-refresh.png |
| 数学数值输入 | 填空与计算共 6/6，70 XP/68 宝石，刷新保留 | numeric-lesson-refresh.png |
| 单元挑战 | 15/15，320 XP/68 宝石；判断、选择、填词、语序、连线；逐对错误反馈不计整题，正确配对刷新增量保留 | challenge-refresh.png |
| 跳级 | 15/15，0 XP/50 宝石；刷新保留服务端跳级结果 | jump-refresh.png |
| 故事理解 | 证据选句与三题，3/3，15 XP；刷新原收据 | story-refresh.png |
| 全文听读 | 三句音频完整播放结束后才开放确认，5 XP；刷新原收据 | listen-refresh.png |
| 隔天数感 | A2 昨日练习夹具，今天 2/2、10 XP；刷新保留 | number-delayed-review-refresh.png |
| API 断连 | 暂停本项目隔离 API，提交时已确认 0 次，无判分与奖励；断连刷新后恢复，原键重试只计一次作答 | api-disconnected-pending.png、api-reconnected-original-key.png |
| 双浏览器同步 | 内置浏览器完成数学课后，Chrome 刷新从 50 XP/1 课更新到 120 XP/2 课 | independent-chrome-progress-sync.png |
| 导入 | 原生 Chrome 上传合成 cstf-backup v1，映射 1 课/1 项未映射；明确确认到 B1，学生只读旧摘要，余额及云端完成课数仍 0 | import-confirmed-chrome.png、import-legacy-zero-balance.png |
| 导出 | 家长最近验证后下载完整家庭备份，两孩子及非敏感账号关联；无认证秘密 | caddy-family-export.png |

证据位于 `deploy-output/family-cloud-final/`，不提交 Git。现有题库没有 `word_problem` 类型；该兼容类型由共用数值渲染器与 API 向量覆盖，不虚构教材浏览器记录。API 断连通过暂停本项目容器模拟，不是实体手机飞行模式。

隔天夹具通过独立 ASGI 测试进程，仅对原本无完成课程的合成 A2，用昨日业务时钟完成真实六题课程事件；运行服务和系统时钟不变。夹具脚本限定数据库名及空白学生，禁止对真实学习记录做同类改写。A1/A2/B1/B2 为合成测试账号；额外的新建与归档档案也仅用于隔离验收。

任务领取、装扮购买和每日奖励完成刷新与原键重试。B1 的问题记录按钮实际写入本标签页学生范围，退出清理；另有 13 项 LearningClient 检查中的报告范围回归，覆盖兄弟姐妹、同学生新登录、防止错误归属数据及退出清理。

## 运行检查

| 检查 | 结果 |
| --- | --- |
| core | 15 文件、315 项通过 |
| Web/core TypeScript | 通过 |
| LearningClient/Provider/本地档案兼容 | 通过；最新 LearningClient 13 项通过；Provider 有 React act 警告，断言通过 |
| web-experience | 答题反馈、文字/数字键盘、跳级、阅读会话、录音生命周期、十主题检查通过 |
| learning-quality / visual-controls | 通过，24 种题目状态检查通过 |
| API + PostgreSQL 16 | 133 项通过，51.31 秒；每项集成使用随机临时库，涵盖迁移往返、权限、并发结算、删除重放及恢复后重放 |
| API Ruff | 通过；新增键盘用例最初一处行长错误已修复并复验 |
| local 生产构建 | 7,468 页及全量公共资源硬链接装配完成，所有大数据均在外置盘 |
| cloud 生产构建 | 7,592 页，15,222 文本文件扫描无问题 |
| 扫描器自检 | 10 个拒绝向量、公共资源引用及运行时映射通过 |
| 真实 HTTPS 合成验收 | 40 项通过：两家庭各两学生、匿名 401、注册 403、角色及跨家庭拒绝、revision/重名 409、管理员建号、重置/停用撤销、学生删除与原键重放、家庭删除、另一孩子与原家庭及管理员保留 |
| OpenSpec / diff | 严格验证及 diff 空白检查通过 |

真实 HTTPS 验收的最后退出清理最初遇到一次 TLS EOF，增加连接重试后重跑完成；无证据表明业务断言失败。内置浏览器文件选择耗时导致五分钟家长验证窗口到期，改用原生 Chrome 文件选择器完成上传，没有延长验证窗口。

## 实现与数据库/API 变化

完整文件清单见 [变更文件](family-cloud-files.txt)。主要范围：

- `apps/api/app/{auth,admin,students,curriculum,content,learning,portability}`：三角色权限、固定题目版本、候选字符及连线逐对反馈、学习事件/检查点/奖励账本、SRS、阅读/故事/数感、导入导出删除。
- 数据库最新迁移 **0010**：沿用既有角色与教材迁移，新增 legacy 导入、删除回执与相关约束。运行账号有业务写入权限，无建库/建角色/超级用户权限，不能修改题库版本或迁移表。
- `apps/web/src/components/{account,learning,question}` 和 `src/lib/{api,learning}`：角色入口、家长与管理员页面、云端学习客户端、隔离投影、学生归属及待同步原键重试。
- 本次补充：录音重复 stop 共用 Promise，卸载与迟到回调释放录音/Blob；英语带标点句子正确识别字母键盘，空格键有可访问名称；家长档案加载态不再误报“没有孩子”；未知单元的听读列表不显示空单元/0 题，数感显示中文标题。
- `deploy/cloud` 与 `scripts/cloud`：local/cloud 独立构建、答案与私有媒体隔离、Caddy TLS、非 root 只读 API、权限模板和可执行部署/备份/回滚流程。

契约入口：[学习会话](cloud-learning-session-api.md)、[客户端](cloud-learning-client.md)、[迁移和删除](cloud-data-portability.md)、[部署](cloud-deployment.md)、[账号使用](family-account-guide.md)。

## 部署与凭据

Caddy 使用独立 8443，证书正常；现有 Xray 443 不变。最终前端目录 `.deployment/releases/20261102-e`，API 镜像 `congcong-cloud-api:preview-20261102-r3`。旧版本保留用于回滚。隔离数据库为 `cstf_cloud_mac_3f7024bd`、版本 0010；原 `cstf_dev` 保持 0006。

管理员密码已按用户授权更新，本机私有文件 `deploy-output/family-cloud-final/admin-current-credentials.json` 权限 0600 且被 Git 忽略；初始密码已失效，不在文档或终端输出密码。服务器 runtime/compose 环境文件同样私有。不得直接用远端 `apps/api/.env` 启动业务，它是原管理数据库连接，仅用于创建随机测试库。

备份保留策略当前 7 天，需运营者执行保留清理；恢复前须重放删除清单。当前为隔离测试部署，没有迁移真实用户数据。完整资源来自 v1.8.2，题库外传已获明确授权，仅用于本项目测试。

## M2 衔接

继续使用追加事件、固定题目版本及规则版本，不重新判分历史或重放奖励；legacy 摘要不能当作逐次作答或隔天独立证据。M2/M3/M4/M5 各建后续变更。本次不实现其新增目标。完成实体录音专项并经 M1 审阅后，才能勾选 5.6 并归档本变更。
