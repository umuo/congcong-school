# 熊猫森林改版验收记录

变更：redesign-child-learning-experience。用户选第 2 稿；01/03 原图及生成记录保留在外置盘 deploy-output/child-ui-redesign。所有本页证据路径相对该目录；设计与 mock 数据边界见 child-forest-design.md。

## 已执行检查

| 检查 | 结果/证据 |
| --- | --- |
| Web/core 类型检查 | type-check.log 通过 |
| core | core.log：15 文件、315 测试通过 |
| LearningClient/Provider/local 档案 | learning-client.log：原键/范围、退休客户端、StrictMode、旧 v13 档案、13 修订版、26 五四制教材通过 |
| 16 Canvas 与头像冲突 | avatars.log；avatar-sheet-r2-390.png、avatar-dialog-1440.png、avatar-conflict-390.png；预览取消/Escape/焦点、保存、独立 API 会话更新后的 409、读取最新与恢复青蛙通过 |
| 题型与视觉控件 | visual-controls.log：24 状态；web-experience.log：文字/数值键盘、反馈、跳级、阅读、录音生命周期、主题通过；连线样例修正为实际八选项结构 |
| 新增体验 | forest-experience.log：推荐/原会话、目录活动顺序、只读查询、主体偏好、受限存储、旧静音、同一 Event 去重、真实合成器的静音与重叠音频 owner gate 通过 |
| 主题和默认森林对比度 | 默认正文、轻表面、主按钮/焦点及 10 主题 × 两模式，通过 4.5:1 检查 |
| 实际学习链路 | A1 原会话 19a66a53-d859-4e69-bec7-b97d6b2de061 刷新保持同 ID，完成六题后才显示服务端确认 +70XP/+48 宝石；result-confirmed-r3-390.png |
| 题面尺寸 | question-responsive.json；360/430/844 横屏/768 平板/1440 桌面均无横向溢出，未发现小于 44px 的可见按钮 |
| 偏好隔离 | A1 刷新保持音效关、朗读开、减少动态开；A2 为音效开、朗读开、减少动态关；student-a2-isolation-390.png |
| 阅读降级 | reading-stopped-390.png、followup-unavailable-390.png：停止/录音不可用均未错误完成 |
| 家长与两家庭 | parent-restored-390.png、family-b-390.png；A 家长星球头像，B 家长考拉头像，B 只见 B1/B2；错误密码被拒后正确密码恢复家长 |
| 无教材 | 新建仅供本次测试的“森林空配置验收”档案：no-curriculum-390.png；不生成教材地址/主要学习任务。验证后已通过 UI 归档，资料保留，未删除任何已有孩子 |
| 功能归位 | cottage-390.png、shop-390.png、league-r2-390.png；浏览商店/排行期间余额保持 190XP/119 宝石，未购买/领奖/周结算 |

## 发布与回滚

最初交付发布为 `20261103-forest-r12`；用户复核后的最终修复为 `20261103-forest-r17`。r12→r10→r12 的兼容回滚、r11 插画缺失自动恢复已实际执行。本次不重复造成切站中断；r14/r12/r10 保留，pending/偏好持久化协议均未变。最终修复结果以 `repair-final-deployment-audit.json`、`20261103-forest-r17-scan.json`、`forest-cloud-build-r17.log`、`forest-local-build-r17.log` 为准；旧记录保留作历史证据。

`release-forest.py <release>` 在同一文件系统原子移动完整静态产物后，仅更新隔离 compose 的 CSF_CLOUD_SITE，执行 `up -d --no-deps web`。重新挂载旧发布也是同一入口，不重建 API、不运行迁移。扫描包含为旧标签保留的兼容 chunk；明确保留 r10（16 头像与偏好 v1 兼容）作为回滚目标。Caddy 使用 8443，现有 Xray 443 保持原状。

头像/成绩/偏好回滚证据：rollback-r12-to-r10-390.png、rollback-restored-r12-390.png。音效关闭、自动朗读和减少动态开启保持，头像青蛙，余额190XP/119宝石；没有因浏览或回滚购买、领奖、周结算。临时语英科配置通过当前 revision 的原有家长接口显式关闭，恢复为仅启用原数学 g1up，保留历史而不删除数据。

## 待完成的联合验收

