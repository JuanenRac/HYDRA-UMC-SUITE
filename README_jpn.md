<!-- =============================================================================
HYDRA-UMC-SUITE - Desktop command center for several HYDRA-UMC servers at once
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🖥️ HYDRA-UMC-SUITE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🖥️ HYDRA-UMC プラットフォーム向けマルチコントローラー群制御コマンドセンター

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.12-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Graphics-OpenGL-5586A4.svg" alt="Graphics">
  <img src="https://img.shields.io/badge/Tests-47%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.7.6-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

**正直な現状確認 - 実際に今動くもの:** ネットワーク検出(並行サブネットスキャン + 本物のmDNS/Bonjour、`hydra_suite/net/discovery.py`)、ライブのREST+WebSocket接続とスウォームサポート(`hydra_suite/net/client.py`、`hydra_suite/app.py`)、24種類すべての実在するロボットモデルに対する3Dビューポートの本物の順運動学に加えプリミティブによる「Generic」フォールバック(`hydra_suite/render/`、HYDRA-UMC STUDIO自身のTypeScript実装のFKとビット単位で数値検証済み)、11分の11のツール装着設定パネルすべて、CAN-OTA/SPI-OTAフラッシング、そして本物のMJPEGカメラ映像レンダリングは本物であり、テスト済みです - `tests/` 配下の47件のオフライン検証/スモークテストスクリプト(`python tools/run_offline_verifiers.py`、`QT_QPA_PLATFORM=offscreen` によるヘッドレスQt)がすべて成功しており。インターフェースは Qt Quick のみです(`qt_suite.py`)。ナビゲーションの全 34 パネルは実際に動作するコードで、3D ビューポートは専用の `OffscreenRobotRenderer` 経由で描画されます。従来のウィンドウは削除されました。このリポジトリ自身の正直さの慣習に従い、明示的にまだ行われていないもの: CAN-OTAのURTC Tool Head/Advanced Expansion階層にはまだ本物のハードウェアリレートンネルがありません。そして `combinedWith`(結合ロボットモード)は、STUDIO自身のデータモデルに存在するにもかかわらず、このアプリのUIには公開されていません。軌道パネル は現在、HYDRA-UMC STUDIO自身の本物の `WORKS/*.json` 形式(`POST /api/upload-work`、`GET /<フォルダ>/index.json`)を通じてエクスポート/インポートします - ここで記録したポイントは、どちらのアプリからも再生できる本物のWorkです。この段落が要約している、本物か先送りかの完全な項目別内訳は [`docs/ROADMAP.md`](docs/ROADMAP.md) を、これまでに実際に出荷されたものの詳細は `CHANGELOG.md` を参照してください。

---

> **安全性とセキュリティの現状:** このエコシステムは認証された安全システムではありません。ハードウェアの E-STOP 経路、ファームウェアが強制する制限やインターロック、検証済みの動作コマンドはまだありません。ファームウェアイメージは CRC-32 と Ed25519 署名で検査し、リリースビルドは公開済みの開発用鍵を拒否します(リレーの先のツールヘッドと拡張ボードは引き続き URTC のブートローダーを使い、署名ではなく共有鍵の HMAC-SHA256 を使います)。TLS と相互 TLS は任意で、既定では無効です。独自基板はまだ実装も試験もされていません。ここに書かれた内容を人の安全のために頼る前に、[セキュリティベースライン](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)と[脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)をお読みください。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.7.6` |
| 成熟度 | 機能する |
| テスト | 47 (`python tools/run_offline_verifiers.py`) |
| 技術 | Python 3.12 / PySide6 |
| 対象 | 利用者の PC |
| 実機での確認 | まだです：このバージョンについて実機での動作記録はありません |

**移動：** [概要](#-概要) · [アーキテクチャ](#-アーキテクチャ) · [機能](#-機能) · [セキュリティと安全](#-セキュリティと安全) · [インターフェース](#-インターフェース) · [設定](#-設定) · [クイックスタート](#-クイックスタート) · [テスト](#-テスト) · [トラブルシューティング](#-トラブルシューティング) · [リポジトリの構成](#-リポジトリの構成) · [関連プロジェクト](#-関連プロジェクト)

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟡 | 主な目的では動作します。足りない点は上の正直さの確認に書かれています |
| テスト | 🟢 | 自動テスト 47 件。変更のたびに実行されます |
| 実機 | 🔴 | まだです：このバージョンについて実機での動作記録はありません |
| ドキュメント | 🟢 | 8 言語の README。変更のたびにマニフェストと照合されます |

## 🎯 概要

**HYDRA-UMC SUITE** は、[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) コントローラーの艦隊全体を一度にミッションコントロールするために構築された、ネイティブな Windows/Linux デスクトップアプリケーション（Python + PySide6/Qt6）です——ローカルネットワークをスキャンする（あるいは、異なる物理ネットワーク上の HYDRA-UMC への既存の VPN トンネル経由も含め、手動で 1 台を追加する）、見つかったすべてに接続する、そしてそれらのいずれかを、1 つのフルスクリーン産業用ダッシュボードから並べてリアルタイムにジョグ／監視／再設定します。

これは、[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) が公開しているのとまったく同じワイヤープロトコルを話します——[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) 自身のブラウザ UI もそのただ 1 つのクライアントとして同じヘッドレスバックエンドと通信しています——完全な契約は [`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md) を参照してください。これは本プロジェクトをサポートするために特別に追加されたものです。SUITE から行われた変更は、開いているブラウザタブにリアルタイムで反映され、その逆も同様です——一方向的なインポート/エクスポートではなく、WebSocket 経由の真の双方向リアルタイム同期です。

**本エコシステムの他のドキュメントと同じ慣例に従った正直な注記：** これは最初の実際に動作するバージョンであり、完成品ではありません。今日実際に実装され、エンドツーエンドで検証されているものと、意図的に後回しにされているものの正確な内容は、[`docs/ROADMAP.md`](docs/ROADMAP.md) を参照してください。このバージョンの時点で、本エコシステムがサポートするすべての実在するロボットモデルには、3D ビューポートに実際の STL ジオメトリと数値検証済みの正運動学が接続されています（Parol6、Faze4、AR3、AR4、UR3e/5e/10e/16e/20、xArm6、Lite 6、e.DO）。加えて、専用のメッシュセットを持たないあらゆるモデル向けに、プリミティブで構築された「汎用」フォールバックも用意されています。

