# iOS 云端测试包

现有 `ChinaTextbookStudy` 目标已改为启动云端学习，固定连接 `https://study.lacknb.com:8443/login/`。包名 `com.lacknb.study.cloudtest`，显示“聪聪学堂云测”，支持 iOS/iPadOS 17 及以上。用户授权使用 GitHub Actions 构建未签名 IPA，由用户自行签名安装；不发布 App Store 或 TestFlight。

功能由系统 WKWebView 连接现有家庭云端服务提供，**不是已完成原生 SwiftUI API 重写**。旧离线源码保留，但不参与当前云端目标；离线种子、题库、Widget、iCloud entitlement、ZIPFoundation 和原离线测试目标不装入云端包，不会回退到免登录本地学习。

- 登录由网页的 Secure/HttpOnly Cookie 和现有服务端权限控制，WKWebsiteDataStore 持久化正常登录；App 不内置账号密码，不提取 Cookie 或提供原生越权 API。
- 只允许测试站的 HTTPS/8443 源作为内嵌学习页面。用户点击的其他 HTTPS 链接使用系统浏览器；不接受任意 HTTP、file、脚本或伪装域名作为页面。
- 麦克风只对该源请求，仍由系统提示用户同意；摄像头请求拒绝。没有 ATS 全局例外或证书校验绕过。跟读录音遵循网页的页面内保留策略。
- 备份导入使用 WebKit 系统文件选择；JSON/Blob 下载通过系统分享菜单保存。临时分享文件在分享面板关闭后清理。
- 连接失败可重试；切到后台时覆盖敏感画面。恢复已确认学习和未确认原键重试继续由云端网页处理。

## 打包

有完整 Xcode 与 XcodeGen 的 Mac 上运行：

```sh
bash scripts/build-ios-cloud.sh
```

构建、DerivedData 和 IPA 默认位于项目忽略目录 `deploy-output/ios-cloud`，可用 `IOS_CLOUD_OUT` 指定外置盘绝对路径。不要把生产签名文件、Apple ID 或密码提交 Git。CI 为 `iOS Cloud IPA` 工作流，仅推送 `codex/ios-cloud-ipa-*` 分支或手动触发；上传 IPA 与 SHA256SUMS，保留 14 天。

产物 `CongcongCloud-unsigned.ipa` **不能直接安装**，需通过你使用的签名工具签名后侧载。正式 development/ad-hoc 分发需要 Apple 签名和相应设备描述文件；本轮不创建或购买证书。

## 实体设备待验收

首次打开和重新登录、家长与学生切换、普通课/复习/故事、锁屏后台恢复、弱网原键重试、系统麦克风授权及拒绝、完整逐句跟读/录音回放、刷新清除录音、文件导入与分享导出。不要将 CI 模拟器单元测试算成这些实体设备路径已通过。

构建自动检查严格源限制、下载文件名边界、iPhoneOS Mach-O、隐私说明、无 ATS 绕过、无种子题库/签名描述文件。服务端开发与浏览器验收仍见 `docs/family-cloud-acceptance.md`，实体录音待办保持未完成。