OpenSpec 6.2 继续保留：两个独立浏览器上下文的完整联合验收、真正 200% 缩放尚未完成。已完成单浏览器两家庭/三角色和独立 API 会话的并发冲突检查；不将标签页或 API 会话充作第二浏览器。按快捷键尝试缩放时实际 DOM 宽度/scale 未变，因此不记录为 200% 通过。长文字合成样例不替代缩放检查。

## 覆盖限制

独立 Chrome 窗口控制不可用；当前仅一个内置浏览器上下文与独立 API 会话。未通过两个独立浏览器的完整联合验收。不得把同浏览器两个标签页视作独立上下文。后续不再切换个人 Chrome 档案。

当前 Mac 音频设备为空；无 adb，simctl 不可用。未做实体 iOS/Android 的软键盘、听感和实体录音验收。M1 录音待办与 M2 计划保持原状。

## 后续实测补充

- 最终管理员页、家长设置页均仅 1 个 `.avatar-trigger`；管理员切换账号类型时先显示“正在读取账号列表”，不将加载中显示成“暂无账号”。敏感停用确认打开后取消，未实际停用或重置密码。改密表单沿用公共字段/样式及原 M1 密码契约，本次不创建或变更凭据。
- 最终故事列表按教材第 1–8 单元排序；读取上学歌既有听读会话后，“返回探索”实际回到 `/explore/?book=chinese-g1up`。语数英科切换都显示对应教材名；等待和待同步期间不显示上一教材任务或发起新会话。
- 390×844 的第一未完成课程入口完整可用：主按钮底边 y532.65625，页面滚动宽度 390；仅一个当前主体头像入口。全部完成后的 review 分支由纯选择器测试覆盖。
- 合成控件页使用实际 QuestionRenderer 与发布 CSS，已验证数值 15、候选字“山”、八选项连线 A-1、词序选择；gallery-numeric-390.png、gallery-text-390.png、gallery-matching-360.png、gallery-word-order-360.png。该页不是教材或真实成绩，不进入 cloud 发布目录。
- 隔离 API 短停期间显示身份保护“请重新连接”（api-offline-guard-390.png）；45 秒保护自动启动同一 API，/health/ready 返回 database ready。重连后原 1 项操作仍在；先保存狐狸头像，待同步仍为 1，随后原标识重试成功、队列消失，余额始终 190XP/119 宝石。头像最后还原青蛙。证据：pending-after-api-recovery-390.png、pending-after-avatar-390.png、original-operation-recovered-390.png。身份保护期间未尝试绕过校验；外观操作在重连后、学习重试前进行。
- 头像网络失败可重试与 409 禁止陈旧保存分别在实际 AvatarPicker 组件回归中验证；原操作字节、路径、作用域和幂等键另由 LearningClient/头像组合回归断言。
- 数据库只读核对：cstf_dev 仍为 0006_regular_password_policy；隔离 cstf_cloud_mac_3f7024bd 仍为 0011_avatars。未迁移或清空原库。

- 最终 r11 实际组件/编译 CSS 合成页：原生头像 dialog 打开后按数字 1，背景计算题仍为“还没有选择”；Escape 关闭且焦点返回“打开头像测试面板”。360px 连续长英文标题换行，scrollWidth=360；gallery-long-name-360.png。此项不替代实际 200% 缩放。
- 排行独立 API 连续两次只读查询：16 行 ID/头像逐项相同，前后 progress revision/state 一致，190XP/119 宝石；不结算或发奖。

- 资源故障窗口：派生只读发布省略森林插画，原始 r11 完整保留；所有 img naturalWidth=0 时主按钮仍启用且底边 y512.859375、scrollWidth=390，装饰 pointer-events:none；artless-390.png。保护脚本 45 秒后自动挂回 r11，API 全程 ready。五张 WebP 共 337362 字节，设计 mock 不进入发布白名单。

## 最终验证命令

