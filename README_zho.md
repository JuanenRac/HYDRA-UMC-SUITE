<!-- =============================================================================
HYDRA-UMC-SUITE - Desktop command center for several HYDRA-UMC servers at once
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🖥️ HYDRA-UMC-SUITE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🖥️ HYDRA-UMC 平台的多控制器集群指挥中心

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="Graphics">
  <img src="https://img.shields.io/badge/Tests-44%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.7.4-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

**诚实核查——今天真正能跑起来的部分：** 网络发现（并发子网扫描 + 真实的 mDNS/Bonjour，`hydra_suite/net/discovery.py`）、实时 REST+WebSocket 连接与集群支持（`hydra_suite/net/client.py`、`hydra_suite/app.py`）、3D 视口针对全部 24 个真实机器人型号外加一个"通用（Generic）"兜底方案的真实正向运动学（`hydra_suite/render/`，已针对 HYDRA-UMC STUDIO 自身的 TypeScript 正向运动学实现做过逐位数值验证）、全部 11/11 个工具挂载配置面板、CAN-OTA/SPI-OTA 刷写，以及真实的 MJPEG 摄像头画面渲染，都是真实且经过测试的——`tests/` 下有 44 个离线校验/冒烟测试脚本（`python tools/run_offline_verifiers.py`，通过 `QT_QPA_PLATFORM=offscreen` 以无头 Qt 方式运行）。界面只有 Qt Quick（`qt_suite.py`）：导航中的全部 33 个面板都是真实可用的代码，包括通过专用 `OffscreenRobotRenderer` 绘制的 3D 视口；经典窗口已被移除。根据本仓库自身的诚实惯例，明确尚未完成的部分：CAN-OTA 的 URTC Tool Head/Advanced Expansion 档位还没有真正的硬件中继通道；`combinedWith`（联合机器人模式）虽然存在于 STUDIO 自己的数据模型中，但尚未在本应用的界面中暴露出来。轨迹面板 现在通过 HYDRA-UMC STUDIO 自身真实的 `WORKS/*.json` 格式（`POST /api/upload-work`、`GET /<文件夹>/index.json`）进行导出/导入——在这里记录的点位是一个真实的、可在两款应用中互相播放的 Work。本段总结的完整、逐项的"真实 vs. 推迟"对照见 [`docs/ROADMAP.md`](docs/ROADMAP.md)，已交付的具体内容见 `CHANGELOG.md`。

---

> **安全与安防现状:**本生态系统不是经认证的安全系统。目前尚无硬件 E-STOP 通路,没有由固件强制执行的限位或联锁,也没有经过验证的运动指令;固件映像使用 CRC-32 和 Ed25519 签名校验,发布构建会拒绝已公开的开发密钥(中继之后的工具头和扩展板仍运行 URTC 的引导程序,它们使用共享密钥的 HMAC-SHA256 而不是签名);TLS 与双向 TLS 均为可选项,默认关闭;自制电路板尚未组装或测试。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.7.4` |
| 成熟度 | 可用 |
| 测试 | 44 (`python tools/run_offline_verifiers.py`) |
| 技术栈 | Python 3.12 / PySide6 |
| 目标 | 使用者的电脑 |
| 真实硬件 | 尚未：此版本没有在真实硬件上运行的记录 |

**跳转：** [概述](#-概述) · [架构](#-架构) · [功能](#-功能) · [安全与防护](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [故障排除](#-故障排除) · [仓库结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟡 | 主要用途可用；上面的诚实性检查列出了仍然缺少的内容 |
| 测试 | 🟢 | 44 项自动测试，每次变更都会运行 |
| 真实硬件 | 🔴 | 尚未：此版本没有在真实硬件上运行的记录 |
| 文档 | 🟢 | 八种语言的 README，每次变更都会与清单核对 |

## 🎯 概述

**HYDRA-UMC SUITE** 是一款原生的 Windows/Linux 桌面应用程序（Python + PySide6/Qt6），构建为整支 [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) 控制器舰队的任务控制中心——扫描本地网络（或手动添加一台，包括通过一个已连接到位于不同物理网络上的 HYDRA-UMC 的 VPN 隧道），连接到所有找到的控制器，并从一个全屏工业仪表盘并排实时点动/监控/重新配置其中任意一台。

它使用的是与 [HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) 完全相同的线路协议——同一个无头式后端，[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 自身的浏览器界面也只是作为它的另一个客户端与之通信——完整契约参见 [`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)，该文档专门为支持本项目而新增。从 SUITE 所做的更改会实时出现在打开的浏览器标签页中，反之亦然——是通过 WebSocket 实现的真正双向实时同步，而非一次性的导入/导出。

**诚实说明，与本生态系统其余文档所采用的惯例一致：** 这是第一个真实可用的版本，而非成品。具体哪些功能今天已真正实现并经过端到端验证、哪些被刻意留待以后，参见 [`docs/ROADMAP.md`](docs/ROADMAP.md)。截至本版本，本生态系统支持的每一个真实机器人型号都已接入 3D 视口，具备真实的 STL 几何数据和经数值验证的正向运动学（Parol6、Faze4、AR3、AR4、UR3e/5e/10e/16e/20、xArm6、Lite 6、e.DO），外加一个基于基本几何体构建的“通用”后备型号，适用于任何没有专属网格集的型号。

## 🧩 在 HYDRA-UMC 中的角色

**HYDRA-UMC-SUITE** 是适用于 Windows 和 Linux 的单元桌面指挥中心：它找出网络上的每个 HYDRA-UMC-SERVER（子网扫描和 mDNS，或手动输入地址），连接任意多个，并在带 3D 视图的 Qt Quick 界面中并排显示、点动和配置它们的机器人。它是 STUDIO 的桌面对应物，使用相同的协议，不做任何安全决定：这些仍由各服务器负责。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-SUITE architecture" width="100%">
</p>

