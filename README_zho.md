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

## ✨ 可视化指挥台

桌面现已提供一个常驻、带有游戏菜单风格的指挥台，使用官方 HYDRA-UMC 图标以及 HYDRA-UMC-UPDATER 的深海军蓝/青色视觉语言。仪表板、机器人控制、相机、轨迹和日志按钮会打开对应的真实可停靠面板；右侧显示实时连接状态、活动服务器目标和 UTC 时钟。这是 Suite 真实功能上的视觉层，而不是模拟仪表板。

## 🏭 功能特性

- **🔍 网络发现** —— 并发子网扫描(`GET /api/hydra-info`)与真实的 mDNS/Bonjour(`_hydra._tcp`,与 `server.ts` 发布、HYDRA-UMC-IOS-CONTROL 已经查询的服务相同)共同运行,针对真实的 HYDRA-UMC STUDIO 服务器进行发现,并按 host:port 去重;外加针对两者都无法到达的任何目标(不同子网、VPN 隧道)的手动按地址添加。
- **🐝 集群连接** —— 可同时连接任意数量的 HYDRA-UMC 服务器，每一个都拥有自己独立的实时 WebSocket 同步；可选择哪一个是其他面板的“活动”对象。
- **📊 概览** —— 逐控制器的机器人名册：型号、角色、在线状态、速度/加速度，一目了然。
- **🦾 机器人控制** —— 每个关节的旋钮 + 滑块（HYDRA-UMC STUDIO 自身 `RotaryKnob`+`FuturisticSlider` 点动组合的桌面版对应物）、速度/加速度滑块，全部实时写回。
- **🧊 真实 3D 视口** —— OpenGL 3.3，真实的 STL 网格，针对全部 24 个真实机器人型号的真实正向运动学（与 HYDRA-UMC STUDIO 自身的 TypeScript 实现经数值验证，结果逐位一致），外加一个基于基本几何体构建的“通用”后备型号——两者都不是风格化的占位符。
- **📍 轨迹点** —— 记录所选机器人的实时姿态，按需点动回到任意已记录的点位。
- **🪟 类 Photoshop 的可停靠工作区** —— 每个面板都是一个真正的 `QDockWidget`：可拖动使其自由浮动，拖回停靠或合并为选项卡组，拆分工作区，关闭，并从 View 菜单重新显示。将面板浮动化会使其成为一个真正独立的顶层窗口，因此将它拖到第二个（或第三个）物理显示器上并留在那里开箱即可使用——Qt/操作系统窗口管理器会像对待任何其他窗口一样放置它，无需额外的“多显示器模式”。
- **🌐 7 种语言** —— 英语、西班牙语、意大利语、法语、德语、简体中文、日语（与 URTC-FLASHER/URTC-TESTER 相同的 `language/*.lng` 惯例），从“语言”菜单切换（重启后生效）。
- **📷 摄像头** —— 每个控制器的真实摄像头名册（存在哪些摄像头、其类型、连接状态，以及一个真实的 USB/IP（RTSP）来源类型切换，配有通用、不限品牌的主机/端口/路径/凭证字段），与真实服务器同步，方式与此处的其他每个面板相同，还带有真实的实时视频：元数据自始至终都是真实的，每张摄像头卡片都会渲染真实的 MJPEG 视频流本身（HYDRA-UMC-VISION-STREAMER 自身的 `stream serve`，通过 HYDRA-UMC-SERVER 的 `GET /api/camera/:id/stream` 中继）。通过一个真实的 JPEG SOI/EOI 标记扫描客户端（与 HYDRA-UMC-ANDROID-CONTROL 自身的 `MjpegStreamParser.kt` 已经使用的真实方法相同）实现，已对真实 USB 和 IP 硬件验证。
- **🛠️ 工具附件配置，11/11 面板全部完成** —— CNC、激光、加热床、真空吸附台、ATC（自动换具装置）、XY 工作台、料架管理、Pick & Place、Kinematic Brain Stage、Flasher 以及 Tester——与 HYDRA-UMC STUDIO 自身的每一个工具专属界面实现了真实的功能对等，每一个都是忠实移植（包括 STUDIO 自身源代码中有时有些怪异的真实行为，故意在此处完整复现而非"修复"），每个都有自己真实的无头测试覆盖。CNC/激光/加热床/真空吸附台共享一个 `ModuleConfigPanel` 实现（STUDIO 自身的 `CNC.tsx`/`Laser.tsx` 除模块键外完全相同）；其余 7 个各自需要一个专门构建的真实面板。相较 STUDIO 仍然存在的唯一差距是这些面板中大多数在 STUDIO 那边具备的实时 3D 预览——`render/viewport.py` 还不支持渲染已挂载模块的几何形状。

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
│   │   ├── discovery.py             # 针对 GET /api/hydra-info 的并发子网扫描 + 真实 mDNS (_hydra._tcp),已去重
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

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**父项目**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— 每个控制客户端真正通信的真实无头后端(REST/WebSocket);本指挥中心是其真实客户端,通过 mDNS 在网络中发现它。