- `npm run type-check`；`npm test --workspace=@cstf/core`：315/315。
- `npm run check:learning-client`、`npm run check:avatars`、`npm run check:web-experience`、`npm run check:visual-controls`、`npm run check:child-ui`：通过，原始日志保留。
- 在服务器项目根执行 `npm run build:cloud --workspace=china-study-free` / `npm run build:local --workspace=china-study-free`：r12 两个独立产物完成，日志 `forest-cloud-build-r12.log`、`forest-local-build-r12.log`。
- cloud 构建扫描 15227 文本文件；合并兼容静态 chunk 后发布扫描 15319 文件，均 issues=[]；`20261103-forest-r12-scan.json`。
- `openspec validate redesign-child-learning-experience --strict`：通过。源代码与资源职责清单见 `docs/child-forest-files.txt`。
- 最终 `home-responsive-final.json`：360/390/430/横屏844/平板768/桌面1440 均无横向溢出；桌面故事链接最终高度44，未发现小于44px的可见按钮/链接目标。

视觉结论和偏差分级见根目录 `design-qa.md`；联合对照 `comparison-final.png`。这份视觉结论不等于尚未完成的两个独立浏览器及真机验收。

- 最终新标签页 console warn/error 均为空；缺图窗口的预期404仅记录在故障验收标签，不将其隐瞒为正常加载。最终原图/实装并排重新查看，视觉范围通过，独立设备验收仍保留。

## 用户复核后的修复（2026-11-03，覆盖旧视觉结论）

用户明确拒绝上一版还原度，并报告滚动背景消失、儿童端复杂、开始学习无法使用。已重新打开相关任务和视觉结论；此前仅首屏的“通过”不足以代表长页面与完整操作体验。

- 背景：展开数学全课程并到达 scrollY=3697，页面总高4972、视口390×844，森林伪元素 position=fixed / height=844px / pointer-events:none，横向宽度仍390。证据 repair-scroll-3697-390.png；不将短页面无滚动当成验证。
- 操作收拢：完整目录和“换教材与更多练习”默认关闭；复习/回心/跳级/数感均保留，小屋补给与已有装扮收起。头像仍单一入口，预览取消未写入。repair-responsive.json 六种尺寸无横向溢出、可见控件均至少44px。
- 视觉：头部独立积分控件、标题比例、透明绘本熊猫，叶绿#517c2c白字约4.92:1。默认/学士帽两张新WebP仅匹配实际装备，不伪造帽子拥有状态，其他装扮继续原渲染。七资源总407582字节，来源和SHA清单保留。
- 开始学习：B1直接登录，点击“学习：左、右方位辨认”一次后，确认进入新会话72c126a9-a615-4264-b98a-2f2a08a8e2c1；没有第二个开始确认。学前提示一次“开始练习”进入九题原序列，其他讲解可展开，不删除内容。
- 自动保存：选“对”出现发送中提示；刷新后仍是同一会话、同题，aria-pressed=true；repair-draft-restored-b1-390.png。提交后服务端确认正确，完成计数1/9。另恢复原会话4c8770a8-1305-4482-9a57-aacdcc622cb0后正常推进和判分；repair-confirmed-answer-b1-390.png。未完成整课，因此B1仍0XP/0宝石，没有伪造奖励。
- 正常发送与失败队列分开；只在失败时提供“重新保存”，题目锁定期间使用原生禁用状态，避免按钮看起来可点却吞掉点击。课程元数据尚未返回时不闪出题目再跳回讲解，失败可重新读取。
- 新增3项LearningClient回归：发送态/失败态与原字节、单次入口恢复/开始、只补发原有用时回执不自动重放答案/奖励；16项通过，Provider/旧local档案均通过。头像、web-experience、视觉控件（追加所有题型等待态原生disabled断言）、child-ui与类型检查通过。
- 原始用户所见具体报错文本尚未获得，当前直接学生和家长代入均未复现客户端异常；不声称定位了未知报错的全部根因。已定位并修复上述可复现的流程与反馈问题。现有独立浏览器/200%/真机及音频缺口继续保留。

最终 r17 复验补充：