## 🖼️ 屏幕截图

在测试台上以 1920×1080 截取，使用示例数据，背后没有真实的安装。

<table>
<tr><td width="50%" valign="top"><img src="images/screenshots/overview.png" alt="概览：当前控制器、其系统指标，以及包含型号、角色、状态和速度的机器人列表。" width="100%"><br><sub>概览：当前控制器、其系统指标，以及包含型号、角色、状态和速度的机器人列表。</sub></td><td width="50%" valign="top"><img src="images/screenshots/robot-control.png" alt="机器人控制：实机或模拟模式、预约按钮、六个关节滑块、回放和工具附件。" width="100%"><br><sub>机器人控制：实机或模拟模式、预约按钮、六个关节滑块、回放和工具附件。</sub></td></tr>
<tr><td width="50%" valign="top"><img src="images/screenshots/flasher-studio.png" alt="Flasher Studio：选择开发板和机器人插槽，查看更新经过的路径，选择固件文件并通过 CAN 烧录。" width="100%"><br><sub>Flasher Studio：选择开发板和机器人插槽，查看更新经过的路径，选择固件文件并通过 CAN 烧录。</sub></td><td width="50%" valign="top"><img src="images/screenshots/tester-center.png" alt="Tester Center：开发板的状态 LED、环形 LED、OLED 模式、持久化检查、自检和原始总线监视器。" width="100%"><br><sub>Tester Center：开发板的状态 LED、环形 LED、OLED 模式、持久化检查、自检和原始总线监视器。</sub></td></tr>
<tr><td width="50%" valign="top"><img src="images/screenshots/safety-limits.png" alt="安全限制：点动的启用、预约规则，以及按机器人型号设置的点动和热床温度上限。" width="100%"><br><sub>安全限制：点动的启用、预约规则，以及按机器人型号设置的点动和热床温度上限。</sub></td></tr>
</table>

## ✨ 功能

### 可视化指挥台

窗口顶部有一个常驻的、受游戏主机菜单启发的标题栏，使用官方 HYDRA-UMC 图标和 HYDRA-UMC-UPDATER 的深海军蓝/青色配色。它显示产品名称、连接状态和版本，并带有全局 STOP 按钮和应用菜单（语言、支持包、键盘快捷键、关于）。通往各面板的导航是左侧边栏。这不是模拟的仪表盘：每个面板都作用于真实的服务器。

### 🛑 全局 STOP

**STOP** 按钮始终位于窗口顶部，在每个面板上都可见。一次点击，无需确认：它会在每个已连接的服务器上调用 `POST /api/stop-all`，停止所有机器人，即使被其他账户预约。它会显示结果：全部停止时显示绿色消息；当有机器人未停止、停止状态无法保存或没有任何响应确认停止时（**STOP 未确认**），显示红色消息并保持到下一次 STOP。如果服务器限制了该调用，则逐台停止机器人。**F12** 在键盘上执行相同操作（列在 **≡ > 键盘快捷键(K)** 中）；它是单独的功能键，因此不会按下获得焦点的按钮，也不会关闭任何内容。

### Qt Quick 界面

HYDRA-UMC SUITE 只有一个界面，用 Qt Quick（QML）编写：一个独立的 `ApplicationWindow`（`assets/qml/Main.qml`），由 `qt_suite.py` 与未改动的 `SuiteController` 相连。这与 HYDRA-UMC-OS-REBUILDER、HYDRA-UMC-UPDATER、URTC-TESTER、URTC-FLASHER 和 HYDRA-UMC-EDITOR-URDF 使用的模式相同，结构也与 HYDRA-UMC-STUDIO 一致：一个导航侧边栏（根菜单加上 Industrial、URTC 和 HYDRA-UMC 子菜单，见 `hydra_suite/nav_items.py`）和一个每次显示 33 个面板之一的内容区。3D 视口和预览由专用的 `OffscreenRobotRenderer`（独立的 `QOpenGLContext`、`QOffscreenSurface` 和帧缓冲，不使用 Qt Quick 自带的 `QQuickFramebufferObject`，否则整个界面会被迫从 Windows 上 Qt Quick 默认的 Direct3D 11 后端切换到 OpenGL）用同一套渲染代码（`RobotGLRenderer`）绘制，并以图像形式交给 QML。早先的经典窗口（带可停靠面板的 `QMainWindow`）已被移除；它的全部功能都在这个界面中，用 `python main.py` 启动。

### 功能特性

