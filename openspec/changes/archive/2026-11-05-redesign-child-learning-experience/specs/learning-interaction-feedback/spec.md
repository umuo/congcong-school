# Spec Delta

## Purpose

为儿童提供一致、轻柔、可控制的点击和学习反馈，使选择、导航及学习结果能被及时理解，同时在静音、音频受阻、阅读、跟读和减少动态场景下继续可用，并防止声音或偏好串到其他学习身份。

## ADDED Requirements

### Requirement: Intent based interaction sounds
系统 SHALL 为普通点击、选项切换和导航提供统一轻音，每次有效用户意图最多播放一次相应声音。组件渲染、后台刷新、被禁用操作、会话恢复或重复响应 MUST 不自动触发点击声音；音效失败不得阻断操作。

#### Scenario: Select or navigate once
- **WHEN** 用户执行一次有效选择或导航，且允许播放音效
- **THEN** 收到一次对应轻音和清楚视觉反馈，不因嵌套控件或页面更新重复播放

#### Scenario: Refresh or encounter audio failure
- **WHEN** 页面后台读取数据、刷新，或设备无法播放音效
- **THEN** 页面正常工作，不产生自动点击声或学习错误

### Requirement: Confirmed learning result feedback
答对、答错、完成及解锁反馈 SHALL 与实际已确认的结果对应，语气轻柔并同时提供可理解的视觉/文字状态。动画或声音 MUST 不抢先表示尚未确认的奖励成功，幂等重放和网络重试 MUST 不重复庆祝同一已处理结果。

#### Scenario: Receive a confirmed result
- **WHEN** 服务端确认作答或学习完成
- **THEN** 显示与确认结果一致的反馈，并在允许时播放对应声音

#### Scenario: Wait for or retry settlement
- **WHEN** 结果仍未确认或返回已处理的同一结果
- **THEN** 页面维持准确的等待/已确认状态，不通过重复动画或声音暗示新奖励

### Requirement: Independent scoped preferences
系统 SHALL 分别提供音效和自动朗读控制，保存当前有效学生或账号在本设备的非敏感偏好并在刷新后恢复；切换身份时 SHALL 加载对应设置并停止旧身份声音。旧静音用户的有效选择 SHALL 兼容保留，不能因改版自动开启声音。

#### Scenario: Disable only effects
- **WHEN** 用户关闭音效而保留朗读
- **THEN** 普通点击和庆祝声音停止，允许的朗读仍按其独立设置工作，刷新后保持选择

#### Scenario: Switch to another student or unavailable storage
- **WHEN** 用户切换身份，或设备无法持久化偏好
- **THEN** 不复用上一身份的运行时设置或声音；受限存储下本页控制仍有效，偏好保存不修改学习数据

### Requirement: Respect audio playback and recording
装饰性点击及庆祝音 SHALL 在朗读、听读或录音期间被抑制或避让，不混入跟读录音；必要语音和阅读完成条件 SHALL 沿用实际播放/录音结果。用户停止、取消或离开后 SHALL 及时停止相关旧声音。

#### Scenario: Record a followup passage
- **WHEN** 孩子正在跟读录音并操作界面
- **THEN** 录音中不加入界面点击或庆祝音，完成判断仍依据真实阅读流程

#### Scenario: Stop or change identity during speech
- **WHEN** 用户停止播放、取消阅读、离开相关流程或切换身份
- **THEN** 相关声音停止，不把旧语音带入下一学生页面或错误显示已读完

### Requirement: User gesture and silent fallback
系统 SHALL 遵守浏览器和 WebView 的音频手势限制，提供易发现的声音状态与控制。无用户手势、拒绝自动播放、静音或无音频能力时 SHALL 继续提供完整视觉操作，不能持续弹出播放错误或要求声音才能完成学习。

#### Scenario: Launch before any gesture
- **WHEN** 用户刚打开页面且尚未发生可解锁音频的交互
- **THEN** 页面安静可用，在后续允许手势时尝试建立音频能力，不自动持续播放背景声

#### Scenario: Use the application silently
- **WHEN** 用户选择静音或浏览器阻止音频
- **THEN** 选择、判分、同步和结果均能通过视觉及可访问文本理解

### Requirement: Reduced motion feedback
按压、选中、导航和学习动效 SHALL 简短且不阻塞操作。系统或用户要求减少动态时 SHALL 以静态强调替代非必要持续动画、位移或闪烁；重要状态和操作路径仍然可理解。

#### Scenario: Request reduced motion
- **WHEN** 系统启用减少动态效果或用户关闭非必要动画
- **THEN** 场景、角色和庆祝的非必要动态停止或降级，学习结果和当前选择保持明确

#### Scenario: Interact repeatedly
- **WHEN** 孩子快速重复点击或切换选项
- **THEN** 动画不无限堆积、遮挡控件或形成阻止继续操作的队列，声音仍遵循一次意图一次反馈