- A1 仍为青蛙/学士帽、190XP/119宝石，音效关/朗读开/减少动态开；小屋默认仅常用设置，家长工具在展开后可访问，周奖励默认关闭且未领取。
- A1 原会话717f24ee-1885-406a-887d-17ec206e545e刷新后保留，补存用时后没有失败提示或“重新保存”按钮；repair-refresh-time-recovered-390.png。“开始练习”真实打开六题数感课程，render无warn/error；repair-question-final-390.png。A1没有新增作答或奖励，仅课前提示及互动草稿验证。
- “小猫1”真实点选触发自动草稿保存，发送期间互动/选项/提示按钮显示原生disabled；刷新后再次确认选中状态，再取消并保存以恢复未操作草稿。此项不替代实体移动键盘测试。
- r17独立cloud/local构建完成；原始cloud扫描15227文本文件，合并兼容chunk后发布扫描15367文件，issues=[]。repair-final-deployment-audit.json确认原API容器/镜像未更换，原库0006_regular_password_policy、隔离库0011_avatars、database ready。
- 最终视觉对照comparison-repair.png及头部/任务卡近景comparison-repair-focus.png已联合查看。旧r12结论不再代表当前修复状态，根design-qa.md记录用户复核后的问题、修复和覆盖限制。


## 提前判错反馈修复（r18）

用户截图为 What is ___ name? 仅输入 y、仍在保存草稿时变红。精确根因已复现：上一轮把 locked 合入 disabled 后，文字/数字填空与词序题错误地用 disabled 选择判分颜色，isCorrect=null被当作错。early-feedback-before.log 保留新增回归的预修复失败（calculation locked/answering rendered border-danger）。

三类题已改为仅 phase=checked 且存在布尔结果时显示颜色；禁用仅控制能否继续编辑。正确答案提示也只在明确false时出现。visual-controls新增36种输入/锁定/已判分组合，先红后绿通过；early-feedback-visual.log、early-feedback-web.log、early-feedback-types.log。没有改后端判分、答案、奖励、学生记录或同步队列。

本机浏览器合成状态页使用实际QuestionRenderer及发布CSS，输入y后保持locked=true/result=null，实测白底rgb(255,255,255)、蓝边rgb(28,176,246)，不变红或绿；模拟已判对/已判错才分别出现对应颜色。数字输入1和词序输入I也在保存中保持中性。证据early-feedback-neutral-y-390.png。这是组件回归，不是假称进入用户截图中的个人账号；未修改用户作答。

r18 cloud/local生产构建及发布扫描通过，已替换r17 Web；API容器、数据库和判分逻辑不变。联合双浏览器/真机验收缺口继续保留。

## 重复登录检查修复（r19）

原因确认：每个儿童页面单独挂载 AccountGuard/LearningProvider，部分工具入口使用原生a整页重载。修复前真实切到小屋即出现“正在确认登录状态…”（session-shell-before.txt）。

云端根布局现在保留单一儿童账号壳；页面 Guard 消费外层已验证身份，仍校验 destination。普通页面切换保留客户端和队列；登录/管理/改密独立 Guard 保持，首次/硬刷新、30秒轮询、前台、跨标签变更、过期和重新验证均保留，不使用localStorage缓存账号。站内商店/探索/返回入口改Next Link；课程离开停止自己的旧TTS。

新增 account-shell 集成回归（加入 check:learning-client）：首次仅一条auth读取；四次页面替换保留同Frame/Client/原pending key；后台focus读取不卸载当前内容；不同destination不显示越权页；跨标签身份改变立即卸载旧主体/清队列、旧client拒绝写入；401与强制再验证均清旧内容。session-shell-client.log / session-shell-types.log / session-shell-web.log / session-shell-avatars.log通过。

线上实测排行→探索→学习→小屋→商店→小屋六次切页，Frame始终_r_0_、头像入口始终1、余额始终190XP119宝石，无整屏登录检查；session-shell-navigation.json。首次加载仍有一次必要校验，不承诺硬刷新免校验。普通页面数据加载仍可显示自身等待状态。前端warn/error为空。session-shell-after-profile.png及after-detail截图保留。

r19独立cloud/local构建完成，合并兼容发布扫描15390文本文件/noissues；session-shell-deployment-audit.json确认原API镜像/容器和两库版本不变。独立双浏览器/200%/真机覆盖缺口仍保留。

## r20：显眼学科切换（2026-11-03）

发布到 https://study.lacknb.com:8443/，版本 20261103-forest-r20。儿童教材下拉框已移除，四学科栏位于欢迎区之前，探索页同样可切换，教材取自家长配置。

