<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


### 🖥️ HYDRA-UMC 平台的多控制器集群指挥中心

<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="OpenGL">
</p>


---

## 🎯 概述

**HYDRA-UMC SUITE** 是一款原生的 Windows/Linux 桌面应用程序（Python + PySide6/Qt6），构建为整支 [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) 控制器舰队的任务控制中心——扫描本地网络（或手动添加一台，包括通过一个已连接到位于不同物理网络上的 HYDRA-UMC 的 VPN 隧道），连接到所有找到的控制器，并从一个全屏工业仪表盘并排实时点动/监控/重新配置其中任意一台。

它使用的是与 [HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) 完全相同的线路协议——同一个无头式后端，[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 自身的浏览器界面也只是作为它的另一个客户端与之通信——完整契约参见 [`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)，该文档专门为支持本项目而新增。从 SUITE 所做的更改会实时出现在打开的浏览器标签页中，反之亦然——是通过 WebSocket 实现的真正双向实时同步，而非一次性的导入/导出。

**诚实说明，与本生态系统其余文档所采用的惯例一致：** 这是第一个真实可用的版本，而非成品。具体哪些功能今天已真正实现并经过端到端验证、哪些被刻意留待以后，参见 [`docs/ROADMAP.md`](docs/ROADMAP.md)。截至本版本，本生态系统支持的每一个真实机器人型号都已接入 3D 视口，具备真实的 STL 几何数据和经数值验证的正向运动学（Parol6、Faze4、AR3、AR4、UR3e/5e/10e/16e/20、xArm6、Lite 6、e.DO），外加一个基于基本几何体构建的“通用”后备型号，适用于任何没有专属网格集的型号。

---

## 🏭 功能特性

- **🔍 网络发现** —— 针对真实 HYDRA-UMC STUDIO 服务器的并发子网扫描（`GET /api/hydra-info`），外加针对扫描无法到达的任何目标（不同子网、VPN 隧道）的手动按地址添加。
- **🐝 集群连接** —— 可同时连接任意数量的 HYDRA-UMC 服务器，每一个都拥有自己独立的实时 WebSocket 同步；可选择哪一个是其他面板的“活动”对象。
- **📊 概览** —— 逐控制器的机器人名册：型号、角色、在线状态、速度/加速度，一目了然。
- **🦾 机器人控制** —— 每个关节的旋钮 + 滑块（HYDRA-UMC STUDIO 自身 `RotaryKnob`+`FuturisticSlider` 点动组合的桌面版对应物）、速度/加速度滑块，全部实时写回。
- **🧊 真实 3D 视口** —— OpenGL 3.3，真实的 STL 网格，针对全部 24 个真实机器人型号的真实正向运动学（与 HYDRA-UMC STUDIO 自身的 TypeScript 实现经数值验证，结果逐位一致），外加一个基于基本几何体构建的“通用”后备型号——两者都不是风格化的占位符。
- **📍 轨迹点** —— 记录所选机器人的实时姿态，按需点动回到任意已记录的点位。
- **🪟 类 Photoshop 的可停靠工作区** —— 每个面板都是一个真正的 `QDockWidget`：可拖动使其自由浮动，拖回停靠或合并为选项卡组，拆分工作区，关闭，并从 View 菜单重新显示。将面板浮动化会使其成为一个真正独立的顶层窗口，因此将它拖到第二个（或第三个）物理显示器上并留在那里开箱即可使用——Qt/操作系统窗口管理器会像对待任何其他窗口一样放置它，无需额外的“多显示器模式”。
- **🌐 5 种语言** —— 英语、西班牙语、意大利语、法语、德语（与 URTC-FLASHER/URTC-TESTER 相同的 `language/*.lng` 惯例），从“语言”菜单切换（重启后生效）。
- **📷 摄像头** —— 每个控制器的真实摄像头名册（存在哪些摄像头、其类型、连接状态），与真实服务器同步，方式与此处的其他每个面板相同——视频画面本身是一个明确标记的占位符，与 HYDRA-UMC-STUDIO 自身 CamerasView.tsx 的诚实边界一致（本生态系统中目前尚不存在任何真实的摄像头硬件/视频流）。

---

## 📸 照片

尚无截图——尚未为文档拍摄。请启动它（见下文）以查看真实的样子，而不是日后信赖一张过时的图片。

---

## 📂 仓库结构

```text
HYDRA-UMC-SUITE/
├── main.py                        # 入口点——全屏，最小 1920x1080，F11 切换全屏/窗口模式
├── requirements.txt
├── HYDRA-UMC_SUITE.spec           # PyInstaller 规范文件（见下方 build_exe.bat/.sh）
├── build_exe.bat                  # 一键式 Windows 构建 -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # 一键式 Linux 构建 -> dist/HYDRA-UMC_SUITE
├── README.md                      # 本文件
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- 翻译
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView —— 对真实 settings.json 结构的
│   │                                 薄型、易于修改的视图
│   ├── app.py                      # SuiteController —— 拥有整个连接集群、“活动”选择，每个面板都与它通信
│   ├── i18n.py                     # 5 语言 KEY=Value 加载器（language/*.lng）
│   ├── net/
│   │   ├── discovery.py             # 针对 GET /api/hydra-info 的并发子网扫描
│   │   └── client.py                # 每服务器 REST + WebSocket 连接、实时双向同步、登录
│   ├── render/
│   │   ├── kinematics.py            # 正向运动学（从 HYDRA-UMC-STUDIO 自身的 urKinematicsShared.ts 移植）
│   │   ├── generic_rig.py           # 面向任何没有专属网格集的型号的基本几何体后备装配
│   │   ├── mesh.py                  # STL 加载（numpy-stl）
│   │   └── viewport.py              # QOpenGLWidget —— 真实的 GLSL 着色器管线，环绕相机
│   └── ui/
│       ├── main_window.py           # QMainWindow + QDockWidget 工作区
│       ├── theme.py                  # 加载 assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # 自定义绘制的旋钮（RotaryKnob.tsx 的桌面版对应物）
│       └── panels/                   # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py, cameras_panel.py, logs_panel.py
├── assets/
│   ├── qss/industrial_dark.qss     # 未来工业风的 Qt 样式表
│   └── meshes/                      # 真实的 STL 网格，每个机器人一个文件夹（24 个型号），从 HYDRA-UMC-STUDIO 自身的
│                                       public/models/<robot>/ 复制而来（各自附带自己的 ATTRIBUTION.txt）
├── language/                        # english/spanish/italian/french/german/chinese/japanese .lng 文件
├── docs/
│   └── ROADMAP.md                   # 诚实的“已真正实现 vs. 尚未实现”范围说明
├── tests/                           # 手动集成冒烟测试（需要一个真实运行的 HYDRA-UMC STUDIO 服务器——而非
│                                       模拟的单元测试套件）+ 运动学验证脚本
└── .vscode/                         # Python 解释器路径、启动配置、推荐扩展
```

---

## 🚀 快速开始

### 系统要求
- Python 3.12+（开发/测试基于 3.14）
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

以最小 1920x1080 全屏启动（依照本应用自身的设计规范）——随时按 **F11** 在全屏和普通最大化窗口之间切换，因此它绝不会真的把你困住而没有退出方式。使用 **Servers** 面板扫描你的网络，或按地址添加一台 HYDRA-UMC STUDIO 服务器。

---

## 🛠️ 技术栈

- **界面框架：** PySide6（Qt6）——原生可停靠面板，没有重新发明自定义停靠框架
- **3D 渲染：** PyOpenGL（核心配置 GLSL 着色器）+ numpy-stl
- **网络通信：** `httpx`（REST）+ `websockets`（实时同步），通过 `qasync` 与 Qt 自身的事件循环集成——没有单独的工作线程
- **数学运算：** NumPy（用于正向运动学的 4x4 齐次变换）

---

## 📦 构建独立可执行文件

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

---

## 🔢 版本管理

`hydra_suite/__version__`（显示于 **Help > About**）遵循一种里程表式的 `MAJOR.MINOR.PATCH` 方案，采用十进制进位规则：每次真正构建时，patch 位加 1；一旦超过 9，就重置为 0 并将 minor 位加 1（例如 `0.1.9` -> `0.2.0`）。“真正构建”指的是运行 `build_exe.bat`/`build_exe.sh`——**而非**每一次普通的 `python main.py` 运行。这一递增操作本身由 `bump_version.py` 自动处理（在 PyInstaller 运行之前由两个构建脚本调用），因此打包好的 `.exe`/二进制文件所携带的版本号总是严格新于上一次实际发布的版本。每个节点的具体变更内容见 [`CHANGELOG.md`](CHANGELOG.md)。

---

## 🔗 相关项目

本项目是同一作者（JuanenRac / Electro Hobby 3D）打造的更大规模机器人生态系统的一部分。值得了解，因为某个请求实际所指的可能正是这些项目之一，而非本仓库：

**HYDRA-UMC 平台** —— 多机器人微工厂单元
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 主板本体：Raspberry Pi CM5 主机 + 双核 STM32H745 实时协处理器，通过 CAN-OTA/SPI-OTA 协调最多 8 个分布式机器人手臂。自有硬件 + 固件，GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0。
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** —— HYDRA-UMC 的网页控制仪表盘：多机器人 3D 可视化、运动学/轨迹记录、面向整个平台的 CAN-OTA 刷写与测试。React + Vite + Three.js。
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— 曾经打包在 HYDRA-UMC-STUDIO 自身进程内的无头式后端（Node/Express/WebSocket）。拥有机器人控制 REST/WS API、settings.json 持久化、JWT 身份验证和 mDNS 发现。HYDRA-UMC-STUDIO 现在是一个纯静态前端客户端，通过网络与之通信。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** —— 通过 Wi-Fi/蓝牙控制 HYDRA-UMC 的 Android 应用。真实可用的应用——完整的远程控制功能集、JWT 身份验证、加密凭证存储。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** —— 通过 Wi-Fi 控制 HYDRA-UMC 的 iOS/iPadOS 应用，基于 Flutter 构建（跨平台，可在 Windows 上验证，无需 Mac；最终 `.ipa` 打包仍需 Xcode）。真实可用的应用——功能集与 Android 应用相同。
- **HYDRA-UMC-SUITE**（本仓库）—— 桌面端（Python/PySide6）集群指挥中心：多控制器网络发现、实时双向同步、真实的 3D 机器人视口、类 Photoshop 的可停靠工作区。真实可用，并非占位程序。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** —— 桌面端（Python/PySide6）图形化 URDF 创建/编辑工具，服务于本项目自身的模型目录：从 GitHub 或本地文件夹拉取源文件，验证自由度可行性，通过实时 3D 预览编辑颜色/比例/运动学，并将完成的结果推送到一个正在运行的 STUDIO 服务器。真实可用，并非占位程序。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** —— 面向 HYDRA-UMC 自身 5"/7" DSI 触摸屏（两种尺寸分辨率均为 1280×720）的原生 Flutter 触控界面，运行于 Compute Module 5 上，直接从主板控制同一台服务器。真实可用的雏形，全部 6 个目录界面（仪表盘、手动控制、摄像头、简化 3D 视图、系统指标、登录）均已连接到实时服务器；真正的 Linux 目标构建尚未在真实硬件上运行过（目前仅在 Windows 环境下可用——参见该项目自身的 README）。

**URTC 平台** —— 每个 HYDRA-UMC 机器人手臂所携带的工具头控制器
- **[URTC](https://github.com/JuanenRac/URTC)** —— 通用机器人工具控制器：基于 STM32F303 的 CAN 总线工具头控制器，25 个已完整实现的工具配置文件，支持 CAN-OTA 固件更新。
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** —— 面向 URTC 板卡的桌面端 CAN-OTA + 全芯片 SWD/JTAG 刷写工具（Windows/Linux）。
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** —— 面向 URTC 板卡的桌面端实时 CAN 总线诊断工具，每个工具配置文件对应一个面板（Windows/Linux）。
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** —— 上述两款桌面工具的浏览器端替代方案（Web Serial API + SLCAN），无需本地安装。

**直接相关的工具**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** —— 让本套件能够像驱动真实硬件一样驱动数字孪生，将一台实时的 HYDRA-UMC 控制器替换为一座硬件在环桥接，而无需改变工作流程中的其他任何部分。
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** —— 本套件最终所服从的集群指挥中心，在超出单个桌面会话所能触及的层级上协调多支 HYDRA-UMC 控制器舰队。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** —— 从命令行提供与本桌面套件相同的 DevOps 功能集，适用于脚本编写和无头环境。

**生态系统的其余部分**

除了上述 HYDRA-UMC 和 URTC 平台之外，同一作者还维护着以下领域中的许多其他项目：

- 👁️ **Vision AI Node (Hailo-8)：** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE) · [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER) · [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF) · [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES) · [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Cognitive AI Node (Hailo-10)：** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) · [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE) · [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI) · [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER) · [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestration & Swarm：** [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC) · [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D) · [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER) · [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Digital Twin & Simulation：** [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN) · [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA) · [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)
- 📊 **Data & Analytics：** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE) · [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR) · [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR) · [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Industrial Gateway：** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL) · [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER) · [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER) · [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Complementary Tools：** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) · [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) · [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH) · [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 作者

**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 许可证与版权声明

HYDRA-UMC SUITE 版权所有 (c) 2026 JuanenRac（Electro Hobby 3D）。分发本项目或其衍生作品时必须包含此声明。

本应用的源代码依据 **GNU 通用公共许可证 v3.0（GPL-3.0）** 提供。完整文本见 https://www.gnu.org/licenses/gpl-3.0.html。

**本文档**（本 README 及其自身的翻译版本——`README_spa.md`、`README_ita.md`、`README_fra.md`、`README_deu.md`、`README_zho.md`、`README_jpn.md`）依据 **知识共享 署名-相同方式共享 4.0 国际许可协议（CC BY-SA 4.0）** 提供。完整文本见 https://creativecommons.org/licenses/by-sa/4.0/。

**第三方网格资产：** `assets/meshes/` 下的每一个文件夹都是从该机器人自身官方制造商仓库原样复制而来——**不**受上述 GPL-3.0 覆盖。每一个都附有自己的 `ATTRIBUTION.txt`，注明确切的来源/许可证参考；下表对其进行了汇总。

| 制造商 | 型号 | 许可证 |
|---|---|---|
| Source Robotics | Parol6 | GPL-3.0 |
| Source Robotics | Faze4 | MIT |
| Annin Robotics | AR3, AR4 | MIT |
| Universal Robots | UR3e, UR5e, UR10e, UR16e, UR20 | BSD-3-Clause |
| UFACTORY | xArm6, Lite 6 | BSD-3-Clause |
| Comau | e.DO | BSD-3-Clause |
| Kinova | Gen3 Lite | BSD-3-Clause |
| FANUC | M-710iC | BSD-3-Clause |
| The Robot Studio | SO-ARM100 | Apache-2.0 |
| Kinova | Gen2 (j2s6s200) | BSD-3-Clause |
| AgileX | PiPER | Apache-2.0 |
| Unitree | Z1 | BSD-3-Clause |
| Trossen Robotics | ViperX 300, WidowX 250 | BSD-3-Clause |
| Koch / Low-Cost Robot Arm | Koch v1.1 | Apache-2.0 |
| Universal Robots (classic) | UR3, UR5, UR10 | BSD-3-Clause |

本项目是 [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 的桌面端集群控制对应物——其自身独立的许可证参见该项目自身的仓库，本仓库自身的许可证并不延伸至该仓库,反之亦然。它最终还控制着 [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) 硬件/固件以及（[经由其中继](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)）[URTC](https://github.com/JuanenRac/URTC) 工具头——二者都是拥有各自独立许可证的独立项目。

如果你基于本项目进行开发，请留意这种许可证划分：代码更改应保持 GPL-3.0,每个机器人自身的网格资产都应保持在其原始许可证条款之下（见上表）——每一项都需附带指向本项目及其作者的署名。

## 🛠️ BUILD & RUN

请在发布构建前使用不改动版本的构建检查：

| 操作 | Windows | Linux / macOS |
|---|---|---|
| 构建检查（不修改版本或 CHANGELOG） | `build-test.bat` | `./build-test.sh` |
| 运行 / 开发（如提供） | `run*.bat` 或 `dev*.bat` | `./run*.sh` 或 `./dev*.sh` |

`build-test.bat` 和 `build-test.sh` 会编译或验证项目技术栈，但不会递增 `hydra-umc.project.json`，也不会修改 `CHANGELOG.md`。它们仅可能生成正常的编译器输出。现有的 `build*.bat`、`build*.sh`、`run*` 和 `dev*` 脚本保留各自的版本化或运行时行为；需要该行为时请使用它们。