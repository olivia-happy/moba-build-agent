# 项目交接文档

## 1. 这是什么项目

《局内出装助手》（Local Build Agent）：一个面向王者荣耀玩家的本地优先动态出装决策 Agent。
玩家在选人/商店阶段主动触发截图，Android 悬浮球截取一帧并立即停止共享，
画面在手机本地降采样为 16×16 亮度网格，识别敌方 5 名英雄（Top-3 候选+置信度），
玩家确认/纠错后调用本机 FastAPI 规则引擎，返回带证据的出装建议（含装备价格、功能解释、组件路径、紧急秒换提醒）。

用途：秋招 GitHub 展示 + 面试 Demo（AI 产品经理岗，体现统计学背景 + 产品思维 + 全栈工程 + 有意义 AI 应用）。

## 2. 技术栈与架构

- 后端：FastAPI + Python（零 API key、零成本、本地离线）
- 前端：Android 原生 + Jetpack Compose（悬浮球、截图识别、确认 UI）
- 数据：官方公开静态资源（pvp.qq.com heroList / item.json / 头像 CDN），已抓取保存到 data/
- 测试：pytest（后端 42 个）+ Kotlin 单元测试（Android 6 个测试文件）

### 目录结构

```
project5/
├── backend/            FastAPI 服务
│   ├── app/            main.py / decision_agent.py / equipment_catalog.py / emergency_swap.py / hero_profiles.py / ...
│   ├── tests/          pytest 测试（42 个）
│   ├── scripts/        build_portrait_index.py / sync_portrait_index_to_android.py
│   └── requirements.txt
├── android-app/        Android 悬浮球 App
│   ├── app/src/main/java/com/localbuildagent/overlay/   MainActivity / OverlayService / ReviewScreen / LocalDecisionClient / ...
│   ├── app/src/test/java/...                           Kotlin 单元测试
│   └── gradle/wrapper/                                 已含 gradle-wrapper.jar（Gradle 9.7）
├── data/               官方数据快照 + 头像索引
│   ├── hero_catalog_raw.json   官方英雄目录（来源+时间）
│   ├── item_catalog_raw.json   官方装备目录（来源+哈希）
│   ├── portrait_index.json     132 英雄 16×16 亮度指纹索引
│   └── portraits/              132 张官方头像（已缓存）
├── pytest.ini
└── README.md
```

## 3. 当前功能状态（已完成并验证）

### 后端（42 个测试全绿）

- GET /health 健康检查
- GET /api/catalog/items 官方装备目录（121 件，价格/功能标签/唯一组/复活甲限次/冷却/来源）
- GET /api/catalog/items/{id} 单件装备规则
- GET /api/catalog/portrait-index 头像索引元信息
- POST /api/frames/analyze 单帧识别（仅 player_tapped_capture）
- POST /api/decisions 出装建议（仅 player_confirmed_screen）
  - 阵容威胁聚合 → 优先需求（魔法防御/韧性/物理防御/减疗）
  - 装备推荐（组件路径/买组件/替换/攒钱）
  - emergency_swap 秒换建议（金身/复活甲/名刀/血魔/苍穹、冷静鞋→抵抗鞋，带金币/格子/复活次数约束）
  - 每条建议带 evidence、function_explanation、item_price、component_path、why_now

### Android（测试通过，APK 已构建成功）

- 悬浮球 → 主动单帧截图（.lum 灰度，原始帧不离开手机）
- 本地 16×16 亮度网格匹配 → Top-3 候选 + 置信度
- ReviewScreen 确认/纠错/手动输 ID，支持输入金币、已持有装备、复活甲次数
- 决策页展示价格/功能/组件/为什么买/秒换提醒

## 4. 本次对话总结（如何走到这一步）

### 需求演进

用户目标：秋招 AI 产品经理，统计学研究生，需要能展示“统计+产品+全栈+AI”的高质感项目。
最初聊过战绩分析、组队匹配、视频剪辑 Agent、阵容出装推荐等多个方向，最终确定：
**王者荣耀局内出装助手（ToC 本地优先）**——解决“玩家只会跟系统推荐、不知道装备功能、不会根据敌方阵容调整”的痛点。

### 关键技术决策

1. **本地优先、零成本**：不接任何付费 API；用官方公开静态资源 + 本地规则引擎代替大模型。
2. **为什么用识别**：选人界面没有官方结构化数据，截图识别头像比手输 5 个英雄名快且不易错；识别结果必须人工确认。
3. **为什么用规则引擎而非黑箱 AI**：把“敌方机制标签计数 → 优先需求 → 装备功能覆盖 → 金币/格子/唯一组/次数约束”做成显式、可解释、可测试的规则。
4. **证据可追溯**：每个建议附装备官方文本证据、索引哈希、规则版本、未知项披露。
5. **隐私边界**：不读内存、不自动点击、不自动购买；原始帧不离开手机，只上传 5 个 16×16 灰度网格。

### 已实现的重要模块