- 自动回归：Web/core 类型、LearningClient/Provider/local 档案、持久登录外壳与学科组件检查、child-ui/主题对比度均通过；新用例覆盖授权配置、禁用学科、快速切换迟到响应、选择记忆以及切换零配置/课程写入。日志为 deploy-output/child-ui-redesign/subject-switch-{client,component,types,ui}.log。
- 独立 cloud/local 生产构建通过，最终发布扫描15414个文本文件，无问题。API 容器 ID/镜像保持原样；cstf_dev 为0006_regular_password_policy，隔离库为0011_avatars；健康检查 ready。详见 subject-switch-deployment-audit.json。
- 真实 IAB 手机390×844：语文→英语→科学→探索科学→数学→学习数学，课程名称、选中项和地址一致，整个过程同一 account frame _r_0_，190XP/119宝石未变。无儿童“当前教材”选择器；四按钮高度46px，学科栏顶74px，继续学习按钮底586.86px。
- 展开全部课程后滚至3780px，学科栏顶8px仍可达。360/390/430、844×390、768×1024、1440×900无横向溢出，学科按钮均至少44px。证据 subject-switch-{390,sticky}.png、subject-switch-{browser,responsive}.json。
- 仅合成A1临时启用四科，使用快照+revision防并发覆盖，验收后恢复原仅数学配置。未更改真实用户课程配置、作答、奖励或学习进度。截图 subject-switch-390.png 展示临时四科配置，用于验证入口，不表示替真实用户开通教材。
- React组件检查确认事件驱动切换、语义按钮/选中态、稳定 key、清理迟到请求，无新增依赖。

OpenSpec6.2的双独立浏览器、真实200%文本放大、实体设备键盘/听感与录音覆盖仍保留，未宣称通过；M1/M2未修改。

## r22：排行榜、小屋与连续输入（2026-11-03）

用户复核要求移除排行榜长介绍和刷新按钮，精简小屋/每日目标/退出，并避免逐字保存卡住答题。最终发布20261103-forest-r22，Caddy只切换Web；r20/r21发布目录保留。

- 排行：390×844真实页面16行头像榜单；长介绍与“刷新榜单”均不存在，仅留“模拟榜·练习伙伴”短标识；打开自动读取、头像更新读取和显式周奖励仍保留。证据 refinement-league-final-390.png / refinement-league-check.json。
- 小屋：默认只展示装扮，任务奖励和学习设置独立切换；目标20/50/100/200XP直接点选，没有select；页头无退出，退出当前账号位于默认收起的家长与账号区域。任务/成就使用core中文名称，已拥有装扮不重复标价。只查看未领取、购买、装备或改设置，190XP/119宝石保持。证据 refinement-cottage-final-390.png、refinement-settings-final-390.png。
- 输入：移除700ms云端草稿定时器。逐键更新同标签页sessionStorage草稿，不调用checkpoint，不锁题型。检查答案直接带最新答案/证据，主动返回先保存脏草稿；存储受限本页仍可用。草稿按context/学生/会话/题目版本/revision隔离并限制24小时，仅同标签页恢复，未提交文字不实时跨设备同步。原提示、学前步骤、连线逐对反馈和时间回执不变。
- 真实浏览器恢复原717f24ee-1885-406a-887d-17ec206e545e会话，连续点小猫1/2，仍可输入且无保存提示；刷新恢复两项，随后撤销测试选择并返回，保留0/6题和原积分。refinement-input-draft-390.png / refinement-input-restored.txt。未检查答案或产生新奖励。
- 新真实组件回归：连续y/yo/you/your后等待1100ms，零checkpoint请求、输入不锁；卸载/重挂恢复草稿；主动返回恰一次checkpoint；显式检查直接提交最新文本，无前置checkpoint；确认后反馈进入checked。覆盖题目/revision/身份隔离和存储异常。测试夹具补全profile.id、使用真实格式会话ID后整组通过；早期失败日志保留，最终以refinement-client-final.log为准。
- Web/core类型、LearningClient全16例、Provider/local档案、持久登录壳/学科切换及输入组件回归、24题型视觉控件均通过。refinement-types.log、refinement-client-final.log、refinement-visual.log。
- 360/390/430、844×390、768×1024、1440×900无横向溢出；分区按钮46px、目标按钮46px以上；refinement-responsive.json。未点击目标或消费控件来制造截图状态。
- r22独立cloud/local生产构建通过；合并兼容资源后的最终扫描15464文本文件无问题。refinement-deployment-audit.json显示健康ready，API镜像/容器保持原样，两库版本仍0006_regular_password_policy / 0011_avatars。无迁移或奖励规则调整。

