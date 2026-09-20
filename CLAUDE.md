# CLAUDE.md

本项目面向 Claude Code 的约定，**主体内容见 [AGENTS.md](AGENTS.md)**（跨工具通用，同一份约定）。

@AGENTS.md

---

## Claude Code 专属补充

### 这是一个三端仓库

`backend/`（Python + FastAPI）+ `h5-demo/`（Vite + React）+ `android-app/`（Kotlin）。
**三端共用一份决策逻辑与目录数据**，改一处要确认另两端。

### 命令的目录前缀

- `pytest -q` **在仓库根执行**——`pytest.ini` 写了 `testpaths = backend/tests` 与 `pythonpath = backend`。
- H5 命令在 `h5-demo/`，Android 命令在 `android-app/`。

### 常用定位

| 目标 | 文件 |
| --- | --- |
| 后端入口 | `backend/app/main.py` |
| 出装决策 | `backend/app/decision_agent.py` |
| 装备目录 / 标签 | `backend/app/equipment_catalog.py` |
| 英雄 / 威胁标签 | `backend/app/hero_profiles.py`、`backend/app/lineup_threats.py` |
| 头像识别（后端） | `backend/app/frame_analysis.py`、`backend/app/portrait_index.py` |
| 保命装秒换 | `backend/app/emergency_swap.py` |
| 建议证据 | `backend/app/evidence.py` |
| Android 识别 | `android-app/app/src/main/java/com/localbuildagent/overlay/FrameAnalyzer.kt`、`HeroPortraitMatcher.kt` |
| Android 选人坐标 ⚠️ | `.../HeroSelectLayout.kt` —— **已知需真机校准** |
| Android 本地决策请求 ⚠️ | `.../LocalDecisionClient.kt` —— 默认 `10.0.2.2`（模拟器） |
| H5 演示 | `h5-demo/src/App.jsx`、`scenarios.js`、`offline-snapshots.json` |
| 数字真值 | `docs/GAME_BREAKDOWN.md` |
| 产品口径 | `docs/MOBA_BUILD_AGENT_PRD.md`、`docs/CASE_STUDY.md` |

### 修改前必做

1. 读 [AGENTS.md](AGENTS.md) 的「架构红线」7 条 —— 尤其**规则引擎不可换成模型**、
   **隐私边界**、**识别必须人工确认**。
2. 动到任何数字前先读 `docs/GAME_BREAKDOWN.md`（数字真值来源）。
3. 跨端改动请同时检查 Python / Kotlin / JS 三处的对应实现。
4. 改完跑 `pytest -q`（仓库根）；改 Android 跑 `cd android-app && ./gradlew test`。

### 高风险改动

- **`docs/GAME_BREAKDOWN.md` 的数字是简历与对外材料的唯一真值来源。**
  尤其：121 件装备中**只有 48 件**进了标签体系（人工 28 + 文本解析 20）。
- **`HeroSelectLayout.kt` 的坐标是假设值**，任何「提高识别率」的说法在真机校准前都不成立。
- **`LocalDecisionClient.kt` 默认指向模拟器地址**，真机联调需改局域网 IP 且后端 `--host 0.0.0.0`。

### 不要做

- ❌ 不要引入模型替代规则引擎。
- ❌ 不要写「121 件全部标注」。
- ❌ 不要声称识别准确率或胜率提升。
- ❌ 不要新增上传原始帧 / 读内存 / 自动点击的能力。
- ❌ 不要删除 `docs/` 与 `HANDOFF.md` 中的边界声明。