**兄弟项目** —— 同样与 HYDRA-UMC-SERVER 自身 API 通信,各自作为独立客户端
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** —— 具有实时多机器人 3D 可视化的网页控制面板。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** —— 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** —— 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** —— 面向机载 7 英寸 DSI 触摸屏的原生触控界面,直接嵌入 CM5 本体。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** —— 通过真实的 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** —— 具备真实 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** —— 面向足式/人形机器人的协调边界,具备真实的 Boston Dynamics Spot 指令发送器。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** —— 读取 3 项真实钥匙/外壳/联锁 GPIO 安全信号的激光单元安全协调器。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** —— 面向 OpenPnP 贴片机板级流程的安全高层协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** —— 面向 Moonraker/Klipper 3D 打印机的安全协调边界,具备真实的受控作业指令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** —— 具备真实的惰性导入 rclpy ROS 2 传输层的安全协调器。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** —— 面向搭载摄像头的无人机的协调边界,具备真实的 MAVLink 指令发送器。

**直接相关**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** —— 在仿真与真实硬件之间路由指令的真实硬件在环安全联锁;让本指挥中心可以像操控真实硬件一样驱动数字孪生,用硬件在环桥接替换实时 HYDRA-UMC 控制器,而不改变工作流程的其他部分。
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** —— 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢;本指挥中心最终听命于的集群指挥中心,以单个桌面会话无法企及的层级协调多个 HYDRA-UMC 控制器组成的车队。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** —— 具备真实、稳定退出码契约的车队 CLI,是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端;为脚本编写和无图形界面环境提供与本桌面指挥中心相同的 DevOps 功能集,可从命令行使用。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 机器人手臂的真实主板——CM5 主机 + 双核 STM32H745,通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** —— 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** —— 每个桥接都据此校验自身指令的共享 JSON-Schema 契约与安全门限边界。

*核心后端与客户端*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** —— 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** —— 面向实体 Universal Robot Tool Controller 板卡的固件,通过 CAN 总线支持 25 种以上工具配置。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** —— 面向 URTC 板卡的桌面图形烧录工具,支持 CAN-OTA 以及全芯片 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** —— 面向 URTC 板卡的桌面实时 CAN 总线诊断工具,每种工具配置对应一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** —— 通过 Web Serial API 实现的浏览器版 URTC-TESTER 替代方案,无需本地安装。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** —— 面向 Hailo-8 视觉流水线的集成中枢,具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** —— 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** —— 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** —— 具备真实 Position-Based Visual Servoing 修正律,并依据上游区域状态进行安全门控。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** —— 具备校准新鲜度强制检查的真实区域入侵检测与 E-STOP 请求。

*认知 AI 节点(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** —— 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** —— 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** —— 具备受限、需确认的 Watch 中继的真实语音前端(VAD + 意图解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** —— 基于真实规则的任务分解,以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** —— 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。

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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** —— 具备真实触觉提醒与配对手机语音中继功能的 WearOS 伴侣应用。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** —— 面向板卡安装机架的固件,具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** —— 面向热成像/RGB 检测工具头的固件及真实 Python 视觉伴侣程序。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** —— 发现、克隆并更新本生态系统中每个仓库的管理类桌面工具。

---

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 许可证

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