OpenSpec6.2双独立浏览器/实体设备及200%文本覆盖仍待补；M1录音待办和M2计划保持原样。

## r25：浮层提示与装扮按钮（2026-11-03）

用户截图显示“操作已同步”正文段落推动小屋分区，已装备按钮仍显示穿上。已发布20261103-forest-r25。成功提示改为fixed可访问浮层，3.2秒自动消失，可手动关闭；未确认操作持续显示恢复入口，不随提示关闭丢失队列。共享学习同步状态同样浮动，账号验证和判分正文仍保留。

- 我的装扮/商店根据各自服务端equippedMascotSkin、equippedTheme、equippedBackdrop显示“已穿上”并禁用。当前请求物品显示“穿上中…”，确认后才换装备；其他类别的装备保持不变。按钮固定116px，已穿上采用主题对应的轻表面。未改价格、权益、装备或奖励规则。
- 实际390×844 IAB：原学士帽已穿上，点击原版聪聪显示穿上中→已穿上，随后恢复学士帽。XP190/宝石134全程保持，不把用户先前已领取的奖励回退到119。仅切换已拥有装扮，无购买。
- 页面高度993px，四卡片文档顶部分别360/470.46875/580.9375/691.40625，行高98.46875，按钮116×48.046875；切换、浮层显示、自动消失后均保持，文档布局变化0px。恢复时工具为点击而自动滚动98px，已按rect.top+scrollY对照，不能把该工具滚动误报为页面排版位移。回到小屋后已恢复顶部展示。
- toast-equipped-390.png显示成功浮层；toast-after-dismiss-390.png显示自动收起后的已穿上状态；toast-layout-proof.json保留原始坐标、浮层fixed与消失状态。
- toast-responsive.json：360/390/430、844×390、768×1024、1440×900无横向溢出，装备按钮均116px宽、48px高以上。
- Web/core类型、完整LearningClient/Provider/local档案与现有输入/导航回归通过，toast-types.log / toast-client.log；toast-component-final.log新增自动消失/再显示/计时器清理、持续恢复不可被关闭、按类别确认装备、正在操作项、禁止重复装备和无正文确认块的实际组件回归。
- 最终cloud/local生产构建通过；最终合并扫描15483文本文件无问题。toast-deployment-audit.json显示ready、API镜像/容器保持原样，cstf_dev仍0006_regular_password_policy，隔离库仍0011_avatars。上一可回退发布r22保留；r23/r24是未上线的构建检查版本，最终上线为r25。

整体OpenSpec仍20/21，6.2覆盖待办保留；未修改M1录音待办与M2计划。

## r26：首次头像双框与请求等待（2026-11-03）

用户截图中第一项熊猫蓝框为默认焦点、老虎绿色勾选为真实选择。弹窗打开改为聚焦标题，键盘焦点用虚线区分；取消仍归还头像触发器焦点。头像保存采用已确认响应与更新事件直接刷新展示，避免保存后再次GET头像，打开面板的revision仍冻结；窗口恢复焦点继续读最新值。头像保存成功提示沿用浮层。

### 性能采样与优化边界

服务器loopback三次采样的中位数：auth/session10.7ms、头像10.6ms、profile9.7ms、progress15.2ms、shop9.9ms、数学课程目录22.8ms。见latency-loopback-before.json。

本机curl的公开healthz采样：首次TCP10ms、TLS5.765s、总6.684s；同进程复用连接总0.827s。见latency-public-health.txt。这是当前Mac到该站点的连接样本，不代表用户4G设备、判分写入或高并发P95。独立脚本的公网鉴权采样返回403，未将其作为接口响应耗时依据；未放宽Origin/CSRF规则。当前依据优先减少冗余往返，未部署Redis或改写API鉴权。

公开目录元信息在同一个有效LearningClient内短时缓存：课程目录30秒、商店配置5分钟，同请求并发合并，独立副本、最多12项；失效/切身份清空，迟到响应不得回填，失败不缓存。头像、鉴权、课程配置、进度、会话、题目、判分、奖励与写入保持实时。价格/权限/奖励仍由服务端实际操作时确认，不从缓存赋予权益。

### 验证

