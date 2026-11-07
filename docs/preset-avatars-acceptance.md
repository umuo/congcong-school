# 内置头像实现与验证记录

变更：`add-preset-avatars`。范围为内置 Canvas 头像、三角色/孩子模式、家庭档案及现有模拟联赛；不包含 M2 诊断、安卓站点切换或原生 UI 重写。

## 已运行检查

| 检查 | 实际结果 |
| --- | --- |
| 完整 API/PostgreSQL `pytest -q`（隔离服务器） | 140 passed，69.02s；每个数据库夹具仅创建/删除随机 cstf_test_ 库 |
| 0010 → 0011 → 0010 → 0011 | 旧家长/管理员、四种孩子头像、账号绑定、学习事件和密码摘要保留 |
| Ruff `ruff check apps/api` | 通过 |
| `npm run type-check` | Web/core 通过 |
| `npm test` | core 315 passed |
| `npm run check:learning-client` | LearningClient、Provider、旧本地档案兼容通过 |
| `npm run check:web-experience` | 作答键盘、反馈、跳级、阅读、录音生命周期、主题通过 |
| `npm run check:avatars` | 16 绘制器、目录一致、SSR/降级、DPR 1/2/3、表单字段、取消/保存/冲突、焦点刷新不升级编辑版本、身份/卸载/迟到响应/丢失响应、待同步字节与原幂等键保留 |
| cloud 生产构建 | 7592 页；扫描 15222 个文本文件，无问题 |
| local 最终生产构建 | 7468 页，独立 local 产物生成完成 |
| 云端扫描器夹具 | 10 类拒绝用例通过 |
| 最终版本真实 HTTPS | 34 项通过；两家庭、三角色、代入、并发版本、上下文、导出、榜单；换头像前后学习 state/revision/cursor 相同 |

命令输出及截图保存在未提交目录 `deploy-output/avatars/`。完整 API 结果来自本次工具实际运行输出；其余构建与前端日志在 `logs/`。没有生成新的真实孩子作答或凭头像发奖。页面联赛初始化使用原有显式结算按钮，之后头像变化只刷新 GET。

## 视觉与交互证据

- `canvas-dpr-1-2-3.png`：共用生产绘制器的 16 款、32/88px 与三种绘制密度检查页面。
- `parent-picker-desktop.png`、`parent-picker-390.png`：桌面/390px 头像选择器；方向键、预览、取消验证。
- `league-long-fallback-390.png`：生产共用榜单组件的合成边界数据，含长中文、无空格英文、未知 ID；390px，无横向溢出。
- `student-saved-refresh-390.png`、`admin-saved-refresh-390.png`：独立学生、管理员保存及刷新后的头像。
- `family-b-isolation-390.png`：切换到另一个家庭后的独立头像。
- `multi-entry-latest-390.png`：r4 点击“读取最新头像”后，两入口均读取到新值（DOM 中确认两个同名头像）。
- `stale-edit-conflict-390.png`：独立 HTTP 会话先保存后，浏览器原编辑版本收到 409，禁用覆盖并可读取最新值。
- `live-league-390.png`：实际测试站榜单，本人与影子同学有头像，名次/XP 可读。

390px 选择项实测约 99 × 96 CSS px，页面宽度为 390，没有横向溢出。这里是浏览器视口及绘制密度检查，不是实体 iPhone/Android 验收。

## 隔离部署与回滚

测试站：`https://study.lacknb.com:8443/`，Caddy；保留 Xray 443。