## 🧩 HYDRA-UMC での役割

**HYDRA-UMC-SUITE** は Windows と Linux 向けのセルのデスクトップ司令センターです。ネットワーク上のすべての HYDRA-UMC-SERVER を探し（サブネットのスキャンと mDNS、または入力したアドレス）、好きな数だけ接続し、Qt Quick の画面と 3D ビューでそれらのロボットを並べて表示・ジョグ・設定します。STUDIO のデスクトップ版で、同じプロトコルを話し、安全に関する判断はしません。それは各サーバーに残ります。

## 🏛️ アーキテクチャ

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-SUITE architecture" width="100%">
</p>

## 🖼️ スクリーンショット

テストベンチで 1920×1080 で撮影。サンプルデータを使用しており、実際の設備は接続されていません。

<table>
<tr><td width="50%" valign="top"><img src="images/screenshots/overview.png" alt="概要：アクティブなコントローラー、そのシステムメトリクス、モデル・役割・状態・速度つきのロボット一覧。" width="100%"><br><sub>概要：アクティブなコントローラー、そのシステムメトリクス、モデル・役割・状態・速度つきのロボット一覧。</sub></td><td width="50%" valign="top"><img src="images/screenshots/robot-control.png" alt="ロボット制御：実機またはシミュレーションのモード、予約ボタン、6 つの関節スライダー、再生、ツールのアクセサリー。" width="100%"><br><sub>ロボット制御：実機またはシミュレーションのモード、予約ボタン、6 つの関節スライダー、再生、ツールのアクセサリー。</sub></td></tr>
<tr><td width="50%" valign="top"><img src="images/screenshots/flasher-studio.png" alt="Flasher Studio：ボードとロボットスロットを選び、更新の経路を確認して、ファームウェアファイルを CAN で書き込みます。" width="100%"><br><sub>Flasher Studio：ボードとロボットスロットを選び、更新の経路を確認して、ファームウェアファイルを CAN で書き込みます。</sub></td><td width="50%" valign="top"><img src="images/screenshots/tester-center.png" alt="Tester Center：ボードのステータス LED、リング LED、OLED モード、永続性チェック、セルフテスト、生バスモニター。" width="100%"><br><sub>Tester Center：ボードのステータス LED、リング LED、OLED モード、永続性チェック、セルフテスト、生バスモニター。</sub></td></tr>
<tr><td width="50%" valign="top"><img src="images/screenshots/safety-limits.png" alt="安全制限：ジョグの有効化、予約ルール、ロボットモデルごとのジョグとベッド温度の上限。" width="100%"><br><sub>安全制限：ジョグの有効化、予約ルール、ロボットモデルごとのジョグとベッド温度の上限。</sub></td></tr>
</table>

## ✨ 機能

### ビジュアル・コマンドデッキ

ウィンドウには、ゲーム機のメニューに着想を得た常時表示のヘッダーがあり、公式の HYDRA-UMC アイコンと HYDRA-UMC-UPDATER のネイビー/シアンの配色を使っています。製品名、接続状態、バージョンを表示し、グローバル STOP ボタンとアプリケーションメニュー(言語、サポート用バンドル、キーボードショートカット、バージョン情報)を備えています。パネルへの移動は左のサイドバーです。シミュレーションのダッシュボードではなく、すべてのパネルが実際のサーバーに対して動作します。

### 🛑 グローバル STOP

**STOP** ボタンは常にウィンドウ上部にあり、すべてのパネルで利用できます。ワンクリックで確認なし：接続中のすべてのサーバーで `POST /api/stop-all` を呼び出し、他のアカウントが予約していても、すべてのロボットを停止します。結果も表示します：すべて停止したときは緑のメッセージ、ロボットが停止しなかった、停止状態を保存できなかった、または停止を確認できなかった場合（**STOP 未確認**）は、次の STOP まで残る赤いメッセージです。サーバーが呼び出しを制限した場合は、ロボットを 1 台ずつ停止します。**F12** キーでも同じ操作ができます（**≡ > キーボードショートカット(K)** に記載）。単独のファンクションキーなので、フォーカス中のボタンを押すことも、何かを閉じることもありません。

### Qt Quick インターフェース

HYDRA-UMC SUITE のインターフェースは Qt Quick(QML)で書かれた 1 つだけです。独立した `ApplicationWindow`(`assets/qml/Main.qml`)を、`qt_suite.py` が変更のない `SuiteController` につないでいます。HYDRA-UMC-OS-REBUILDER、HYDRA-UMC-UPDATER、URTC-TESTER、URTC-FLASHER、HYDRA-UMC-EDITOR-URDF と同じ方式で、HYDRA-UMC-STUDIO と同じ構成です。ナビゲーションのサイドバー(ルートメニューと Industrial、URTC、HYDRA-UMC のサブメニュー。`hydra_suite/nav_items.py`)と、34 個のパネルのうち 1 つを表示するコンテンツ領域からなります。3D ビューポートとプレビューは専用の `OffscreenRobotRenderer`(別個の `QOpenGLContext`、`QOffscreenSurface`、フレームバッファ。Windows で Qt Quick が既定で使う Direct3D 11 バックエンドから全体を OpenGL に切り替えさせてしまう Qt Quick 自身の `QQuickFramebufferObject` は使いません)が同じ描画コード(`RobotGLRenderer`)で描き、画像として QML に渡されます。以前のクラシックウィンドウ(ドッキング可能なパネルを持つ `QMainWindow`)は削除されました。その機能はすべてこのインターフェースにあり、`python main.py` で起動します。

### 機能

