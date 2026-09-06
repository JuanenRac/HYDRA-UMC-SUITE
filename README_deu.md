<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-SUITE banner" width="100%">
</p>

# 🧰 HYDRA-UMC SUITE

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  🇩🇪 <b>Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


### 🖥️ Multi-Controller-Schwarm-Kommandozentrale für die HYDRA-UMC-Plattform

<p align="center">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Sprache-Python%203.12-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
</p>


---

## 🎯 Überblick

**HYDRA-UMC SUITE** ist eine native Windows/Linux-Desktopanwendung (Python
+ PySide6/Qt6), die als Missionskontrollzentrale für eine ganze Flotte von
[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)-Controllern gleichzeitig
gebaut wurde - durchsuche das lokale Netzwerk (oder füge einen manuell
hinzu, auch über einen bereits verbundenen VPN-Tunnel zu einem HYDRA-UMC in
einem anderen physischen Netzwerk), verbinde dich mit so vielen wie
gefunden werden, und steuere/überwache/konfiguriere jeden von ihnen live,
nebeneinander, von einem einzigen industriellen Vollbild-Dashboard aus.

Es spricht genau dasselbe Übertragungsprotokoll, das
[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) bereitstellt
- dasselbe Headless-Backend, mit dem auch die eigene Browser-Oberfläche von
[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) als
einer von mehreren Clients spricht - siehe
[`HYDRA-UMC-SERVER/docs/REMOTE_API.md`](https://github.com/JuanenRac/HYDRA-UMC-SERVER/blob/main/docs/REMOTE_API.md)
für den vollständigen Vertrag, der eigens hinzugefügt wurde, um dieses
Projekt zu unterstützen. Eine von SUITE aus vorgenommene Änderung erscheint
live in einem geöffneten Browser-Tab, und umgekehrt - echte bidirektionale
Synchronisierung über WebSocket, kein einmaliger Import/Export.

**Ehrlichkeitshinweis, passend zur eigenen Dokumentationskonvention des
restlichen Ökosystems:** dies ist ein erster echter, funktionierender
Durchgang, kein fertiges Produkt. Siehe
[`docs/ROADMAP.md`](docs/ROADMAP.md) für genau das, was heute wirklich
implementiert und Ende-zu-Ende verifiziert ist, gegenüber dem, was
absichtlich für später aus dem Umfang ausgeklammert wurde. Zum Zeitpunkt
dieses Durchgangs verfügt jedes reale Robotermodell, das dieses Ökosystem
unterstützt, über echte STL-Geometrie und numerisch verifizierte
Vorwärtskinematik, die in das 3D-Viewport eingebunden ist (Parol6, Faze4,
AR3, AR4, UR3e/5e/10e/16e/20, xArm6, Lite 6, e.DO), plus ein aus Primitiven
gebauter "Generic"-Fallback für jedes Modell ohne eigenen Mesh-Satz.

---

## ✨ Visuelles Command Deck

Der Desktop enthält jetzt ein dauerhaftes, von Spielemenüs inspiriertes Command Deck mit dem offiziellen HYDRA-UMC-Symbol und der dunkelblau/cyanfarbenen Sprache von HYDRA-UMC-UPDATER. Die Steuerelemente für Übersicht, Robotersteuerung, Kameras, Trajektorie und Logs öffnen die jeweiligen echten, andockbaren Panels; rechts stehen Verbindungsstatus, aktives Serverziel und UTC-Uhr. Es ist eine visuelle Ebene über echten Suite-Funktionen, kein simuliertes Dashboard.

### Vollständiges Qt-Quick-Redesign (`--qtquick`)

Dieses Command Deck ist eine Ebene über dem klassischen `QMainWindow`. Diese App hat außerdem eine völlig eigenständige Qt-Quick-Shell:

~~~
python main.py --qtquick
~~~

Ein echtes QML-`ApplicationWindow` - anders als das obige Command Deck überhaupt nicht in das klassische Fenster eingebettet (beide echten Wege, QML in den klassischen `QMainWindow`/`QDockWidget`-Baum einzubetten, wurden ausprobiert und verworfen: `QQuickWidget` zeigte durchgehend Schwarz, und `QQuickView`+`createWindowContainer()` rendierte isoliert korrekt, verfälschte aber die echte Z-Reihenfolge benachbarter Docks, sobald es in das echte 26-Dock-Layout dieser App eingesetzt wurde). Dasselbe reale, bereits bewährte Muster, das HYDRA-UMC-OS-REBUILDER, HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER und HYDRA-UMC-EDITOR-URDF bereits verwenden, gestartet neben dem unveränderten klassischen Einstiegspunkt, ohne ihn zu ersetzen. Tauscht die Flexibilität von `QDockWidget` (freischweben/teilen/als Tabs zusammenführen) gegen STUDIOs eigene einfachere Form aus Navigations-Seitenleiste plus einem einzigen Inhaltsbereich (bildet die reale Taxonomie von `nav_sidebar.py` Punkt für Punkt nach) - alle 26 echten klassischen Panels sind zu echtem QML-Inhalt portiert, einschließlich des 3D-Viewports, dessen Live-Vorschau über einen eigenen `OffscreenRobotRenderer` gespeist wird (ein echter, separater `QOpenGLContext`/`QOffscreenSurface`/Framebuffer, bewusst nicht das eigene `QQuickFramebufferObject` von Qt Quick, das das gesamte Quick-Backend der App vom echten Direct3D11-Standard unter Windows auf OpenGL zwingen würde) und dabei denselben echten Rendering-Code (`RobotGLRenderer`) wiederverwendet, den das klassische Viewport-Widget nutzt, übertragen an QML über einen `QQuickImageProvider`.

## 🏭 Funktionen

- **🔍 Netzwerkerkennung** - ein gleichzeitiger Subnetz-Scan (`GET /api/hydra-info`) und echtes mDNS/Bonjour (`_hydra._tcp`, derselbe Dienst, den `server.ts` veröffentlicht und den HYDRA-UMC-IOS-CONTROL bereits abfragt) laufen gemeinsam auf der Suche nach echten HYDRA-UMC-STUDIO-Servern, dedupliziert nach Host:Port, plus manuelles Hinzufügen per Adresse für alles, was keines von beiden erreichen kann (ein anderes Subnetz, ein VPN-Tunnel).
- **🐝 Schwarmverbindungen** - verbinde dich mit so vielen HYDRA-UMC-Servern
  gleichzeitig, wie du willst, jeder mit seiner eigenen live
  WebSocket-Synchronisierung; wähle, welcher für die anderen Panels
  "aktiv" ist.
- **📊 Übersicht** - Roboterliste pro Controller: Modell, Rolle,
  Online-Status, Geschwindigkeit/Beschleunigung, auf einen Blick.
- **🦾 Robotersteuerung** - Drehregler + Schieberegler pro Gelenk (das
  Desktop-Gegenstück zum eigenen `RotaryKnob`+`FuturisticSlider`-Jog-Paar
  von HYDRA-UMC STUDIO), Geschwindigkeits-/Beschleunigungsregler, alles
  wird live zurückgeschrieben.
- **🧊 Echtes 3D-Viewport** - OpenGL 3.3, echte STL-Meshes, echte
  Vorwärtskinematik für alle 24 realen Robotermodelle (numerisch
  verifiziert gegen die eigene TypeScript-Implementierung von HYDRA-UMC
  STUDIO, bit-für-bit identische Ergebnisse) plus ein aus Primitiven
  gebauter "Generic"-Fallback - für keinen von ihnen ein stilisierter
  Platzhalter.
- **📍 Trajektorienpunkte** - zeichne die Live-Pose des ausgewählten
  Roboters auf, fahre auf Wunsch zu jedem aufgezeichneten Punkt zurück.
- **🪟 Andockbarer Arbeitsbereich im Photoshop-Stil** - jedes Panel ist ein
  echtes `QDockWidget`: ziehen, um es frei schweben zu lassen, zurückziehen
  zum Andocken oder Zusammenführen in eine Tab-Gruppe, den Arbeitsbereich
  aufteilen, schließen und über das Ansicht-Menü wieder anzeigen. Ein
  freischwebendes Panel wird zu einem echten Top-Level-Fenster - es auf
  einen zweiten (oder dritten) physischen Monitor zu ziehen und dort zu
  lassen, funktioniert daher von Haus aus: Qt/der Fenstermanager des
  Betriebssystems platziert es wie jedes andere Fenster, ganz ohne
  eigenen "Multi-Monitor-Modus".
- **🌐 7 Sprachen** - English, Español, Italiano, Français, Deutsch, 简体中文,
  日本語
  (dieselbe `language/*.lng`-Konvention wie URTC-FLASHER/URTC-TESTER), wird
  über das Sprachmenü gewechselt (wirksam nach einem Neustart).
- **📷 Kameras** - echte Kameraliste pro Controller (welche Kameras
  existieren, ihr Typ, Verbindungsstatus und ein
  echter USB/IP-(RTSP-)Quelltyp-Umschalter mit generischen, markenneutralen
  Host-/Port-/Pfad-/Zugangsdaten-Feldern), synchronisiert mit dem echten
  Server auf dieselbe Weise wie jedes andere Panel hier, plus echtes
  Live-Video: Die Metadaten sind durchgehend echt, und jede Kamerakarte
  rendert den echten MJPEG-Stream selbst (HYDRA-UMC-VISION-STREAMERs
  eigenes `stream serve`, weitergeleitet über HYDRA-UMC-SERVERs
  `GET /api/camera/:id/stream`) über einen echten JPEG-SOI/EOI-Marker-
  Scan-Client (derselbe echte Ansatz, den HYDRA-UMC-ANDROID-CONTROLs
  eigenes `MjpegStreamParser.kt` bereits verwendet), verifiziert gegen
  echte USB- und IP-Hardware.
- **🛠️ Werkzeug-Konfiguration, alle 11 von 11 Panels** - CNC, Laser,
  Heizbett, Vakuumtisch, ATC (Automatischer Werkzeugwechsler), XY-Tisch,
  Rack-Manager, Pick & Place, Kinematic Brain Stage, Flasher und Tester -
  echte Funktionsparität mit jedem einzelnen werkzeugspezifischen
  Bildschirm von HYDRA-UMC STUDIO, jeweils ein originalgetreuer Port
  (einschließlich des echten, manchmal eigenwilligen Verhaltens, das
  STUDIOs eigener Quellcode hat - absichtlich reproduziert statt hier
  "repariert") mit eigener echter Headless-Testabdeckung. CNC/Laser/
  Heizbett/Vakuumtisch teilen sich eine `ModuleConfigPanel`-Implementierung
  (STUDIOs eigene `CNC.tsx`/`Laser.tsx` sind bis auf den Modul-Schlüssel
  identische Komponenten); die übrigen 7 brauchten jeweils ein eigenes,
  eigens gebautes Panel. Alle 5 Module, die auf STUDIOs Seite eine
  Live-3D-Vorschau haben, haben sie jetzt auch hier: CNC/Laser/Heizbett/
  Vakuumtisch (`render/module_rig.py`, ein echter Port von STUDIOs
  eigener Box-/Zylinder-Geometrie) und Pick & Place
  (`render/pnp_rig.py`, ein echter Port von STUDIOs eigenem
  `LumenPnPRig.tsx` - die 5 echten `.stl`-Meshes in
  `assets/meshes/lumenpnp/`, positioniert über eine echte kartesische
  Portal-Kinematikkette statt Primitiven), jeweils gezeichnet von einem
  `RobotViewport` im eigenen modul-only-Modus.

---

## 📸 Fotos

Noch keine Screenshots - noch nicht für die Dokumentation erfasst. Starte
es (siehe unten), um das echte Ding zu sehen, anstatt hier später einem
veralteten Bild zu vertrauen.

---

## 📂 Repository-Struktur

```text
HYDRA-UMC-SUITE/
├── main.py                        # Einstiegspunkt - Vollbild min. 1920x1080, F11 schaltet zwischen Vollbild/Fenster um; --qtquick wechselt zum Panel unten
├── qt_suite.py                     # Qt-Quick-Frontend - eigenständiges `--qtquick`-Kommandopult (alle 26 Panels), verbindet den unveränderten SuiteController mit QML
├── requirements.txt
├── hydra-umc.project.json         # Ökosystem-Manifest - Version/Familie/Elternteil, die Quelle, die Dashboard/Updater/OS-REBUILDER lesen
├── bump_version.py                # Odometer-Versionserhöhung für das eigene __version__ von hydra_suite/__init__.py, ausgeführt von build_exe.bat/.sh vor jedem echten PyInstaller-Build
├── bump_manifest_version.py       # Synchronisiert die Version von hydra-umc.project.json mit der nativen (generisch, unverändert im gesamten Ökosystem kopiert)
├── build.bat / build.sh           # venv + editierbare Installation + echte Testsuite (inkrementeller Build, mit Versionierung)
├── build-test.bat / build-test.sh # Gleiche Prüfungen, ohne Mutation - erhöht nie die Version, rührt CHANGELOG.md nie an
├── run.bat / run.sh               # Startet main.py über das venv
├── HYDRA-UMC_SUITE.spec           # PyInstaller-Spec (siehe build_exe.bat/.sh unten)
├── build_exe.bat                  # Windows-Build in einem Schritt -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Linux-Build in einem Schritt -> dist/HYDRA-UMC_SUITE
├── CHANGELOG.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md / SECURITY.md / SUPPORT.md / LICENSE / LICENSE.md
├── README.md                      # diese Datei
├── README_spa.md / README_fra.md / README_ita.md / README_deu.md / README_zho.md / README_jpn.md  <- Übersetzungen
├── .github/                        # CI-Workflow, Issue-Vorlagen, PR-Vorlage (generisch, ökosystemweit geteilt)
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView/CameraView - leichte, mutationsfreundliche Ansichten über die echte settings.json-Form
│   ├── app.py                      # SuiteController - verwaltet den Schwarm an Verbindungen, die "aktive" Auswahl; jedes Panel spricht damit
│   ├── i18n.py                     # 7-Sprachen-KEY=Value-Lader (language/*.lng)
│   ├── can_ota.py                  # Gemeinsamer CAN-OTA/SPI-OTA-Transport (echter Port von STUDIOs eigenem canOta.ts) - genutzt von Flasher und Tester
│   ├── logging_handler.py          # Leitet Python-Logging an das Logs-Panel weiter
│   ├── net/
│   │   ├── discovery.py             # Gleichzeitiger Subnetz-Scan + echtes mDNS (_hydra._tcp) gegen GET /api/hydra-info, mit Deduplizierung
│   │   └── client.py                # REST- + WebSocket-Verbindung pro Server, echte bidirektionale Live-Synchronisation, Login, Admin-/Erkennungs-/PTZ-Endpunkte
│   ├── render/
│   │   ├── kinematics.py            # Vorwärtskinematik (portiert aus HYDRA-UMC-STUDIOs eigenem urKinematicsShared.ts)
│   │   ├── generic_rig.py           # Aus Primitiven gebautes Ausweich-Rig für jedes Modell ohne eigenes Mesh
│   │   ├── module_rig.py            # Geometrie der Werkzeugmodule (CNC/Laser/Heizbett/Vakuumtisch)
│   │   ├── pnp_rig.py               # Echte kartesische Portalkette für das LumenPnP/JuanenPnP-Mesh-Rig
│   │   ├── mesh.py                  # STL-Laden (numpy-stl)
│   │   └── viewport.py              # RobotGLRenderer (echte GLSL-Shader-Pipeline, Orbit-Kamera) + der klassische QOpenGLWidget-Wrapper + OffscreenRobotRenderer für das 3D-Viewport-Panel des `--qtquick`-Decks
│   └── ui/
│       ├── main_window.py           # QMainWindow + QDockWidget-Arbeitsbereich
│       ├── about_dialog.py          # Echter Über-Dialog (Version/Autor/Lizenz)
│       ├── theme.py                  # Lädt assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Selbst gezeichneter Drehregler (Desktop-Gegenstück zu RotaryKnob.tsx)
│       └── panels/                   # Eine Datei pro andockbarem Panel - echte 1:1-Parität mit STUDIOs eigenen Tabs: server_browser, overview, robot_control, viewport_panel, trajectory_panel, cameras_panel (+ echte PTZ-Steuerung), ai_family_status_panel, ecosystem_services_panel, ecosystem_telemetry_panel, admin_clients_panel, admin_logs_panel, admin_server_panel, logs_panel, module_config_panel (+cnc/laser/heated_bed/vacuum_table), atc_tools_panel, xy_table_panel, rack_config_panel, pick_and_place_panel, kinematic_brain_stage_panel, flasher_panel, tester_panel
├── assets/
│   ├── qss/industrial_dark.qss     # Das futuristisch-industrielle Qt-Stylesheet
│   ├── qml/Main.qml                 # Qt-Quick-UI des `--qtquick`-Kommandopults (alle 26 Panels)
│   └── meshes/                      # Echte STL-Meshes, ein Ordner pro Roboter/Modul, kopiert aus HYDRA-UMC-STUDIOs eigenem public/models/ (jeweils mit eigener ATTRIBUTION.txt)
├── language/                        # .lng-Dateien english/spanish/french/german/italian/japanese/chinese
├── docs/
│   └── ROADMAP.md                   # Ehrliche Aussage zum echten Umfang vs. noch nicht Umgesetztem
├── tools/
│   ├── build_test.py                # Nicht-versionierende Kompilierungsprüfung (generisch, ökosystemweit geteilt)
│   └── ci_validate.py               # Manifest-/CHANGELOG-/Doku-Validierung, von der CI verwendet (generisch, ökosystemweit geteilt)
├── tests/                           # Echte Testsuite ohne Anzeige (QApplication, kein Display nötig) - ein verify_*.py pro Panel/Subsystem, plus Kinematik-Ports und manuelle Smoke-Tests, die einen echten laufenden STUDIO-Server brauchen
├── installer/                       # Hinweise und Assets zur Plattform-Paketierung
└── .vscode/                         # Python-Interpreter-Pfad, Startkonfigurationen, empfohlene Erweiterungen
```

---

## 🚀 Erste Schritte

### Voraussetzungen
- Python 3.12+ (entwickelt/getestet mit 3.14)
- Ein laufender [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)-Server, zu dem verbunden wird

### Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux

pip install -r requirements.txt
```

### Ausführen

```bash
python main.py
```

Startet im Vollbild mit einem Minimum von 1920x1080 (gemäß der eigenen
Design-Spezifikation dieser App) - drücke jederzeit **F11**, um zwischen
Vollbild und einem normalen maximierten Fenster zu wechseln, sodass sie
dich nie wirklich ohne Fluchtweg gefangen hält. Verwende das Panel
**Servers**, um dein Netzwerk zu scannen oder einen
HYDRA-UMC-STUDIO-Server per Adresse hinzuzufügen.

---

## 🛠️ Technologie-Stack

- **UI-Framework:** PySide6 (Qt6) - native andockbare Panels, kein
  eigenes neu erfundenes Docking-Framework
- **3D-Rendering:** PyOpenGL (Core-Profile-GLSL-Shader) + numpy-stl
- **Netzwerk:** `httpx` (REST) + `websockets` (Live-Synchronisierung),
  integriert in die eigene Event-Loop von Qt über `qasync` - kein
  separater Worker-Thread
- **Mathematik:** NumPy (4x4-homogene Transformationen für die
  Vorwärtskinematik)

---

## 📦 Eine eigenständige ausführbare Datei erstellen

Zwei Wege, gleiches Ergebnis (`dist/HYDRA-UMC_SUITE.exe` unter Windows,
`dist/HYDRA-UMC_SUITE` unter Linux) - keine Python-Installation nötig, um
das Ergebnis in beiden Fällen auszuführen.

**Automatisiert (empfohlen):**

```bash
build_exe.bat    # Windows
./build_exe.sh   # Linux
```

Jedes Skript erstellt/verwendet `.venv` wieder, installiert
`requirements.txt` + PyInstaller darin, bereinigt jedes vorherige
`build/`/`dist/`, kompiliert mit PyInstaller (bündelt `assets/` und nur
die 4 Qt-Plugin-Unterordner, die diese App tatsächlich verwendet -
`platforms`/`styles`/`imageformats`/`iconengines`, nicht das gesamte
PySide6-Paket, was das Ergebnis im Bereich von einigen Dutzend MB statt
Hunderten hält), und kopiert `README.md`/`LICENSE`/`docs/` sowie die
editierbaren `language/*.lng`-Dateien neben die ausführbare Datei, anstatt
sie darin einzufrieren.

**Manuelles Äquivalent**, falls du jeden Schritt selbst sehen/kontrollieren
möchtest (dieselben Befehle, die die obigen Skripte ausführen):

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

# dann README.md, LICENSE, docs/ und language/ neben dist/HYDRA-UMC_SUITE.exe kopieren
```

Unter Linux (siehe `build_exe.sh` für den exakten, getesteten Befehl)
verwende `:` statt `;` als `--add-data`-Trennzeichen, entferne den
`OpenGL.platform.win32`-Hidden-Import (nur Windows), entferne
`--windowed`, und beachte, dass der Plugin-Pfad dort eine Ebene tiefer
verschachtelt ist (`<PySide6 dir>/Qt/plugins/platforms` gegenüber dem
flachen `<PySide6 dir>\plugins\platforms` unter Windows) - ein
Packaging-Detail des Wheels selbst, nicht etwas, das eines der beiden
Skripte gewählt hat. `HYDRA-UMC_SUITE.spec` im Repository-Root ist die
eigene generierte Spec-Datei von PyInstaller aus dem letzten Build -
sicher zu löschen und neu zu erzeugen, nicht von Hand gepflegt.

---

## 🔢 Versionierung

`hydra_suite/__version__` (angezeigt unter **Hilfe > Über**) folgt einem
Kilometerzähler-artigen `MAJOR.MINOR.PATCH`-Schema mit einer
Übertragsregel zur Basis 10: Patch erhöht sich bei jedem echten Build um
1; sobald er 9 überschreiten würde, wird er auf 0 zurückgesetzt und Minor
erhöht sich stattdessen um 1 (z. B. `0.1.9` -> `0.2.0`). „Ein echter
Build" bedeutet ein Lauf von `build_exe.bat`/`build_exe.sh` - **nicht**
jeder einfache Aufruf von `python main.py`. Die eigentliche Erhöhung
übernimmt automatisch `bump_version.py` (von beiden Build-Skripten vor dem
PyInstaller-Lauf aufgerufen), sodass eine gepackte `.exe`/Binärdatei immer
eine Versionsnummer trägt, die strikt neuer ist als die zuletzt tatsächlich
ausgelieferte. Siehe [`CHANGELOG.md`](CHANGELOG.md) für die Details dazu,
was sich an welcher Stelle geändert hat.

---

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Übergeordnetes Projekt**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht; dieser Leitstand ist ein echter Client seiner eigenen API und entdeckt sie im Netzwerk per mDNS.

**Geschwisterprojekte** — sprechen ebenfalls mit der eigenen API von HYDRA-UMC-SERVER, jeweils als eigener Client
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit echtem GRBL-Status-/Steuerbyte-Zugriff.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, liest 3 echte Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Sicherungen.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, träge importierten rclpy-ROS-2-Transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem echten MAVLink-Befehlssender.

**Direkt verwandt**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echte Hardware-in-the-Loop-Sicherheitsverriegelung, die Befehle zwischen Simulation und echter Hardware routet; ermöglicht diesem Leitstand, den digitalen Zwilling anzusteuern, als wäre er echte Hardware - ein echter HYDRA-UMC-Controller wird gegen eine Hardware-in-the-Loop-Bridge ausgetauscht, ohne sonst am Workflow etwas zu ändern.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine; der Schwarmleitstand, dem dieser Leitstand letztlich untersteht und der Flotten von HYDRA-UMC-Controllern auf einer Ebene koordiniert, die eine einzelne Desktop-Sitzung nicht erreicht.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER; bietet denselben DevOps-Funktionsumfang wie dieser Desktop-Leitstand von der Kommandozeile aus, für Skripting und Headless-Umgebungen.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das physische Motherboard des Roboterarms: CM5-Host + Dual-Core-STM32H745, koordiniert bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Sicherheitsschranke, gegen die jede Bridge ihre Befehle validiert.
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — deklaratives Adapter-Manifest-Register und Validator für Konnektoren externer Maschinen; erweitert die eigene Vertragsidee des SDK auf externe Maschinen, ohne die Industrie-Gateway-Projekte zu ersetzen.

*Kern-Backend & Clients*
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes Position-Based-Visual-Servoing-Korrekturgesetz, sicherheitsgesteuert nach vorgelagertem Zonenstatus.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und E-STOP-Anforderung, mit erzwungener Kalibrierungsaktualität.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrationsknoten, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe.

*Ergänzende Tools & Ökosystembetrieb*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux-Desktop-Tool, das ein flashbereites CM5-Image baut, vorgeladen mit den aktuellsten Versionen des Ökosystems, mit Ersteinrichtungs-Konfiguration für WLAN/Benutzer/SSH im Stil von Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — Wartungsvorfall-Koordinator: eine Edge-Rolle mit niedrigem Privileg sammelt einen bereinigten Inventar-/Gesundheits-Snapshot, eine Control-Plane-Rolle rendert ihn schreibgeschützt und bittet einen KI-Anbieter um einen Diagnosevorschlag - wendet nie einen Patch an und stellt nie etwas bereit.

---

## 📚 Dokumentation & Community

- **[docs/ROADMAP.md](docs/ROADMAP.md)** — was heute real und Ende-zu-Ende verifiziert ist, im Vergleich zu dem, was bewusst noch außerhalb des Umfangs liegt.
- **[installer/README.md](installer/README.md)** — den Windows-`.exe`-Installer und das Linux-`.deb`-Paket bauen.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieser App.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.
- **[LICENSE.md](LICENSE.md)** — die eigene Lizenz dieses Projekts sowie die separate Lizenz, unter der jeder Ordner in `assets/meshes/` weitergegeben wird.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

HYDRA-UMC SUITE ist (c) 2026 JuanenRac (Electro Hobby 3D). Dieser Hinweis muss in jede Weitergabe dieses Projekts oder abgeleiteter Werke aufgenommen werden.

Der Quellcode dieser Anwendung ist verfügbar unter der **GNU General Public License v3.0 (GPL-3.0)**. Vollständiger Text unter https://www.gnu.org/licenses/gpl-3.0.html.

**Diese Dokumentation** (dieses README und seine eigenen Übersetzungen - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) ist verfügbar unter **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Vollständiger Text unter https://creativecommons.org/licenses/by-sa/4.0/.

**Mesh-Assets von Drittanbietern:** jeder Ordner unter `assets/meshes/` ist wortgetreu aus dem eigenen offiziellen Hersteller-Repository dieses Roboters kopiert - NICHT von der obigen GPL-3.0 abgedeckt. Jeder hat seine eigene `ATTRIBUTION.txt` mit dem genauen Quell-/Lizenzverweis; die Tabelle unten fasst sie zusammen.

| Hersteller | Modelle | Lizenz |
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
| Universal Robots (klassisch) | UR3, UR5, UR10 | BSD-3-Clause |

Dieses Projekt ist das Desktop-Schwarmsteuerungs-Gegenstück zu [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) - siehe das eigene Repository dieses Projekts für dessen eigene separate Lizenz, auf die sich die eigene Lizenz dieses Repositorys nicht erstreckt, und umgekehrt. Es steuert letztlich auch die Hardware/Firmware von [HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) und (weitergeleitet über diese, [siehe hier](https://github.com/JuanenRac/HYDRA-UMC/blob/main/docs/architecture.md)) die [URTC](https://github.com/JuanenRac/URTC)-Werkzeugköpfe - beides separate Projekte mit ihren eigenen separaten Lizenzen.

Wenn du auf diesem Projekt aufbaust, behalte die Lizenzaufteilung im Hinterkopf: Codeänderungen sollten GPL-3.0 bleiben, und die eigenen Mesh-Assets jedes Roboters sollten unter ihren eigenen ursprünglichen Lizenzbedingungen bleiben (siehe Tabelle oben) - jeweils mit Namensnennung zurück zu diesem Projekt und seinem Autor.
