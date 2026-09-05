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
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  🇯🇵 <b>日本語</b>
</p>


### 🖥️ HYDRA-UMC プラットフォーム向けマルチコントローラー群制御コマンドセンター

<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="OpenGL">
</p>


---

## 🎯 概要

**HYDRA-UMC SUITE** は、[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) コントローラーの艦隊全体を一度にミッションコントロールするために構築された、ネイティブな Windows/Linux デスクトップアプリケーション（Python + PySide6/Qt6）です——ローカルネットワークをスキャンする（あるいは、異なる物理ネットワーク上の HYDRA-UMC への既存の VPN トンネル経由も含め、手動で 1 台を追加する）、見つかったすべてに接続する、そしてそれらのいずれかを、1 つのフルスクリーン産業用ダッシュボードから並べてリアルタイムにジョグ／監視／再設定します。

これは、[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) が公開しているのとまったく同じワイヤープロトコルを話します——[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 自身のブラウザ UI もそのただ 1 つのクライアントとして同じヘッドレスバックエンドと通信しています——完全な契約は [`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md) を参照してください。これは本プロジェクトをサポートするために特別に追加されたものです。SUITE から行われた変更は、開いているブラウザタブにリアルタイムで反映され、その逆も同様です——一方向的なインポート/エクスポートではなく、WebSocket 経由の真の双方向リアルタイム同期です。

**本エコシステムの他のドキュメントと同じ慣例に従った正直な注記：** これは最初の実際に動作するバージョンであり、完成品ではありません。今日実際に実装され、エンドツーエンドで検証されているものと、意図的に後回しにされているものの正確な内容は、[`docs/ROADMAP.md`](docs/ROADMAP.md) を参照してください。このバージョンの時点で、本エコシステムがサポートするすべての実在するロボットモデルには、3D ビューポートに実際の STL ジオメトリと数値検証済みの正運動学が接続されています（Parol6、Faze4、AR3、AR4、UR3e/5e/10e/16e/20、xArm6、Lite 6、e.DO）。加えて、専用のメッシュセットを持たないあらゆるモデル向けに、プリミティブで構築された「汎用」フォールバックも用意されています。

---

## ✨ ビジュアル・コマンドデッキ

デスクトップには、公式 HYDRA-UMC アイコンと HYDRA-UMC-UPDATER と同じ濃紺/シアンの視覚言語を使用した、ゲームメニュー風の常設コマンドデッキが加わりました。ダッシュボード、ロボット操作、カメラ、軌道、ログの操作は対応する実際のドッキングパネルを開き、右側には接続状態、アクティブサーバーターゲット、UTC 時計を表示します。これは Suite の実機能上の視覚レイヤーであり、模擬ダッシュボードではありません。
### Qt Quick への全面リデザイン(`--qtquick`)

このコマンドデッキは従来の `QMainWindow` の上に重なるレイヤーです。このアプリには、それとは別に完全に独立した Qt Quick シェルもあります:

~~~
python main.py --qtquick
~~~

本物の QML `ApplicationWindow` で、上記のコマンドデッキとは異なり従来のウィンドウにはまったく組み込まれていません(従来の `QMainWindow`/`QDockWidget` ツリーに QML を組み込む本物の 2 つの方法はどちらも試された上で断念されました:`QQuickWidget` は真っ黒に表示され、`QQuickView`+`createWindowContainer()` は単体では正しく描画されたものの、このアプリの実際の 26 ドックのレイアウトに組み込むと隣接するドックの本物の Z オーダーが壊れました)。HYDRA-UMC-OS-REBUILDER、HYDRA-UMC-UPDATER、URTC-TESTER、URTC-FLASHER、HYDRA-UMC-EDITOR-URDF がすでに使っている、実証済みの同じ本物のパターンで、従来のエントリポイントを置き換えるのではなく、その隣で起動します。`QDockWidget` のフロート/分割/タブ統合という柔軟性を、STUDIO 自身のよりシンプルなナビゲーションサイドバー+単一コンテンツペインという形(`nav_sidebar.py` 自身の実際の分類体系を項目ごとに忠実に再現)と引き換えており、26 個すべての従来パネルが本物の QML コンテンツに移植済みで、3D Viewport も含まれます。その Viewport のライブプレビューは専用の `OffscreenRobotRenderer`(本物の、独立した `QOpenGLContext`/`QOffscreenSurface`/フレームバッファで、Qt Quick 自身の `QQuickFramebufferObject` はあえて使っていません——それを使うとアプリ全体の Quick バックエンドを Windows の本来のデフォルトである Direct3D11 から OpenGL に強制的に切り替える必要が生じるためです)を介して供給されており、従来のビューポートウィジェットが使うのと同じ本物の描画コード(`RobotGLRenderer`)を再利用し、`QQuickImageProvider` 経由で QML に渡されます。


## 🏭 機能

- **🔍 ネットワークディスカバリー** —— 並行サブネットスキャン(`GET /api/hydra-info`)と実際のmDNS/Bonjour(`_hydra._tcp`。`server.ts` が公開し、HYDRA-UMC-IOS-CONTROL がすでに問い合わせているのと同じサービス)が共に実行され、実際の HYDRA-UMC STUDIO サーバーを host:port で重複排除しながら検出する。加えて、どちらも到達できないもの(異なるサブネット、VPN トンネル)向けの手動アドレス追加。
- **🐝 群接続** —— 好きなだけ多くの HYDRA-UMC サーバーへ同時に接続でき、それぞれが自身のリアルタイム WebSocket 同期を持ちます。他のパネルにとってどれを「アクティブ」にするか選択できます。
- **📊 概要** —— コントローラーごとのロボット一覧：型式、役割、オンライン状態、速度/加速度を一目で確認できます。
- **🦾 ロボット制御** —— 各関節ごとのロータリーノブ＋スライダー（HYDRA-UMC STUDIO 自身の `RotaryKnob`+`FuturisticSlider` ジョグペアのデスクトップ版対応物）、速度/加速度スライダー、すべてリアルタイムで書き戻されます。
- **🧊 実際の 3D ビューポート** —— OpenGL 3.3、実際の STL メッシュ、24 個の実在するロボットモデルすべてに対する実際の正運動学（HYDRA-UMC STUDIO 自身の TypeScript 実装に対して数値検証済みで、結果はビット単位で同一）に加え、プリミティブで構築された「汎用」フォールバック——いずれも様式化されたプレースホルダーではありません。
- **📍 軌道ポイント** —— 選択したロボットの実時間の姿勢を記録し、必要に応じて記録済みのポイントへジョグして戻ります。
- **🪟 Photoshop 風のドッキング可能なワークスペース** —— すべてのパネルは本物の `QDockWidget` です：ドラッグして自由に浮遊させる、ドラッグして戻してドッキングまたはタブグループへ統合する、ワークスペースを分割する、閉じる、そして View メニューから再表示する、といった操作が可能です。パネルをフローティング化すると、それは真に独立したトップレベルウィンドウになるため、2 台目（あるいは 3 台目）の物理モニターへドラッグしてそこに置いておくことがそのまま機能します——Qt/OS のウィンドウマネージャーが他のウィンドウと同様にそれを配置するため、追加の「マルチモニターモード」は不要です。
- **🌐 7 言語** —— 英語、スペイン語、イタリア語、フランス語、ドイツ語、簡体中国語、日本語（URTC-FLASHER/URTC-TESTER と同じ `language/*.lng` 方式）、Language メニューから切り替え（再起動後に反映）。
- **📷 カメラ** —— コントローラーごとの実際のカメラ一覧(存在するカメラ、その種類、接続状態、そしてブランドを問わない汎用のホスト/ポート/パス/認証情報フィールドを備えた実際の USB/IP(RTSP)ソースタイプ切り替え)を、ここにある他のすべてのパネルと同じ方式で実際のサーバーと同期します。メタデータは最初から最後まで本物であり、各カメラカードが実際の MJPEG ストリーム自体をレンダリングします(HYDRA-UMC-VISION-STREAMER 自身の `stream serve` が、HYDRA-UMC-SERVER の `GET /api/camera/:id/stream` を通じて中継され)。実際の JPEG SOI/EOI マーカーをスキャンする実際のクライアント（HYDRA-UMC-ANDROID-CONTROL 自身の `MjpegStreamParser.kt` がすでに使っているのと同じ実際の手法）を使っており、実際の USB・IP ハードウェアに対して検証済みです。
- **🛠️ ツールアタッチメント設定、全11パネル完備** —— CNC、レーザー、ヒートベッド、バキュームテーブル、ATC(自動工具交換装置)、XY テーブル、ラックマネージャー、Pick & Place、Kinematic Brain Stage、Flasher、Tester——HYDRA-UMC STUDIO 自身のツール別画面それぞれとの実際の機能パリティで、それぞれが忠実な移植です(STUDIO 自身のソースコードが持つ、時に癖のある実際の挙動も含め、ここで「修正」するのではなく意図的に再現しています)。それぞれに実際のヘッドレステストカバレッジがあります。CNC/レーザー/ヒートベッド/バキュームテーブルは1つの `ModuleConfigPanel` 実装を共有しています(STUDIO 自身の `CNC.tsx`/`Laser.tsx` はモジュールキー以外は同一のコンポーネントです)。残りの7つはそれぞれ独自に作られた実際のパネルが必要でした。STUDIO 側でライブ 3D プレビューを持つ5つのモジュールすべてが、今ではこちらにも揃っています——CNC/レーザー/ヒートベッド/バキュームテーブル(`render/module_rig.py`——STUDIO 自身のボックス/シリンダー形状を実際に移植したもの)と Pick & Place(`render/pnp_rig.py`——STUDIO 自身の `LumenPnPRig.tsx` を実際に移植したもの。`assets/meshes/lumenpnp/` にある5つの本物の `.stl` メッシュを、プリミティブではなく実際のカーテシアン・ガントリー機構チェーンで位置づけています)。それぞれ、モジュール専用モードに切り替えた独自の `RobotViewport` が描画します。

---

## 📸 スクリーンショット

まだありません——ドキュメント用にはまだ撮影されていません。実際の姿を見るには、後で古びた画像を信頼するのではなく、（下記の手順で）実際に起動してみてください。

---

## 📂 リポジトリ構成

```text
HYDRA-UMC-SUITE/
├── main.py                        # エントリーポイント - 最小1920x1080のフルスクリーン、F11でフルスクリーン/ウィンドウ表示を切替。--qtquickで下記のデッキに切り替え
├── qt_suite.py                     # Qt Quick フロントエンド —— 独立した `--qtquick` コマンドデッキ(全26パネル)、変更を加えていないSuiteControllerをQMLに接続
├── requirements.txt
├── hydra-umc.project.json         # エコシステムマニフェスト - バージョン/ファミリー/親、dashboard/updater/OS-REBUILDERが読み取る実際の情報源
├── bump_version.py                # hydra_suite/__init__.py自身の__version__に対するオドメーター式バージョン増分、実際のPyInstallerビルドの前にbuild_exe.bat/.shが実行する
├── bump_manifest_version.py       # hydra-umc.project.jsonのバージョンをネイティブのものと同期（汎用、エコシステム全体でそのままコピーされる）
├── build.bat / build.sh           # venv + 編集可能インストール + 実際のテストスイート（インクリメンタルビルド、バージョン管理あり）
├── build-test.bat / build-test.sh # 同じチェックだが変更を伴わない - バージョンを増分せず、CHANGELOG.mdにも触れない
├── run.bat / run.sh               # venv経由でmain.pyを起動
├── HYDRA-UMC_SUITE.spec           # PyInstallerスペック（下記build_exe.bat/.sh参照）
├── build_exe.bat                  # ワンショットのWindowsビルド -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # ワンショットのLinuxビルド -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md
├── README.md                      # このファイル
├── README_spa.md / README_fra.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md  <- 翻訳版
├── .github/                        # CIワークフロー、issueテンプレート、PRテンプレート（汎用、エコシステム共有）
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView/CameraView - 実際のsettings.json構造の上に構築された、軽量で変更しやすいビュー
│   ├── app.py                      # SuiteController - 接続群と「アクティブ」選択を管理する。各パネルはこれと通信する
│   ├── i18n.py                     # 7言語対応のKEY=Valueローダー（language/*.lng）
│   ├── can_ota.py                  # 共有のCAN-OTA/SPI-OTAトランスポート（STUDIO自身のcanOta.tsの実際の移植）- FlasherとTesterで使用
│   ├── logging_handler.py          # PythonのロギングをLogsパネルへルーティング
│   ├── net/
│   │   ├── discovery.py             # 並行サブネットスキャン + 実際のmDNS（_hydra._tcp）、GET /api/hydra-infoに対する重複排除付き
│   │   └── client.py                # サーバーごとのREST + WebSocket接続、実際の双方向ライブ同期、ログイン、管理/検出/PTZエンドポイント
│   ├── render/
│   │   ├── kinematics.py            # 順運動学（HYDRA-UMC-STUDIO自身のurKinematicsShared.tsから移植）
│   │   ├── generic_rig.py           # 専用メッシュを持たないモデル向けのプリミティブ構築フォールバックリグ
│   │   ├── module_rig.py            # ツールアタッチメントモジュールのジオメトリ（CNC/レーザー/ヒートベッド/バキュームテーブル）
│   │   ├── pnp_rig.py               # LumenPnP/JuanenPnPメッシュリグ用の実際のデカルトガントリーチェーン
│   │   ├── mesh.py                  # STL読み込み（numpy-stl）
│   │   └── viewport.py              # RobotGLRenderer(実際のGLSLシェーダーパイプライン、オービットカメラ)+ 従来のQOpenGLWidgetラッパー + `--qtquick`デッキの3D Viewportパネル向けのOffscreenRobotRenderer
│   └── ui/
│       ├── main_window.py           # QMainWindow + QDockWidgetワークスペース
│       ├── about_dialog.py          # 実際のAboutダイアログ（バージョン/作者/ライセンス）
│       ├── theme.py                  # assets/qss/industrial_dark.qssを読み込み
│       ├── widgets/rotary_knob.py    # カスタム描画のロータリーノブ（RotaryKnob.tsxのデスクトップ版対応物）
│       └── panels/                   # ドッキング可能なパネルごとに1ファイル - STUDIO自身のタブとの実際の1:1パリティ：server_browser、overview、robot_control、viewport_panel、trajectory_panel、cameras_panel（+実際のPTZ制御）、ai_family_status_panel、ecosystem_services_panel、ecosystem_telemetry_panel、admin_clients_panel、admin_logs_panel、admin_server_panel、logs_panel、module_config_panel（+cnc/laser/heated_bed/vacuum_table）、atc_tools_panel、xy_table_panel、rack_config_panel、pick_and_place_panel、kinematic_brain_stage_panel、flasher_panel、tester_panel
├── assets/
│   ├── qss/industrial_dark.qss     # 未来的・産業的なQtスタイルシート
│   ├── qml/Main.qml                 # `--qtquick` コマンドデッキ(全26パネル)のQt Quick UI
│   └── meshes/                      # 実際のSTLメッシュ、ロボット/モジュールごとに1フォルダ、HYDRA-UMC-STUDIO自身のpublic/models/からコピー（それぞれ独自のATTRIBUTION.txt付き）
├── language/                        # english/spanish/french/german/italian/japanese/chineseの.lngファイル
├── docs/
│   └── ROADMAP.md                   # 実際の範囲と未実装部分についての正直な記述
├── tools/
│   ├── build_test.py                # バージョン管理を伴わないコンパイルチェック（汎用、エコシステム共有）
│   └── ci_validate.py               # CIで使用されるマニフェスト/CHANGELOG/ドキュメントの検証（汎用、エコシステム共有）
├── tests/                           # 実際のヘッドレステストスイート（QApplication、ディスプレイ不要）- パネル/サブシステムごとに1つのverify_*.py、加えて運動学の移植と、実際に稼働中のSTUDIOサーバーが必要な手動スモークテスト
├── installer/                       # プラットフォームごとのパッケージング資料・アセット
└── .vscode/                         # Pythonインタープリターのパス、起動構成、推奨拡張機能
```

---

## 🚀 はじめに

### 必要環境
- Python 3.12 以上（3.14 で開発/テスト済み）
- 接続先となる、稼働中の [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) サーバー

### インストール

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### 実行

```bash
python main.py
```

最小 1920x1080 のフルスクリーンで起動します（本アプリ自身の設計仕様に基づく）——いつでも **F11** を押すことでフルスクリーンと通常の最大化ウィンドウを切り替えられるため、逃げ道なくトラップされることは決してありません。**Servers** パネルを使ってネットワークをスキャンするか、アドレスを指定して HYDRA-UMC STUDIO サーバーを追加してください。

---

## 🛠️ 技術スタック

- **UI フレームワーク：** PySide6（Qt6）——ネイティブなドッキング可能パネル、カスタムドッキングフレームワークの再発明はなし
- **3D レンダリング：** PyOpenGL（コアプロファイル GLSL シェーダー）+ numpy-stl
- **ネットワーキング：** `httpx`（REST）+ `websockets`（リアルタイム同期）、`qasync` を介して Qt 自身のイベントループに統合——別個のワーカースレッドなし
- **数学：** NumPy（正運動学のための 4x4 同次変換）

---

## 📦 スタンドアロン実行ファイルのビルド

2 通りの方法、結果は同じです（Windows では `dist/HYDRA-UMC_SUITE.exe`、Linux では `dist/HYDRA-UMC_SUITE`）——どちらの方法でも、出力を実行するのに Python のインストールは不要です。

**自動化（推奨）：**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

各スクリプトは `.venv` を作成/再利用し、そこに `requirements.txt` + PyInstaller をインストールし、以前の `build/`/`dist/` があれば削除し、PyInstaller でコンパイルし（`assets/` と、本アプリが実際に使用する 4 つの Qt プラグインサブフォルダのみ——`platforms`/`styles`/`imageformats`/`iconengines`——をバンドルし、PySide6 パッケージ全体ではないため、結果が数百 MB ではなく数十 MB に収まります）、`README.md`/`LICENSE`/`docs/` および編集可能な `language/*.lng` ファイルを、実行ファイル内に凍結するのではなく、その隣にコピーします。

**手動での同等の手順**（すべてのステップを自分自身で確認/制御したい場合。上記スクリプトが実行するのと同じコマンド）：

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

# その後、README.md、LICENSE、docs/、language/ を dist/HYDRA-UMC_SUITE.exe の隣にコピー
```

Linux では（正確な、テスト済みのコマンドは `build_exe.sh` を参照）、`--add-data` の区切り文字として `;` の代わりに `:` を使用し、`OpenGL.platform.win32` の隠れたインポート（Windows 専用）を削除し、`--windowed` を削除し、そちらではプラグインパスが 1 階層深くネストされている点に注意してください（Windows のフラットな `<PySide6 ディレクトリ>\plugins\platforms` に対し、`<PySide6 ディレクトリ>/Qt/plugins/platforms`）——これはその wheel パッケージ自体のパッケージング上の詳細であり、どちらのスクリプトが選んだものでもありません。リポジトリルートの `HYDRA-UMC_SUITE.spec` は、前回のビルドから PyInstaller 自身が生成した spec ファイルです——安全に削除して再生成できるもので、手作業で保守されているものではありません。

---

## 🔢 バージョン管理

`hydra_suite/__version__`（**Help > About** に表示）は、10 進法の繰り上げルールを持つ、オドメーター方式の `MAJOR.MINOR.PATCH` スキームに従います：実際のビルドのたびに patch が 1 増加し、9 を超えると 0 にリセットされて代わりに minor が 1 増加します（例：`0.1.9` -> `0.2.0`）。「実際のビルド」とは `build_exe.bat`/`build_exe.sh` の実行を意味し、単なる `python main.py` の実行の**たびではありません**。この加算自体は `bump_version.py` によって自動的に処理されます（PyInstaller が実行される前に、両方のビルドスクリプトから呼び出されます）。そのため、パッケージ化された `.exe`/バイナリは、常に実際に最後に出荷されたバージョンよりも厳密に新しいバージョン番号を持ちます。各時点での変更内容は [`CHANGELOG.md`](CHANGELOG.md) を参照してください。

---

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**親プロジェクト**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。本コマンドセンターはその実際のクライアントであり、mDNS でネットワーク上に発見する。

**兄弟プロジェクト** —— それぞれ独自のクライアントとして、同じく HYDRA-UMC-SERVER 自身の API と通信する
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 実際の VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 実際の GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 実際の Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 実際のキー/筐体/インターロック GPIO セーフガード 3 系統を読み取る、レーザーセルの安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 実際の遅延インポート rclpy ROS 2 トランスポートを持つ安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 実際の MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界。

**直接関連**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実際のハードウェアの間でコマンドをルーティングする、実際のハードウェア・イン・ザ・ループ安全インターロック。実際の HYDRA-UMC コントローラーをハードウェア・イン・ザ・ループのブリッジに置き換え、ワークフローの他の部分を一切変えずに、本コマンドセンターがデジタルツインを実機のように制御できるようにする。
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。本コマンドセンターが最終的に従うスウォームコマンドセンターであり、単一のデスクトップセッションでは届かないレベルで HYDRA-UMC コントローラーの群れを調整する。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を持つフリート CLI、HYDRA-UMC-SERVER 自身の API の本物のライブクライアント。スクリプティングやヘッドレス環境向けに、コマンドラインからこのデスクトップコマンドセンターと同じ DevOps 機能セットを提供する。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 実際のロボットアームのマザーボード——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが自身のコマンドを検証する共有 JSON-Schema 契約と安全ゲートの境界。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由の 25 以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板用のデスクトップ GUI 書き込みツール、CAN-OTA およびフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けのデスクトップ CAN バスライブ診断ツール、ツールプロファイルごとに 1 パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API を使ったブラウザベースの URTC-TESTER の代替、ローカルインストール不要。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 上流のゾーン状態に応じて安全ゲート制御される、実際の Position-Based Visual Servoing 補正則。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — キャリブレーションの鮮度を強制する、実際のゾーン侵入チェックと E-STOP 要求。

*コグニティブ AI ノード(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 確認ゲート付きの限定的な Watch リレーを備えた、実際の音声フロントエンド(VAD + 意図解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。

*オーケストレーション&スウォーム*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上に構築された、優先度ベースの実際のジョブキュー(重複排除付き)。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/ワークスペース衝突検証を備えた、実際の RRT ベースの 3D 経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 複数セルの収束についてプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツイン&シミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を持つ、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 実際の URDF サブセットに対する、実際の順運動学と関節限界検証。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — YOLO/COCO アノテーションのエクスポート機能を持つ、実際のプロシージャル 2D シーンジェネレーター。

*データ&分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 実際の取り込み/クエリ HTTP API を備えた、実際の sqlite3 ベースの時系列ストア。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — ドリフト監視を備えた、実際の FFT + 統計ベースラインによる異常検知器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — DATALAKE の履歴に対する実際の OEE/稼働率計算、再現可能な CSV エクスポート付き。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — シーケンス重複排除機能を備えた、DATALAKE への実際の CAN/WebSocket 取り込みパイプライン。

*産業用ゲートウェイ*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 実際のコマンド許可リスト/バックプレッシャー層を持つ、産業用プロトコルへ中継する統合ハブ。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 実際のバイナリプロトコルクライアントセッションで検証された、実際の OPC-UA アドレス空間。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — クライアント単位のオプション認証とトピック ACL を備えた、実際の MQTT ブローカー。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 縮退モード出力を備えた、実際の MTConnect `/probe` および `/current` XML エンドポイント。

*補完ツール&エコシステム運用*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 誠実な統計フォールバックを備えた、DATALAKE/ANOMALY-DETECTOR 上のスマートサマリーと異常ハイライトパネル。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 実際の触覚アラートとペアリングされたスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際の工具 ID デコードと Smart Idle 予熱ロジックを備えた、基板搭載ラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの、ファームウェアと実際の Python ビジョンコンパニオン。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — このエコシステム内のすべてのリポジトリを検出・クローン・更新する、管理用デスクトップツール。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — エコシステムの最新バージョンをプリロードした、書き込み可能なCM5イメージを構築するWindows/Linuxデスクトップツール。Raspberry Pi Imager方式の初回起動Wi-Fi/ユーザー/SSH設定を備える。

---

## 📚 ドキュメント & コミュニティ

- **[docs/ROADMAP.md](docs/ROADMAP.md)** —— 今日の時点で実際にエンドツーエンドで検証済みのものと、意図的にまだ対象外のもの。
- **[installer/README.md](installer/README.md)** —— Windows 用 `.exe` インストーラーと Linux 用 `.deb` パッケージのビルド方法。
- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— プルリクエストのための技術スタックとコーディング指針。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— このコミュニティで期待される行動規範。
- **[SECURITY.md](SECURITY.md)** —— 脆弱性の報告方法と、このアプリの実際のセキュリティ重点領域。
- **[SUPPORT.md](SUPPORT.md)** —— 質問の投稿先とバグの報告先。
- **[LICENSE.md](LICENSE.md)** —— このプロジェクト自身のライセンス、および `assets/meshes/` の各フォルダが再配布されている個別のライセンス。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス

HYDRA-UMC SUITE の著作権は (c) 2026 JuanenRac（Electro Hobby 3D）に帰属します。本プロジェクトまたはその派生物を配布する際は、この表示を必ず含めてください。

本アプリケーションのソースコードは、**GNU General Public License v3.0（GPL-3.0）** の下で提供されます。全文は https://www.gnu.org/licenses/gpl-3.0.html を参照してください。

**本ドキュメント**（本 README およびその自身の翻訳版——`README_spa.md`、`README_ita.md`、`README_fra.md`、`README_deu.md`、`README_zho.md`、`README_jpn.md`）は、**クリエイティブ・コモンズ 表示-継承 4.0 国際（CC BY-SA 4.0）** の下で提供されます。全文は https://creativecommons.org/licenses/by-sa/4.0/ を参照してください。

**サードパーティのメッシュアセット：** `assets/meshes/` 下のすべてのフォルダは、そのロボット自身の公式メーカーリポジトリからそのままコピーされたものです——上記の GPL-3.0 の対象では **ありません**。それぞれが、正確な出典/ライセンス参照を記した自身の `ATTRIBUTION.txt` を持ちます。下表はそれらをまとめたものです。

| メーカー | モデル | ライセンス |
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

本プロジェクトは [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) のデスクトップ版群制御対応物です——その自身の独立したライセンスは同プロジェクト自身のリポジトリを参照してください。本リポジトリ自身のライセンスはそちらには及ばず、その逆も同様です。また、最終的には [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) のハードウェア/ファームウェア、および（[それを経由して中継される](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)）[URTC](https://github.com/JuanenRac/URTC) ツールヘッドを制御します——いずれもそれぞれ独立したライセンスを持つ独立したプロジェクトです。

本プロジェクトを基に開発を行う際は、このライセンス区分を念頭に置いてください：コードの変更は GPL-3.0 を維持し、各ロボット自身のメッシュアセットはそれぞれの原本ライセンス条件のもとに維持してください（上表参照）——いずれも本プロジェクトおよびその作者への帰属表示を伴う必要があります。