- **🔍 ネットワークディスカバリー** —— 並行サブネットスキャン(`GET /api/hydra-info`)と実際のmDNS/Bonjour(`_hydra._tcp`。`server.ts` が公開し、HYDRA-UMC-IOS-CONTROL がすでに問い合わせているのと同じサービス)が共に実行され、実際の HYDRA-UMC SERVER サーバーを host:port で重複排除しながら検出する。加えて、どちらも到達できないもの(異なるサブネット、VPN トンネル)向けの手動アドレス追加。
- **🐝 群接続** —— 好きなだけ多くの HYDRA-UMC サーバーへ同時に接続でき、それぞれが自身のリアルタイム WebSocket 同期を持ちます。他のパネルにとってどれを「アクティブ」にするか選択できます。
- **📊 概要** —— コントローラーごとのロボット一覧：型式、役割、オンライン状態、速度/加速度を一目で確認できます。
- **🦾 ロボット制御** - モデルの可動範囲内の関節ごとのスライダー、速度/加速度スライダー、記録した軌道の再生 / 一時停止 / 停止、ツール(確認付き)、バルブとポンプを備え、すべてアトミックなコマンドとしてライブで書き戻されます。
- **🔐 予約、安全上限、Live / Sim** - ロボット制御パネルにはアクセスバーがあり、選択したロボットをこのプログラム用に予約・解除でき(保持している間は自動更新されます)、他のロボットを誰が持っているかが分かり、管理者は引き継ぐこともできます。すべての予約、解除、ジョグのアーム、コマンドには、このプログラムが起動時に選んだコントローラ ID が付き、拒否(別のアカウント、別の場所の同じアカウント、コントローラ ID の欠如、アームされていないジョグ)はそれぞれ専用の文で画面に届きます。ジョグの大きさとベッドの最高目標温度はサーバー(`GET /api/safety-limits`)から読み取り、送信前に確認します。管理者は **安全上限** パネルでモデルごとに編集でき、任意のジョグのアーム(既定ではオフ)と必須のコントローラ ID も設定できます。各ロボットには **Live / Sim** スイッチがあり(既定は Live)、Sim ではロボットを動かすものや何かをオンにするものはこのプログラムから出ず、STOP は常に出ます。関節スライダーはモデルの可動範囲に従い、範囲外の点を含む Work はその一覧とともに拒否され、アームが届かない点を含む Work はそれらの点とともに拒否されますが、ロボットのベースを基準に拡縮して読み込むこともでき、ベッドヒーターをオンにする前には確認が出ます。 書き込みは条件付きです。各書き込みには、このプログラムが最後に見たロボットのリビジョン(`If-Match`)が付き、その間に他の人がロボットを変更していた場合、サーバーは 412 を返し、何も適用されず、ロボットが読み直されて通知で知らされます(標準は予約、テーブル、単発のコマンドを確認、厳格は STOP 以外すべてを確認、オフは何も確認せず、選択は予約一覧の下にあり、STOP は確認されません)。XY テーブルのジョグはアトミックな `table` コマンド 1 回で、サーバーは WebSocket で予約を通知するためパネルは通知が届く間ポーリングを止め、管理者は **エコシステム > 監査記録** で、SHA-256 チェーンを(サーバーとここで)2 回検証した追記専用の監査記録を読めます。 管理者は **エコシステム > ユーザー** で、サーバーのアカウント(管理者またはオペレーター)の作成・変更・削除もできます。 **エコシステム > サーバー管理** 画面では、ローカル AI リレーを使える人、ホスト情報にサインインを求めるか、TLS(証明書のフィンガープリント付き)、サーバーの Bluetooth LE サービスも設定でき、それぞれ値の出所が表示されます。 **エコシステム > 送信されたモデル** は、URDF エディターと STL エディターがサーバーに送信したモデルを一覧表示し、モデルの URDF を保存します。
- **🩺 エコシステムの健全性：** Ecosystem の下に、サービスごとに 1 枚のカード（状態、理由、報告バージョンと期待バージョン、最後に応答してからの時間）、状態とバージョンのずれによるフィルター、サーバーの TLS 証明書がまもなく期限切れになる場合やサービスがマニフェストと異なるバージョンを報告する場合の通知を備えたビューがあります。サーバーの `GET /api/ecosystem/health` を読み取り、これは管理者が Server Admin でオンにします。オフの場合はビューがその旨を表示し、応答しない 1 つのサービスが他を隠すことはありません。
- **🧊 実際の 3D ビューポート** —— OpenGL 3.3、実際の STL メッシュ、24 個の実在するロボットモデルすべてに対する実際の正運動学（HYDRA-UMC STUDIO 自身の TypeScript 実装に対して数値検証済みで、結果はビット単位で同一）に加え、プリミティブで構築された「汎用」フォールバック——いずれも様式化されたプレースホルダーではありません。
- **📍 軌道ポイント** —— 選択したロボットの実時間の姿勢を記録し、必要に応じて記録済みのポイントへジョグして戻ります。
- **🧭 サイドバー 1 つ、コンテンツ領域 1 つ** - パネルは左のナビゲーション(ルートメニューと Industrial、URTC、HYDRA-UMC のサブメニュー)から 1 つずつ開き、HYDRA-UMC-STUDIO のサイドバーと同じ区分になっています。ウィンドウはネイティブのタイトルバー付きで最大化して起動し、**F11** で本当の全画面を切り替えます。
- **💾 記憶したサーバーとサポート用バンドル** - サーバーを追加するとき *記憶する* は既定でオンです (何も保存したくない場合はオフにします)。アドレス、ニックネーム、ユーザー名は設定ファイルに、パスワードは `keyring` を通じてオペレーティングシステムの安全な保管領域(Windows の資格情報マネージャー、macOS のキーチェーン、Linux デスクトップの Secret Service)に保存され、ファイルには書かれません。安全な保管領域がない場合、パスワードは再度入力します。アプリケーションメニューは、バージョン、サーバー一覧、クライアントのログをパスワード、ユーザー名、トークンなしで zip にまとめて書き出します。
- **🌐 8 言語** —— 英語、スペイン語、イタリア語、フランス語、ドイツ語、簡体中国語、日本語、ポルトガル語（URTC-FLASHER/URTC-TESTER と同じ `language/*.lng` 方式）、Language メニューから切り替え（再起動後に反映）。
- **📷 カメラ** —— コントローラーごとの実際のカメラ一覧(存在するカメラ、その種類、接続状態、そしてブランドを問わない汎用のホスト/ポート/パス/認証情報フィールドを備えた実際の USB/IP(RTSP)ソースタイプ切り替え)を、ここにある他のすべてのパネルと同じ方式で実際のサーバーと同期します。メタデータは最初から最後まで本物であり、各カメラカードが実際の MJPEG ストリーム自体をレンダリングします(HYDRA-UMC-VISION-STREAMER 自身の `stream serve` が、HYDRA-UMC-SERVER の `GET /api/camera/:id/stream` を通じて中継され)。実際の JPEG SOI/EOI マーカーをスキャンする実際のクライアント（HYDRA-UMC-ANDROID-CONTROL 自身の `MjpegStreamParser.kt` がすでに使っているのと同じ実際の手法）を使っており、実際の USB・IP ハードウェアに対して検証済みです。
- **🛠️ ツールアタッチメント設定、全11パネル完備** —— CNC、レーザー、ヒートベッド、バキュームテーブル、ATC(自動工具交換装置)、XY テーブル、ラックマネージャー、Pick & Place、Kinematic Brain Stage、Flasher、Tester——HYDRA-UMC STUDIO 自身のツール別画面それぞれとの実際の機能パリティで、それぞれが忠実な移植です(STUDIO 自身のソースコードが持つ、時に癖のある実際の挙動も含め、ここで「修正」するのではなく意図的に再現しています)。それぞれに実際のヘッドレステストカバレッジがあります。CNC/レーザー/ヒートベッド/バキュームテーブルは1つの `moduleConfigComponent` 実装を共有しています(STUDIO 自身の `CNC.tsx`/`Laser.tsx` はモジュールキー以外は同一のコンポーネントです)。残りの7つはそれぞれ独自に作られた実際のパネルが必要でした。ヒートベッドと真空テーブルは `render/module_rig.py` で STL を使用します。PnP、CNC、レーザーは `render/pnp_rig.py` を使用し、独立したフォルダーごとに 7 個の可動メッシュと 160 個の個別部品があります。`OffscreenRobotRenderer` が各アセンブリを表示します。[機械モデル](docs/MACHINE_ASSETS.md)を参照してください。
- **🔑 2段階サインイン** - **エコシステム > Server Admin** に、ログイン中のアカウント用のカードがあります(所有者が有効にするまでオフ)。otpauth アドレスの QR コード(Web 版と同じシンボルを作る小さなエンコーダーでここに描画)、コピーボタン付きの手入力用キー、最初のコード、一度だけ表示される 10 個の使い切りリカバリーコードを扱います。サーバー認証情報のダイアログには、有効なアカウント用のコード欄があり(そのサインイン一回のためだけにメモリに保持され、保存はされません)、**エコシステム > ユーザー** には、電話とリカバリーコードを失ったアカウントの 2 段階目を解除するボタンがあります。

