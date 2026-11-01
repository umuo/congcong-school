# 家庭学习系统 M0 技术审计

审计日期：2026-11-01。代码基线：`34fbb65`；开发分支：`codex/family-learning-platform`。本报告覆盖源码、数据、生产构建和本机 Chrome 学习闭环；实体设备与真实麦克风验收未执行。这是 M0 阶段快照；当前 M1 实现进度见 [交接记录](family-learning-handoff.md) 与 OpenSpec 任务清单。

## 最新验收结果

M0 环境阻塞已解除，任务 1.4 的本机浏览器基线已完成：

- 缺失的 22 个分包（23,206,341,887 字节）全部下载，逐包 SHA-256、解包成员校验和最终 546,399 文件校验通过。安装收据已更新，原始下载包已清理。
- 使用临时目录中的独立 FFmpeg 7.1（支持 libmp3lame）完成 `npm run build`，没有修改本机 Homebrew。
- 构建后的站点完整性检查通过：缺失路由 0、完整性错误 0；17,918 句课文与 5,037 句故事均有音频，1,311 篇课文有原页，284 篇故事有配图。
- 390×844 和 1280×800 Chrome 冒烟检查通过，覆盖选年级、教材、课程、讲解、听读、故事、个人中心、错题及商店；实际课文音频播放进度推进，图片加载正常，HTTP Range 检查通过。
- 在隔离的 390px Chrome 档案中完成六题课程：首次故意答错一题，刷新后保留判错反馈和错题，再完成全部题目及回炉题。结算显示首答 5/6、重练后 6/6，学习记录保存成功。
- 从错题本进入真实复习，完成一题正确作答，显示复习完成、+5 XP 和红心恢复。
- 使用实际学习宝石购买学士帽，核对 80 宝石支出、新增装扮及触发的成就奖励；新建第二孩子后年级、成绩、错题独立，切回并刷新保留原孩子的成绩、错题和余额。

运行报告与截图保存在 Git 忽略的 `deploy-output/family-learning-m0/`。浏览器自动化使用合成档案，未读取真实孩子资料。早期脚本因把链接误作按钮、忽略购买触发的成就奖励和误计默认装扮数量而失败；按实际组件与状态修正断言后通过，这些不作为应用缺陷。

完整性报告还有已有内容提示：104 个含控制字符的文本字段、42 个以非 PNG 扩展名承载 PNG 内容的图片。它们未被现有完整性检查判为阻塞；仍需内容质量复核。下述已复现分数判分问题也保留为任务 4.3 的明确修复项，不宣称通过全部检查代表题库语义完全正确。

## 初次检查结果（环境阻塞已解除）

保留原 Web 与共享领域逻辑、增加模块化后端，是当前最小改造方向。以下是资源补齐前的检查记录，后续验收结果以上节为准：

1. 本地 `ASSETS-VERSION.json` 声明 `v1.8.2`、资源标签 `v1.8.2-web-resources`，但 `installed_asset_kinds` 仅为 `source-data`；不是完整资源安装。
2. `public/audio`、`public/story-images`、`public/textbook-pages` 均不存在。课文和故事数据可读取，但尚无可验证的朗读、原页与故事图片。
3. `npm run build` 完成数据生成和内容保留检查后，在音频转换阶段失败：FFmpeg 无法运行。单独执行 `ffmpeg -version` 退出码为 134，动态加载器报告 leptonica 所需的 `libtiff.5.dylib` 缺失。FFmpeg 已安装，问题不是 PATH 中找不到命令。
4. `apps/web/out` 不存在。未执行浏览器学习闭环、实际音频播放和完整生产导出；没有用跳过音频步骤的构建冒充完整基线。

## 架构和阅读入口

| 层次 | 已有实现 | 阅读入口 |
| --- | --- | --- |
| 工程 | npm workspaces，Web 与 TypeScript 共享包 | [根脚本](../package.json) |
| Web | Next.js 15、React 19、TypeScript、Tailwind、Zustand，静态导出 | [Web 配置](../apps/web/next.config.mjs)、[依赖](../apps/web/package.json) |
| 路由 | 首页选书、教材学习路径、讲解、课程、复习、听读、故事、商店、个人中心等 | [页面目录](../apps/web/src/app) |
| 组件 | 答题、题型、朗读、任务、成就、档案及响应式外壳 | [组件目录](../apps/web/src/components) |
| 领域 | 判分、SRS、奖励、成就、任务、联赛、日期、阅读、备份 | [共享核心](../packages/core/src/index.ts) |
| 内容构建 | output 题库与 data 课文故事转换为 public/data，附加媒体引用 | [构建器](../apps/web/scripts/build-data.ts) |
| iOS | SwiftUI 原生，与共享领域语义对照，资源按书下载 | [工程目录](../apps/mobile) |
| Android | Java WebView 加载 HTTPS 课堂，独立浏览器存储与权限处理 | [Activity](../apps/android/app/src/main/java/org/chinatextbook/study/MainActivity.java) |

