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

<p align="left">
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

## 🏭 Funktionen

- **🔍 Netzwerkerkennung** - gleichzeitiger Subnetz-Scan nach echten
  HYDRA-UMC-STUDIO-Servern (`GET /api/hydra-info`), plus manuelles
  Hinzufügen per Adresse für alles, was ein Scan nicht erreichen kann (ein
  anderes Subnetz, ein VPN-Tunnel).
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
- **🌐 5 Sprachen** - English, Español, Italiano, Français, Deutsch
  (dieselbe `language/*.lng`-Konvention wie URTC-FLASHER/URTC-TESTER), wird
  über das Sprachmenü gewechselt (wirksam nach einem Neustart).
- **📷 Kameras** - echte Kameraliste pro Controller (welche Kameras
  existieren, ihr Typ, Verbindungsstatus), synchronisiert mit dem echten
  Server auf dieselbe Weise wie jedes andere Panel hier - der Video-Feed
  selbst ist ein klar gekennzeichneter Platzhalter, entsprechend derselben
  Ehrlichkeitsgrenze wie das eigene CamerasView.tsx von HYDRA-UMC-STUDIO
  (es existiert noch keine echte Kamera-Hardware/kein echter Stream
  irgendwo in diesem Ökosystem).

---

## 📸 Fotos

Noch keine Screenshots - noch nicht für die Dokumentation erfasst. Starte
es (siehe unten), um das echte Ding zu sehen, anstatt hier später einem
veralteten Bild zu vertrauen.

---

## 📂 Repository-Struktur