---

### 🧩 選択可能な真空テーブル

真空テーブルメニューで6種類の実際のSTLモデルから選択できます：160 × 120、230 × 210、230 × 250、232 × 217、240 × 240、250 × 250 mm。ベース厚は15 mm、位置決め壁を含む全高は16.2 mmです。幅と長さは5 mm刻みで変更できます（10–5000 mm）。平面寸法のみを拡大・縮小し、厚さは変えません。モデルを選ぶと元の寸法に戻ります。カスタム寸法はSERVER経由で同期されます。拡大・縮小した穴や溝は配置の可視化用であり、製造用STLの再生成ではありません。モデルの選択は位置、ポンプ、バルブの状態を保持します。リセットは160 × 120 mmを選択し、ポンプとバルブをオフにします。旧設定や不明なモデルIDは最初のモデルで表示されます。STUDIOとSUITEの両インターフェースは同じカタログとロボット設定のmodelIdを使用します。

[モデル・設定・再生成ガイド](docs/VACUUM_TABLE_MODELS.md).

### 🔥 ヒートベッドモデル

STLプリセットは100×100、200×100、200×200、255×255 mmの4種類で、厚さはすべて5 mmです。幅と長さは5 mm刻みで変更できます（25–5000 mm）。モデルを選ぶと寸法が戻り、加熱状態は変わりません。可視化用であり、電気設計や製造設計ではありません。

[ヒートベッドモデル — STL / OpenSCAD](docs/HEATED_BED_MODELS.md).

### 🗄️ 設定可能な STL ラック

STL ラック：幅と奥行きは 40～1000 mm、1 mm 刻み。基板数は 1～24 枚、間隔は 10 mm 固定です。表示設定であり、ロボットの校正ではありません。

[設定可能な STL ラック — STL / OpenSCAD](docs/RACK_MODELS.md).

### 🛠️ 独立した機械モデル

JuanenPnP、JuanenCNC、JuanenLaser は独立した STL コピーを使用し、LumenPnP は元のモデルを維持します。各モデルは専用フォルダーで編集してください。CAD 寸法を使用し、従来のサイズ設定ではモデルを引き伸ばしません。

[独立した機械モデル — STL](docs/MACHINE_ASSETS.md).

これらのオリジナルJuanenPNP / HYDRA-UMCモデルとSCADソースはGPL-3.0です。Opulo製マシンのCADではありません。

### メッシュを 1 つのパッケージから