当前没有家庭业务 API 或数据库。生产架构不能通过同步一份 localStorage JSON 就获得家庭权限和可追溯学习记录。

## 内容模型和答题链路

[共享类型](../packages/core/src/types.ts)中，`Book` 定义年级、册次、学制、出版社及版次等信息；`Outline` 包含单元，单元下有知识点；`Lesson` 保存教材、单元、知识点序号、讲解和题组。知识点目前没有独立稳定 ID。题目关联的是知识点名称，数字题号不能作为全库唯一身份。

原始数据经构建器按知识点名称分组，生成教材索引、单元路径和课程 JSON。课程页面在构建时读取完整 Lesson，再传入客户端答题组件。`LessonRunner` 接收输入，调用判分器，展示反馈、重排错题、保存会话并在结束时计算奖励和记录进度。完整题目包含答案和解析，现有模式不具备云端答案保护。

题型支持选择、判断、数字填空/计算、文字填空、排序、配对和视觉数感。判分实现有文本和数字归一化、选项内容识别等兼容逻辑。本轮直接调用现有 `gradeAnswer` 已复现：数字填空正确答案为 `1/2` 时，提交 `1/3` 返回 `true`，与数字分支的 `parseFloat` 前缀回退一致。任务 4.3 仍需补充完整回归用例及版本化修正，目前未修改判分业务代码。

## 学习状态与本地兼容

[进度 store](../apps/web/src/store/progress.ts)通过 Zustand persist 保存 `csf-progress-v1`，迁移版本为 13，包含课程汇总、未完成会话、错题、经验、宝石、任务、阅读、设置等。`completedLessons` 主要记录星级、正确率和完成时间，不是逐次作答日志。`addMistake` 替换同课程同题条目，未保留每一次错误答案。部分每日历史只保留近 60 天。

[本地档案管理](../apps/web/src/lib/learnerProfiles.ts)使用 localStorage 保存档案列表，并用 sessionStorage 固定标签页的活动档案；默认档案沿用旧键，其他档案附加命名空间。切换后整页导航重置 store、计时和缓存。已有备份校验、旧版课程与阅读 ID 兼容应保留，不能直接删掉本地迁移逻辑。

## 功能复用矩阵

现有完整清单见[功能总览](feature-overview.md)。

| 能力 | 直接保留 | M1 改造或新增 |
| --- | --- | --- |
| 儿童体验 | 学习路径、讲解、题型、反馈、动效、音效控制 | 通过统一学习客户端读取题目和提交答案 |
| 教材 | 原教材 ID、版次、单元、课文故事与媒体映射 | 服务端目录、每学生学科开关、选书历史 |
| 多孩子 | 档案选择交互、本地兼容与导出 | 家庭成员、服务端学生身份、编辑归档及权限 |
| 错题 | 原复习页面、SRS 语义 | 全部错误答案与复习事件，学生内去重投影 |
| 奖励 | 任务、成就、红心、宝箱、商店规则及展示 | 服务端幂等账本和事务结算 |
| 阅读 | 逐句播放、故事答题、录音回放 | 学生身份、阅读事件与权威奖励 |
| 周报 | 日期及周窗口、图表 | 从事件重建统计，区分旧摘要 |
| 特殊入口 | 跳级、挑战、数感、问题记录、分享卡 | 所有写入口纳入学生上下文，防止漏接同步 |
| Android | 现有 HTTPS WebView 及权限基线 | M4 再评估 Capacitor，M1 不替换工程 |

## 计划修改位置和 M1 顺序

| 位置 | 改造内容 |
| --- | --- |
| `apps/api/`（新增） | auth、families、students、curriculum、content、learning、portability 领域与测试、Alembic 迁移 |
| `apps/web/src/lib/api/`（新增） | 类型化 API、错误、会话、幂等及重试 |
| `apps/web/src/app/parent/`（新增） | 家庭首页、孩子管理、教材配置与学习总览 |
| `apps/web/src/lib/learnerProfiles.ts` | local/cloud 身份适配与旧档案迁移 |
| `apps/web/src/store/progress.ts` | 将服务端投影缓存和 UI 状态分离 |
| `apps/web/src/components/LessonRunner.tsx` | 使用异步服务端结果，保留答题队列和体验 |
| `apps/web/src/app/lesson/`、`review/`、`reading/`、`stories/`、`jump/`、`number-sense/` | 移除云端提前答案，覆盖各类学习事件 |
| `apps/web/scripts/build-data.ts`、`next.config.mjs`、部署配置 | local/cloud 独立产物、答案过滤、API 代理及缓存清理 |
| `packages/core/` | 规则对照与适配，保留旧类型兼容；不直接重写所有模块 |

M1 先建立数据库迁移和家庭会话，再完成两家庭隔离、学生与教材，之后才接入私有题库、服务端判分、逐次作答、奖励和同步，最后执行导入导出删除及两设备验收。知识诊断、个性化计划、Capacitor 和 AI 分别留给后续阶段。