- 真实390×844首次打开：focus=H2、一个打开dialog、仅老虎一个选中项、无其他选项outline。按Tab焦点进入当前老虎并显示虚线；改选狮子只保留一个勾选，取消后仍老虎、焦点回原按钮，260XP190宝石保持，无头像保存或学习写入。avatar-focus-first-390.png / avatar-focus-browser.json。
- 360/390/430/768/1440宽度16选项、唯一选中、无横向溢出；avatar-focus-responsive.json。未用这些宽度替代实体iOS/Android验收。
- 头像回归通过16绘制器、DPR/回退、预览/取消/保存/409冲突、面板revision冻结、失效迟到响应、待同步字节保留；新增实际Editor成功保存仅一次PUT、不再额外GET。avatar-focus-avatars.log。
- 学习客户端18项通过，新增目录并发合并/30秒过期/副本隔离/身份隔离/缓存读取后撤销/失败不缓存/迟到请求拒绝，且progress每次仍请求。Provider/local档案、持续登录壳、学科切换、输入草稿及浮层/装备组件回归通过。avatar-focus-client-final.log。
- Web类型检查及最终独立cloud/local构建通过；最终合并扫描15486文本文件无问题；API镜像/容器和两库版本保持原样，ready正常。avatar-focus-types.log、forest-{cloud,local}-build-r26.log、avatar-focus-deployment-audit.json。上一线上r25保留。

OpenSpec总体20/21，6.2设备/双浏览器等覆盖仍待；不修改M1录音待办/M2计划。

## r29：继续儿童界面改进（2026-11-03）

用户选择继续儿童界面改进；本轮沿用第2稿森林风格，范围为可视化衣柜/商店、探索空状态和明确的继续学习标题。最终上线20261103-forest-r29，原有学习、价格、权益、奖励与身份规则不变。

- 衣柜按熊猫装扮、界面主题、答题背景分组。原版/学士帽复用已有森林图，其他装扮复用renderer，主题与背景显示真实配置预览；无新资源文件或自动购买/装备。真实A1衣柜4件（2/1/1），商店30件（12/10/8），没有丢失条目。未知条目保留“其他装扮”回退。
- 手机两列、大屏四列，按钮高度48px，宽度不超过180px。360/390/430/844×390/768×1024/1440×900均无横向溢出；最终ui-round-responsive.json记录117/132/152/180px按钮宽度。收尾前大屏曾拉伸到493px，已修正，旧测量保留ui-round-responsive-before.json，不作为通过依据。
- 探索无材料时主卡片区别故事/听读，直接给返回课程按钮，不先展示材料插画。390×844实测返回按钮底464.4375px且仅一个，链接/learn/?book=g1up；切换听读显示相应空状态，返回仍同一本数学教材。ui-round-explore-final-390.png、ui-round-browser.json。早期入口在951px，实际验收后收紧首屏，最终已解决。
- 首页实际恢复入口显示“跳级挑战”，继续按钮底586.86px保持完整首屏；只改显示名称与kind/source_id匹配，不更改会话排序或原恢复ID。纯函数回归覆盖复习/挑战/听读/数感及同source_id跨kind不得借标题。
- 本轮浏览、导航、预览没有点击购买/装备/领奖或开始课程，A1老虎头像、260XP190宝石保持；主页面导航继承已验证外壳，不重新出现整屏登录检查。ui-round-cottage-final-390.png / ui-round-shop-390.png / ui-round-learning-390.png。
- Web/core类型检查、客户端18项与Provider/local档案、头像/装备浮层、草稿恢复、学科切换和身份保护回归通过；最终组件新增空状态故事/听读切换、返回原book、无装饰材料卡与零写入用例。ui-round-types.log / ui-round-client.log / ui-round-component-final.log / ui-round-child.log。新增测试曾有作用域与Next尾斜杠归一化断言错误，已修正测试，最终日志通过。
- 独立cloud/local生产构建通过，最终合并扫描15509文本文件无问题。ui-round-deployment-audit.json：API镜像及容器保持原样，两库版本仍0006_regular_password_policy/0011_avatars，健康ready。r27是本轮中途上线版本，r28未上线，最终r29；旧r27/r26发布目录保留。

OpenSpec整体20/21，6.2双独立浏览器、实际200%文本和实体设备覆盖继续保留，未改M1录音待办/M2计划。