3D モデルはリポジトリのツリーに含まれなくなりました（221 MiB、HYDRA-UMC-STUDIO と共有）。`meshes.pack.json` は 1 つのパッケージ（45 MB、HYDRA-UMC-MESHES で公開）と各メッシュの SHA-256 を固定し、`python -m hydra_suite.mesh_pack`（`status`、`check`、`ensure`、`prepare`）が `assets/meshes/` をその状態にします。`python main.py`、`run.sh`、`run.bat`、`build_exe` は初回実行時にパッケージを取得します。インターネット接続が必要なのは一度だけで、その後パッケージは `~/.cache/hydra-umc/meshes`（または `HYDRA_UMC_MESH_CACHE`）に保存されて再利用されます。ネットワークがない場合は、パッケージをそこにコピーするか、`HYDRA_UMC_MESH_PACKAGE` にそのパスを指定してください。取得元は `auto`（既定）、`local`（ダウンロードしない）、`download`（各メッシュをハッシュで検証）で、`mesh_pack.config.json` または `HYDRA_UMC_MESH_SOURCE` で選びます。一致しないパッケージは何もインストールせず、`https` アドレスのみ受け付けます。ビルド済みのプログラムにはモデルが含まれます。メッセージは 8 言語に対応しています。[`docs/MESH_PACKAGE.md`](docs/MESH_PACKAGE.md) を参照してください。

## 🔒 セキュリティと安全

| 脅威 | 防御 | 場所 |
|---|---|---|
| 設定ファイルに置かれたパスワード | 認証情報は `keyring` 経由でシステムの安全なストア（Windows 資格情報マネージャー、Linux の Secret Service）に保存されます。本物のストアが無いコンピューターでは、パスワードを平文で書かずに何も保存しません | `hydra_suite/credentials.py` |
| 誤った、または悪意のある応答をするサーバー | 探索の応答には必要なキーが正しい型で含まれている必要があり、クライアントはすべての返答を信頼しません。検証スクリプトが悪意のある応答を与え、アプリが落ちず、受け入れないことを確認します | `hydra_suite/net/discovery.py`, `tests/verify_hostile_server_answers.py` |
| ネットワーク上での通信の盗み見やサーバーのなりすまし | クライアントは TLS 証明書を検証する `httpx` を使い、これを無効にするスイッチはありません。TLS 自体はサーバー側で任意で既定はオフ（Server Admin）なので、平文 HTTP の LAN では通信は隠されません | `hydra_suite/net/client.py` |
| 待たされる、または失われる停止 | STOP は常にヘッダーにあり（F12 でも可）、確認なしで、接続中のすべてのサーバーに `POST /api/stop-all` を 2 秒の制限と 1 回の再試行で送ります。止まらなかったロボットがある、状態を保存できなかった、停止が確認されなかった場合は、赤いメッセージが次の STOP まで残ります | `hydra_suite/net/client.py`, `qt_suite.py`, `tests/verify_stop_all.py` |
| アクセスオプションを誤って弱める（音声、MAVLink、Bluetooth、TLS など） | Server Admin パネルは各値の出どころを示し、サーバーの環境変数が決めたものをロックし、保護を弱める前に確認し、警告を画面に残します。対象は、話した内容を繰り返す音声返答、認識信頼度 0、署名のない MAVLink メッセージ、MAVLink 署名オフです | `hydra_suite/panel_logic/server_security.py`, `tests/verify_server_security.py` |
| ロボットが届かないインポートされた Work、または改ざんされた監査記録 | Work はロボットが許容差内（既定 5 mm、`work_reach_tolerance_mm` で 0.5〜50 mm）で届く必要があり、届かなければ拒否されます。監査記録はハッシュチェーンとして、サーバー（`?verify=1`）と、このプログラムが受け取った内容に対して確認できます | `hydra_suite/reach.py`, `hydra_suite/access.py` |

**絶対にしないこと：** 安全の判断、およびハードウェアの非常停止経路になること。制限、ロール、予約はすべてサーバーのものです。このアプリは実際のコントローラーやロボットに対して動かしたことがありません。

## 🔌 インターフェース

| トピックまたはルート | 内容 |
|---|---|
| `/api/*`, `/ws` | HYDRA-UMC-SERVER の REST と WebSocket プロトコル。ヘッダー `X-Hydra-Client: suite/<version>` により、管理者がこのアプリだけを許可・遮断できます |
| `GET /api/hydra-info`, `_hydra._tcp.local.` | 探索：ポート 3000 のサブネットスキャン（1 ホット 1.5 秒、同時 64）と mDNS（4 秒）、または入力したアドレス（VPN 経由も可） |
| `HYDRA_UMC_DATALAKE_URL` | テレメトリパネル用の HYDRA-UMC-DATALAKE の任意のアドレス |
| `hydra_suite/can_ota.py` | サーバー経由の Flasher と Tester の CAN-OTA 階層（URTC と HYDRA-UMC）。実機ができるまでは内蔵シミュレーション |
| F11, F12 | F11 で全画面を切り替え、F12 で全体 STOP を送る |

## ⚙️ 設定

プログラムは小さな `hydra_suite_config.json` を保持します。そのフォルダーが書き込み可能な間（ポータブル版、ソースのチェックアウト）はプログラムの隣、そうでなければユーザーのフォルダー（Windows は `%APPDATA%\HYDRA-UMC-SUITE`、Linux は `$XDG_CONFIG_HOME/hydra-umc-suite`）です。下のアクセススイッチは、Server Admin が編集するサーバーのものでこのファイルのものではありません。

| 変数 | 既定値 | 設定する内容 |
|---|---|---|
| `language` | `english` | 画面の言語：english、spanish、german、french、italian、japanese、chinese、portuguese（`language/*.lng`） |
| `work_reach_tolerance_mm` | `5.0` | インポートした Work の点が要求姿勢から外れてよい量（0.5〜50 mm） |
| `HYDRA_UMC_DATALAKE_URL` | 空 | テレメトリパネル用の DATALAKE のアドレス |
| `aiAccess` | `open` | ローカル AI リレーを使える人。`open` はサインイン済みの全アカウント、`admin` は管理者のみ |
| `infoAuth` | オフ | 読み取り専用のホスト情報（メトリクス、プロセス監視、エコシステム状態）にサインインを要求する |
| `tls.enabled` | オフ（平文 HTTP） | 指定した証明書と鍵で HTTPS / WSS にする。使用中の証明書のフィンガープリントを画面に表示 |
| `ble.mode` | `off` | サーバー近くのスマートフォン向け Bluetooth LE：`off`、`state`（状態の公開のみ）、`commands`（コマンドも受付）。不明な語はオフ扱い |
| `ble.requireEncryption` | オン | コマンド用キャラクタリスティックへの書き込みと状態の読み出しは暗号化されたリンクのみ。変数が `off` のときだけ無効 |
| `mqtt.mode` | `off` | セルのブローカーへの MQTT ブリッジ：`off`、`state`、`commands`。URL・プレフィックス・ユーザーも設定 |
| `voice.includeHeardText` | オフ | 音声の返答が話した内容を繰り返す。個人データなので既定はオフで、変数では `1` という語だけがオンにします |
| `voice.minConfidence` | `0.6` | 動作を始める要求を受け付ける音声認識の最小信頼度（0〜1）。0 で確認をオフにし、停止は決して保留されません。変数の不正な数値は無視されます |
| `mavlink.signingKeyFile` | 空（署名なし） | UAV ブリッジの MAVLink 2 署名：32 バイトの鍵（生の 32 バイトまたは 16 進 64 文字）を入れたファイルのパス。保存するのはパスだけで鍵は保存せず、ブリッジは起動時に読みます |
| `mavlink.signingAllowUnsigned` | オフ | 署名のないメッセージも受け付ける（まだ署名しない機体向け）。オンの間は画面が警告します |