```text
HYDRA-UMC-SUITE/
├── main.py                        # Einstiegspunkt - Vollbild mind. 1920x1080, F11 wechselt Vollbild/Fenstermodus
├── requirements.txt
├── HYDRA-UMC_SUITE.spec           # PyInstaller-Spec (siehe build_exe.bat/.sh weiter unten)
├── build_exe.bat                  # Windows-Build in einem Schritt -> dist/HYDRA-UMC_SUITE.exe
├── build_exe.sh                   # Linux-Build in einem Schritt -> dist/HYDRA-UMC_SUITE
├── README.md                      # diese Datei
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  <- Uebersetzungen
├── hydra_suite/
│   ├── models.py                   # HydraState/ControllerView/RobotView - schlanke, mutationsfreundliche Views ueber die reale settings.json-Form
│   ├── app.py                      # SuiteController - besitzt den Schwarm an Verbindungen, die "aktive" Auswahl, jedes Panel spricht mit diesem
│   ├── i18n.py                     # 5-Sprachen-Lader SCHLUESSEL=Wert (language/*.lng)
│   ├── net/
│   │   ├── discovery.py             # Gleichzeitiger Subnetz-Scan gegen GET /api/hydra-info
│   │   └── client.py                # REST- + WebSocket-Verbindung pro Server, live bidirektionale Synchronisierung, Login
│   ├── render/
│   │   ├── kinematics.py            # Vorwaertskinematik (portiert aus dem eigenen urKinematicsShared.ts von HYDRA-UMC-STUDIO)
│   │   ├── generic_rig.py           # Aus Primitiven gebautes Fallback-Rig fuer jedes Modell ohne eigenen Mesh-Satz
│   │   ├── mesh.py                  # STL-Laden (numpy-stl)
│   │   └── viewport.py              # QOpenGLWidget - echte GLSL-Shader-Pipeline, Orbit-Kamera
│   └── ui/
│       ├── main_window.py           # QMainWindow + QDockWidget-Arbeitsbereich
│       ├── theme.py                  # Laedt assets/qss/industrial_dark.qss
│       ├── widgets/rotary_knob.py    # Individuell gezeichneter Drehregler (Desktop-Gegenstueck zu RotaryKnob.tsx)
│       └── panels/                   # server_browser.py, overview.py, robot_control.py, viewport_panel.py, trajectory_panel.py, cameras_panel.py
├── assets/
│   ├── qss/industrial_dark.qss     # Das "futuristisch-industrielle" Qt-Stylesheet
│   └── meshes/                      # Echte STL-Meshes, ein Ordner pro Roboter (24 Modelle), kopiert vom eigenen public/models/<robot>/ von HYDRA-UMC-STUDIO (jeweils mit eigener ATTRIBUTION.txt)
├── language/                        # Englische/spanische/italienische/franzoesische/deutsche .lng-Dateien
├── docs/
│   └── ROADMAP.md                   # Ehrliche Erklaerung zum Ist-vs-Noch-nicht-Umfang
├── tests/                           # Manuelle Integrations-Smoke-Tests (benoetigen einen echten laufenden HYDRA-UMC-STUDIO-Server - keine gemockte Unit-Suite) + Kinematik-Verifizierungsskripte
└── .vscode/                         # Python-Interpreter-Pfad, Start-Konfigurationen, empfohlene Erweiterungen
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

Dieses Projekt ist Teil eines größeren Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage tatsächlich eines dieser Projekte betreffen könnte statt dieses Repository:

**HYDRA-UMC-Plattform** — die Multi-Roboter-Mikrofabrikzelle
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — die Hauptplatine selbst: Raspberry-Pi-CM5-Host + Dual-Core-STM32H745-Echtzeit-Coprozessor, der bis zu 8 verteilte Roboterarme über CAN-OTA/SPI-OTA orchestriert. Eigene Hardware + Firmware, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — webbasiertes Steuerungs-Dashboard für HYDRA-UMC: Multi-Roboter-3D-Visualisierung, Kinematik-/Trajektorienaufzeichnung, CAN-OTA-Flashing und -Tests für die gesamte Plattform. React + Vite + Three.js.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das Headless-Backend (Node/Express/WebSocket), das früher im eigenen Prozess von HYDRA-UMC-STUDIO gebündelt war. Es besitzt die REST/WS-API zur Robotersteuerung, die settings.json-Persistenz, die JWT-Authentifizierung und die mDNS-Erkennung. HYDRA-UMC-STUDIO ist jetzt ein reiner statischer Frontend-Client, der über das Netzwerk mit ihm kommuniziert.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android-Steuerungs-App für HYDRA-UMC über Wi-Fi/Bluetooth. Echte, funktionierende App - vollständiger Funktionsumfang für Fernsteuerung, JWT-Authentifizierung, verschlüsselte Speicherung der Zugangsdaten.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App für HYDRA-UMC über Wi-Fi, gebaut in Flutter (plattformübergreifend, unter Windows ohne Mac überprüfbar; die endgültige `.ipa`-Paketierung benötigt dennoch Xcode). Echte, funktionierende App - gleicher Funktionsumfang wie die Android-App.
- **HYDRA-UMC-SUITE** *(dieses Repository)* — Desktop-Schwarmkommandozentrale (Python/PySide6): Multi-Controller-Netzwerkerkennung, live bidirektionale Synchronisierung, echtes 3D-Roboter-Viewport, andockbarer Arbeitsbereich im Photoshop-Stil. Echt und funktionierend, kein Platzhalter.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor (Python/PySide6) für den eigenen Modellkatalog dieses Projekts: zieht Quelldateien von GitHub oder einem lokalen Ordner, validiert die Machbarkeit der Freiheitsgrade, bearbeitet Farbe/Skalierung/Kinematik mit einer Live-3D-Vorschau und überträgt das fertige Ergebnis an einen laufenden STUDIO-Server. Echt und funktionierend, kein Platzhalter.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Flutter-Touch-UI für HYDRA-UMCs eigenen 5"/7"-DSI-Touchscreen (1280×720, gleiche Auflösung bei beiden Größen) am Compute Module 5, die denselben Server direkt von der Platine aus steuert. Echtes, funktionierendes Grundgerüst mit allen 6 Katalogbildschirmen (Dashboard, manuelle Steuerung, Kamera, vereinfachte 3D-Ansicht, Systemmetriken, Login), angebunden an den Live-Server; der echte Linux-Build wurde bisher noch nicht auf echter Hardware ausgeführt (bislang nur Windows-Arbeitsumgebung - siehe das eigene README dieses Projekts).

**URTC-Plattform** — der Werkzeugkopf-Controller, den jeder HYDRA-UMC-Roboterarm trägt
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: STM32F303-basierter CAN-Bus-Werkzeugkopf-Controller, 25 vollständig implementierte Werkzeugprofile, CAN-OTA-Firmware-Update.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-Tool für CAN-OTA- + Full-Chip-SWD/JTAG-Flashing für URTC-Boards (Windows/Linux).
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Tool zur Live-CAN-Bus-Diagnose für URTC-Boards, ein Panel pro Werkzeugprofil (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu den 2 oben genannten Desktop-Tools (Web Serial API + SLCAN), keine lokale Installation nötig.

**Direkt verwandte Werkzeuge**
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — ermöglicht es, den digitalen Zwilling von dieser Suite aus so zu steuern, als wäre er echte Hardware, indem ein live laufender HYDRA-UMC-Controller durch eine Hardware-in-the-Loop-Brücke ersetzt wird, ohne sonst etwas am Arbeitsablauf zu ändern.
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — die Schwarm-Kommandozentrale, der diese Suite letztlich untergeordnet ist und die Flotten von HYDRA-UMC-Controllern auf einer Ebene oberhalb dessen koordiniert, was eine einzelne Desktop-Sitzung erreichen kann.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — bietet denselben DevOps-Funktionsumfang wie diese Desktop-Suite von der Kommandozeile aus, gedacht für Scripting und Umgebungen ohne grafische Oberfläche.

**Der Rest des Ökosystems**

Über die HYDRA-UMC- und URTC-Plattformen oben hinaus pflegt derselbe Autor viele weitere Projekte in den folgenden Bereichen:

- 👁️ **Vision AI Node (Hailo-8):** [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE) · [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER) · [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF) · [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES) · [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)
- 🧠 **Cognitive AI Node (Hailo-10):** [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) · [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE) · [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI) · [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER) · [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)
- 🐝 **Orchestrierung & Schwarm:** [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC) · [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D) · [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER) · [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)
- 🎮 **Digitaler Zwilling & Simulation:** [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN) · [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA) · [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)
- 📊 **Daten & Analytik:** [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE) · [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR) · [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR) · [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)
- 🏭 **Industrielles Gateway:** [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL) · [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER) · [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER) · [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)
- 🛠️ **Ergänzende Werkzeuge:** [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) · [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) · [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH) · [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 Autor

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 youtube.com/@electrohobby3d

---

## 📜 Lizenz- und Urheberrechtshinweise

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

## 🛠️ BUILD & RUN

Verwenden Sie den Build-Check ohne Versionierung vor einem Release-Build:

| Aktion | Windows | Linux / macOS |
|---|---|---|
| Build-Check (ohne Änderung von Version oder CHANGELOG) | `build-test.bat` | `./build-test.sh` |
| Ausführung / Entwicklung (falls vorhanden) | `run*.bat` oder `dev*.bat` | `./run*.sh` oder `./dev*.sh` |

`build-test.bat` und `build-test.sh` kompilieren oder validieren den Projekt-Stack, ohne `hydra-umc.project.json` zu erhöhen oder `CHANGELOG.md` zu verändern. Sie dürfen nur normale Compiler-Ausgaben erzeugen. Die vorhandenen Skripte `build*.bat`, `build*.sh`, `run*` und `dev*` behalten ihr projektbezogenes Versions- oder Laufzeitverhalten bei; verwenden Sie sie, wenn dieses Verhalten benötigt wird.