- **🔍 网络发现** —— 并发子网扫描(`GET /api/hydra-info`)与真实的 mDNS/Bonjour(`_hydra._tcp`,与 `server.ts` 发布、HYDRA-UMC-IOS-CONTROL 已经查询的服务相同)共同运行,针对真实的 HYDRA-UMC SERVER 服务器进行发现,并按 host:port 去重;外加针对两者都无法到达的任何目标(不同子网、VPN 隧道)的手动按地址添加。
- **🐝 集群连接** —— 可同时连接任意数量的 HYDRA-UMC 服务器，每一个都拥有自己独立的实时 WebSocket 同步；可选择哪一个是其他面板的“活动”对象。
- **📊 概览** —— 逐控制器的机器人名册：型号、角色、在线状态、速度/加速度，一目了然。
- **🦾 机器人控制** - 范围限定在型号范围内的每关节滑块、速度/加速度滑块、录制轨迹的播放 / 暂停 / 停止、工具（需确认）、阀门和泵，全部以原子命令实时写回。
- **🔐 预留、安全限制与 Live / Sim** - 机器人控制面板有一个访问栏：为本程序预留或释放所选机器人（保持期间会自动续期），查看其他机器人由谁持有，管理员还可以接管。每次预留、释放、点动启用和命令都带有本程序启动时选定的控制器 ID，拒绝情况（其他账户、同一账户在别处、缺少控制器 ID、点动未启用）都会以各自的提示出现在屏幕上。点动的大小和热床的最高目标温度从服务器读取（`GET /api/safety-limits`）并在发送前检查；管理员可在 **安全限制** 面板中按型号编辑它们，同时设置可选的点动启用（默认关闭）和必填的控制器 ID。每个机器人都有 **Live / Sim** 开关（默认 Live）：在 Sim 下，任何会移动机器人或接通设备的内容都不会离开本程序，而 STOP 始终会发出。关节滑块遵循型号的范围，含有范围外点的 Work 会被拒绝并列出这些点，机械臂够不到其点的 Work 会连同这些点被拒绝，也可以以机器人底座为基准缩放后加载，打开热床加热器前会先询问。 写入是有条件的:每次写入都带有此程序最后看到的机器人修订号(`If-Match`),如果期间有其他人修改了机器人,服务器返回 412,不会应用任何内容,机器人会被重新读取并弹出通知(标准模式检查预约、工作台和一次性命令;严格模式检查除 STOP 外的全部命令;关闭则不检查;该选项位于预约列表下方;STOP 永远不检查)。XY 工作台的点动是一条原子的 `table` 命令,服务器通过 WebSocket 推送预约,因此在推送到达期间面板不再轮询,管理员可在 **生态系统 > 审计记录** 中读取仅追加的审计记录,其 SHA-256 链会被(服务器和本程序)校验两次。 管理员还可在 **生态系统 > 用户** 中创建、更改和删除服务器的账户(管理员或操作员)。 **生态系统 > 服务器管理** 界面还可设置谁可以使用本地 AI 中继、主机信息是否要求登录、TLS(含证书指纹)以及服务器的蓝牙 LE 服务,并显示每个值的来源。 **生态系统 > 已提交的模型** 列出 URDF 和 STL 编辑器提交到服务器的模型,并保存其中一个的 URDF。
- **🧊 真实 3D 视口** —— OpenGL 3.3，真实的 STL 网格，针对全部 24 个真实机器人型号的真实正向运动学（与 HYDRA-UMC STUDIO 自身的 TypeScript 实现经数值验证，结果逐位一致），外加一个基于基本几何体构建的“通用”后备型号——两者都不是风格化的占位符。
- **📍 轨迹点** —— 记录所选机器人的实时姿态，按需点动回到任意已记录的点位。
- **🧭 一个侧边栏，一个内容区** - 通过左侧导航（根菜单加上 Industrial、URTC 和 HYDRA-UMC 子菜单）逐个进入各面板，分组方式与 HYDRA-UMC-STUDIO 的侧边栏相同。窗口以带原生标题栏的最大化状态启动，**F11** 可切换真正的全屏。
- **💾 记住的服务器和支持包** - 添加服务器时 *记住* 默认已勾选（取消勾选则不保存任何内容）：地址、昵称和用户名保存在配置文件中，密码通过 `keyring` 保存到操作系统的安全存储（Windows 凭据管理器、macOS 钥匙串、Linux 桌面的 Secret Service），绝不写入文件；没有安全存储时会再次询问密码。应用菜单可导出供支持使用的 zip，包含版本、服务器列表和客户端日志，不含密码、用户名或令牌。
- **🌐 8 种语言** —— 英语、西班牙语、意大利语、法语、德语、简体中文、日语、葡萄牙语（与 URTC-FLASHER/URTC-TESTER 相同的 `language/*.lng` 惯例），从“语言”菜单切换（重启后生效）。
- **📷 摄像头** —— 每个控制器的真实摄像头名册（存在哪些摄像头、其类型、连接状态，以及一个真实的 USB/IP（RTSP）来源类型切换，配有通用、不限品牌的主机/端口/路径/凭证字段），与真实服务器同步，方式与此处的其他每个面板相同，还带有真实的实时视频：元数据自始至终都是真实的，每张摄像头卡片都会渲染真实的 MJPEG 视频流本身（HYDRA-UMC-VISION-STREAMER 自身的 `stream serve`，通过 HYDRA-UMC-SERVER 的 `GET /api/camera/:id/stream` 中继）。通过一个真实的 JPEG SOI/EOI 标记扫描客户端（与 HYDRA-UMC-ANDROID-CONTROL 自身的 `MjpegStreamParser.kt` 已经使用的真实方法相同）实现，已对真实 USB 和 IP 硬件验证。
- **🛠️ 工具附件配置，11/11 面板全部完成** —— CNC、激光、加热床、真空吸附台、ATC（自动换具装置）、XY 工作台、料架管理、Pick & Place、Kinematic Brain Stage、Flasher 以及 Tester——与 HYDRA-UMC STUDIO 自身的每一个工具专属界面实现了真实的功能对等，每一个都是忠实移植（包括 STUDIO 自身源代码中有时有些怪异的真实行为，故意在此处完整复现而非"修复"），每个都有自己真实的无头测试覆盖。CNC/激光/加热床/真空吸附台共享一个 `moduleConfigComponent` 实现（STUDIO 自身的 `CNC.tsx`/`Laser.tsx` 除模块键外完全相同）；其余 7 个各自需要一个专门构建的真实面板。加热床和真空台通过 `render/module_rig.py` 使用 STL。PnP、CNC 和激光使用 `render/pnp_rig.py`，每个独立文件夹包含 7 个运动部件网格和 160 个独立零件。`OffscreenRobotRenderer` 显示各个总成。参见[机器模型](docs/MACHINE_ASSETS.md)。
- **🔑 两步登录** - **生态系统 > Server Admin** 有一张用于您当前登录账户的卡片(在其所有者开启之前是关闭的):otpauth 地址的二维码(由一个与网页程序生成相同图案的小型编码器在此绘制)、带复制按钮的可手动输入密钥、第一个验证码，以及只显示一次的十个一次性恢复码。服务器凭据对话框有一个供已开启账户使用的验证码输入栏(只在内存中保留给那一次登录，绝不保存)，**生态系统 > 用户**有一个按钮，可为丢失手机和恢复码的账户移除第二步。