## 🚀 クイックスタート

Python 3.12 以上が必要で、実際に使うには起動中の HYDRA-UMC-SERVER が必要です（サーバーパネルがネットワークをスキャンするか、アドレスを受け付けます）。

```bash
python -m venv .venv                   # Windows: .venv\Scripts\activate - Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py                         # starts the app; F11 toggles full screen, F12 sends the global STOP
python tools/run_offline_verifiers.py  # every verifier under tests/, headless
```

バージョンは **ヘルプ > バージョン情報** に表示されます。`build_exe.bat` / `build_exe.sh` でのビルドは変更せず、明示的なコマンド `python tools/hydra_project_tool.py bump` だけが変更します。各バージョンの変更点は [`CHANGELOG.md`](CHANGELOG.md) を参照してください。

## 🧪 テスト

`python tools/run_offline_verifiers.py` で自動テスト 47 件を実行します。 各テストは 1 つの検証スクリプトで、多数のチェックを含みます（単一のアサーションではありません）。PySide6 などの依存関係が必要で、画面なしの Qt プラットフォームで動き、実際のサーバーやロボットへの接続は開きません。

CI は `HYDRA_UMC_CI=1 python tools/ci_validate.py` を実行し、マニフェスト、文書、8 つの README、図を検査します。

## 🏗️ ビルドとリリース

### はじめに

### 必要環境
- Python 3.12 以上（CI は 3.12 を使用、ローカルでは 3.14 でも実行）
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

最小 1280x720 の最大化ウィンドウで起動します（本アプリ自身の設計仕様に基づく）——いつでも **F11** を押すことでフルスクリーンと通常の最大化ウィンドウを切り替えられるため、逃げ道なくトラップされることは決してありません。**Servers** パネルを使ってネットワークをスキャンするか、アドレスを指定して HYDRA-UMC SERVER サーバーを追加してください。

いつでも **F12** を押すとグローバル STOP を送信します（上部バーの **STOP** ボタンも同じです）。

### 技術スタック

- **UI フレームワーク:** PySide6(Qt6)と Qt Quick(QML) - インターフェースは 1 つで、独自のドッキングフレームワークは作り直していません
- **3D レンダリング：** PyOpenGL（コアプロファイル GLSL シェーダー）+ numpy-stl
- **ネットワーキング：** `httpx`（REST）+ `websockets`（リアルタイム同期）、`qasync` を介して Qt 自身のイベントループに統合——別個のワーカースレッドなし
- **数学：** NumPy（正運動学のための 4x4 同次変換）

### スタンドアロン実行ファイルのビルド

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

### インストーラーの確認

Windows 用インストーラーは Authenticode で署名されていないため、実行時に Windows SmartScreen が警告を出すことがあります。代わりに、インストーラーの SHA-256 チェックサム（`.sha256`）と Ed25519 署名（`.sig`）がリリースに併せて公開されます。実行前に確認してください。チェックサムは `sha256sum`（または `Get-FileHash`）で比較し、署名は HYDRA-UMC-TOOL-CLI の `hydra-sign verify --pub PUBLIC.pem FILE` で、HYDRA リリース鍵の公開鍵を使って検証します。これは Authenticode の代わりではなく、ファイルが公開されたものと同一であることを確かめる手段です。

## 🩺 トラブルシューティング

| 表示 | 原因 | 対処 |
|---|---|---|
| サーバーパネルが何も見つけない | サーバーが別のサブネットにある、ファイアウォールがポート 3000 や mDNS を遮断している、またはサーバーが動いていない | アドレスでサーバーを追加する（VPN トンネルも使えます） |
| 起動のたびにパスワードを聞かれる | このコンピューターには本物の安全なストアが無いため、プログラムはパスワードを保存しません | Secret Service のプロバイダーを入れる（Linux）か Windows で使う。これは意図した動作です |
| STOP のメッセージが赤いまま | 止まらなかったロボットがある、停止状態を保存できなかった、またはサーバーが停止を確認しなかった | メッセージを読み、ロボットを確認して、もう一度 STOP を押す。次の STOP まで残ります |
| インポートした Work が拒否される | Work の点が、このロボットが届く範囲から許容差より遠い | 別のロボットモデルを選ぶか、`work_reach_tolerance_mm` を上げる（最大 50） |

## 📂 リポジトリの構成

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-SUITE" width="100%">
</p>

<details>
<summary>ツリーのテキスト版</summary>

