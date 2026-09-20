# AGENTS.md

> 本文件是写给 AI 编码助手（Codex CLI / Gemini CLI / Cursor / Copilot / Aider / Zed / Windsurf 等）的项目约定。
> 人类读者请先看 [README.md](README.md) 和 [HANDOFF.md](HANDOFF.md)。
> 修改本项目前，请先读完本文件——尤其是「架构红线」一节。

## 项目一句话

**MOBA Build Agent**（王者荣耀出装助手）：手机截图 → 本地识别敌方 5 个英雄头像 →
按「敌方机制标签 → 优先需求 → 装备功能覆盖 → 金币 / 格子 / 唯一组 / 次数约束」的**显式规则引擎**
算出出装顺序，每条建议都附带官方装备文本证据。

**核心取舍：用规则引擎，不用黑箱 AI。** 全部本地运行、零付费 API。
识别结果**必须人工确认**后才用于推荐。

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python + FastAPI（`backend/app/`，16 个模块）· pytest（42 个用例） |
| H5 演示 | Vite + React 18（`h5-demo/`），有离线快照（`offline-snapshots.json`） |
| Android | Kotlin + Jetpack Compose（`android-app/`），6 个单元测试 |

## 环境与命令

```bash
# 后端（pytest.ini 在仓库根：testpaths = backend/tests，pythonpath = backend）
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -r backend/requirements.txt
pytest -q                                           # 42 个用例（仓库根执行）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

# H5 演示
cd h5-demo
npm install
npm run dev                                         # vite
npm run build                                       # 产出 dist/

# Android
cd android-app
./gradlew test                                      # 单元测试
./gradlew assembleDebug                             # 产出 app/build/outputs/apk/debug/app-debug.apk
```

**测试入口**：后端 `pytest -q`（仓库根）、Android `./gradlew test`（`android-app/`）。

## 架构红线（改代码前必须确认没有违反）

1. **规则引擎，不是黑箱模型。** 「敌方机制标签计数 → 优先需求 → 装备功能覆盖 → 约束求解」
   必须是**显式、可解释、可测试**的规则。**不要**引入模型来替代规则（红线中的红线）。
2. **推荐只对敌不对己是已知缺口，不要假装它是功能。** 当前**没有**「我在玩谁 / 什么定位 /
   经济阶段 / 预购装备」输入，推荐逻辑对「我方」维度是空洞的。不要写文案把它说成已支持。
3. **隐私边界不可突破。** 不读内存、不自动点击、不自动购买；
   **原始帧不离开手机**，只上传 5 个 16×16 灰度网格。任何新增上传/联网功能都必须重新论证。
4. **识别结果必须人工确认。** 识别是 Top-3 候选 + 人工确认的流程，**不允许**让识别结果
   直接驱动推荐而不经确认。
5. **证据可追溯。** 每条装备建议都要附官方装备文本证据、索引哈希、规则版本、未知项披露。
   删除证据字段等于砍掉这个项目的核心价值。
6. **本地优先、零成本。** 不接任何付费 API。这是产品的立身之本，不要在重构中破掉。
7. **数据真值不可夸大。** 见下方「数据边界」——尤其是 **121 件 ≠ 全部人工标注**。

## 数据边界（写文档、写简历、对外介绍时的措辞纪律）

### 🔴 必须守住的一条

`docs/GAME_BREAKDOWN.md` §1 自己写明：**「121 件是目录接入量，不是都做了人工标注」**。

- 人工标注 **28 件** + 文本解析补 **20 件** = **48 件**进入标签体系；
- 其余 **73 件**无标签。
- **禁止**写成「121 件全部完成标签标注」。被问到就答「没有，是 48 件」。

### 其他边界

- **识别坐标是拍脑袋写的**：`HeroSelectLayout.default` 假设 1080×2400 屏幕、敌方 5 人纵向右侧固定位置。
  真机是环绕式棋盘布局，不同分辨率 / 刘海 / 导航栏都会偏。**必须真机截图校准**——
  不要在任何对外材料中声称「识别准确率高」。
- **无真实用户数据**：不宣称提升胜率，不做效果承诺。
- **布局版本硬编码**：`layout_version=draft-layout-1080x2400-v1` 写死在前后端，校准后应版本化。
- **`GAME_BREAKDOWN.md` 里的数字是真值来源**，改动数据前先读它。

> 诚实披露「没验到什么」在这个项目里是**加分项**。不要为了好看而删边界声明。

## 目录导航