---

### 🧩 可选真空台模型

在真空台菜单中选择六种真实STL模型之一：160 × 120、230 × 210、230 × 250、232 × 217、240 × 240或250 × 250 mm。底座厚15 mm，含定位壁的总高度为16.2 mm。宽度和长度可按5 mm步长调整（10–5000 mm）。仅缩放平面尺寸，厚度保持不变。选择预设模型可恢复原始尺寸。自定义尺寸通过SERVER同步；缩放后的孔和通道仅用于布局显示，并非重新生成的制造用STL。切换型号保留位置、泵和阀门状态；重置选择160 × 120 mm并关闭泵和阀门。旧型号或未知型号ID显示第一个模型。STUDIO和SUITE的两种界面使用相同目录以及机器人配置中的modelId。

[型号、配置与重新生成指南](docs/VACUUM_TABLE_MODELS.md).

### 🔥 加热床模型

四种STL预设：100×100、200×100、200×200和255×255 mm，厚度均为5 mm。宽度和长度可按5 mm步长调整（25–5000 mm）；选择预设会恢复尺寸，但不会改变加热状态。仅供可视化，不是电气或制造设计。

[加热床模型 — STL / OpenSCAD](docs/HEATED_BED_MODELS.md).

### 🗄️ 可配置的 STL 料架

STL 料架：宽度和深度为 40–1000 毫米，以 1 毫米递增；可放置 1–24 块电路板，固定间距为 10 毫米。这些是显示设置，并非机器人标定。

[可配置的 STL 料架 — STL / OpenSCAD](docs/RACK_MODELS.md).

### 🛠️ 独立的机器模型

JuanenPnP、JuanenCNC 和 JuanenLaser 使用独立的 STL 副本，LumenPnP 保留原始模型。请在各自文件夹中编辑模型。显示采用 CAD 尺寸，原有尺寸设置不会拉伸模型。

[独立的机器模型 — STL](docs/MACHINE_ASSETS.md).

这些原创JuanenPNP / HYDRA-UMC模型及其SCAD源文件采用GPL-3.0；它们不是Opulo机器的CAD文件。

## 🔒 安全与防护

| 威胁 | 防御 | 位置 |
|---|---|---|
| 密码保存在设置文件中 | 凭据通过 `keyring` 存入系统的安全存储（Windows 凭据管理器、Linux 的 Secret Service）；如果计算机没有真正的存储，程序什么也不保存，而不是明文写下密码 | `hydra_suite/credentials.py` |
| 给出错误或恶意应答的服务器 | 发现应答必须带有类型正确的必需键，客户端把每个答复都当作不可信；验证脚本向其提供恶意应答，并检查应用既不崩溃也不接受 | `hydra_suite/net/discovery.py`, `tests/verify_hostile_server_answers.py` |
| 网络上的流量被读取或服务器被冒充 | 客户端使用会验证 TLS 证书的 `httpx`，程序没有关闭验证的开关；TLS 本身在服务器上是可选的，默认关闭（Server Admin），因此在明文 HTTP 的局域网中没有任何东西隐藏流量 | `hydra_suite/net/client.py` |
| 等待或丢失的停止 | STOP 始终位于顶栏（也可按 F12），不做任何询问，并以 2 秒限制和一次重试向每个已连接服务器调用 `POST /api/stop-all`；如果有机器人没停下、状态无法保存或没有任何确认，红色消息会保留到下一次 STOP | `hydra_suite/net/client.py`, `qt_suite.py`, `tests/verify_stop_all.py` |
| 误降低了某个访问选项（语音、MAVLink、蓝牙、TLS 等） | Server Admin 面板显示每个值的来源，锁定由服务器环境设置的内容，降低保护前先询问，并在屏幕上保留警告：复述所说内容的语音回复、识别置信度为 0、未签名的 MAVLink 消息，或关闭 MAVLink 签名 | `hydra_suite/panel_logic/server_security.py`, `tests/verify_server_security.py` |
| 导入了机器人够不到的 Work，或审计记录被篡改 | Work 必须在容差内适合机器人（默认 5 毫米，`work_reach_tolerance_mm` 中可设 0.5 到 50 毫米），否则被拒绝；审计记录可作为哈希链检查，由服务器（`?verify=1`）以及本程序对其收到的内容进行 | `hydra_suite/reach.py`, `hydra_suite/access.py` |

**它绝不做的事：** 决定安全或充当硬件紧急停止路径。每项限制、角色和预约都属于服务器；本应用从未对真实控制器或机器人运行过。

## 🔌 接口