```text
HYDRA-UMC-SUITE/
├── hydra_suite/                                                                                            ソースコード
│   ├── models.py                                                                                           HydraState/ControllerView/RobotView/CameraView - 実際のsettings.json構造の上に構築された、軽量で変更しやすいビュー
│   ├── app.py                                                                                              SuiteController - 接続群と「アクティブ」選択を管理する。各パネルはこれと通信する
│   ├── i18n.py                                                                                             8言語対応のKEY=Valueローダー（language/*.lng）
│   ├── can_ota.py                                                                                          共有のCAN-OTA/SPI-OTAトランスポート（STUDIO自身のcanOta.tsの実際の移植）- FlasherとTesterで使用
│   ├── logging_handler.py                                                                                  PythonのロギングをLogsパネルへルーティング
│   ├── diagnostics.py                                                                                      サポート用バンドル（バージョン、サーバー、ログを含む zip。認証情報は除外）
│   ├── net/                                                                                                REST・WebSocket クライアントと探索
│   ├── render/                                                                                             OpenGL ビューと運動学
│   ├── robot_catalog.py                                                                                    24 のロボットモデルのメーカーと自由度のメタデータ (STUDIO のものと手作業で同期)
│   ├── access.py                                                                                           コントローラ ID、予約、サーバーから読む安全上限、Live / Sim - Qt もネットワークも不要
│   ├── reach.py                                                                                            各モデルのツールが届く位置、逆運動学、Work の拡縮 - Qt もネットワークも不要
│   ├── credentials.py                                                                                      記憶したサーバー: 設定ファイルとオペレーティングシステムの安全な保管領域(keyring)
│   ├── joint_limits.py                                                                                     可動範囲を公開しているモデルの各関節の範囲
│   ├── nav_items.py                                                                                        ナビゲーション: ルートメニューと Industrial / URTC / HYDRA-UMC サブメニュー
│   └── panel_logic/                                                                                        ウィンドウに依存しないパネル用の値と処理: ティア、既定値、MJPEG の解析、スーパーバイザーのグラフ
├── .github/                                                                                                CIワークフロー、issueテンプレート、PRテンプレート（汎用、エコシステム共有）
├── assets/                                                                                                 QML 画面とロボットのメッシュ
├── language/                                                                                               english/spanish/french/german/italian/japanese/chinese/portugueseの.lngファイル
├── docs/                                                                                                   プロジェクトの文書
├── tools/                                                                                                  プロジェクトのツールと CI の検査
├── tests/                                                                                                  実際のヘッドレステストスイート（QApplication、ディスプレイ不要）- パネル/サブシステムごとに1つのverify_*.py、加えて運動学の移植と、実際に稼働中のSTUDIOサーバーが必要な手動スモークテスト
├── installer/                                                                                              プラットフォームごとのパッケージング資料・アセット
├── .vscode/                                                                                                Pythonインタープリターのパス、起動構成、推奨拡張機能
├── images/                                                                                                 バナーと README の図
├── main.py                                                                                                 エントリーポイント - Qt Quick インターフェースを起動(最大化、最小 1280x720。F11 で本当の全画面を切り替え)
├── qt_suite.py                                                                                             Qt Quick フロントエンド - 変更のない SuiteController を QML につなぐ(全 33 パネル)
├── verify_qt_suite_shell.py                                                                                ハードウェア/ネットワーク不要の本物のQt Quickシェルチェック —— tests/ の外に意図的に配置(URTC-TESTER/URTC-FLASHER自身のverify_qt_*.pyと同じ理由)、`QT_QPA_PLATFORM=offscreen python verify_qt_suite_shell.py` で実行
├── requirements.txt                                                                                        固定された依存関係
├── hydra-umc.project.json                                                                                  エコシステムマニフェスト - バージョン/ファミリー/親、dashboard/updater/OS-REBUILDERが読み取る実際の情報源
├── bump_version.py                                                                                         明示的なバージョン更新
├── bump_manifest_version.py                                                                                hydra-umc.project.jsonのバージョンをネイティブのものと同期（汎用、エコシステム全体でそのままコピーされる）
├── build-test.bat / build-test.sh                                                                          .venv を有効化して tools/build_test.py（実際のテストスイート）を実行、変更を伴わない - バージョンを増分せず、CHANGELOG.mdにも触れない
├── run.bat / run.sh                                                                                        venv経由でmain.pyを起動
├── mesh_pack.config.json                                                                                   3Dモデルの取得元：local（既定）、auto、download、およびパッケージのアドレス
├── meshes.pack.json                                                                                        メッシュパッケージとそれに含まれる各メッシュのサイズと SHA-256
├── HYDRA-UMC_SUITE.spec                                                                                    PyInstallerスペック（下記build_exe.bat/.sh参照）
├── build_exe.bat                                                                                           ワンショットのWindowsビルド -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                                                                                            ワンショットのLinuxビルド -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md   各バージョンの変更点
└── test.sh                                                                                                 テストを実行
```

</details>

## 🗺️ ロードマップと既知の制限

**現時点の既知の制限**

* CAN-OTA の URTC Tool Head と Advanced Expansion 階層には、ハードウェアへの実際の中継トンネルがなく、チェーンは内蔵シミュレーション上で動きます。
* ロボット結合モード（`combinedWith`）は STUDIO のデータモデルにはありますが、このアプリでは公開されていません。
* この README にはまだスクリーンショットがありません。
* このアプリは実際のコントローラーやロボットに対して動かしたことがなく、Qt Quick が唯一の画面です。従来のウィンドウは削除されました。

**次：** STUDIO の新機能はすべてここへ移植します。完了と先送りの詳細な一覧は `docs/ROADMAP.md` を参照してください。

## 🌍 言語

この README とリポジトリの文書は、英語・スペイン語・ドイツ語・フランス語・イタリア語・日本語・中国語・ポルトガル語（ポルトガル）の 8 言語で提供されています。8 つのファイルは同時に書かれ、同じ節と同じリンクを持つことを CI が確認します。

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**親プロジェクト**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。本コマンドセンターはその実際のクライアントであり、mDNS でネットワーク上に発見する。

