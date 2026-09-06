# 局内出装助手 · H5 场景 Demo

手机竖屏游戏界面风格的产品演示。选择左侧的预置对局场景后，Demo 会自动带入敌我阵容与对局状态，并真实调用本地 FastAPI 的识别和决策接口。

## 本地运行

在项目根目录启动后端：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开一个终端启动 H5：

```powershell
cd h5-demo
npm install
npm run dev
```

浏览器打开 <http://localhost:5173/>。

## 演示流程

1. 选择“高地前的法爆团战”“河道遭遇战”或“龙坑拉扯”。
2. 页面自动模拟主动抓取一帧，提交 5 个头像的 16×16 亮度网格到 `/api/frames/analyze`。
3. 识别完成后，提交玩家已确认的敌方英雄、我方英雄和自动抓取的经济状态到 `/api/decisions`。
4. 在悬浮助手面板查看针对敌方机制与我方定位的出装建议、证据和紧急秒换提醒。
5. 点击我方阵容中的英雄，观察同一敌方阵容下定位调整的变化；滑动透明度条观察悬浮窗透明度变化。

## 在线 / 离线双模式（静态部署可独立运行）

Demo 具备后端探测能力，无需任何开关：

- **在线模式**：启动本地 FastAPI 后端后（见「本地运行」），页面自动走 `/api/frames/analyze` + `/api/decisions` 真实引擎。
- **离线模式**：后端不可用时（如纯静态托管到 GitHub Pages、别人打开你分享的网址），页面自动回退到 `src/offline-snapshots.json` 的内置快照——该快照**由真实规则引擎一次性生成**，不是手工编的数据。顶部状态条会如实显示「离线演示 · 内置快照」或「本地规则引擎 · 已连接」。

### 离线快照如何再生成

改过规则引擎或预置场景后，在**项目根目录**重跑一次即可同步快照：

```powershell
.\.venv\Scripts\python.exe backend/scripts/generate_h5_offline_snapshots.py
```

脚本用 FastAPI TestClient 直接调用真实端点，按三个预置场景 × 我方各英雄输出识别与决策响应，覆盖 H5 里所有可切换状态。

### 部署到 GitHub Pages（免费、不开机也能访问）

```powershell
cd h5-demo
npm run build        # 产物在 dist/，已用相对路径（base './'），适合子路径部署
```

把 `dist/` 内容推到 GitHub Pages（或复制到任意静态托管）即可。已配置相对资源路径与相对接口路径，放到 `<org>.github.io/<repo>/` 子路径也能正常工作。

## 数据与隐私边界

- 英雄目录：<https://pvp.qq.com/web201605/js/herolist.json>
- 装备目录：<https://pvp.qq.com/web201605/js/item.json>
- 本地头像与指纹索引来自项目 `data/` 的官方资源快照。
- H5 使用预置场景的本地头像指纹 fixture，真实调用 `/api/frames/analyze`，不读取浏览器或王者荣耀进程。
- H5 不请求系统截图权限；Android 版才使用 MediaProjection 进行玩家主动的一帧截图，并在手机本地降采样。
- 后端规则是显式、可追溯的启发式建议，不宣称唯一最优解，也不会自动购买或操作游戏。

## 生产构建

```powershell
npm run build
npm run preview
```

构建产物位于 `dist/`，可以部署到 GitHub Pages 等静态托管；若部署后仍要实时调用 FastAPI，需要把后端部署到受信任的 HTTPS 服务，或在纯前端 Demo 中提供离线演示数据。不要把本地 HTTP 后端地址公开到公网。