| 主题或路由 | 内容 |
|---|---|
| `/api/*`, `/ws` | HYDRA-UMC-SERVER 的 REST 和 WebSocket 协议，带 `X-Hydra-Client: suite` 标头，管理员可单独允许或阻止本应用 |
| `GET /api/hydra-info`, `_hydra._tcp.local.` | 发现：端口 3000 的子网扫描（每台主机 1.5 秒，同时 64 台）和 mDNS（4 秒），或手动输入的地址（也可通过 VPN） |
| `HYDRA_UMC_DATALAKE_URL` | 遥测面板使用的 HYDRA-UMC-DATALAKE 可选地址 |
| `hydra_suite/can_ota.py` | 通过服务器的 Flasher 与 Tester CAN-OTA 层级（URTC 和 HYDRA-UMC），在真实板卡出现前使用内置模拟 |
| F11, F12 | F11 切换全屏；F12 发送全局 STOP |

## ⚙️ 配置

程序保存一个小的 `hydra_suite_config.json`：在该文件夹可写时（便携副本、源码检出）放在程序旁边，否则放在用户自己的文件夹（Windows 为 `%APPDATA%\HYDRA-UMC-SUITE`，Linux 为 `$XDG_CONFIG_HOME/hydra-umc-suite`）。下面的访问开关属于 Server Admin 编辑的服务器，而不是这个文件。

| 变量 | 默认值 | 设置内容 |
|---|---|---|
| `language` | `english` | 界面语言：english、spanish、german、french、italian、japanese、chinese 或 portuguese（`language/*.lng`） |
| `work_reach_tolerance_mm` | `5.0` | 导入的 Work 的某个点可以偏离所需姿态多远，范围 0.5 到 50 毫米 |
| `HYDRA_UMC_DATALAKE_URL` | 空 | 遥测面板使用的 DATALAKE 地址 |
| `aiAccess` | `open` | 谁可以使用本地 AI 中继：`open` 为任何已登录账户，`admin` 仅管理员 |
| `infoAuth` | 关闭 | 对只读主机信息（指标、进程监控、生态系统状态）要求登录 |
| `tls.enabled` | 关闭（明文 HTTP） | 使用你指定的证书和密钥启用 HTTPS 与 WSS；画面显示正在使用的证书指纹 |
| `ble.mode` | `off` | 供服务器附近手机使用的蓝牙 LE：`off`、`state`（仅发布状态）或 `commands`（也接受命令）；未知词表示关闭 |
| `ble.requireEncryption` | 开启 | 命令特征值的写入和状态的读取只在加密链路上进行；只有变量为 `off` 才会关闭 |
| `mqtt.mode` | `off` | 连接单元代理的 MQTT 桥：`off`、`state` 或 `commands`，以及其 URL、前缀和用户 |
| `voice.includeHeardText` | 关闭 | 语音回复会复述所说的话；这属于个人数据，所以默认关闭，变量中只有恰好为 `1` 才会开启 |
| `voice.minConfidence` | `0.6` | 语音识别器接受启动运动请求所需的最低置信度（0 到 1）；0 表示关闭检查，停止命令从不被拦下，变量中的无效数字会被忽略 |
| `mavlink.signingKeyFile` | 空（不签名） | UAV 桥的 MAVLink 2 签名：包含 32 字节密钥的文件路径（32 个原始字节或 64 个十六进制字符）；只保存路径，绝不保存密钥，桥在启动时读取 |
| `mavlink.signingAllowUnsigned` | 关闭 | 仍接受未签名的消息（尚不签名的载具）；开启期间画面会给出警告 |

## 🚀 快速开始

需要 Python 3.12 或更高版本；要做有用的事，还需要正在运行的 HYDRA-UMC-SERVER（“服务器”面板会扫描网络或接受地址）。

```bash
python -m venv .venv                   # Windows: .venv\Scripts\activate - Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py                         # starts the app; F11 toggles full screen, F12 sends the global STOP
python tools/run_offline_verifiers.py  # every verifier under tests/, headless
```

版本显示在 **帮助 > 关于** 中。用 `build_exe.bat` / `build_exe.sh` 构建绝不会改变它；只有显式命令 `python tools/hydra_project_tool.py bump` 才会。每个版本的变更见 [`CHANGELOG.md`](CHANGELOG.md)。

## 🧪 测试

运行 `python tools/run_offline_verifiers.py` 会执行 44 个自动测试。 每个都是包含大量检查的验证脚本，而不是单个断言；它们需要 PySide6 和其他依赖，在无界面的 Qt 平台下运行，从不连接真实服务器或机器人。

CI 运行 `HYDRA_UMC_CI=1 python tools/ci_validate.py`，检查清单、文档、八个 README 和图片。

## 🏗️ 构建与发布

### 快速开始