**兄弟プロジェクト** —— それぞれ独自のクライアントとして、同じく HYDRA-UMC-SERVER 自身の API と通信する
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界(エミュレートしたフリートに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界(エミュレーターに対してのみテスト済み)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — キー/筐体/インターロックの GPIO 信号 3 系統を読み取るレーザーセルのコーディネーター(模擬チップに対してのみテスト済み。レーザーの武装や発射はできない)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 遅延インポートの rclpy ROS 2 トランスポートを持つコーディネーター(ROS 2 環境ではまだ実行していない)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界(エミュレーターに対してのみテスト済み)。

**直接関連**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実機の間にソフトウェアの衝突インターロックを備えたハードウェア・イン・ザ・ループのルーター(実機なしでテスト済み)。実際の HYDRA-UMC コントローラーをハードウェア・イン・ザ・ループのブリッジに置き換え、ワークフローの他の部分を一切変えずに、本コマンドセンターがデジタルツインを実機のように制御できるようにする。
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。本コマンドセンターが最終的に従うスウォームコマンドセンターであり、単一のデスクトップセッションでは届かないレベルで HYDRA-UMC コントローラーの群れを調整する。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を持つフリート CLI、HYDRA-UMC-SERVER 自身の API の本物のライブクライアント。スクリプティングやヘッドレス環境向けに、コマンドラインからこのデスクトップコマンドセンターと同じ DevOps 機能セットを提供する。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — ロボットアームのマザーボードの設計——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括することを目指す(ファームウェアは初期段階で、実装済みの基板はまだない)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが自身のコマンドを検証する共有 JSON-Schema 契約とソフトウェアのジョブゲート境界(認証済みの安全機能ではない)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 外部マシン用コネクタのための宣言的アダプターマニフェストのレジストリとバリデーター。SDK 自身の契約という発想を外部マシンにまで拡張し、産業用ゲートウェイ系のプロジェクトを置き換えることはありません。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — 本アプリ自身の `assets/meshes/` ライブラリ（および STUDIO が保持するそのミラー）向けのデスクトップ STL モデルエディタ - 実在するパーツを変換/置換/削除/追加し、何かを永久に削除することは決してない。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由の 25 以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板用のデスクトップ GUI 書き込みツール、CAN-OTA およびフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けのデスクトップ CAN バスライブ診断ツール、ツールプロファイルごとに 1 パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API を使ったブラウザベースの URTC-TESTER の代替、ローカルインストール不要。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — URTC の CAN バスの前に置くゲートウェイ：許可する識別子のリスト、レート制限、セッション鍵。コンピューター上でテスト済みで、実際のバスではまだ試していません。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ゾーン状態を条件に承認する Position-Based Visual Servoing 補正則。カメラによる姿勢推定はまだない。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — ファイルから物体位置を受け取る、ゾーン侵入・キャリブレーション鮮度・E-STOP 要求の v0 ロジック。検出器は接続されておらず、物理 E-STOP もまだ配線されていない。

*コグニティブ AI ノード(Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — 確認ゲート付きの限定的な Watch リレーを備えた、実際の音声フロントエンド(VAD + 意図解析)。
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — エコシステム自身のための、ローカルでポリシーゲート付きのAIメンテナンス技術者 — 観察、診断し、修正を提案する;最上位の2つのリスクレベルは意図的にまだ実装されていない。

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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 触覚アラートのパターンとペアリング済みスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ(物理的なウォッチではまだ実行していない)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際の工具 ID デコードと Smart Idle 予熱ロジックを備えた、基板搭載ラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの、ファームウェアと実際の Python ビジョンコンパニオン。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — このエコシステム内のすべてのリポジトリを検出・クローン・更新する、管理用デスクトップツール。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — エコシステムの最新バージョンをプリロードした、書き込み可能なCM5イメージを構築するWindows/Linuxデスクトップツール。Raspberry Pi Imager方式の初回起動Wi-Fi/ユーザー/SSH設定を備える。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 保守インシデントコーディネーター: 低権限のエッジ役割がサニタイズされたインベントリ/ヘルスのスナップショットを収集し、コントロールプレーン役割がそれを読み取り専用でレンダリングして AI プロバイダーに診断の提案を依頼します - パッチを適用することも、何かをデプロイすることも決してありません。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 再現可能な開発ホスト（Raspberry Pi 5 / CM5）。エコシステムのソースコードを保管し、永続キューのもとで境界の明確なビルド/テストタスクを実行する。運用中の CM5 とは明確に異なる、開発専用の役割。

## 📚 ドキュメント

さらに読むには：

* **[docs/ROADMAP.md](docs/ROADMAP.md)** —— 今日の時点で実際にエンドツーエンドで検証済みのものと、意図的にまだ対象外のもの。
* **[installer/README.md](installer/README.md)** —— Windows 用 `.exe` インストーラーと Linux 用 `.deb` パッケージのビルド方法。
* **[docs/MESH_PACKAGE.md](docs/MESH_PACKAGE.md)** — チェックサムを固定した 1 つのパッケージとしての 3D メッシュ。取得元 `local`、`auto`、`download` と、検証・取得のコマンド。
* **[docs/MACHINE_ASSETS.md](docs/MACHINE_ASSETS.md)** — 独立した機械モデル：モデルの選び方と所有者。
* **[docs/RACK_MODELS.md](docs/RACK_MODELS.md)** — 設定可能な入力・出力ラック：設定と互換性。
* **[docs/HEATED_BED_MODELS.md](docs/HEATED_BED_MODELS.md)** — ヒートベッドのモデル：4 つのプリセットの選択と寸法。
* **[docs/VACUUM_TABLE_MODELS.md](docs/VACUUM_TABLE_MODELS.md)** — 真空テーブルのモデル：ロボットに割り当てる方法。
* [エコシステムのセキュリティ基準](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [エコシステムの脅威モデル](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [このリポジトリのライセンス](LICENSE.md)

## 🤝 コントリビュートとコミュニティ

* プルリクエストの前に `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（または `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）を実行してください。`CI_VALIDATION=PASS` と表示される必要があります。この確認に `build.sh` や `build.bat` は使わないでください。ビルドは検査ではありません。
* 8 つの README は HYDRA-UMC-DOCS の 1 つのソースから書かれます。手で編集しないでください。ソースを変更し、`tools/make_readmes.py` で書き直します。
* 実行していないことを README に書かないでください。事実であれば「シミュレーションのみ」「実機では未確認」と書きます。
* [CONTRIBUTING.md](CONTRIBUTING.md)、[行動規範](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md)、[SUPPORT.md](SUPPORT.md) を参照してください。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE).