数据库初步实体包含 users、auth_sessions、families、family_memberships、students、subjects、student_subjects、textbooks、教材选择历史、question_versions、learning_sessions、answer_attempts、learning_events、reward_ledger、进度错题投影和 legacy 导入记录。API 覆盖身份、模式切换、学生、教材、学习会话、幂等作答、变化游标与数据管理。具体字段、接口和失败语义以本变更的 design 与规格为准，尚未实现数据库或 API。

## 初次资源与验证记录

本地收据只证明曾安装源数据；未对所有 Release 分包执行逐文件哈希验证。内容结构检查不能替代媒体与完整 Release 校验。

| 本轮检查 | 结果 |
| --- | --- |
| `npm test` | 通过：13 个测试文件、231 项测试 |
| `npm run type-check` | Web 与 core 均通过 |
| `npm run check:web-experience` | 通过：反馈、输入、跳级加载、阅读、录音生命周期、主题 |
| `npm run check:learning-quality` | 通过：周报、奖励幂等、数感和首课入口 |
| `npm run check:visual-controls` | 通过：24 种题目状态等组件检查，不等同浏览器截图验收 |
| `node_modules/.bin/tsx scripts/checks/learner-profiles.ts` | 通过：v13 store、两档案隔离、13 个修订版与 26 册五四制兼容 |
| `python3 scripts/checks/content-retention.py --report /tmp/congcong-m0-content-retention.json` | 通过：4,448 常规课、27,669 题；验证历史基线 2,356 课、15,117 题，缺讲解和少于六题课程均为 0 |
| `python3 scripts/checks/site-integrity.py --report /tmp/congcong-m0-site-integrity.json` | 退出 1：静态导出目录不存在。读取到 84 册、1,311 课文、284 故事，句子音频、原页、故事图均为 0；检查未将“无媒体引用”判成媒体完整 |
| `npm run build` | 退出 1：数据构建及内容保留通过，音频准备因 FFmpeg 动态依赖损坏失败，尚未进入完整 Next 生产导出 |
| 浏览器与音频实际使用 | 初次检查尚未执行；后续已完成，见最新验收结果 |

首次 tsx 检查因沙箱 IPC 权限报 EPERM，解除该执行限制后上述检查通过。这不是应用逻辑失败。npm 另有本机旧配置项警告，不影响上述通过结果。

构建重新生成了被 Git 忽略的 `public/data` 和检查产物，没有修改题库源数据或业务逻辑。原始机器检查报告位于临时目录及 `deploy-output/`，其中包含本机路径，不作为公开文档附件。

## 依赖和资源授权

代码仓库的 [LICENSE](../LICENSE) 为 MIT；[README 教材说明](../README.md)明确教材文本和原页属于相应权利人，代码许可不包含第三方教材授权。逐项素材许可、音频来源和教师审核仍需清点，当前不认定已取得新产品公开分发授权。

现有 npm 依赖以 lockfile 为准；FastAPI、PostgreSQL、SQLAlchemy、Alembic 和 FastAPI Users 尚未安装。提案完成了文档级组件比较，尚无后端依赖兼容验证或完整直接/传递依赖许可证清单；该清单属于任务 2.1 的交付。

## 恢复 M0 的步骤

已在临时目录安装独立 `imageio-ffmpeg 0.6.0`，实际执行 FFmpeg 7.1 成功，确认有 `libmp3lame`；本机 Homebrew 安装未改动。安装器 dry-run 确认源数据包可复用；其余 22 包现已安装并逐文件验证。浏览器验收使用临时 Playwright 和本机 Chrome，见最新验收结果。独立 FFmpeg 只在本次构建进程的 PATH 中使用；系统默认 FFmpeg 的旧依赖问题仍存在，后续执行原构建命令时须继续使用该独立工具或先修复系统工具。

1. 修复或换用可运行且包含 libmp3lame 的 FFmpeg；先验证 `ffmpeg -version` 和编码器列表。本机 Homebrew 动态库修复会影响工程外环境，未执行。
2. 使用安装器先预览资源：`python3 scripts/install-release.py --tag v1.8.2 --dry-run`。再安装缺失资源并按 Release 清单校验；不能仅凭收据声称完整安装。
3. 本地收据中完整源模式的音频原包约 9.81 GB、Web 音频约 12.30 GB、图片与原页约 1.06 GB，以上为声明的压缩包体积，未核验下载内容；还需要解压和暂存空间。README 建议至少预留 80 GB。
4. 重新执行构建、站点完整性检查、浏览器各入口及实际媒体播放，记录证据后才能完成任务 1.4 并进入 M1。

没有将系统环境修复或缺失媒体视为可静默跳过的验收项。

## 后续实施说明

本报告的“尚未实现”描述保留为 M0 审计快照。后续已完成账号基础、私有题库及部分云端学习后端；分数判分风险已由 `cstf-grading-2` 和共用向量修复，不重判历史成绩。最新范围与验证结果以 [交接记录](family-learning-handoff.md)、[判分规则](cloud-grading-rules.md) 和变更任务清单为准。
