# family-access Specification

## Purpose

提供管理员、家长、学生统一登录及集中账号管理，关闭公开注册，约束角色与家庭访问边界，并使学生独立登录和家长代入孩子模式均只能执行获准的学生学习操作。

## Requirements

### Requirement: Closed public registration
系统 MUST 关闭公开注册页面及后端公开建号能力，家长和学生登录账号 SHALL 由管理员创建；提交客户端角色或调用旧接口不得绕过该约束。

#### Scenario: Call legacy registration directly
- **WHEN** 未认证用户或普通家长直接调用原公开注册接口，或提交角色字段要求创建账号
- **THEN** 请求被拒绝且不产生用户、家庭、成员关系或会话，登录页面没有公开注册入口

### Requirement: Administrator bootstrap
系统 SHALL 提供部署时显式初始化一个管理员的方式，初始凭据 MUST 由本地配置提供而非硬编码。初始化 MUST 原子且可重复执行，已存在管理员时不得重复创建、重置密码、复活账号或提升既有普通账号。

#### Scenario: Bootstrap and repeat
- **WHEN** 操作者在空缺管理员的已迁移数据库中提供合法初始凭据执行初始化，随后重复或并发执行
- **THEN** 只创建一个管理员及安全密码哈希，重复执行不改变已有凭据，缺失配置或账号冲突不留下半成品

#### Scenario: First administrator sign in
- **WHEN** 初始管理员首次使用配置提供的凭据登录
- **THEN** 只能修改密码、退出或查询最小会话导航状态，修改成功并轮换会话后才能进入管理后台，初始密码不进入日志或公开文件

### Requirement: Administrator managed accounts
系统 SHALL 允许最近验证密码的管理员列出、创建、停用家长和学生账号以及重置其密码。新家长 MUST 关联明确家庭及成员身份；新学生账号 MUST 关联明确家庭中的单一学生档案。创建账号和相关家庭/档案关系 MUST 在同一事务完成。管理员权限 SHALL 限于专用管理接口，不自动获得家庭学习明细、家庭导出或代登录权限。

#### Scenario: Create parent and family
- **WHEN** 管理员创建家长并选择新建家庭或明确的已有家庭
- **THEN** 新家庭原子建立 owner，已有家庭保留原 owner 并建立合法成员关系，重复登录名或无效关联使整个操作回滚

#### Scenario: Create student login for existing profile
- **WHEN** 管理员为某家庭的已有学生档案开通登录账号
- **THEN** 账号绑定该学生，保留原学生 ID、教材和学习历史；不得跨家庭关联、重复绑定或将已有历史的账号转移至其他学生

#### Scenario: Disable or reset credentials
- **WHEN** 管理员停用普通账号或为其重置密码
- **THEN** 该账号全部旧会话被撤销；停用后不能登录，普通用户重置后可直接使用新密码访问本人获准业务，不强制改密，学习历史保持不变

#### Scenario: Unauthorized account management
- **WHEN** 家长或学生直接调用管理员接口，或管理员通过普通建号接口要求创建管理员角色
- **THEN** 服务端拒绝且不改变账号或角色，不依赖页面是否显示管理按钮

### Requirement: Unified role based sign in
系统 SHALL 提供统一账号密码登录、退出和本人资料入口。服务端 MUST 判定 admin、parent、student 角色及当前会话模式，成功登录后分别进入 `/admin`、`/parent`、`/learn`；客户端角色选择、URL 或请求体不得决定权限。学生登录 MUST 无需邮箱，原家长邮箱登录须兼容。密码 MUST 以安全哈希存储，登录失败与限流不得泄露凭据。

#### Scenario: Sign in by role
- **WHEN** 已完成初始改密的管理员，或普通家长、学生使用合法凭据通过统一入口登录
- **THEN** 服务端返回对应身份及入口，家长仅取得本家庭资料，学生仅取得绑定学生的最小资料，不强制管理员或学生具备家长成员关系

#### Scenario: Invalid credentials
- **WHEN** 登录凭据不正确或超过尝试限制
- **THEN** 系统返回稳定的认证错误或限流响应，不建立有效会话

#### Scenario: Forged role and direct page access
- **WHEN** 普通用户篡改登录请求角色、浏览器缓存或手动进入其他角色页面并调用其 API
- **THEN** 服务端仍按真实角色拒绝越权，页面重新校验身份并返回本人获准入口

#### Scenario: Open default site without authentication
- **WHEN** 用户未登录访问默认 cloud 站点的首页或直接打开原课程、复习、商店等页面 URL
- **THEN** 页面先校验会话并跳转统一登录，不挂载原免登录学习界面；已有有效会话按角色进入获准入口，服务不可用则阻断并提示重试，不能回退到本地免登录模式