- 仅升级 `cstf_cloud_mac_3f7024bd` 到 `0011_avatars`；原库不迁移。
- 迁移前备份 `avatar-before-20261102T102720.dump`，私有权限 0600，使用官方 PostgreSQL 16 工具验证归档清单；备份仍位于服务器私有备份目录，按原 7 天策略管理。
- API 镜像 `congcong-cloud-api:avatars-20261102-r1`；运行角色新列写权限与题库禁止写权限验证通过。
- Caddy 挂载 `.deployment/releases/20261102-avatars-r4`，先发布兼容 API，再发布扫描通过的 Web。
- 已实际演练 r4 → 兼容的头像 r3 页面 → r4，期间 API 保持支持全部 16 ID，已保存的新 `star` 值可读，数据库不降级；证据 `rollback-proof.json`。
- 原库只读核对仍为 `0006_regular_password_policy`。
- 原来的四值 API 不能作为回滚目标。生产回滚不得重置头像值或删除新列。

## 双独立浏览器验收（2026-11-02 已完成）

用户打开 Chrome 窗口后，原生 Google Chrome 通过本机窗口界面连接成功；另一会话为内置浏览器。两者分别登录、切换身份，非共享 Cookie 的两个标签页。

- Chrome 独立学生 A1 预览后取消，头像未改变；随后保存机器人头像。内置浏览器中家长 A 的旧档案表单得到冲突，刷新后显示机器人。
- 家长在内置浏览器代入 A1，并打开头像编辑；Chrome 先保存猫头鹰，另一浏览器旧头像选择器保存得到冲突且禁止覆盖，读取最新值恢复一致。
- 短暂停止隔离 API 制造 Chrome 的一笔待同步操作后立即恢复。页面重新连接仍显示一笔未同步；保存青蛙头像后仍保留该操作，显示仍为 120 XP、71 宝石、2 课。使用“用原标识重试未同步操作”后显示“已同步”。原幂等键和待同步字节不变还由专项客户端/组件回归验证。
- Chrome 独立学生与内置浏览器家长代入均显示青蛙头像；两端联赛的全部 16 行姓名、名次、XP、头像逐行比对一致（`two-browser-results.json`）。
- 家长恢复模式后仍显示本人星球头像；Chrome 仍保持独立学生身份。兄弟档案保持小狗头像，归档档案不可编辑或进入学习。
- Chrome 退出后切换家长 B，原两个孩子均为熊猫；家长 B 保存考拉并刷新后保留。内置浏览器切换管理员并保存宇航员，刷新后两个入口一致，未混入家长或孩子头像。

新增截图包括 `two-browser-avatar-conflict-390.png`、`two-browser-parent-stale-form.png`、`two-browser-chrome-league-desktop.png`、`two-browser-league-390.png`、`chrome-pending-before-avatar.png`、`chrome-pending-after-avatar.png`、`chrome-original-operation-retried.png`、`two-browser-archived-readonly-390.png`、`two-browser-family-b-desktop.png`、`two-browser-admin-independent-390.png`。

全部 16 项实现/验收任务现已完成。这里仍是桌面浏览器与 390px 视口验证，不宣称实体 iPhone/Android 已测试。

本变更不修改 M1 录音暂不验收的待办，不代替 M2 全学科诊断计划，不宣称实体移动设备已测试。头像变更需用户另行审阅后再同步/归档，不自动归档其他变更。

## 本变更涉及的文件

- API：`app/avatars/{catalog.json,catalog.py,router.py}`；`auth/{models.py,service.py}`；`students/{models.py,schemas.py,router.py}`；`learning/{league.py,router.py}`；`portability/privacy.py`；`main.py`；迁移 `0011_avatars.py`。
- API 验证：`tests/test_avatars.py`、`tests/test_league.py`、`tests/test_portability.py`。
- Web：`components/avatars/`、`lib/avatars/`；AccountShell、AdminDashboard、ParentDashboard、StudentForm、CloudEconomy；`app/{admin,learn}/page.tsx`。
- 构建与说明：`scripts/cloud/export-avatar-catalog.mjs`、`scripts/cloud/web-target.mjs`、`scripts/checks/avatars.tsx`、根 `package.json` 的头像检查脚本、本说明与 `docs/preset-avatars.md`、本 OpenSpec 变更目录。

此列表描述头像增量，不意味着工作区内其他未提交的 M1/iOS 文件属于本变更；未提交或推送本次头像开发。