| 模块 | 说明 |
| --- | --- |
| portrait_index | 132 英雄头像指纹索引（官方头像→16×16 亮度网格+哈希），可复现构建 |
| frame_analysis | Android 端截图→裁剪→降采样→本地匹配，返回 Top-3 候选 |
| equipment_catalog | 官方 121 件装备目录+功能标签+组件路径+限制（唯一组/复活甲限次/冷却） |
| emergency_swap | 保命装秒换+冷静鞋→抵抗鞋，带金币/格子/次数约束 |
| hero_profiles | 官方 132 英雄目录+威胁标签（越切/护盾/控制/法爆/物爆/回血等） |
| decision_agent | 威胁聚合→需求排序→装备覆盖→购买计划，全部带证据 |

### 已知风险与待办

1. **识别坐标是拍脑袋写的**：HeroSelectLayout.default 假设 1080×2400 屏幕、敌方 5 人纵向右侧固定位置。真机王者选人界面是环绕式棋盘布局，不同分辨率/刘海/导航栏都会偏。**必须真机截图校准（建议做成可视化拖框校准）**。
2. **推荐只对敌不对己**：目前没有“我在玩谁、什么定位、经济阶段、预购装备”输入，推荐逻辑对“我方”维度是空洞的。建议下一步补 own_hero_id + 定位 + 游戏阶段。
3. **悬浮球体验**：目前点悬浮球会拉起 MainActivity（过授权），不是悬浮小窗直接出结果，打断感明显。MVP 可接受，真机验证后优化。
4. **真机联调**：LocalDecisionClient 默认 10.0.2.2（模拟器），真机需改成电脑局域网 IP，后端要 --host 0.0.0.0。
5. **布局版本硬编码**：layout_version=draft-layout-1080x2400-v1 写死在前后端，校准后要变成版本化配置。

## 5. 新电脑安装环境（完整步骤）

> 只需装 Python + JDK + Android SDK/Studio 即可；Gradle wrapper 和依赖都会自动下载（需要网络）。

### 5.1 Python（后端）

1. 下载 Python 3.12（64 位）：https://www.python.org/downloads/
2. 安装时勾选 **Add python.exe to PATH**
3. 验证：`python --version`（应显示 3.12.x）

### 5.2 JDK（Android 构建）

1. 下载 Temurin JDK 21（64 位，免费）：https://adoptium.net/zh-CN/temurin/releases/?version=21
2. 安装后设置 JAVA_HOME：
   - 系统设置→高级系统设置→环境变量→新建 JAVA_HOME，值为 JDK 安装路径（如 C:\Program Files\Eclipse Adoptium\jdk-21.0.x）
   - 把 %JAVA_HOME%\bin 加到 Path
3. 验证：`java -version`（应显示 openjdk 21）

### 5.3 Android SDK / Android Studio（Android 构建）

1. 下载 Android Studio（免费）：https://developer.android.com/studio
2. 安装时勾选 **Android SDK 组件**，安装完打开一次，让它自动下载默认 SDK
3. 在 SDK Manager（Settings→Languages & Frameworks→Android SDK）确认安装：
   - Android SDK Platform **API 37**（compileSdk/targetSdk 用 37）
   - Android SDK Build-Tools 37
   - Android SDK Platform-Tools（adb）
4. 记下 SDK 路径（Windows 默认 C:\Users\你的用户名\AppData\Local\Android\Sdk）

### 5.4 新电脑配置项目

1. 解压 zip 到任意目录（例如 D:\projects\local-build-agent）
2. 在解压后的 android-app 目录创建 local.properties：
```
sdk.dir=C:\\Users\\你的用户名\\AppData\\Local\\Android\\Sdk
```
（注意是双反斜杠或正斜杠）

### 5.5 恢复 Python 环境

打开 PowerShell，进入项目根目录：
```powershell
cd D:\projects\local-build-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 5.6 运行后端
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 5.7 构建 Android APK
```powershell
cd android-app
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot'  # 换成你实际路径
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
# APK 在 app\build\outputs\apk\debug\app-debug.apk
```

### 5.8 跑后端测试
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q   # 期望 42 passed
```

## 6. 常见问题

- **Gradle 下载慢/失败**：多试几次；或换国内镜像（gradle-wrapper.properties 里 distributionUrl 改成腾讯/阿里镜像）。
- **Android 构建报 SDK 找不到**：确认 local.properties 的 sdk.dir 指向实际路径。
- **手机连不上后端**：确认同一 Wi-Fi、后端 --host 0.0.0.0、LocalDecisionClient 里 IP 是电脑局域网 IP。
- **Windows 无法识别 python**：检查是否勾选 Add to PATH。

## 7. 面试叙事要点

1. 用户与痛点：大量玩家只跟系统推荐出装，不知道装备功能，不会根据敌方阵容调整。
2. 为什么识别：选人界面没有官方结构化数据，截图识别比手输快；人工确认防止误判。
3. 为什么规则引擎：显式、可解释、可测试，避免黑箱。
4. 紧急场景：金身/复活甲/名刀/血魔/苍穹、冷静鞋→抵抗鞋，在金币/格子/次数约束下给可执行建议。
5. 可追溯：证据、索引哈希、规则版本、未知项披露。
6. 工程闭环：公开数据可复现、哈希校验、单帧即停、测试与 E2E。