### Requirement: Initial password change
系统 MUST 限制初始管理员在改密前只使用修改密码、退出及最小会话导航状态查询，不得通过直接业务 API 或再次验证跳过；改密后 MUST 撤销旧凭据对应会话并建立新的会话。普通家长和学生首次登录及管理员重置其密码后的登录 SHALL 直接进入对应业务页面，不强制改密；重置仍 MUST 撤销全部旧会话。

#### Scenario: Administrator tries business API before change
- **WHEN** 初始管理员首次登录后直接调用管理接口
- **THEN** 返回必须修改密码的稳定提示，完成改密后才可进入管理后台

#### Scenario: Regular first and reset login
- **WHEN** 家长或学生使用管理员设置或重置的合法密码登录
- **THEN** 直接进入本角色获准入口，不跳转强制改密页；重置前的旧会话依然无效

### Requirement: Account and password input feedback
管理员建号页面 SHALL 在输入账号后即时检查全局重名，使用与服务端一致的归一规则，不区分家长、学生、管理员或停用状态；检查接口 MUST 仅向最近验证的管理员开放。创建、重置及管理员首次改密表单 MUST 要求再次输入密码并即时提示一致性，不一致时阻止提交。最终账号唯一性 MUST 由数据库和服务端保证，不能依赖前端预查。

#### Scenario: Duplicate account while typing
- **WHEN** 管理员输入已存在账号或其大小写变体
- **THEN** 显示账号已存在并阻止提交；检查其他角色的账号同样有效，不公开账号详情，普通用户不能调用查重接口

#### Scenario: Password confirmation mismatch
- **WHEN** 创建、重置或改密时两次密码不一致，或确认后又改动第一次输入
- **THEN** 前端即时给出可访问的错误提示并阻止写请求，只有一致后才可提交，确认密码不传给 API

#### Scenario: Delayed availability or concurrent creation
- **WHEN** 旧账号输入的检查响应延迟返回，或预查可用后另一个请求创建同名账号
- **THEN** 旧响应不能覆盖新输入状态，最终保存仍通过唯一约束拒绝冲突且不会留下半成品

### Requirement: Revocable authenticated sessions
系统 MUST 验证每个受保护请求的有效会话，并支持退出及会话撤销；会话过期或撤销后不得继续读取缓存中的家庭资料或提交业务操作。

#### Scenario: Revoked session
- **WHEN** 已退出设备再次携带原会话请求学生数据
- **THEN** 系统拒绝请求，客户端清除该会话的敏感展示缓存

#### Scenario: Parent disabled while in child mode
- **WHEN** 管理员停用家长账号，原家长已在其他设备代入孩子模式
- **THEN** 家长及其代入会话均被撤销；同家庭其他有效的独立学生账号不因此被停用

### Requirement: Server-enforced family boundary
系统 MUST 根据真实角色、家长成员关系或学生账号绑定校验所有家庭和学生资源；资源标识、查询参数、请求体与客户端角色声明不得作为授权依据。学生账号不得因加入家庭而取得家长成员权限。家庭成员模型 SHALL 容纳未来多个监护人，M1 不开放邀请入口。

#### Scenario: Cross-family access
- **WHEN** 家庭 A 的家长请求家庭 B 的学生、记录、导出或写入接口
- **THEN** 系统拒绝请求且不泄露资源详情、不改变数据

#### Scenario: Student enumerates sibling
- **WHEN** 独立学生账号请求同家庭另一个孩子或其他家庭孩子的配置、学习记录或管理接口
- **THEN** 系统拒绝请求，不泄露其他孩子或家长备注，学生仅能访问绑定身份获准的学习数据

#### Scenario: Administrator calls family export
- **WHEN** 仅具备管理员身份而无家长成员关系的账号直接请求家庭记录或家庭导出
- **THEN** 系统拒绝请求，不因为账号管理权限放行家庭业务

### Requirement: Child mode and parent verification
系统 SHALL 保留家长代入孩子模式，并提供学生独立登录；两者均 MUST 限定一个学生，仅允许该学生的学习操作。家长代入会话恢复家长管理 MUST 验证原家长密码及成员关系；独立学生会话不得通过本人密码恢复为家长。修改家庭设置或导出删除数据 MUST 要求有效家长身份及最近一次密码验证。

#### Scenario: Child attempts management request
- **WHEN** 孩子模式通过手工调用 API 尝试修改学生资料或读取其他孩子资料
- **THEN** 服务端拒绝请求，即使浏览器中仍存在家长登录 Cookie

#### Scenario: Return to parent mode
- **WHEN** 从孩子模式返回家长端
- **THEN** 系统要求家长再次验证密码，成功后更新服务端会话模式并恢复家长导航，共享该会话的标签页保持一致

#### Scenario: Independent student attempts parent recovery
- **WHEN** 独立学生使用本人密码调用恢复家长模式或再次验证接口
- **THEN** 其角色与学习范围不会提升；要使用家长端必须退出后由家长账号重新登录