```
backend/app/            # 后端 16 个模块
  main.py               # FastAPI 入口
  portrait_index.py     # 132 英雄头像指纹索引（16×16 亮度网格 + 哈希）
  frame_analysis.py     # 截图 → 裁剪 → 降采样 → 本地匹配，返回 Top-3
  equipment_catalog.py  # 官方 121 件装备目录 + 功能标签 + 组件路径 + 限制
  hero_profiles.py      # 官方 132 英雄目录 + 威胁标签
  lineup_threats.py     # 敌方阵容威胁聚合
  decision_agent.py     # 威胁聚合 → 需求排序 → 装备覆盖 → 购买计划
  emergency_swap.py     # 保命装秒换 / 冷静鞋→抵抗鞋，带约束
  scoring.py            # 评分
  evidence.py           # 证据挂载
  match_state.py        # 对局状态
  game_catalog.py       # 目录读取
  build_recommendations.py
  review_stats.py       # 复盘统计
  video_workflow.py     # 视频流程
  scripts/              # 构建索引等脚本
backend/tests/          # 18 个测试文件 / 42 个用例
h5-demo/                # Vite + React 演示（src/App.jsx、scenarios.js、offline-snapshots.json）
android-app/            # Kotlin 应用
  app/src/main/java/com/localbuildagent/overlay/
                        # MainActivity / OverlayService / SingleFrameCaptureService /
                        # FrameAnalyzer / HeroPortraitMatcher / HeroSelectLayout /
                        # PortraitIndexParser / PortraitIndexStore / LocalDecisionClient /
                        # CaptureIntentPolicy / ReviewScreen
  app/src/main/assets/portrait_index.json
  app/src/test/         # 6 个 Kotlin 单元测试
docs/                   # PRD、CASE_STUDY、GAME_BREAKDOWN（数字真值）、SCREENCAST_GUIDE、截图
scripts/capture_demo_gif.py
pytest.ini              # testpaths = backend/tests ; pythonpath = backend
```

## 关键文件速查

| 你要改什么 | 去哪 |
| --- | --- |
| 出装决策逻辑 | `backend/app/decision_agent.py` |
| 装备目录 / 标签 | `backend/app/equipment_catalog.py` |
| 英雄威胁标签 | `backend/app/hero_profiles.py`、`lineup_threats.py` |
| 头像识别 | `backend/app/frame_analysis.py`、`portrait_index.py`（含 Android 侧对应实现） |
| 保命装秒换 | `backend/app/emergency_swap.py` |
| 建议证据 | `backend/app/evidence.py` |
| Android 选人布局坐标 | `android-app/.../HeroSelectLayout.kt` ⚠️ 已知需真机校准 |
| Android 本地决策请求 | `android-app/.../LocalDecisionClient.kt` ⚠️ 默认 10.0.2.2（模拟器） |
| 数字真值 | `docs/GAME_BREAKDOWN.md` |
| 交给下一个人的上下文 | [HANDOFF.md](HANDOFF.md) |

## 跨端一致性（最容易出错的地方）

- **后端与 Android 各有一份头像匹配实现**（Python `frame_analysis.py` / Kotlin `FrameAnalyzer.kt` 等），
  改算法时**两端都要改**，否则 H5 演示与 App 结果会不一致。
- **`layout_version` 硬编码在前后端**，改布局参数要同时搜两端。
- **`portrait_index.json` 由后端脚本生成后放入 Android assets**，重新生成后要同步搬过去。
- **H5 与 Android 共用后端 API 契约**，改 `main.py` 的接口要同时检查 `h5-demo/src/api.js`
  与 Android 的 `LocalDecisionClient.kt`。

## 代码风格

- Python：类型注解尽量补全；模块职责单一（一个模块一件事，见上表）。
- Kotlin：Compose 风格；策略类（`*Policy.kt`）保持纯函数以便单测。
- 前端（H5）：React 函数组件 + hooks。
- 提交信息写清「做了什么 + 为什么」。
- **不要提交**：`.venv/`、`__pycache__/`、`android-app/local.properties`、
  `android-app/.gradle/`、`android-app/app/build/`、`node_modules/`。

## 不要做的事

- ❌ 不要用模型替代规则引擎（违反红线 1）
- ❌ 不要把「推荐只对敌不对己」包装成已支持我方维度（违反红线 2）
- ❌ 不要新增读取内存 / 自动点击 / 上传原始帧的能力（违反红线 3）
- ❌ 不要写「121 件全部标注」（真值是 48 件）
- ❌ 不要声称识别准确率高 / 提升胜率 —— 坐标未校准、无真实用户数据
- ❌ 不要删除 `docs/GAME_BREAKDOWN.md` 与 `HANDOFF.md` 中的边界声明
- ❌ 不要只改一端就提交（见「跨端一致性」）