### 系统要求
- Python 3.12+（CI 使用 3.12；本地也在 3.14 上运行）
- 一台正在运行的 [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 服务器供连接

### 安装

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

以最小 1280x720 的最大化窗口启动（依照本应用自身的设计规范）——随时按 **F11** 在全屏和普通最大化窗口之间切换，因此它绝不会真的把你困住而没有退出方式。使用 **Servers** 面板扫描你的网络，或按地址添加一台 HYDRA-UMC SERVER 服务器。

随时按 **F12** 发送全局 STOP（顶部栏中的 **STOP** 按钮作用相同）。

### 技术栈

- **UI 框架：** PySide6（Qt6）与 Qt Quick（QML）——只有一个界面，没有重新发明自定义停靠框架
- **3D 渲染：** PyOpenGL（核心配置 GLSL 着色器）+ numpy-stl
- **网络通信：** `httpx`（REST）+ `websockets`（实时同步），通过 `qasync` 与 Qt 自身的事件循环集成——没有单独的工作线程
- **数学运算：** NumPy（用于正向运动学的 4x4 齐次变换）

### 构建独立可执行文件

两种途径，结果相同（Windows 上是 `dist/HYDRA-UMC_SUITE.exe`，Linux 上是 `dist/HYDRA-UMC_SUITE`）——无论哪种方式，运行输出都无需安装 Python。

**自动化（推荐）：**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

每个脚本都会创建/复用 `.venv`，向其中安装 `requirements.txt` + PyInstaller，清理任何先前的 `build/`/`dist/`，用 PyInstaller 编译（打包 `assets/` 及本应用实际使用的仅 4 个 Qt 插件子文件夹——`platforms`/`styles`/`imageformats`/`iconengines`，而非整个 PySide6 包，这正是让结果保持在数十 MB 而非数百 MB 的原因），并将 `README.md`/`LICENSE`/`docs/` 及可编辑的 `language/*.lng` 文件复制到可执行文件旁边，而不是将它们冻结在其内部。

**等效的手动方式**，如果你想亲自查看/控制每一个步骤（与上述脚本运行的命令相同）：

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux

pip install -r requirements.txt
pip install pyinstaller

python -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_SUITE" ^
    --add-data "assets;assets" ^
    --add-data "<PySide6 install dir>\plugins\platforms;PySide6\plugins\platforms" ^
    --add-data "<PySide6 install dir>\plugins\styles;PySide6\plugins\styles" ^
    --add-data "<PySide6 install dir>\plugins\imageformats;PySide6\plugins\imageformats" ^
    --add-data "<PySide6 install dir>\plugins\iconengines;PySide6\plugins\iconengines" ^
    --hidden-import qasync --hidden-import websockets ^
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets ^
    --hidden-import OpenGL.platform.win32 ^
    main.py

# 随后将 README.md、LICENSE、docs/ 及 language/ 复制到 dist/HYDRA-UMC_SUITE.exe 旁边
```

在 Linux 上（确切的、经过测试的命令见 `build_exe.sh`），使用 `:` 而非 `;` 作为 `--add-data` 分隔符，删除 `OpenGL.platform.win32` 隐式导入（仅限 Windows），删除 `--windowed`，并注意那里的插件路径要深一层嵌套（`<PySide6 目录>/Qt/plugins/platforms` 相对于 Windows 扁平的 `<PySide6 目录>\plugins\platforms`）——这是该 wheel 包自身的打包细节，并非任一脚本自行选择的。仓库根目录下的 `HYDRA-UMC_SUITE.spec` 是 PyInstaller 自身在上一次构建中生成的规范文件——可以安全删除并重新生成，不是手工维护的。

### 校验安装程序

Windows 安装程序没有使用 Authenticode 签名，因此运行时 Windows SmartScreen 可能会发出警告。作为替代，发布时会在安装程序旁附上其 SHA-256 校验和（`.sha256`）与 Ed25519 签名（`.sig`）。运行前请先核对：用 `sha256sum`（或 `Get-FileHash`）比对校验和，并用 HYDRA-UMC-TOOL-CLI 的 `hydra-sign verify --pub PUBLIC.pem FILE`，配合 HYDRA 发布密钥的公钥验证签名。这不能取代 Authenticode，只能确认文件就是已发布的那个。

## 🩺 故障排除

| 你看到 | 原因 | 处理 |
|---|---|---|
| “服务器”面板什么也没找到 | 服务器在另一个子网，防火墙阻止了 3000 端口或 mDNS，或服务器未运行 | 按地址添加服务器（VPN 隧道也可以） |
| 每次启动都要求输入密码 | 这台计算机没有真正的安全存储，所以程序不保存密码 | 安装 Secret Service 提供程序（Linux）或在 Windows 上登录；这是有意为之 |
| STOP 消息一直是红色 | 有机器人没停下、停止状态无法保存，或没有服务器确认停止 | 阅读消息，检查机器人，再按一次 STOP；它会保留到下一次 STOP |
| 导入的 Work 被拒绝 | Work 的某个点超出了此机器人可达范围的容差 | 选择另一个机器人型号，或提高 `work_reach_tolerance_mm`（最高 50） |

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-SUITE" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
HYDRA-UMC-SUITE/
├── hydra_suite/                                                                                            源代码
│   ├── models.py                                                                                           HydraState/ControllerView/RobotView/CameraView —— 基于真实 settings.json 结构的轻量、可变视图
│   ├── app.py                                                                                              SuiteController —— 管理连接集群与"当前激活"选择；每个面板都与它通信
│   ├── i18n.py                                                                                             8 语言 KEY=Value 加载器（language/*.lng）
│   ├── can_ota.py                                                                                          共享的 CAN-OTA/SPI-OTA 传输层（STUDIO 自身 canOta.ts 的真实移植）—— 供 Flasher 和 Tester 使用
│   ├── logging_handler.py                                                                                  将 Python 日志路由到日志面板
│   ├── diagnostics.py                                                                                      支持包（含版本、服务器和日志的 zip，不含凭据）
│   ├── net/                                                                                                REST、WebSocket 客户端和发现
│   ├── render/                                                                                             OpenGL 视图和运动学
│   ├── robot_catalog.py                                                                                    24 个机器人型号的制造商与自由度元数据,与 STUDIO 的手动保持一致
│   ├── access.py                                                                                           控制器 ID、预留、从服务器读取的安全限制、Live / Sim——不依赖 Qt，不联网
│   ├── reach.py                                                                                            每个型号的工具可到达的位置、逆运动学和 Work 缩放——不依赖 Qt，不联网
│   ├── credentials.py                                                                                      记住的服务器：配置文件和操作系统的安全存储（keyring）
│   ├── joint_limits.py                                                                                     公布了范围的型号的每个关节范围
│   ├── nav_items.py                                                                                        导航：根菜单和 Industrial / URTC / HYDRA-UMC 子菜单
│   └── panel_logic/                                                                                        面板所需且不依赖窗口的内容：层级、默认值、MJPEG 解析、监控图表
├── .github/                                                                                                CI 工作流、issue 模板、PR 模板（通用，生态系统共享）
├── assets/                                                                                                 QML 界面和机器人网格
├── language/                                                                                               english/spanish/french/german/italian/japanese/chinese/portuguese 的 .lng 文件
├── docs/                                                                                                   项目文档
├── tools/                                                                                                  项目工具和 CI 检查
├── tests/                                                                                                  真实的无头测试套件（QApplication，无需显示器）—— 每个面板/子系统一个 verify_*.py，外加运动学移植验证和需要真实运行中 STUDIO 服务器的手动烟雾测试
├── installer/                                                                                              各平台打包说明与资源
├── .vscode/                                                                                                Python 解释器路径、启动配置、推荐扩展
├── images/                                                                                                 横幅和 README 的图片
├── main.py                                                                                                 入口——启动 Qt Quick 界面（最大化，最小 1280x720；F11 切换真正的全屏）
├── qt_suite.py                                                                                             Qt Quick 前端——把未改动的 SuiteController 连接到 QML（全部 33 个面板）
├── verify_qt_suite_shell.py                                                                                不依赖硬件/网络的真实 Qt Quick 外壳检查 —— 刻意放在 tests/ 之外（与 URTC-TESTER/URTC-FLASHER 自己的 verify_qt_*.py 同样的理由），用 `QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py` 运行
├── requirements.txt                                                                                        固定的依赖
├── hydra-umc.project.json                                                                                  生态系统清单 - 版本/家族/父项目，dashboard/updater/OS-REBUILDER 读取的真实来源
├── bump_version.py                                                                                         显式提升版本
├── bump_manifest_version.py                                                                                将 hydra-umc.project.json 的版本与原生版本同步（通用，在整个生态系统中原样复制）
├── build-test.bat / build-test.sh                                                                          激活 .venv 并运行 tools/build_test.py（真实测试套件），不产生变更 - 从不递增版本，也不改动 CHANGELOG.md
├── run.bat / run.sh                                                                                        通过 venv 启动 main.py
├── HYDRA-UMC_SUITE.spec                                                                                    PyInstaller 规格文件（见下方 build_exe.bat/.sh）
├── build_exe.bat                                                                                           一步式 Windows 构建 -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                                                                                            一步式 Linux 构建 -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md   每个版本的变更
└── test.sh                                                                                                 运行测试
```

</details>

## 🗺️ 路线图与已知限制

**目前已知的限制**

* CAN-OTA 的 URTC Tool Head 和 Advanced Expansion 层级没有通向硬件的真实中继隧道；该链运行在内置模拟上。
* 组合机器人模式（`combinedWith`）存在于 STUDIO 的数据模型中，但本应用没有提供。
* 此 README 还没有截图。
* 本应用从未对真实控制器或机器人运行过，Qt Quick 是它唯一的界面：经典窗口已被移除。

**下一步：** STUDIO 的每项新功能都会移植到这里。已完成与推迟事项的详细清单见 `docs/ROADMAP.md`。

## 🌍 语言

本 README 和仓库文档提供八种语言：英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语（葡萄牙）。它们同时编写，并由 CI 检查八个文件拥有相同的章节和相同的链接。

## 🔗 相关项目

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**父项目**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— 每个控制客户端真正通信的真实无头后端(REST/WebSocket);本指挥中心是其真实客户端,通过 mDNS 在网络中发现它。

**兄弟项目** —— 同样与 HYDRA-UMC-SERVER 自身 API 通信,各自作为独立客户端
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** —— 具有实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** —— 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** —— 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** —— 面向机载 7 英寸 DSI 触摸屏的原生触控界面,直接嵌入 CM5 本体。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** —— 通过 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界(仅针对仿真车队测试)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** —— 具备 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** —— 面向足式/人形机器人的协调边界,带有 Boston Dynamics Spot 指令发送器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** —— 读取 3 路钥匙/外壳/联锁 GPIO 信号的激光单元协调器(仅针对模拟芯片测试;无法使激光器上膛或发射)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** —— 面向 OpenPnP 贴片机板级流程的安全高层协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** —— 面向 Moonraker/Klipper 3D 打印机的安全协调边界,具备真实的受控作业指令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** —— 带有惰性导入 rclpy ROS 2 传输层的协调器(尚未在 ROS 2 环境中运行)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** —— 面向搭载摄像头的无人机的协调边界,带有 MAVLink 指令发送器(仅针对模拟器测试)。

**直接相关**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** —— 在仿真与真实硬件之间带有软件碰撞联锁的硬件在环路由器(未在真实硬件上测试);让本指挥中心可以像操控真实硬件一样驱动数字孪生,用硬件在环桥接替换实时 HYDRA-UMC 控制器,而不改变工作流程的其他部分。
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** —— 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢;本指挥中心最终听命于的集群指挥中心,以单个桌面会话无法企及的层级协调多个 HYDRA-UMC 控制器组成的车队。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** —— 具备真实、稳定退出码契约的车队 CLI,是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端;为脚本编写和无图形界面环境提供与本桌面指挥中心相同的 DevOps 功能集,可从命令行使用。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 机器人手臂主板设计——CM5 主机 + 双核 STM32H745,目标是通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂(固件处于早期阶段,尚无已组装的电路板)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** —— 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** —— 每个桥接都据此校验自身指令的共享 JSON-Schema 契约与软件作业门限边界(并非经认证的安全功能)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 面向外部机器连接器的声明式适配器清单注册与校验工具；把 SDK 自身的契约理念扩展到外部机器，而不取代工业网关类项目。

*核心后端与客户端*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** —— 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** —— 面向本应用自身 `assets/meshes/` 库（以及 STUDIO 维护的镜像）的桌面 STL 模型编辑器——变换/替换/移除/添加真实部件，绝不永久删除任何内容。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** —— 面向实体 Universal Robot Tool Controller 板卡的固件,通过 CAN 总线支持 25 种以上工具配置。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** —— 面向 URTC 板卡的桌面图形烧录工具,支持 CAN-OTA 以及全芯片 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** —— 面向 URTC 板卡的桌面实时 CAN 总线诊断工具,每种工具配置对应一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** —— 通过 Web Serial API 实现的浏览器版 URTC-TESTER 替代方案,无需本地安装。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** —— URTC CAN 总线前的网关：允许的标识符列表、速率限制和会话密钥；软件已在计算机上测试，尚未在真实总线上测试。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** —— 面向 Hailo-8 视觉流水线的集成中枢,具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** —— 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** —— 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** —— 以区域状态为授权条件的 Position-Based Visual Servoing 修正律;尚无摄像头位姿估计。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** —— 从文件读取物体位置的 v0 区域入侵、校准新鲜度与 E-STOP 请求逻辑;没有检测器为其供数,也尚未连接任何物理 E-STOP。

*认知 AI 节点(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** —— 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** —— 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** —— 具备受限、需确认的 Watch 中继的真实语音前端(VAD + 意图解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** —— 基于真实规则的任务分解,以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** —— 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — 面向生态系统自身的本地、按策略门控的 AI 维护技师——观察、诊断并提出修复建议;两个最高风险等级目前特意尚未实现。

*编排与集群*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** —— 基于真实 HTTP API 的真实优先级任务队列,支持去重。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** —— 具备重试/退避与身份不匹配检测的真实基于 gRPC 的车队健康看门狗。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** —— 具备真实障碍物/工作空间碰撞校验的真实基于 RRT 的三维路径规划器。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** —— 经过多单元收敛属性测试的真实 CRDT LWW-Element-Map 状态同步。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** —— 面向数字孪生引擎的集成中枢,具备真实的版本兼容性同步契约。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** —— 面向真实 URDF 子集的真实正向运动学与关节限位校验。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** —— 具备 YOLO/COCO 标注导出功能的真实程序化 2D 场景生成器。

*数据与分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** —— 具备真实数据摄入/查询 HTTP API 的真实 sqlite3 时序数据存储。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** —— 具备漂移监测能力的真实 FFT + 统计基线异常检测器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** —— 基于 DATALAKE 历史数据的真实 OEE/可用率计算,支持可复现的 CSV 导出。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** —— 面向 DATALAKE 的真实 CAN/WebSocket 数据摄入管道,支持序列去重。

*工业网关*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** —— 中继至工业协议的集成中枢,具备真实的指令白名单/背压控制层。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** —— 经真实二进制协议客户端会话验证的真实 OPC-UA 地址空间。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** —— 具备可选按客户端认证与主题 ACL 的真实 MQTT 代理。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** —— 具备降级模式输出的真实 MTConnect `/probe` 与 `/current` XML 端点。

*辅助工具与生态系统运维*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** —— 基于 DATALAKE/ANOMALY-DETECTOR 的智能摘要与异常高亮面板,具备诚实的统计回退机制。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** —— 带有触觉提醒模式与配对手机语音中继的 WearOS 伴侣应用(尚未在实体手表上运行)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** —— 面向板卡安装机架的固件,具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** —— 面向热成像/RGB 检测工具头的固件及真实 Python 视觉伴侣程序。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** —— 发现、克隆并更新本生态系统中每个仓库的管理类桌面工具。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** —— 构建即刻可烧录、预装生态系统最新版本的 CM5 镜像的 Windows/Linux 桌面工具,具备类似 Raspberry Pi Imager 风格的首次启动 Wi-Fi/用户/SSH 配置。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 维护事件协调器：一个低权限的边缘角色采集经过脱敏的库存/健康快照，一个控制面角色以只读方式渲染它，并请求某个 AI 提供方给出诊断建议——从不应用补丁，也从不部署任何内容。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 可复现的开发主机（Raspberry Pi 5 / CM5），保存整个生态系统的源代码，并在持久队列下运行有界的构建/测试任务；这是专用的开发角色，明确区别于运行中的 CM5。

## 📚 文档

更多阅读：

* **[docs/ROADMAP.md](docs/ROADMAP.md)** —— 今天哪些是真实且端到端验证过的，哪些是刻意仍未纳入范围的。
* **[installer/README.md](installer/README.md)** —— 如何构建 Windows `.exe` 安装程序和 Linux `.deb` 软件包。
* [生态系统的安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [生态系统的威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [本仓库的更新日志](CHANGELOG.md)
* [本仓库的许可证](LICENSE.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（或 `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）：它必须输出 `CI_VALIDATION=PASS`。此检查不要运行 `build.sh` 或 `build.bat`；构建不是检查。
* 八个 README 由 HYDRA-UMC-DOCS 中的同一个源生成；请勿手工编辑。修改源文件，再用 `tools/make_readmes.py` 重新生成。
* 不要在 README 中声称尚未运行过的内容：属实时请写“仅模拟”或“尚未在硬件上试过”。
* 请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md) 和 [SUPPORT.md](SUPPORT.md)。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - [LICENSE](LICENSE).
